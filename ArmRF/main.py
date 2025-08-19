import sys
import json
import os
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, \
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem, QPushButton, QVBoxLayout, QWidget, QCheckBox, QHBoxLayout
from PyQt5.QtGui import QPixmap, QColor, QFont, QPen
from PyQt5.QtCore import Qt, QTimer

class ImageViewer(QGraphicsView):
    def __init__(self, image_path, json_directory):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.show_names = True
        self.show_transport = True
        self.enabled_types = {0, 1, 2, 3}
        self.pixmap_item = QGraphicsPixmapItem(QPixmap(image_path))
        self.scene().addItem(self.pixmap_item)
        self.json_directory = json_directory
        pixmap = self.pixmap_item.pixmap()
        self.setSceneRect(-pixmap.width(), -pixmap.height(), 3 * pixmap.width(), 3 * pixmap.height())
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_points_from_json)
        self.timer.start(20)
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.timeout.connect(self.cleanup_resources)
        self.cleanup_timer.start(9999999)
        self.scale_x = 2.0
        self.scale_y = 2.0
        self.dot_size = 50
        self.text_size = 50
        self.total_points = 0
        self.points_text_item = QGraphicsTextItem()
        self.points_text_item.setFont(QFont("Arial", 16))
        self.scene().addItem(self.points_text_item)
        self.name_text_items = []
        self.transport_text_items = []
        self.is_dragging = False
        self.last_mouse_position = None
        self.x_axis = None
        self.y_axis = None
        self.x_label = None
        self.y_label = None
        self.map_width = 31000
        self.map_height = 31000
        self.current_map = 'altis'
        self.load_map_sizes()
        self.load_points_from_json()

        self.follow_mode = False
        self.local_player_pos = None  # (x, y)
        self.follow_timer = QTimer(self)
        self.follow_timer.timeout.connect(self.follow_player)

    def set_enabled_types(self, types):
        self.enabled_types = types
        self.load_points_from_json()

    def toggle_names(self):
        self.show_names = not self.show_names
        self.update_names_visibility()

    def load_transport_data(self):
        transport = {}
        try:
            with open(os.path.join(self.json_directory, 'transport_players.json'), 'r', encoding='utf-8') as file:
                transport_data = json.load(file)
                for transport_item in transport_data.get('network_players', []):
                    transport[str(transport_item['identity'])] = transport_item['name']
        except Exception as e:
            print(f"Error loading transport data: {e}")
        return transport

    def load_map_sizes(self):
        filename = ''
        if hasattr(self, 'current_map'):
            if self.current_map == 'arland':
                filename = os.path.join(self.json_directory, 'map_sizes_arland.json')
            elif self.current_map == '****':
                filename = os.path.join(self.json_directory, '****.json')
            else:
                filename = os.path.join(self.json_directory, 'map_sizes_everon.json')
        else:
            filename = os.path.join(self.json_directory, 'map_sizes_everon.json')
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.map_width = int(data.get('x', 31000))
                self.map_height = int(data.get('y', 31000))
        except Exception as e:
            print(f"Error loading map sizes from {filename}: {e}")
            self.map_width = 31000
            self.map_height = 31000

    def load_points_from_json(self):
        self.clear_scene_items()
        self.total_points = 0
        self.name_text_items.clear()
        self.transport_text_items.clear()
        transport_data = self.load_transport_data()
        self.load_map_sizes()
        for json_file in os.listdir(self.json_directory):
            if json_file.endswith('.json') and json_file != 'local_player.json' and json_file not in (
                    'map_sizes_arland.json', 'map_sizes_everon.json'):
                try:
                    filename_without_ext = os.path.splitext(json_file)[0]
                    number_str = filename_without_ext.split('coords')[-1]
                    number = int(number_str)
                    if number in self.enabled_types:
                        self.load_points_from_file(os.path.join(self.json_directory, json_file), number, transport_data)
                except (IndexError, ValueError):
                    continue
        self.load_local_player()
        self.update_points_text()
        self.draw_axes()
        self.update_names_visibility()
        self.update_transport_visibility()

    def load_points_from_file(self, file_path, number, transport_data):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                data = json.load(file)
            if not isinstance(data, dict) or "points" not in data:
                print(f"Invalid format in {file_path}: missing 'points'")
                return
            players_data = self.load_network_players()
            pixmap = self.pixmap_item.pixmap()
            self.scale_x = pixmap.width() / self.map_width
            self.scale_y = pixmap.height() / self.map_height
            valid_points = 0
            for point in data['points']:
                try:
                    x = float(point.get('x'))
                    y = float(point.get('y'))
                except (TypeError, ValueError, KeyError):
                    print(f"Invalid coordinates in {file_path}: {point}")
                    continue
                x_scaled = x * self.scale_x
                y_scaled = pixmap.height() - (y * self.scale_y)
                if not (0 <= x_scaled <= pixmap.width() and 0 <= y_scaled <= pixmap.height()):
                    print(f"Point out of bounds: ({x}, {y}) scaled to ({x_scaled}, {y_scaled})")
                    continue
                color = self.get_color_by_type_or_string(point.get('type', 1))
                self.add_dot(x_scaled, y_scaled, color)
                valid_points += 1
                network_id = point.get('network_id')
                if network_id and str(network_id) in players_data:
                    player_name = players_data[str(network_id)]
                    self.add_name_text(x_scaled, y_scaled, player_name)
                transport = point.get('transport')
                if transport and self.show_transport:
                    self.add_transport_text(x_scaled, y_scaled, transport)
                if all(k in point for k in ['view_x', 'view_y', 'view_z']):
                    self.draw_view_line(x_scaled, y_scaled, point['view_x'], point['view_y'], point['view_z'])
            self.total_points += valid_points
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")

    def load_local_player(self):
        local_player_file = os.path.join(self.json_directory, 'local_player.json')
        if os.path.exists(local_player_file):
            try:
                with open(local_player_file, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if "local_player" in data:
                        self.render_local_player(data["local_player"])
            except Exception as e:
                print(f"Error loading local player data: {e}")
                
    def render_local_player(self, player_info):
        pixmap = self.pixmap_item.pixmap()
        self.scale_x = pixmap.width() / self.map_width
        self.scale_y = pixmap.height() / self.map_height
        x = player_info.get('x')
        y = player_info.get('y')
        if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
            return
        if abs(x) < 1e-10 or abs(x) > 1e10 or abs(y) < 1e-10 or abs(y) > 1e10:
            return
        x_scaled = x * self.scale_x
        y_scaled = pixmap.height() - (y * self.scale_y)
        self.local_player_pos = (x_scaled, y_scaled)

        color = QColor(255, 255, 0)  # желтый

        self.add_dot(x_scaled, y_scaled, color)

        view_x = player_info.get('view_x')
        view_y = player_info.get('view_y')
        view_z = player_info.get('view_z')
        if None not in (view_x, view_y, view_z):
            self.draw_view_line(x_scaled, y_scaled, view_x, view_y, view_z, is_local=True)
        if not self.follow_timer.isActive():
            self.follow_timer.start(50)

    def load_network_players(self):
        players = {}
        try:
            with open(os.path.join(self.json_directory, 'netplayer.json'), 'r', encoding='utf-8',
                      errors='replace') as file:
                player_data = json.load(file)
                for player in player_data['network_players']:
                    players[str(player['identity'])] = player['name']
        except Exception as e:
            print(f"Error loading network players: {e}")
        return players

    def get_color_by_type_or_string(self, point_type):
        if isinstance(point_type, str):
            if point_type.upper() == "BLUFOR" or point_type.upper() == "US":
                return QColor(0, 0, 255)  # синий
            elif point_type.upper() == "OPFOR" or point_type.upper() == "USSR":
                return QColor(255, 0, 0)  # красный
            elif point_type.upper() == "INDFOR":
                return QColor(0, 255, 0)  # зеленый
            else:
                return Qt.black
        else:
            color_map = {
                1337: QColor(255, 255, 0),
                0: QColor(153, 0, 0),
                1: QColor(0, 0, 153),
                2: QColor(0, 153, 0),
                3: QColor(153, 0, 153)
            }
            return color_map.get(point_type, Qt.black)

    def clear_scene_items(self):
        for item in self.scene().items():
            if item not in (self.pixmap_item, self.points_text_item):
                self.scene().removeItem(item)
        self.total_points = 0
        self.update_points_text()
        self.name_text_items.clear()
        self.transport_text_items.clear()

    def remove_axes(self):
        for axis in [self.x_axis, self.y_axis, self.x_label, self.y_label]:
            if axis and axis.scene():
                self.scene().removeItem(axis)
        self.x_axis = self.y_axis = self.x_label = self.y_label = None

    def draw_axes(self):
        pixmap = self.pixmap_item.pixmap()
        width, height = pixmap.width(), pixmap.height()
        center_x, center_y = width / 2, height / 2
        self.remove_axes()
        self.x_axis = self.scene().addLine(0, center_y, width, center_y, QPen(Qt.black, 2))
        self.y_axis = self.scene().addLine(center_x, 0, center_x, height, QPen(Qt.black, 2))
        font = QFont("Arial", 12)
        self.x_label = self.scene().addText("X", font)
        self.x_label.setPos(width - 30, center_y + 10)
        self.y_label = self.scene().addText("Y", font)
        self.y_label.setPos(center_x + 10, 10)

    def add_dot(self, x, y, color):
        dot = QGraphicsEllipseItem(-self.dot_size / 2, -self.dot_size / 2, self.dot_size, self.dot_size)
        dot.setBrush(color)
        dot.setPos(x, y)
        self.scene().addItem(dot)

    def add_name_text(self, x, y, name):
        if not self.show_names:
            return
        text_item = QGraphicsTextItem(name)
        text_item.setFont(QFont("Arial", self.text_size))
        transparent_color = QColor(0, 0, 0, 150)
        text_item.setDefaultTextColor(transparent_color)
        text_item.setPos(x + self.dot_size / 2 + 5, y - text_item.boundingRect().height() / 2)
        self.scene().addItem(text_item)
        self.name_text_items.append(text_item)

    def add_transport_text(self, x, y, transport):
        if not self.show_transport:
            return
        transport_item = QGraphicsTextItem(transport)
        transport_item.setFont(QFont("Arial", self.text_size - 2))
        transparent_color = QColor(0, 0, 0, 200)
        transport_item.setDefaultTextColor(transparent_color)
        transport_item.setPos(x + self.dot_size / 2 + 5, y + self.text_size + 2)
        self.scene().addItem(transport_item)
        self.transport_text_items.append(transport_item)

    def draw_view_line(self, x, y, view_x, view_y, view_z, is_local=False):
        length = 1110 if is_local else 20 #8000
        try:
            view_x = float(view_x)
            view_y = float(view_y)
            view_z = float(view_z)
        except (TypeError, ValueError):
            return
        magnitude = (view_x ** 2 + view_y ** 2) ** 0.5
        if magnitude < 0.001:
            return
        dir_x = view_x / magnitude
        dir_y = view_y / magnitude
        pixmap = self.pixmap_item.pixmap()
        width, height = pixmap.width(), pixmap.height()
        end_x = x - (length * dir_y)
        end_y = y - (length * dir_x)
        line = QGraphicsLineItem(x, y, end_x, end_y)
        pen = QPen(Qt.red if is_local else Qt.blue)
        if is_local:
            pen.setWidth(1)
        line.setPen(pen)
        self.scene().addItem(line)

    def cleanup_resources(self):
        self.clear_scene_items()
        self.total_points = 0
        self.update_points_text()

    def update_points_text(self):
        self.points_text_item.setPlainText(f"Total Points: {self.total_points}")
        self.points_text_item.setPos(10, 10)

    def wheelEvent(self, event):
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.scale(factor, factor)
        self.scale_x *= factor
        self.scale_y *= factor

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            self.dot_size = min(500, self.dot_size + 2)
            self.text_size = min(500, self.text_size + 2)
        elif event.key() == Qt.Key_Down:
            self.dot_size = max(2, self.dot_size - 2)
            self.text_size = max(2, self.text_size - 2)
        self.load_points_from_json()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.last_mouse_position = event.pos()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            delta = event.pos() - self.last_mouse_position
            self.last_mouse_position = event.pos()
            max_delta = 100
            dx = max(-max_delta, min(max_delta, delta.x()))
            dy = max(-max_delta, min(max_delta, delta.y()))
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False

    def update_names_visibility(self):
        for item in self.name_text_items:
            item.setVisible(self.show_names)

    def update_transport_visibility(self):
        for item in self.transport_text_items:
            item.setVisible(self.show_transport)

    def follow_player(self):
        if self.follow_mode and self.local_player_pos:
            x, y = self.local_player_pos
            self.centerOn(x, y)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_widget = QWidget()
    layout = QVBoxLayout()

    viewer = ImageViewer(
        image_path='C:\\ArmRF\\Everon.png',
        json_directory='C:\\ArmRF\\'
    )

    follow_button = QPushButton("Follow")
    def toggle_follow():
        viewer.follow_mode = not viewer.follow_mode
        if viewer.follow_mode:
            follow_button.setText("Follow (On)")
            viewer.follow_timer.start(50)
        else:
            follow_button.setText("Follow")
            viewer.follow_timer.stop()
    follow_button.clicked.connect(toggle_follow)

    #checkbox_red = QCheckBox("Red (coords0)")
    #checkbox_blue = QCheckBox("Blue (coords1)")
    #checkbox_green = QCheckBox("Green (coords2)")
    #checkbox_violet = QCheckBox("Violet (coords3)")
    checkbox_transport = QCheckBox("Show name")
    checkbox_transport.setChecked(True)
    #toggle_button = QPushButton("Показать/Скрыть ники")
    #for cb in [checkbox_red, checkbox_blue, checkbox_green, checkbox_violet]:
    #    cb.setChecked(True)

    btn_everon = QPushButton("Everon")
    btn_arland = QPushButton("Arland")

    def switch_to_everon():
        viewer.current_map = 'everon'
        viewer.load_map_sizes()
        new_pixmap = QPixmap('C:\\ArmRF\\Everon.png')
        viewer.pixmap_item.setPixmap(new_pixmap)
        pixmap = new_pixmap
        viewer.setSceneRect(-pixmap.width(), -pixmap.height(), 3 * pixmap.width(), 3 * pixmap.height())
        viewer.load_points_from_json()

    def switch_to_arland():
        viewer.current_map = 'arland'
        viewer.load_map_sizes()
        new_pixmap = QPixmap('C:\\ArmRF\\Arland.jpg')
        viewer.pixmap_item.setPixmap(new_pixmap)
        pixmap = new_pixmap
        viewer.setSceneRect(-pixmap.width(), -pixmap.height(), 3 * pixmap.width(), 3 * pixmap.height())
        viewer.load_points_from_json()

    def switch_to_empty():
        viewer.current_map = 'arland'
        viewer.load_map_sizes()
        new_pixmap = QPixmap('C:\\ArmRF\\empty.jpg')
        viewer.pixmap_item.setPixmap(new_pixmap)
        pixmap = new_pixmap
        viewer.setSceneRect(-pixmap.width(), -pixmap.height(), 3 * pixmap.width(), 3 * pixmap.height())
        viewer.load_points_from_json()

    btn_everon.clicked.connect(switch_to_everon)
    btn_arland.clicked.connect(switch_to_arland)
    #btn_empty.clicked.connect(switch_to_empty)

    #def update_filters():
    #    enabled = set()
    #    if checkbox_red.isChecked():
    #        enabled.add(0)
    #    if checkbox_blue.isChecked():
    #        enabled.add(1)
    #    if checkbox_green.isChecked():
    #        enabled.add(2)
    #    if checkbox_violet.isChecked():
    #        enabled.add(3)
    #    viewer.set_enabled_types(enabled)

    def toggle_transport():
        viewer.show_transport = checkbox_transport.isChecked()
        viewer.update_transport_visibility()

    def toggle_names():
        viewer.toggle_names()

   # checkbox_red.stateChanged.connect(update_filters)
    #checkbox_blue.stateChanged.connect(update_filters)
   # checkbox_green.stateChanged.connect(update_filters)
   # checkbox_violet.stateChanged.connect(update_filters)
    checkbox_transport.stateChanged.connect(toggle_transport)
   # toggle_button.clicked.connect(toggle_names)
    layout_follow = QHBoxLayout()
    layout_follow.addWidget(follow_button)

    controls_layout = QVBoxLayout()
   # for cb in [checkbox_red, checkbox_blue, checkbox_green, checkbox_violet]:
   #    controls_layout.addWidget(cb)
    controls_layout.addWidget(checkbox_transport)
   # controls_layout.addWidget(toggle_button)
    controls_layout.addWidget(btn_everon)
    controls_layout.addWidget(btn_arland)
    #controls_layout.addWidget(btn_altis_amazing)
    controls_layout.addLayout(layout_follow)

    main_layout = QHBoxLayout()
    main_layout.addLayout(controls_layout)
    main_layout.addWidget(viewer)
    main_widget.setLayout(main_layout)
    main_widget.setWindowTitle('Who')
    main_widget.resize(1000, 600)
    main_widget.show()

    sys.exit(app.exec_())