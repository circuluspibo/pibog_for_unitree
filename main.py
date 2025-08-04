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
import pyrealsense2 as rs
import threading
import time
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용, 보안을 위해 실제 사용시 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- RealSense 초기화 ---
print("init realsense")
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
#config.enable_stream(rs.stream.accel)
#config.enable_stream(rs.stream.gyro)

pipeline.start(config)

frame_lock = threading.Lock()
latest_color_frame = None
latest_depth_frame = None
latest_imu_data = {'accel': None, 'gyro': None}

# --- 프레임 수집 쓰레드 ---
# --- 백그라운드 프레임 수집 시작 ---
def frame_reader():
    global latest_color_frame, latest_depth_frame, latest_imu_data
    while True:
        frames = pipeline.wait_for_frames(timeout_ms=5000)
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()

        accel_frame = frames.first_or_default(rs.stream.accel)
        gyro_frame = frames.first_or_default(rs.stream.gyro)

        if not color_frame or not depth_frame:
            continue

        with frame_lock:
            latest_color_frame = np.asanyarray(color_frame.get_data())
            latest_depth_frame = np.asanyarray(depth_frame.get_data())

            if accel_frame:
                accel = accel_frame.as_motion_frame().get_motion_data()
                latest_imu_data['accel'] = {'x': accel.x, 'y': accel.y, 'z': accel.z}
            if gyro_frame:
                gyro = gyro_frame.as_motion_frame().get_motion_data()
                latest_imu_data['gyro'] = {'x': gyro.x, 'y': gyro.y, 'z': gyro.z}

        time.sleep(0.01)

# 백그라운드 스레드로 프레임 수집 시작
threading.Thread(target=frame_reader, daemon=True).start()

# --- RGB 이미지 스트리밍 ---
async def generate_video():
    while True:
        with frame_lock:
            if latest_color_frame is not None:
                ret, jpeg = cv2.imencode('.jpg', latest_color_frame)
                if ret:
                    frame = jpeg.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        await asyncio.sleep(0.03)

# --- Depth 이미지 스트리밍 ---
async def generate_depth_image():
    while True:
        with frame_lock:
            if latest_depth_frame is not None:
                # Normalize depth to 0-255 and convert to 8-bit
                depth_normalized = cv2.convertScaleAbs(latest_depth_frame, alpha=0.03)
                depth_colored = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
                ret, jpeg = cv2.imencode('.jpg', depth_colored)
                if ret:
                    frame = jpeg.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        await asyncio.sleep(0.1)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],#origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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

@app.get("/") # , response_class=HTMLResponse)
async def main():
    return {"result" : True}

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

@app.get("/arm")
async def arm(id: str = '17'):
    try:
        subprocess.run(["./g1_arm", id], check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"action 실행 실패: {e}"}

    return {"message": f"action  설정 완료: ({id})"}      



@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_video(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/depth_feed")
async def depth_image():
    return StreamingResponse(generate_depth_image(), media_type="multipart/x-mixed-replace; boundary=frame")


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


#@app.get("/video")
#def video():
#    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


# --- Depth 데이터 (raw) GET ---
@app.get("/depth")
def get_depth():
    with frame_lock:
        if latest_depth_frame is not None:
            depth_list = latest_depth_frame.tolist()
            return JSONResponse(content={"depth": depth_list})
        return JSONResponse(content={"error": "No depth frame available"}, status_code=404)

# --- IMU 데이터 GET ---
@app.get("/imu")
def get_imu():
    with frame_lock:
        if latest_imu_data["accel"] or latest_imu_data["gyro"]:
            return JSONResponse(content=latest_imu_data)
        return JSONResponse(content={"error": "No IMU data available"}, status_code=404)

def convert_to_mono_16k_pydub(src_path: str, dst_path: str):
    try:
        audio = AudioSegment.from_file(src_path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(dst_path, format='wav', codec="pcm_s16le" )
        #audio.export(dst_path, format="wav")
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

@app.get("/led")
async def led(r: str = '255', g: str = '255', b: str = '255'):
    try:
        subprocess.run(["./g1_vui", r, g, b], check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"g1_vui 실행 실패: {e}"}

    return {"message": f"LED 색상 설정 완료: ({r}, {g}, {b})"}
"""
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
"""

success = convert_to_mono_16k_pydub('intel_inside.mp3', 'intel.wav')
subprocess.Popen(["./g1_audio", 'intel.wav']) # async