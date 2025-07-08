/**
 * @file g1_arm_action_example.cpp
 * @brief This example demonstrates how to use the G1 Arm Action Client to execute predefined arm actions via command-line arguments.
 */
#include "unitree/robot/g1/arm/g1_arm_action_error.hpp"
#include "unitree/robot/g1/arm/g1_arm_action_client.hpp"

using namespace unitree::robot::g1;

int main(int argc, const char** argv) 
{
    std::cout << " --- Unitree Robotics --- \n";
    std::cout << "     G1 Arm Action Example (CMD version)     \n\n";

    if (argc < 3) {
        std::cerr << "Usage:\n";
        std::cerr << "  " << argv[0] << " <action_id>\n";
        std::cerr << "Example:\n";
        std::cerr << "  " << argv[0] << " 1\n";
        std::cerr << "  " << argv[0] << " -1   # to print supported actions\n";
        return 1;
    }

    const std::string net_interface = "eth0";
    int32_t action_id = std::stoi(argv[1]);

    // Unitree DDS Initialization
    unitree::robot::ChannelFactory::Instance()->Init(0, net_interface);

    auto client = std::make_shared<G1ArmActionClient>();
    client->Init();
    client->SetTimeout(10.f); // All actions will last less than 10 seconds.

    if (action_id == -1) {
        std::string action_list_data;
        int32_t ret = client->GetActionList(action_list_data);
        if (ret != 0) {
            std::cerr << "Failed to get action list, error code: " << ret << "\n";
            return 1;
        }
        std::cout << "Available actions:\n" << action_list_data << std::endl;
    } else {
        int32_t ret = client->ExecuteAction(action_id);
        if(ret != 0) {
            switch (ret)
            {
            case UT_ROBOT_ARM_ACTION_ERR_ARMSDK:
                std::cout << UT_ROBOT_ARM_ACTION_ERR_ARMSDK_DESC << std::endl;
                break;
            case UT_ROBOT_ARM_ACTION_ERR_HOLDING:
                std::cout << UT_ROBOT_ARM_ACTION_ERR_HOLDING_DESC << std::endl;
                break;
            case UT_ROBOT_ARM_ACTION_ERR_INVALID_ACTION_ID:
                std::cout << UT_ROBOT_ARM_ACTION_ERR_INVALID_ACTION_ID_DESC << std::endl;
                break;
            case UT_ROBOT_ARM_ACTION_ERR_INVALID_FSM_ID:
                std::cout << "The actions are only supported in fsm id {500, 501, 801}" << std::endl;
                std::cout << "You can subscribe the topic rt/sportmodestate to check the fsm id." << std::endl;
                std::cout << "And in the state 801, the actions are only supported in the fsm mode {0, 3}." << std::endl;
                std::cout << "If an error is still returned at this point, ignore this action.";
                break;
            default:
                std::cerr << "Execute action failed, error code: " << ret << std::endl;
                break;
            }
            return 1;
        } else {
            std::cout << "Action " << action_id << " executed successfully.\n";
        }
    }

    return 0;
}