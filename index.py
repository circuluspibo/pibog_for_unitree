
import uvicorn
import playsound

playsound.playsound('intel_inside.mp3')

if __name__ == '__main__':    
    uvicorn.run("main:app",host="0.0.0.0",port=59521,reload=False)