'''
This is the python program to run monitor only 
'''

import os
import sys
import ctypes
import argparse
from .monitor import *

_monitor_mutex = None


def _another_monitor_is_running():
    """Use a Windows named mutex instead of repeatedly querying processes."""
    global _monitor_mutex
    if os.name != "nt":
        return False
    _monitor_mutex = ctypes.windll.kernel32.CreateMutexW(
        None, False, "Local\\SpecLog.SpecMonitor"
    )
    return ctypes.windll.kernel32.GetLastError() == 183

def main_func(argv=None):
    parser = argparse.ArgumentParser(prog='SpecMonitor')
    parser.add_argument('number_of_file', type=int, nargs='?', default = 10, 
                        help='To select number of files to plot in real-time')
    args = parser.parse_args(argv)
    if _another_monitor_is_running():
        return
    else:
        qt_args = [sys.argv[0], *(argv if argv is not None else sys.argv[1:])]
        app = QApplication(qt_args)
        window = MainWindow(number_of_files=max(1, args.number_of_file))
        window.show()
        app.exec()

if __name__ == "__main__":
    main_func()
