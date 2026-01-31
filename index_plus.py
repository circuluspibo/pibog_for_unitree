import uvicorn

if __name__ == '__main__':    
    uvicorn.run("main_plus:app",host="0.0.0.0",port=59521,reload=False)
