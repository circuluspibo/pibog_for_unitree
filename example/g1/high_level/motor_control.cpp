#include <array>
#include <chrono>
#include <iostream>
#include <thread>
#include <string>
#include <sstream>
#include <vector>
#include <map>
#include <atomic>
#include <mutex>

#include <unitree/idl/hg/LowCmd_.hpp>
#include <unitree/idl/hg/LowState_.hpp>
#include <unitree/robot/channel/channel_publisher.hpp>
#include <unitree/robot/channel/channel_subscriber.hpp>

static const std::string kTopicArmSDK = "rt/arm_sdk";
static const std::string kTopicState = "rt/lowstate";
constexpr float kPi = 3.141592654;
constexpr float kPi_2 = 1.57079632;

enum JointIndex {
    // Left leg
    kLeftHipPitch = 0,
    kLeftHipRoll = 1,
    kLeftHipYaw = 2,
    kLeftKnee = 3,
    kLeftAnkle  = 4,
    kLeftAnkleRoll = 5,

    // Right leg
    kRightHipPitch = 6,
    kRightHipRoll = 7,
    kRightHipYaw = 8,
    kRightKnee = 9,
    kRightAnkle = 10,
    kRightAnkleRoll = 11,

    kWaistYaw = 12,
    kWaistRoll = 13,
    kWaistPitch = 14,

    // Left arm
    kLeftShoulderPitch = 15,
    kLeftShoulderRoll = 16,
    kLeftShoulderYaw = 17,
    kLeftElbowPitch = 18,
    kLeftElbowRoll = 19,
    
    // Right arm
    kRightShoulderPitch = 22,
    kRightShoulderRoll = 23,
    kRightShoulderYaw = 24,
    kRightElbowPitch = 25,
    kRightElbowRoll = 26,

    kNotUsedJoint = 29,
    kNotUsedJoint1 = 30,
    kNotUsedJoint2 = 31,
    kNotUsedJoint3 = 32,
    kNotUsedJoint4 = 33,
    kNotUsedJoint5 = 34
};

// Joint name mapping for easier command parsing
std::map<std::string, JointIndex> joint_name_map = {
    {"left_shoulder_pitch", kLeftShoulderPitch},
    {"left_shoulder_roll", kLeftShoulderRoll},
    {"left_shoulder_yaw", kLeftShoulderYaw},
    {"left_elbow_pitch", kLeftElbowPitch},
    {"left_elbow_roll", kLeftElbowRoll},
    {"right_shoulder_pitch", kRightShoulderPitch},
    {"right_shoulder_roll", kRightShoulderRoll},
    {"right_shoulder_yaw", kRightShoulderYaw},
    {"right_elbow_pitch", kRightElbowPitch},
    {"right_elbow_roll", kRightElbowRoll},
    {"waist_yaw", kWaistYaw},
    {"waist_roll", kWaistRoll},
    {"waist_pitch", kWaistPitch}
};

// Command structure
struct MotorCommand {
    std::string joint_name;
    float position;
    float velocity;
    float kp;
    float kd;
    float tau;
    bool valid;
    
    MotorCommand() : position(0), velocity(0), kp(60), kd(1.5), tau(0), valid(false) {}
};

// Global variables for thread communication
std::atomic<bool> running(true);
std::atomic<bool> control_enabled(false);
std::mutex command_mutex;
std::vector<MotorCommand> pending_commands;

// Function to parse command from stdin
MotorCommand parseCommand(const std::string& input) {
    MotorCommand cmd;
    std::istringstream iss(input);
    std::string token;
    std::vector<std::string> tokens;
    
    while (iss >> token) {
        tokens.push_back(token);
    }
    
    if (tokens.size() < 3) {
        std::cout << "Invalid command format. Use: <joint_name> <position> [velocity] [kp] [kd] [tau]" << std::endl;
        return cmd;
    }
    
    cmd.joint_name = tokens[0];
    cmd.position = std::stof(tokens[1]);
    
    if (tokens.size() > 2) cmd.velocity = std::stof(tokens[2]);
    if (tokens.size() > 3) cmd.kp = std::stof(tokens[3]);
    if (tokens.size() > 4) cmd.kd = std::stof(tokens[4]);
    if (tokens.size() > 5) cmd.tau = std::stof(tokens[5]);
    
    cmd.valid = true;
    return cmd;
}

// Function to handle user input in separate thread
void inputHandler() {
    std::string input;
    std::cout << "\n=== Motor Control Commands ===" << std::endl;
    std::cout << "Commands:" << std::endl;
    std::cout << "  start - Enable motor control" << std::endl;
    std::cout << "  stop  - Disable motor control" << std::endl;
    std::cout << "  quit  - Exit program" << std::endl;
    std::cout << "  status - Show current status" << std::endl;
    std::cout << "  list  - List available joints" << std::endl;
    std::cout << "  <joint_name> <position> [velocity] [kp] [kd] [tau] - Control specific joint" << std::endl;
    std::cout << "Example: left_shoulder_pitch 1.57 0 60 1.5 0" << std::endl;
    std::cout << "================================" << std::endl;
    
    while (running) {
        std::cout << "> ";
        std::getline(std::cin, input);
        
        if (input == "quit" || input == "exit") {
            running = false;
            break;
        } else if (input == "start") {
            control_enabled = true;
            std::cout << "Motor control enabled" << std::endl;
        } else if (input == "stop") {
            control_enabled = false;
            std::cout << "Motor control disabled" << std::endl;
        } else if (input == "status") {
            std::cout << "Control status: " << (control_enabled ? "ENABLED" : "DISABLED") << std::endl;
        } else if (input == "list") {
            std::cout << "Available joints:" << std::endl;
            for (const auto& pair : joint_name_map) {
                std::cout << "  " << pair.first << std::endl;
            }
        } else if (!input.empty()) {
            MotorCommand cmd = parseCommand(input);
            if (cmd.valid) {
                if (joint_name_map.find(cmd.joint_name) != joint_name_map.end()) {
                    std::lock_guard<std::mutex> lock(command_mutex);
                    pending_commands.push_back(cmd);
                    std::cout << "Command queued for " << cmd.joint_name << std::endl;
                } else {
                    std::cout << "Unknown joint: " << cmd.joint_name << std::endl;
                }
            }
        }
    }
}

int main(int argc, char const *argv[]) {
    if (argc < 2) {
        std::cout << "Usage: " << argv[0] << " networkInterface" << std::endl;
        exit(-1);
    }

    unitree::robot::ChannelFactory::Instance()->Init(0, argv[1]); // 

    unitree::robot::ChannelPublisherPtr<unitree_hg::msg::dds_::LowCmd_>
        arm_sdk_publisher;
    unitree_hg::msg::dds_::LowCmd_ msg;

    arm_sdk_publisher.reset(
        new unitree::robot::ChannelPublisher<unitree_hg::msg::dds_::LowCmd_>(
            kTopicArmSDK));
    arm_sdk_publisher->InitChannel();

    unitree::robot::ChannelSubscriberPtr<unitree_hg::msg::dds_::LowState_>
        low_state_subscriber;

    unitree_hg::msg::dds_::LowState_ state_msg;
    low_state_subscriber.reset(
        new unitree::robot::ChannelSubscriber<unitree_hg::msg::dds_::LowState_>(
            kTopicState));
    low_state_subscriber->InitChannel([&](const void *msg) {
        auto s = (const unitree_hg::msg::dds_::LowState_*)msg;
        memcpy(&state_msg, s, sizeof(unitree_hg::msg::dds_::LowState_));
    }, 1);

    std::array<JointIndex, 13> arm_joints = {
        JointIndex::kLeftShoulderPitch,  JointIndex::kLeftShoulderRoll,
        JointIndex::kLeftShoulderYaw,    JointIndex::kLeftElbowPitch,
        JointIndex::kLeftElbowRoll,
        JointIndex::kRightShoulderPitch, JointIndex::kRightShoulderRoll,
        JointIndex::kRightShoulderYaw,   JointIndex::kRightElbowPitch,
        JointIndex::kRightElbowRoll,
        JointIndex::kWaistYaw,
        JointIndex::kWaistRoll,
        JointIndex::kWaistPitch
    };

    // Current joint positions
    std::array<float, 13> current_positions{};
    
    // Default control parameters
    float default_kp = 60.f;
    float default_kd = 1.5f;
    float default_dq = 0.f;
    float default_tau = 0.f;
    float control_dt = 0.02f;
    
    auto sleep_time = std::chrono::milliseconds(static_cast<int>(control_dt / 0.001f));

    // Start input handler thread
    std::thread input_thread(inputHandler);

    std::cout << "Motor control system initialized. Type 'start' to begin control." << std::endl;

    // Main control loop
    while (running) {
        // Process pending commands
        std::vector<MotorCommand> commands_to_process;
        {
            std::lock_guard<std::mutex> lock(command_mutex);
            commands_to_process = pending_commands;
            pending_commands.clear();
        }

        // Apply commands if control is enabled
        if (control_enabled) {
            // Set weight for control
            msg.motor_cmd().at(JointIndex::kNotUsedJoint).q(1.0);

            // Update current positions from state
            for (int i = 0; i < arm_joints.size(); ++i) {
                current_positions[i] = state_msg.motor_state().at(arm_joints[i]).q();
            }

            // Process commands
            for (const auto& cmd : commands_to_process) {
                auto joint_it = joint_name_map.find(cmd.joint_name);
                if (joint_it != joint_name_map.end()) {
                    JointIndex joint_idx = joint_it->second;
                    
                    // Find the joint in our control array
                    for (int i = 0; i < arm_joints.size(); ++i) {
                        if (arm_joints[i] == joint_idx) {
                            current_positions[i] = cmd.position;
                            break;
                        }
                    }
                    
                    // Set motor command
                    msg.motor_cmd().at(joint_idx).q(cmd.position);
                    msg.motor_cmd().at(joint_idx).dq(cmd.velocity);
                    msg.motor_cmd().at(joint_idx).kp(cmd.kp);
                    msg.motor_cmd().at(joint_idx).kd(cmd.kd);
                    msg.motor_cmd().at(joint_idx).tau(cmd.tau);
                    
                    std::cout << "Applied command to " << cmd.joint_name 
                              << " - Position: " << cmd.position << std::endl;
                }
            }

            // Set all controlled joints with current positions
            for (int i = 0; i < arm_joints.size(); ++i) {
                msg.motor_cmd().at(arm_joints[i]).q(current_positions[i]);
                msg.motor_cmd().at(arm_joints[i]).dq(default_dq);
                msg.motor_cmd().at(arm_joints[i]).kp(default_kp);
                msg.motor_cmd().at(arm_joints[i]).kd(default_kd);
                msg.motor_cmd().at(arm_joints[i]).tau(default_tau);
            }
        } else {
            // Set weight to 0 when control is disabled
            msg.motor_cmd().at(JointIndex::kNotUsedJoint).q(0.0);
        }

        // Send message
        arm_sdk_publisher->Write(msg);

        // Sleep
        std::this_thread::sleep_for(sleep_time);
    }

    // Cleanup: disable control
    std::cout << "\nShutting down motor control..." << std::endl;
    msg.motor_cmd().at(JointIndex::kNotUsedJoint).q(0.0);
    arm_sdk_publisher->Write(msg);

    // Wait for input thread to finish
    if (input_thread.joinable()) {
        input_thread.join();
    }

    std::cout << "Motor control system shut down." << std::endl;
    return 0;
}