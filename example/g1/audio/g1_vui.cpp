#include <fstream>
#include <iostream>
#include <thread>
#include <unitree/common/time/time_tool.hpp>
#include <unitree/idl/ros2/String_.hpp>
#include <unitree/robot/channel/channel_subscriber.hpp>
#include <unitree/robot/g1/audio/g1_audio_client.hpp>

int main(int argc, char const *argv[]) {
  if (argc < 2) {
    std::cout << "Usage: audio_client_example [NetWorkInterface(eth0)]"
              << std::endl;
    exit(0);
  }
  int32_t ret;

  unitree::robot::ChannelFactory::Instance()->Init(0, "eth0");
  unitree::robot::g1::AudioClient client;
  client.Init();
  client.SetTimeout(10.0f);

  int r{std::stoi(argv[1])};
  int g{std::stoi(argv[2])};
  int b{std::stoi(argv[3])};

  client.LedControl(r, g, b);

}