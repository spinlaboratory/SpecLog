import os
import sys
import argparse
import shutil
from collections import Counter
from .pyB12LOG import *

def main_func():

    parser = argparse.ArgumentParser(prog='pyB12logger')
    parser.add_argument('status', type=str, nargs='?', default = 'start', choices = ['start', 'stop'],
                        help='To start/stop pyB12logger. If no argument, the pyB12logger will start by default')
    parser.add_argument('-desktop', type=bool, default = False,
                        help='To create desktop icons')
    parser.add_argument('-startup', type=bool,
                        help='To enable/disable pyB12logger at startup.')
    args = parser.parse_args()
    if args.status == 'start':
        current_exe = os.popen('wmic process get description').read().strip().replace(' ', '').split('\n\n')
        hashDict = Counter(current_exe) 

        #auto start and adding icon to desktop (public)
        startup_folder = os.path.normpath('C:/ProgramData/Microsoft/Windows/Start Menu/Programs/StartUp/')
        desktop_folder = os.path.normpath('C:/Users/Public/Desktop/')
        source_running_logger = os.path.dirname(sys.executable) + '/scripts/pyB12logger_running.exe' 
        source_plotter = os.path.dirname(sys.executable) + '/scripts/pyB12plotter.exe' 

        if args.startup:
            if not os.path.exists(startup_folder + 'pyB12logger_running.exe'):
                shutil.copy(source_running_logger, startup_folder)
                print('Startup Enables.')
            else:
                print('Startup has been enabled.')
        elif args.startup == False:
            if not os.path.exists(startup_folder + 'pyB12logger_running.exe'):
                print('Startup has not been enabled.')
            else:
                os.remove(startup_folder + 'pyB12logger_running.exe')
                print('Startup disables.')

        if args.desktop:
            if not os.path.exists(desktop_folder + 'pyB12logger_running.exe'):
                shutil.copy(source_running_logger, desktop_folder)
                print('Create pyB12logger_running.exe on the desktop.')
            else:
                print('pyB12logger_running.exe is on desktop already.')
            
            if not os.path.exists(desktop_folder + 'pyB12plotter.exe'):
                shutil.copy(source_plotter, desktop_folder)
                print('pyB12plotter.exe is on desktop already.')


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