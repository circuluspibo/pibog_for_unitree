
import uvicorn

if __name__ == '__main__':    
    uvicorn.run("main2:app",host="0.0.0.0",port=59511,reload=False)