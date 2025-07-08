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

app = FastAPI()

G1_ARM = {
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
  "Release Arm" : 99,
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

# 정적 파일 서비스 (업로드한 파일 재생 가능)
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")
origins = [
    "http://canvers.net",
    "https://canvers.net",   
    "http://www.canvers.net",
    "https://www.canvers.net",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],#origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app = FastAPI()
camera = None
conn = None
state = { "charge" : 0, "temp" : 0, "voltage" : 0, "cnt_live" : 0, "cnt_object" : 0 }


def gen_frames():
    camera = cv2.VideoCapture(6)
    while True:
        success, frame = camera.read()
        if not success:
            continue
        frame = cv2.flip(frame, 1)
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
        <head>
            <title>웹캠 스트리밍</title>
        </head>
        <body>
            <h1>웹캠 스트리밍</h1>
            <img src="/video" width="640" height="480" />
        </body>
    </html>
    """

@app.get("/connect")
async def connect():
  global conn
  #global audio_hub
  conn =  Go2WebRTCConnection(WebRTCConnectionMethod.LocalSTA, ip="192.168.123.161") #Go2WebRTCConnection(WebRTCConnectionMethod.LocalAP) #Go2WebRTCConnection(WebRTCConnectionMethod.LocalSTA, ip="192.168.0.101")
  await conn.connect()
  print("connect okay")
  def lowstate_callback(message):
    #print(message)
    msg = message['data']      
    state["charge"] = msg['bms_state']['soc']
    state["temp"] = msg['temperature_ntc1']
    state["voltage"] = msg['power_v']

  conn.datachannel.pub_sub.subscribe(RTC_TOPIC['LOW_STATE'], lowstate_callback)

  return { "result" : True, "data" : True }     

@app.post("/arm")
async def arm(id: str = '17'):
    try:
        subprocess.run(["./g1_arm", id], check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"arm 실행 실패: {e}"}

    return {"message": f"arm  설정 완료: ({id})"}      

@app.get("/walk")
async def walk(lx = 0, ly = 0, rx = 0, ry = 0):
  print("walking",f"L : {lx} {ly} | R : {rx} {ry}")
  global conn

  conn.datachannel.pub_sub.publish_without_callback(
     "rt/wirelesscontroller", {
        "lx": float(lx), "ly": float(ly), "rx": float(rx), "ry": float(ry) 
     }
  )
  
  return { "result" : True, "data" : True }     

@app.get("/stateG1")
async def stateG1(cmd="Walk_G1"):
  global conn
  global G1_STATE

  await conn.datachannel.pub_sub.publish_request_new(
    "rt/api/sport/request", {
        "api_id": 7101,
        "parameter" : { "data" : G1_STATE[cmd] }
    }
  )

  return { "result" : True, "data" : True }      

@app.get("/balanceG1")
async def balanceG1(cmd="Stand_G1"):
  global conn
  global G1_BALANCE

  await conn.datachannel.pub_sub.publish_request_new(
    "rt/api/sport/request", {
        "api_id": 7102,
        "parameter" : { "data" : G1_BALANCE[cmd] }
    }
  )

  return { "result" : True, "data" : True }    

@app.get("/heartbeat")
async def heartbeat():
  global state
  print(state)
  return { "result" : True, "data" : state }   

@app.get("/video")
def video():
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

def convert_to_mono_16k_pydub(src_path: str, dst_path: str):
    try:
        audio = AudioSegment.from_file(src_path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(dst_path, format="wav")
        return True
    except Exception as e:
        print(f"변환 오류: {e}")
        return False

@app.post("/audio")
async def audio(audio_file: UploadFile = File(...)):
    original_path = os.path.join(UPLOAD_DIR, audio_file.filename)
    converted_path = os.path.join(UPLOAD_DIR, f"converted_{audio_file.filename}")

    # 업로드 저장
    with open(original_path, "wb") as f:
        shutil.copyfileobj(audio_file.file, f)

    # 변환 처리
    success = convert_to_mono_16k_pydub(original_path, converted_path)
    if not success:
        return {"error": "오디오 변환 실패 (pydub)"}

    # g1_audio 실행
    try:
        subprocess.Popen(["./g1_audio", converted_path]) # async
        #subprocess.run(["g1_audio", converted_path], check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"g1_audio 실행 실패: {e}"}

    return {
        "message": f"{audio_file.filename} 재생 중 (pydub 변환됨)",
        "url": f"/files/converted_{audio_file.filename}"
    }

@app.post("/led")
async def led(r: str = '255', g: str = '255', b: str = '255'):
    try:
        subprocess.run(["./g1_vui", r, g, b], check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"g1_vui 실행 실패: {e}"}

    return {"message": f"LED 색상 설정 완료: ({r}, {g}, {b})"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)