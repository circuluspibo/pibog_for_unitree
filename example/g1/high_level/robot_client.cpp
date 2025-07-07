#include <chrono>
#include <iostream>
#include <thread>
#include <sstream>
#include <map>
#include <vector>
#include <string>
#include <cstdlib>

#include <unitree/robot/g1/loco/g1_loco_api.hpp>
#include <unitree/robot/g1/loco/g1_loco_client.hpp>

// JSON-like response formatting
void printResponse(const std::string& status, const std::string& message = "", 
                   const std::string& data = "") {
    std::cout << "{\"status\":\"" << status << "\"";
    if (!message.empty()) {
        std::cout << ",\"message\":\"" << message << "\"";
    }
    if (!data.empty()) {
        std::cout << ",\"data\":" << data;
    }
    std::cout << "}" << std::endl;
}

void printError(const std::string& message) {
    std::cerr << "{\"status\":\"error\",\"message\":\"" << message << "\"}" << std::endl;
}

std::vector<float> stringToFloatVector(const std::string &str) {
    std::vector<float> result;
    std::stringstream ss(str);
    float num;
    while (ss >> num) {
        result.push_back(num);
        ss.ignore();
    }
    return result;
}

std::string floatVectorToString(const std::vector<float>& vec) {
    std::stringstream ss;
    ss << "[";
    for (size_t i = 0; i < vec.size(); ++i) {
        if (i > 0) ss << ",";
        ss << vec[i];
    }
    ss << "]";
    return ss.str();
}

int main(int argc, char const *argv[]) {
    try {
        std::map<std::string, std::string> args = {{"network_interface", "lo"}};

        // Parse command line arguments
        std::map<std::string, std::string> values;
        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg.substr(0, 2) == "--") {
                size_t pos = arg.find("=");
                std::string key, value;
                if (pos != std::string::npos) {
                    key = arg.substr(2, pos - 2);
                    value = arg.substr(pos + 1);

                    if (value.front() == '"' && value.back() == '"') {
                        value = value.substr(1, value.length() - 2);
                    }
                } else {
                    key = arg.substr(2);
                    value = "";
                }
                if (args.find(key) != args.end()) {
                    args[key] = value;
                } else {
                    args.insert({{key, value}});
                }
            }
        }

        // Initialize robot connection
        unitree::robot::ChannelFactory::Instance()->Init(0, args["network_interface"]);
        unitree::robot::g1::LocoClient client;
        client.Init();
        client.SetTimeout(10.f);

        // Process commands
        for (const auto &arg_pair : args) {
            if (arg_pair.first == "network_interface") {
                continue;
            }

            try {
                if (arg_pair.first == "get_fsm_id") {
                    int fsm_id;
                    client.GetFsmId(fsm_id);
                    printResponse("success", "FSM ID retrieved", std::to_string(fsm_id));
                }

                else if (arg_pair.first == "get_fsm_mode") {
                    int fsm_mode;
                    client.GetFsmMode(fsm_mode);
                    printResponse("success", "FSM mode retrieved", std::to_string(fsm_mode));
                }

                else if (arg_pair.first == "get_balance_mode") {
                    int balance_mode;
                    client.GetBalanceMode(balance_mode);
                    printResponse("success", "Balance mode retrieved", std::to_string(balance_mode));
                }

                else if (arg_pair.first == "get_swing_height") {
                    float swing_height;
                    client.GetSwingHeight(swing_height);
                    printResponse("success", "Swing height retrieved", std::to_string(swing_height));
                }

                else if (arg_pair.first == "get_stand_height") {
                    float stand_height;
                    client.GetStandHeight(stand_height);
                    printResponse("success", "Stand height retrieved", std::to_string(stand_height));
                }

                else if (arg_pair.first == "get_phase") {
                    std::vector<float> phase;
                    client.GetPhase(phase);
                    printResponse("success", "Phase retrieved", floatVectorToString(phase));
                }

                else if (arg_pair.first == "set_fsm_id") {
                    int fsm_id = std::stoi(arg_pair.second);
                    client.SetFsmId(fsm_id);
                    printResponse("success", "FSM ID set to " + std::to_string(fsm_id));
                }

                else if (arg_pair.first == "set_balance_mode") {
                    int balance_mode = std::stoi(arg_pair.second);
                    client.SetBalanceMode(balance_mode);
                    printResponse("success", "Balance mode set to " + std::to_string(balance_mode));
                }

                else if (arg_pair.first == "set_swing_height") {
                    float swing_height = std::stof(arg_pair.second);
                    client.SetSwingHeight(swing_height);
                    printResponse("success", "Swing height set to " + std::to_string(swing_height));
                }

                else if (arg_pair.first == "set_stand_height") {
                    float stand_height = std::stof(arg_pair.second);
                    client.SetStandHeight(stand_height);
                    printResponse("success", "Stand height set to " + std::to_string(stand_height));
                }

                else if (arg_pair.first == "set_velocity") {
                    std::vector<float> param = stringToFloatVector(arg_pair.second);
                    auto param_size = param.size();
                    float vx, vy, omega, duration;
                    if (param_size == 3) {
                        vx = param.at(0);
                        vy = param.at(1);
                        omega = param.at(2);
                        duration = 1.f;
                    } else if (param_size == 4) {
                        vx = param.at(0);
                        vy = param.at(1);
                        omega = param.at(2);
                        duration = param.at(3);
                    } else {
                        printError("Invalid param size for method SetVelocity: " + std::to_string(param_size));
                        return 1;
                    }

                    client.SetVelocity(vx, vy, omega, duration);
                    printResponse("success", "Velocity set", arg_pair.second);
                }

                else if (arg_pair.first == "damp") {
                    client.Damp();
                    printResponse("success", "Damp executed");
                }

                else if (arg_pair.first == "start") {
                    client.Start();
                    printResponse("success", "Start executed");
                }

                else if (arg_pair.first == "squat") {
                    client.Squat();
                    printResponse("success", "Squat executed");
                }

                else if (arg_pair.first == "sit") {
                    client.Sit();
                    printResponse("success", "Sit executed");
                }

                else if (arg_pair.first == "stand_up") {
                    client.StandUp();
                    printResponse("success", "Stand up executed");
                }

                else if (arg_pair.first == "zero_torque") {
                    client.ZeroTorque();
                    printResponse("success", "Zero torque executed");
                }

                else if (arg_pair.first == "stop_move") {
                    client.StopMove();
                    printResponse("success", "Stop move executed");
                }

                else if (arg_pair.first == "high_stand") {
                    client.HighStand();
                    printResponse("success", "High stand executed");
                }

                else if (arg_pair.first == "low_stand") {
                    client.LowStand();
                    printResponse("success", "Low stand executed");
                }

                else if (arg_pair.first == "balance_stand") {
                    client.BalanceStand();
                    printResponse("success", "Balance stand executed");
                }

                else if (arg_pair.first == "continous_gait") {
                    bool flag;
                    if (arg_pair.second == "true") {
                        flag = true;
                    } else if (arg_pair.second == "false") {
                        flag = false;
                    } else {
                        printError("Invalid argument for continous_gait: " + arg_pair.second);
                        return 1;
                    }
                    client.ContinuousGait(flag);
                    printResponse("success", "Continuous gait set to " + arg_pair.second);
                }

                else if (arg_pair.first == "switch_move_mode") {
                    bool flag;
                    if (arg_pair.second == "true") {
                        flag = true;
                    } else if (arg_pair.second == "false") {
                        flag = false;
                    } else {
                        printError("Invalid argument for switch_move_mode: " + arg_pair.second);
                        return 1;
                    }
                    client.SwitchMoveMode(flag);
                    printResponse("success", "Move mode switched to " + arg_pair.second);
                }

                else if (arg_pair.first == "move") {
                    std::vector<float> param = stringToFloatVector(arg_pair.second);
                    auto param_size = param.size();
                    float vx, vy, omega;
                    if (param_size == 3) {
                        vx = param.at(0);
                        vy = param.at(1);
                        omega = param.at(2);
                    } else {
                        printError("Invalid param size for method Move: " + std::to_string(param_size));
                        return 1;
                    }
                    client.Move(vx, vy, omega);
                    printResponse("success", "Move executed", arg_pair.second);
                }

                else if (arg_pair.first == "set_task_id") {
                    int task_id = std::stoi(arg_pair.second);
                    client.SetTaskId(task_id);
                    printResponse("success", "Task ID set to " + std::to_string(task_id));
                }

                else if (arg_pair.first == "shake_hand") {
                    client.ShakeHand(0);
                    printResponse("success", "Shake hand started, waiting 10s");
                    std::this_thread::sleep_for(std::chrono::seconds(10));
                    client.ShakeHand(1);
                    printResponse("success", "Shake hand completed");
                }

                else if (arg_pair.first == "wave_hand") {
                    client.WaveHand();
                    printResponse("success", "Wave hand executed");
                }

                else if (arg_pair.first == "wave_hand_with_turn") {
                    client.WaveHand(true);
                    printResponse("success", "Wave hand with turn executed");
                }

                else if (arg_pair.first == "set_speed_mode") {
                    client.SetSpeedMode(std::stoi(arg_pair.second));
                    printResponse("success", "Speed mode set to " + arg_pair.second);
                }

                else {
                    printError("Unknown command: " + arg_pair.first);
                }

            } catch (const std::exception& e) {
                printError("Error executing " + arg_pair.first + ": " + e.what());
            }
        }

    } catch (const std::exception& e) {
        printError("Fatal error: " + std::string(e.what()));
        return 1;
    }

    return 0;
}