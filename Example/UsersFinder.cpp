void ProcessEntityRange(Memory& mem, int64_t base_entity_ai_part_3, int32_t start, int32_t end, const std::string& filename) {
    std::vector<Point> points; // локальный вектор дл€ хранени€ точек

    for (int i = start; i < end; ++i) {
        int64_t player_info_road_1 = mem.Read<int64_t>(base_entity_ai_part_3 + 0x0 + 0x08 * i);
        int64_t counter_subgroup_01 = mem.Read<int64_t>(player_info_road_1 + 0x68);
        int32_t counter_subgroup_01_subs = mem.Read<int32_t>(player_info_road_1 + 0x70);

        for (int g = 0; g < counter_subgroup_01_subs; ++g) {
            int64_t counter_subgroup_02 = mem.Read<int64_t>(counter_subgroup_01 + 0x08 * g);
            int32_t counter_subgroup = mem.Read<int32_t>(counter_subgroup_02 + 0x70);

            if (counter_subgroup > 0) {
                for (int k = 0; k < counter_subgroup; ++k) {
                    int64_t sub_player_in = mem.Read<int64_t>(counter_subgroup_02 + 0x68);
                    int64_t sub_player_in1 = mem.Read<int64_t>(sub_player_in + 0x08 * k);
                    int64_t sub_player_in2 = mem.Read<int64_t>(sub_player_in1 + 0xC8);
                    int64_t sub_player_in3 = mem.Read<int64_t>(sub_player_in2 + 0x8);
                    int64_t sub_player_in4 = mem.Read<int64_t>(sub_player_in3 + 0xD0);

                    int64_t sub_player_inX = mem.Read<int64_t>(sub_player_in4 + 0x2C);
                    int64_t sub_player_inY = mem.Read<int64_t>(sub_player_in4 + 0x34);
                    int64_t sub_player_view_x = mem.Read<int64_t>(sub_player_in4 + 0x08);
                    int64_t sub_player_view_y = mem.Read<int64_t>(sub_player_in4 + 0x10);
                    int64_t sub_player_view_z = mem.Read<int64_t>(sub_player_in4 + 0x20);
                    int32_t sub_player_Network_id = mem.Read<int32_t>(sub_player_in3 + 0xB2C);

                    // „тение имени транспорта
                    int64_t sub_player_Transport_road_0 = mem.Read<int64_t>(sub_player_in1 + 0xD0);
                    int64_t sub_player_Transport_road_1 = mem.Read<int64_t>(sub_player_Transport_road_0 + 0x8);
                    int64_t sub_player_Transport_road_2 = mem.Read<int64_t>(sub_player_Transport_road_1 + 0x150);
                    int64_t sub_player_Transport_road_3 = mem.Read<int64_t>(sub_player_Transport_road_2 + 0x13C8);
                    int64_t sub_player_Transport_Display_Name_Array = mem.Read<int64_t>(sub_player_Transport_road_3 + 0x8);
                    std::string Player_Transport_Name;
                    for (int array = 0; array < sub_player_Transport_Display_Name_Array - 1; array++) {
                        char sub_player_Transport_Display_Name = mem.Read<char>(sub_player_Transport_road_3 + 0x10 + array);
                        Player_Transport_Name.push_back(sub_player_Transport_Display_Name);
                    }

                    float sub_finalX = *reinterpret_cast<float*>(&sub_player_inX);
                    float sub_finalY = *reinterpret_cast<float*>(&sub_player_inY);
                    float sub_finalview_x = *reinterpret_cast<float*>(&sub_player_view_x);
                    float sub_finalview_y = *reinterpret_cast<float*>(&sub_player_view_y);
                    float sub_finalview_z = *reinterpret_cast<float*>(&sub_player_view_z);

                    if (sub_finalX >= MIN_COORD_VALUE && sub_finalY >= MIN_COORD_VALUE &&
                        !IsScientificNotation(sub_finalX) && !IsScientificNotation(sub_finalY)) {
                        points.emplace_back(Point{ sub_finalX, sub_finalY, sub_finalview_x, sub_finalview_y, sub_finalview_z,
                                                    sub_player_Network_id, std::move(Player_Transport_Name), 0 });
                    }
                }
            }
        }
    }

    // «аписываем данные из локального вектора в файл
    WriteCoordsToJson(filename, points);
}