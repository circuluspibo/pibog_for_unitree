from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse, Response
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
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
import cv2
import numpy as np
import pyrealsense2 as rs
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

async def generate_depth_video():
    while True:
        with frame_lock:
            if latest_depth_frame is not None:
                ret, jpeg = cv2.imencode('.jpg', latest_depth_frame)
                if ret:
                    frame = jpeg.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        await asyncio.sleep(0.1)


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

app = FastAPI()

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


@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_video(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/depth_feed")
async def depth_image():
    return StreamingResponse(generate_depth_image(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/video_raw")
async def video_raw():
    with frame_lock:
        if latest_color_frame is not None and latest_depth_frame is not None:
            # 1. 두 프레임을 바이너리(bytes)로 변환
            # RGB: 640*480*3 bytes, Depth: 640*480*2 bytes
            color_bytes = latest_color_frame.tobytes()
            depth_bytes = latest_depth_frame.tobytes()
            
            # 2. 하나로 합쳐서 전송
            return Response(content=color_bytes + depth_bytes, media_type="application/octet-stream")
        
        return JSONResponse(content={"error": "Frames not ready"}, status_code=404)

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
