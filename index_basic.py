
import uvicorn

if __name__ == '__main__':    
    uvicorn.run("main_basic:app",host="0.0.0.0",port=59521,reload=False)
