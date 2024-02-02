'''
This is the python program to run logger only 
'''

import os
import traceback
from collections import Counter
from .pyB12LOG import *
from .debugLog import *

def main_func(config_file = None):
    debugLogger = debugLog(config_file).logger
    current_exe = os.popen('wmic process get description').read().strip().replace(' ', '').split('\n\n')
    hashDict = Counter(current_exe) 
    if 'pyB12logger_running.exe' in hashDict and hashDict['pyB12logger_running.exe'] > 1:
        debugLogger.warning('start fail: pyB12logger is running in the background')
        return 
    else:
        try:
            log = pyB12LOG()
            debugLogger.info('pyB12LOG initialization succeed')
        except Exception as err:
            debugLogger.warning('pyB12LOG initialization failed')
            debugLogger.error(traceback.format_exc())
            
            return
        
        debugLogger.info('pyB12LOG logging started')
        while(1):
            try:
                log.log()
            except Exception as err:
                debugLogger.warning('logging failed')
                debugLogger.critical(traceback.format_exc())                    
                return 
                
if __name__ == "__main__":
    main_func()