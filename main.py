from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import cv2
import uvicorn
import threading

app = FastAPI()
camera = 0

def gen_frames():
    camera = cv2.VideoCapture(0)
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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)