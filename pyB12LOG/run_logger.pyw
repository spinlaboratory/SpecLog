import os
import argparse
from collections import Counter
from .pyB12LOG import *

def main_func():
    parser = argparse.ArgumentParser(prog='pyB12logger')
    parser.add_argument('status', type=str, nargs='?', default = 'start', choices = ['start', 'stop'],
                        help='To start/stop pyB12logger. If no argument, the pyB12logger will start by default')
    args = parser.parse_args()
    if args.status == 'start':
        current_exe = os.popen('wmic process get description').read().strip().replace(' ', '').split('\n\n')
        hashDict = Counter(current_exe) 
        if 'pyB12logger.exe' in hashDict and hashDict['pyB12logger.exe'] > 1:
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

    elif args.status == 'stop':
        os.system("taskkill /im pyB12logger.exe /F")
        print('pyB12logger has been terminated.')
    else:
        return
            
if __name__ == "__main__":
    main_func()