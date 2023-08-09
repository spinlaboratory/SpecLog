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
        if 'pyB12logger_running.exe' in hashDict and hashDict['pyB12logger_running.exe'] > 0:
            print('pyB12logger has started already.')
            return 
        else:
            os.startfile('pyB12logger_running.exe')
            print('pyB12logger starts')
    
    elif args.status == 'stop':
        os.system("taskkill /im pyB12logger_running.exe /F")
        print('pyB12logger stops')
    else:
        return

if __name__ == "__main__":
    main_func()