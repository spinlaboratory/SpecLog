'''
This is the python program to run logger only 
'''

import os
import traceback
import ctypes
import time
import threading
from collections import Counter
from .SpecLog import *
from .debugLog import *

_logger_mutex = None


def _another_logger_is_running():
    global _logger_mutex
    if os.name != "nt":
        return False
    _logger_mutex = ctypes.windll.kernel32.CreateMutexW(
        None, False, "Local\\SpecLog.SpecLogger"
    )
    return ctypes.windll.kernel32.GetLastError() == 183


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
    # thread = threading.Thread(target=popout, args=(0))
    if _another_logger_is_running():
        debugLogger.warning('start fail: SpecLogger is running in the background')
        return 
    else:
        try:
            log = SpecLog(config_file)
            debugLogger.info('SpecLog initialization succeed')
        except Exception as err:
            debugLogger.warning('SpecLog initialization failed')
            debugLogger.error(traceback.format_exc())
            return
        debugLogger.info('SpecLog logging started')
        try:
            while(1):
                log.log()
                # Avoid a tight loop that continuously rescans serial ports
                # between configured logging intervals.
                time.sleep(max(0.1, log.delay))
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
        finally:
            log.close()
                
if __name__ == "__main__":
    main_func()
