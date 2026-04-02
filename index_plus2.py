import uvicorn

if __name__ == '__main__':    
    uvicorn.run("main_plus2:app",host="0.0.0.0",port=58521,reload=False)
