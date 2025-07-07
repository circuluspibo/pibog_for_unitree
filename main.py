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

app = FastAPI()

UPLOAD_DIR = "uploaded_audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 정적 파일 서비스 (업로드한 파일 재생 가능)
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")

app = FastAPI()
camera = 0

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