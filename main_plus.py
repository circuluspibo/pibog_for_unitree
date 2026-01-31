from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import cv2
from fastapi import FastAPI, File, UploadFile, Form
import uvicorn
import threading
from pydub import AudioSegment
import subprocess
from fastapi import UploadFile
import os
import shutil
from fastapi.staticfiles import StaticFiles
import asyncio
from go2_webrtc_driver.webrtc_driver import Go2WebRTCConnection, WebRTCConnectionMethod
from go2_webrtc_driver.constants import RTC_TOPIC, VUI_COLOR, SPORT_CMD
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
import cv2
import numpy as np
import threading
import time
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
from asyncio import Queue
audio_queue = Queue()  # 오디오 큐

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용, 보안을 위해 실제 사용시 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


G1_ACTION = {
  "clamp": 17, 
  "highFive": 18, 
  "shakeHands_1": 27,
  "makeHeartBothHands": 20, 
  "makeHeartSingleHands": 21,
  "blowKiss": 12, 
  "hug": 19,
  "hightWave": 26, 
  "lowWave" : 25,
  "ultramanRay" : 24, 
  "bothHandsUp" : 15,
  "singleHandsUp" : 23,
  "Refuse" : 22, 
  "Release_Arm" : 99,
}

G1_STATE = {
  "ZeroTorque" : 0,
  "Damp" : 1,
  "Preparation": 4,
  "Seating": 3,       
  "Walk_G1": 500,
  "Walk2_G1" : 501,
  "Run_G1" : 801,
  "Squat_G1" : 706,  
  "SquatUp_G1" : 706,
  "LieUp_G1" : 702,
}

G1_BALANCE = {
  "Stand_G1" : 0,
  "Step_G1" : 1 
}

UPLOAD_DIR = "uploaded_audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()

# 정적 파일 서비스 (업로드한 파일 재생 가능)
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")
app.mount("/web", StaticFiles(directory="web"), name="web")
app.mount("/webfonts", StaticFiles(directory="webfonts"), name="webfonts")

origins = [
    "http://canvers.net",
    "https://canvers.net",   
    "http://www.canvers.net",
    "https://www.canvers.net",
]

from mandro import HandControler

try:
    hand = HandControler('/dev/ttyACM0') # L 컨트롤러 L동글 부터 연결
    print("컨트롤러 초기화 성공")
except Exception as e:
    print(f"컨트롤러 초기화 실패: {e}")
    exit()

@app.get("/hands")
async def hands(cmd : str = 'fold', selector : str = 'both'):
    if cmd != "release":
        hand.send_motion(cmd, selector)
        hand.send_motion(cmd, selector)
    else:
        hand.send_release(None, selector)
        hand.send_release(None, selector)
    return {"result" : True}


@app.get("/") # , response_class=HTMLResponse)
async def main():
    return {"result" : True}

@app.get("/cmd")
async def cmd(key : str = "set_fsm_id", value : str = None):
    result = 0

    try:
        if value != None:
            subprocess.run(["./g1_cmd", f"--{key}={value}"], check=True)
        else:
            res = subprocess.run(["./g1_cmd", f"--{key}"], check=True, capture_output=True, text=True)
            result = res.stdout

    except subprocess.CalledProcessError as e:
        return {"result": False, "data": e }

    return {"result" : True, "data" : result }


@app.get("/action")
async def action(value : str = 'clamp'):
    result = 0

    try:
        subprocess.run(["./g1_action", str(G1_ACTION[value])], check=True)

    except subprocess.CalledProcessError as e:
        return {"result": False, "data": e }

    return {"result" : True, "data" : result }

@app.get("/state")
async def state(value : str = 'Walk2_G1'):
    result = 0

    try:
        subprocess.run(["./g1_cmd", f"--set_fsm_id={G1_STATE[value]}"], check=True)

    except subprocess.CalledProcessError as e:
        return {"result": False, "data": e }

    return {"result" : True, "data" : result }


async def process_audio():
    """
    백그라운드에서 오디오를 하나씩 처리하는 함수.
    """
    while True:
        # 큐에서 오디오 파일을 하나씩 가져옴
        audio_data = await audio_queue.get()  # 큐에서 비동기적으로 가져오기
        if audio_data is None:
            break  # 큐에 종료 신호가 들어오면 종료

        original_path, converted_path = audio_data['paths']
        audio_file = audio_data['file']
        
        # 변환 처리
        success = convert_to_mono_16k_pydub(original_path, converted_path)
        if not success:
            print(f"Error converting {audio_file.filename}")
            continue

        # g1_audio 실행
        try:
            process = subprocess.Popen(["./g1_audio", converted_path])  # 비동기 실행
            process.wait()  # 실행이 끝날 때까지 대기
        except subprocess.CalledProcessError as e:
            print(f"Error executing g1_audio: {e}")
            continue
        
        # 완료된 후 메시지
        print(f"{audio_file.filename} 재생 완료")

async def audio_task(audio_file: UploadFile):
    original_path = os.path.join(UPLOAD_DIR, audio_file.filename)
    converted_path = os.path.join(UPLOAD_DIR, f"converted_{audio_file.filename}")

    # 업로드 저장
    with open(original_path, "wb") as f:
        shutil.copyfileobj(audio_file.file, f)

    # 큐에 오디오 처리 요청 추가
    await audio_queue.put({
        "file": audio_file,
        "paths": (original_path, converted_path)
    })

    return {
        "message": f"{audio_file.filename} 재생 대기 중 (pydub 변환됨)",
        "url": f"/files/converted_{audio_file.filename}"
    }

@app.post("/audio")
async def audio(audio_file: UploadFile = File(...)):
    # audio_queue에 요청 추가
    await audio_task(audio_file)
    return {"message": "Audio request received, processing started."}

# 별도의 비동기 루프에서 audio 프로세싱을 시작
def start_audio_processor():
    loop = asyncio.get_event_loop()
    loop.create_task(process_audio())  # 비동기 작업으로 처리 시작

# 앱 시작 시 오디오 프로세서 시작
start_audio_processor()

@app.get("/led")
async def led(r: str = '255', g: str = '255', b: str = '255'):
    try:
        subprocess.run(["./g1_vui", r, g, b], check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"g1_vui 실행 실패: {e}"}

    return {"message": f"LED 색상 설정 완료: ({r}, {g}, {b})"}

success = convert_to_mono_16k_pydub('intel_inside.mp3', 'intel.wav')
subprocess.Popen(["./g1_audio", 'intel.wav']) # async
