import os
from collections import Counter
from .plotter import *

def main_func():
    current_exe = os.popen('wmic process get description').read().strip().replace(' ', '').split('\n\n')
    hashDict = Counter(current_exe) 
    if 'pyB12plotter.exe' in hashDict and hashDict['pyB12plotter.exe'] > 1:
        exit()
    else:
        fig = plotter()

if __name__ == "__main__":
    main_func()