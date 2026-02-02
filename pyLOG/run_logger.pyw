'''
This is the python program to run logger only 
'''

import os
import traceback
import ctypes
import time
import threading
from collections import Counter
from .pyLOG import *
from .debugLog import *


def popout(level = 0):
    if level == 0:
        return 
    elif level == 1:
        ctypes.windll.user32.MessageBoxW(0, 'Warning: System is reaching the limit', "Logger", 1)
    elif level > 2:
        ctypes.windll.user32.MessageBoxW(0, 'Warning: System is error', "Logger", 1)

def main_func(config_file = None):
    # last_warning = 0
    debugLogger = debugLog(config_file).logger
    current_exe = os.popen('wmic process get description').read().strip().replace(' ', '').split('\n\n')
    hashDict = Counter(current_exe) 
    # thread = threading.Thread(target=popout, args=(0))
    if 'pylogger_running.exe' in hashDict and hashDict['pylogger_running.exe'] > 1:
        debugLogger.warning('start fail: pylogger is running in the background')
        return 
    else:
        try:
            log = pyLOG()
            debugLogger.info('pyLOG initialization succeed')
        except Exception as err:
            debugLogger.warning('pyLOG initialization failed')
            debugLogger.error(traceback.format_exc())
            return
        debugLogger.info('pyLOG logging started')
        while(1):
            try:
                log.log()
                # warning = log.warning
                # if last_warning != warning:
                #     if warning == 0 and thread.is_alive: # error clean
                #         thread.join()
                #     elif warning != last_warning: # error changes
                #         if thread.is_alive():
                #             wd=ctypes.windll.user32.FindWindowA(0,"Logger") # close window 
                #             ctypes.windll.user32.SendMessageA(wd,0x0010,0,0)
                #             thread.join()
                #         thread = threading.Thread(target=popout, kwargs = {'level': warning})  
                #         thread.start()
                        
                #     last_warning = warning                     

            except Exception as err:
                debugLogger.warning('logging failed')
                debugLogger.critical(traceback.format_exc())                    
                return 
                
if __name__ == "__main__":
    main_func()