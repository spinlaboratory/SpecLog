from .pyB12LOG import *

def main_func():
    log = pyB12LOG()
    debugLogger = log.initDebugLog()
    while(1):
        try:
            log.log()
        except Exception as err:
            debugLogger.info(err)
            log = pyB12LOG()
    
if __name__ == "__main__":
    main_func()