'''
This is the python program to control pyB12logger 
'''

import os
import sys
import argparse
import shutil
import subprocess
from collections import Counter
from .pyB12LOG import *

def main_func():

    parser = argparse.ArgumentParser(prog='pyB12logger')
    parser.add_argument('status', type=str, nargs='?', default = None, choices = ['start', 'stop'],
                        help='To start/stop pyB12logger. If no argument, the pyB12logger will start by default')
    parser.add_argument('-desktop', type=str, default = False, choices = ['True', 'False'],
                        help='To create desktop icons')
    parser.add_argument('-startup', type=str, default = None, choices = ['True', 'False'],
                        help='To enable/disable pyB12logger at startup.')
    parser.add_argument('-debug', type=str, default = 'False', choices = ['True', 'False'],
                        help='To start debug console pyB12logger.')
    args = parser.parse_args()

    if args.startup == 'True':
        if not os.path.exists(startup_folder + '/pyB12logger_running.exe'):
            shutil.copy(source_running_logger, startup_folder)
            print('pyB12logger will run on startup.')
    elif args.startup == 'False':
        if not os.path.exists(startup_folder + '/pyB12logger_running.exe'):
            print(startup_folder + 'pyB12logger_running.exe')
            print('pyB12logger does not run on startup.')
        else:
            os.remove(startup_folder + '/pyB12logger_running.exe')
            print('pyB12logger will not run on startup.')

    if args.desktop == 'True':
        if not os.path.exists(desktop_folder + '/pyB12logger_running.exe'):
            shutil.copy(source_running_logger, desktop_folder)
            print('Create pyB12logger_running.exe on the desktop.')
        else:
            print('pyB12logger_running.exe is on desktop already.')
        
        if not os.path.exists(desktop_folder + '/pyB12monitor.exe'):
            shutil.copy(source_monitor, desktop_folder)
            print('Create pyB12monitor_running.exe on the desktop.')
        else:    
                print('pyB12monitor.exe is on desktop already.')
    
    if not args.startup and not args.desktop and not args.status: # not arguments 
        args.status = 'start'

    if args.status == 'start':
        current_exe = os.popen('wmic process get description').read().strip().replace(' ', '').split('\n\n')
        hashDict = Counter(current_exe) 

        #auto start and adding icon to desktop (public)
        startup_folder = os.path.normpath('C:/ProgramData/Microsoft/Windows/Start Menu/Programs/StartUp/')
        desktop_folder = os.path.normpath('C:/Users/Public/Desktop/')
        source_running_logger = os.path.dirname(sys.executable) + '/scripts/pyB12logger_running.exe' 
        source_monitor = os.path.dirname(sys.executable) + '/scripts/pyB12monitor.exe' 


        if 'pyB12logger_running.exe' in hashDict and hashDict['pyB12logger_running.exe'] > 0:
            print('pyB12logger has started already.')
            return 
        
        else:
            if args.debug == 'False':          
                subprocess.Popen('pyB12logger_running.exe', creationflags = subprocess.CREATE_NO_WINDOW)
                print('pyB12logger starts')
            elif args.debug == 'True': 
                os.startfile('pyB12logger_running.exe')
                print('pyB12logger debug mode starts')
    
    elif args.status == 'stop':
        os.system("taskkill /im pyB12logger_running.exe /F")
        print('pyB12logger stops')
    else: # ignore
        return

if __name__ == "__main__":
    main_func()