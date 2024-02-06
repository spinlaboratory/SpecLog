'''
This is the python program to run monitor only 
'''

import os
import sys
from collections import Counter
import argparse
from .monitor import *

def main_func():
    parser = argparse.ArgumentParser(prog='pyB12monitor')
    parser.add_argument('number_of_file', type=int, nargs='?', default = 10, 
                        help='To select number of files to plot in real-time')
    args = parser.parse_args()
    current_exe = os.popen('wmic process get description').read().strip().replace(' ', '').split('\n\n')
    hashDict = Counter(current_exe) 
    if 'pyB12monitor.exe' in hashDict and hashDict['pyB12monitor.exe'] > 1:
        exit()
    else:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        app.exec()

if __name__ == "__main__":
    main_func()