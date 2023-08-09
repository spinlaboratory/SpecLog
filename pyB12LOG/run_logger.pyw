import os
from collections import Counter
from .pyB12LOG import *

def main_func():
    current_exe = os.popen('wmic process get description').read().strip().replace(' ', '').split('\n\n')
    hashDict = Counter(current_exe) 
    if 'pyB12logger_running.exe' in hashDict and hashDict['pyB12logger_run.exe'] > 1:
        return 
    else:
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