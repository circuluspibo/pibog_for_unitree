#include <fstream>
#include <iostream>
#include <thread>
#include <unitree/common/time/time_tool.hpp>
#include <unitree/idl/ros2/String_.hpp>
#include <unitree/robot/channel/channel_subscriber.hpp>
#include <unitree/robot/g1/audio/g1_audio_client.hpp>

#include "wav.hpp"

#define AUDIO_FILE_PATH "../example/g1/audio/test.wav"

#define WAV_SECOND 5  // record seconds
#define WAV_LEN (16000 * 2 * WAV_SECOND)
#define CHUNK_SIZE 96000  // 3 seconds

int main(int argc, char const *argv[]) {
  if (argc < 2) {
    std::cout << "Usage: audio_client_example [NetWorkInterface(eth0)]"
              << std::endl;
    exit(0);
  }
  int32_t ret;
  /*
   * Initilaize ChannelFactory
   */
  unitree::robot::ChannelFactory::Instance()->Init(0, "eth0"); // argv[1]
  unitree::robot::g1::AudioClient client;
  client.Init();
  client.SetTimeout(10.0f);

  int32_t sample_rate = 16000; //-1;
  int8_t num_channels = 1; // 0;
  bool filestate = true; //false;
  //std::vector<uint8_t> pcm = ReadWave(AUDIO_FILE_PATH, &sample_rate, &num_channels, &filestate);
  std::vector<uint8_t> pcm = ReadWave(argv[1], &sample_rate, &num_channels, &filestate);

  std::cout << "wav file sample_rate = " << sample_rate
            << " num_channels =  " << std::to_string(num_channels)
            << " filestate =" << filestate << "filesize = " << pcm.size()
            << std::endl;

  int dur = 0;
  int cnt = 0;

  if (filestate && sample_rate == 16000 && num_channels == 1) {
    size_t total_size = pcm.size();
    size_t offset = 0;
    int chunk_index = 0;
    std::string stream_id = std::to_string(unitree::common::GetCurrentTimeMillisecond());

    while (true) {
      cnt += 1;
      size_t remaining = total_size - offset;
      size_t current_chunk_size = std::min(static_cast<size_t>(CHUNK_SIZE), remaining);

      std::vector<uint8_t> chunk(pcm.begin() + offset,
                                pcm.begin() + offset + current_chunk_size);

      client.PlayStream("example", stream_id, chunk);
      unitree::common::Sleep(1);
    
      std::cout << "Playing offset: " << offset << " / " << total_size << std::endl;

      if(offset == total_size && dur == 0){
        dur = cnt * 2; // total minus already played
        cnt = 0;
      }

      if(cnt == dur - 1){
        std::cout << "Playback finished (played " << total_size << " bytes)." << std::endl;
        break;
      }

      offset += current_chunk_size;
    }

    ret = client.PlayStop(stream_id);  // stop playback after transmission ends

  } else {
    std::cout << "audio file format error, please check!" << std::endl;
  }

}