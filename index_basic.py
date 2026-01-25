#arm_freq=1200
#core_freq=300
#sdram_freq=2500
#over_voltage=-1
#force_turbo=0

import uvicorn

if __name__ == '__main__':    
    uvicorn.run("main_basic:app",host="0.0.0.0",port=59521,reload=False)
