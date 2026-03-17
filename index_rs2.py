
import uvicorn

if __name__ == '__main__':    
    uvicorn.run("main_rs2:app",host="0.0.0.0",port=59512,reload=False)
