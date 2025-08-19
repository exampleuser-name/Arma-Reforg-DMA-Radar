#include <iostream>
#include <DMALibrary/Memory/Memory.h>
#include <thread>
#include <chrono>
#include <iomanip>
#include <fstream>
#include <string>
#include <vector>
#include <cmath>
#include <cstdint>
#include <atomic>
#include <mutex>
#include <sstream>
#include <algorithm>
#include <utility>

//   
constexpr int MAX_THREADS = 6;
constexpr int ENTITY_TYPES = 4;
constexpr int READ_DELAY_MS = 1;
constexpr float MIN_COORD_VALUE = 10.0f;
const std::string OUTPUT_PATH = "C:\\ArmRF\\";

struct Point {
    float x;
    float y;
    float view_x;
    float view_y;
    float view_z;
    int32_t network_id;
    std::string transport;
    std::string type;
};

struct Inpoint {
    int64_t address;
};

struct PredSoilder {
    int64_t address;
};

struct Soilder {
    int64_t address;
};

struct TransportSoilder {
    int64_t address;
};

struct Faction {
    int64_t address;
};

struct Health {
    int64_t address;
};

const DWORD local_pl[] = { 0x21C8850, 0x2C68, 0x08, 0xD0 };
const DWORD Network[] = { 0x2181628, 0x48, 0x38, 0x40 };

//     
std::mutex file_mutex;

//     
std::string numberToByteString(int64_t number) {
    const uint8_t* bytes = reinterpret_cast<const uint8_t*>(&number);
    std::string result;
    result.reserve(sizeof(int64_t));

    for (size_t i = 0; i < sizeof(int64_t); ++i) {
        if (bytes[i] >= 32 && bytes[i] <= 126) {
            result.push_back(static_cast<char>(bytes[i]));
        }
    }
    return result;
}

inline bool IsScientificNotation(float value) {
    return std::fabs(value) > 1e10f;
}

std::string escapeJson(const std::string& str) {
    std::string escaped;
    escaped.reserve(str.size() * 1.1); 

    for (char c : str) {
        switch (c) {
        case '\"': escaped += "\\\""; break;
        case '\\': escaped += "\\\\"; break;
        case '/':  escaped += "\\/";  break;
        case '\b': escaped += "\\b";  break;
        case '\f': escaped += "\\f";  break;
        case '\n': escaped += "\\n";  break;
        case '\r': escaped += "\\r";  break;
        case '\t': escaped += "\\t";  break;
        default:   escaped += c;      break;
        }
    }
    return escaped;
}

void WriteCoordsToJson(const std::string& path, const std::vector<Point>& points) {
    std::lock_guard<std::mutex> lock(file_mutex);
    std::ofstream outFile(path);
    if (!outFile.is_open()) {
        std::cerr << "Failed to open file for writing: " << path << std::endl;
        return;
    }


    std::stringstream ss;
    ss << "{\n\"points\": [\n";

    for (size_t i = 0; i < points.size(); ++i) {
        const auto& p = points[i];
        ss << "    {\"x\": " << p.x
            << ", \"y\": " << p.y
            << ", \"view_x\": " << p.view_x
            << ", \"view_y\": " << p.view_y
            << ", \"view_z\": " << p.view_z
            << ", \"network_id\": \"" << p.network_id
            << "\", \"transport\": \"" << escapeJson(p.transport)
            << "\", \"type\": \"" << escapeJson(p.type) << "\"}";

        if (i < points.size() - 1) ss << ",";
        ss << "\n";
    }

    ss << "]}\n";
    outFile << ss.str();
    outFile.close();
}



void WriteInpoint(const std::string& path, const std::vector<Inpoint>& inpoint) {
    std::lock_guard<std::mutex> lock(file_mutex);
    std::ofstream outFile(path);
    if (!outFile.is_open()) {
        std::cerr << "Failed to open file for writing: " << path << std::endl;
        return;
    }


    std::stringstream ss;
    ss << "{\n\"points\": [\n";

    for (size_t i = 0; i < inpoint.size(); ++i) {
        const auto& inp = inpoint[i];
        ss << "    {\"x\": " << inp.address << "}";

        if (i < inpoint.size() - 1) ss << ",";
        ss << "\n";
    }

    ss << "]}\n";
    outFile << ss.str();
    outFile.close();
}

void WriteNetworkClientsToJson(const std::string& path, const std::vector<std::pair<int32_t, std::string>>& players) {
    std::lock_guard<std::mutex> lock(file_mutex);
    std::ofstream outFile(path);
    if (!outFile.is_open()) {
        std::cerr << "Failed to open file for writing: " << path << std::endl;
        return;
    }

    std::stringstream ss;
    ss << "{\n\"network_players\": [\n";

    for (size_t i = 0; i < players.size(); ++i) {
        ss << "    {\"identity\": " << players[i].first
            << ", \"name\": \"" << escapeJson(players[i].second) << "\"}";

        if (i < players.size() - 1) ss << ",";
        ss << "\n";
    }

    ss << "]}\n";
    outFile << ss.str();
    outFile.close();
}



void WriteLocalPlayerToJson(const std::string& path, const Point& point) {
    std::lock_guard<std::mutex> lock(file_mutex);
    std::ofstream outFile(path);
    if (!outFile.is_open()) {
        std::cerr << "Failed to open file for writing: " << path << std::endl;
        return;
    }

    std::stringstream ss;
    ss << "{\n\"local_player\": {\n"
        << "    \"x\": " << point.x << ",\n"
        << "    \"y\": " << point.y << ",\n"
        << "    \"view_x\": " << point.view_x << ",\n"
        << "    \"view_y\": " << point.view_y << ",\n"
        << "    \"view_z\": " << point.view_z << ",\n"
        << "    \"network_id\": \"" << point.network_id << "\",\n"
        << "    \"type\": " << point.type << ",\n"
        << "    \"transport\": \"" << escapeJson(point.transport) << "\"\n"
        << "}}\n";

    outFile << ss.str();
    outFile.close();
}

void GetLocalPlayer(Memory& mem, uintptr_t Chimera_Game, const DWORD local_pl[]) {

    
    int64_t World = mem.Read<int64_t>(Chimera_Game +0x130);
    int64_t LocalPlayer_0 = mem.Read<int64_t>(World + 0x378);
    int64_t LocalPlayer_1 = mem.Read<int64_t>(LocalPlayer_0 + 0x8);
    int64_t LocalPlayer_X = mem.Read<int64_t>(LocalPlayer_1 +0x58);
    int64_t LocalPlayer_Y = mem.Read<int64_t>(LocalPlayer_1 +0x60);
    int64_t LocalPlayer_View_X = mem.Read<int64_t>(LocalPlayer_1 + 0x78);
    int64_t LocalPlayer_View_Y = mem.Read<int64_t>(LocalPlayer_1 + 0x70);
    float local_final_x = *reinterpret_cast<float*>(&LocalPlayer_X);
    float local_final_y = *reinterpret_cast<float*>(&LocalPlayer_Y);
    float sub_finalview_x = *reinterpret_cast<float*>(&LocalPlayer_View_X);
    float sub_finalview_y = *reinterpret_cast<float*>(&LocalPlayer_View_Y);
    if (local_final_x >= MIN_COORD_VALUE && local_final_y >= MIN_COORD_VALUE &&
        !IsScientificNotation(local_final_x) && !IsScientificNotation(local_final_y)) {
        Point localPlayer = Point{ local_final_x, local_final_y, sub_finalview_y, sub_finalview_x,1, 1337, "BEBRAEDINA", "1" };
        WriteLocalPlayerToJson(OUTPUT_PATH + "local_player.json", localPlayer);
    }
}

std::vector<Inpoint> inpoint;
std::vector<Soilder> soilder;
std::vector<TransportSoilder> transportsoilders;
std::vector<PredSoilder> predsoilder;
std::vector<Faction> faction;
std::vector<Health> health;



void Optimization(Memory& mem, uintptr_t base) {
    auto start_time = std::chrono::steady_clock::now();
    std::vector<Point> points;
    points.reserve(1000);

    int sizeAddress = inpoint.size();
    float Entity_X, Entity_Y, sub_player_inX, sub_player_inY;
    float view_x, view_y;
    float HP;
    int32_t isPlayer;

    for (int i = 0; i < sizeAddress; i++) {
        auto handle = mem.CreateScatterHandle();
        int64_t countVector = inpoint[i].address;
        int64_t countName = soilder[i].address;
        int64_t Health = health[i].address;
        int64_t Faction_String = faction[i].address;
        char Name[50];
        char Faction[50];
        std::string factionStr(Faction);


        mem.AddScatterReadRequest(handle, countVector + 0x58, &sub_player_inX, sizeof(float));
        mem.AddScatterReadRequest(handle, countVector + 0x60, &sub_player_inY, sizeof(float));
        mem.AddScatterReadRequest(handle, countVector + 0x70, &view_x, sizeof(float)); // 0x70
        mem.AddScatterReadRequest(handle, countVector + 0x78, &view_y, sizeof(float)); // 0x78
        mem.AddScatterReadRequest(handle, countName + 0x0, &Name, sizeof(Name));
        mem.AddScatterReadRequest(handle, Health + 0x44, &HP, sizeof(float));
        mem.AddScatterReadRequest(handle, Faction_String + 0x0, &Faction, sizeof(Faction));
        mem.AddScatterReadRequest(handle, Faction_String + 0x0, &Faction, sizeof(Faction));
        mem.ExecuteReadScatter(handle);
        
        if (HP == 0) {
            if (std::isfinite(sub_player_inX) && std::isfinite(sub_player_inY) &&
                sub_player_inX >= MIN_COORD_VALUE && sub_player_inY >= MIN_COORD_VALUE) {
                points.emplace_back(Point{ sub_player_inX, sub_player_inY, view_x, view_y, 1, 1, Name, "Dead" });
            }
        }
        else {
            if (std::isfinite(sub_player_inX) && std::isfinite(sub_player_inY) &&
                sub_player_inX >= MIN_COORD_VALUE && sub_player_inY >= MIN_COORD_VALUE) {
                points.emplace_back(Point{ sub_player_inX, sub_player_inY, view_x, view_y, 1, 1, Name, Faction });
            }
        
        }
        mem.CloseScatterHandle(handle);
    }
    std::string filename = OUTPUT_PATH + "coords" + std::to_string(0) + ".json";
    WriteCoordsToJson(filename, points);
    auto end_time = std::chrono::steady_clock::now();
    auto duration_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count();
}

int countoptimaize = 0;
void ProcessEntities_road(Memory& mem, uintptr_t base,int64_t Chimera_Game) {
    auto handle = mem.CreateScatterHandle();
    float sub_player_inX, sub_player_inY;
    float sub_player_view_x, sub_player_view_y, sub_player_view_z;
    int32_t sub_player_Network_id;
    byte isDead;
    int32_t counter_subgroup_01_subs;
    int64_t counter_subgroup_01;
    std::vector<Point> points;
    points.reserve(1000);
    int64_t Chimera_PlayerManager = mem.Read<int64_t>(Chimera_Game + 0x2C8);
    int64_t Chimera_Player_List = mem.Read<int64_t>(Chimera_PlayerManager + 0x18);
    int32_t Chimera_Player_List_Array = mem.Read<int32_t>(Chimera_PlayerManager + 0x24);

    for (int i = 0; i < Chimera_Player_List_Array; ++i) {
        int64_t Entity_In = mem.Read<int64_t>(Chimera_Player_List + 0x0 + 0x08 * i);
        int64_t Player_Name = mem.Read<int64_t>(Entity_In + 0x18);
        int64_t Entity_Checking0 = mem.Read<int64_t>(Entity_In +0x48);
        int64_t Entity_Checking1 = mem.Read<int64_t>(Entity_Checking0 +0x8);
        int64_t HP1 = mem.Read<int64_t>(Entity_Checking1 +0x138);
        int64_t HP2 = mem.Read<int64_t>(HP1 +0xC8);
        int64_t Faction0 = mem.Read<int64_t>(Entity_Checking1 + 0x178);
        int64_t Faction1 = mem.Read<int64_t>(Faction0 + 0x8);
        int64_t Faction2 = mem.Read<int64_t>(Faction1 + 0x68);
        inpoint.emplace_back(Inpoint{ Entity_Checking1 });
        soilder.emplace_back(Soilder{ Player_Name });
        faction.emplace_back(Faction{ Faction2 });
        health.emplace_back(Health{ HP2 });
    }
    countoptimaize++;
}



int main() {
    setlocale(LC_ALL, "Russian");
    Memory mem;
    if (!mem.Init("ArmaReforgerSteam.exe", true, true)) {
        std::cerr << "Failed to initialize DMA" << std::endl;
        return 1;
    }

    std::cout << "DMA initialized" << std::endl;

    if (!mem.FixCr3()) {
        std::cerr << "Failed to fix CR3" << std::endl;
        return 1;
    }

    std::cout << "CR3 fixed" << std::endl;

    uintptr_t base = mem.GetBaseDaddy("ArmaReforgerSteam.exe");
    if (base == 0) {
        std::cerr << "Failed to get base address" << std::endl;
        return 1;
    }

    int64_t Chimera_Game = mem.Read<int64_t>(base + 0x1D59488);


    std::atomic<bool> running = true;

    std::thread localPlayerThread([&]() {
        while (running) {
            GetLocalPlayer(mem, Chimera_Game, local_pl);
            std::this_thread::sleep_for(std::chrono::milliseconds(READ_DELAY_MS));
        }
       });


    std::thread ProcessEntitiesThread([&]() {
        while (running) {
            inpoint.clear();
            soilder.clear();
            faction.clear();
            health.clear();
            

            ProcessEntities_road(mem, base, Chimera_Game);
            std::this_thread::sleep_for(std::chrono::seconds(5));
        }
        });


     std::thread OptimazeMethod([&]() {
        while (running) {
            Optimization(mem, base);
            std::this_thread::sleep_for(std::chrono::milliseconds(READ_DELAY_MS));

        }
        });
    

    std::cout << "Press Enter to stop..." << std::endl;
    std::cin.get();


    running = false;

    // Join threads before exiting
    //localPlayerThread.detach();
    //networkClientsThread.detach();
    //GetTransortPlayerThread.detach();
    //ProcessEntitiesThread.detach();

    return 0;
}