
add_executable(g1_loco_client high_level/g1_loco_client_example.cpp)
target_link_libraries(g1_loco_client unitree_sdk2)

add_executable(g1_arm5_sdk_dds_example high_level/g1_arm5_sdk_dds_example.cpp)
target_link_libraries(g1_arm5_sdk_dds_example unitree_sdk2)

add_executable(g1_arm7_sdk_dds_example high_level/g1_arm7_sdk_dds_example.cpp)
target_link_libraries(g1_arm7_sdk_dds_example unitree_sdk2)

add_executable(g1_arm_action_example high_level/g1_arm_action_example.cpp)
target_link_libraries(g1_arm_action_example unitree_sdk2)

add_executable(g1_ankle_swing_example low_level/g1_ankle_swing_example.cpp)
target_link_libraries(g1_ankle_swing_example unitree_sdk2)

add_executable(g1_audio_client_example audio/g1_audio_client_example.cpp)
target_link_libraries(g1_audio_client_example unitree_sdk2)

add_executable(g1_dex3_example dex3/g1_dex3_example.cpp)
target_link_libraries(g1_dex3_example unitree_sdk2)

add_executable(motor_control high_level/motor_control.cpp)
target_link_libraries(motor_control unitree_sdk2)

add_executable(robot_client high_level/robot_client.cpp)
target_link_libraries(robot_client unitree_sdk2)

add_executable(g1_arm high_level/g1_arm.cpp)
target_link_libraries(g1_arm unitree_sdk2)

add_executable(g1_audio audio/g1_audio.cpp)
target_link_libraries(g1_audio unitree_sdk2)

add_executable(g1_vui audio/g1_vui.cpp)
target_link_libraries(g1_vui unitree_sdk2)


find_package(yaml-cpp QUIET)
if(yaml-cpp_FOUND)
    if (${yaml-cpp_VERSION} VERSION_GREATER_EQUAL "0.6")
        message(STATUS "Found yaml-cpp version ${yaml-cpp_VERSION}")
        add_executable(g1_dual_arm_example low_level/g1_dual_arm_example.cpp)
        target_link_libraries(g1_dual_arm_example PRIVATE unitree_sdk2 yaml-cpp)
        target_compile_definitions(g1_dual_arm_example PUBLIC BLIB_DIR="${CMAKE_CURRENT_SOURCE_DIR}/low_level/behavior_lib/")
    else()
        message(STATUS "yaml-cpp version ${yaml-cpp_VERSION} is too old, skipping build of g1_dual_arm_example.")
    endif()
endif()
