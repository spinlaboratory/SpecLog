"""
This is the python program to control pyB12logger 
"""

import os
import sys
import argparse
import shutil
import subprocess
from collections import Counter
from .pyLOG import *

# auto start and adding icon to desktop (public)
startup_folder = os.path.join(
    os.environ["APPDATA"],
    r"Microsoft\Windows\Start Menu\Programs\Startup"
)
desktop_folder = os.path.join(os.environ["USERPROFILE"], "Desktop")

source_running_logger = os.path.join(
    os.path.dirname(sys.executable), "scripts", "pylogger_running.exe"
)

source_monitor = os.path.join(
    os.path.dirname(sys.executable), "scripts", "pylogger_monitor.exe"
)

def main_func():
    parser = argparse.ArgumentParser(prog="pylogger")
    parser.add_argument(
        "status",
        type=str,
        nargs="?",
        default=None,
        choices=["start", "stop"],
        help="To start/stop pylogger. If no argument, the pylogger will start by default",
    )
    parser.add_argument(
        "-desktop",
        type=str,
        default=False,
        choices=["True", "False"],
        help="To create desktop icons",
    )
    parser.add_argument(
        "-startup",
        type=str,
        default=None,
        choices=["True", "False"],
        help="To enable/disable pylogger at startup.",
    )
    parser.add_argument(
        "-debug",
        type=str,
        default="False",
        choices=["True", "False"],
        help="To start debug console pylogger.",
    )
    args = parser.parse_args()

    if args.startup == "True":
        target = os.path.join(startup_folder, "pylogger_running.exe")
        if not os.path.exists(target):
            shutil.copy(source_running_logger, target)
            print("pylogger will run on startup.")
    elif args.startup == "False":
        if not os.path.exists(startup_folder + "/pylogger_running.exe"):
            print(startup_folder + "pylogger_running.exe")
            print("pylogger does not run on startup.")
        else:
            os.remove(startup_folder + "/pylogger_running.exe")
            print("pylogger will not run on startup.")

    if args.desktop == "True":
        target_logger = os.path.join(desktop_folder, "pylogger_running.exe")
        target_monitor = os.path.join(desktop_folder, "pylogger_monitor.exe")

        if not os.path.exists(target_logger):
            shutil.copy(source_running_logger, target_logger)
            print("Create pylogger_running.exe on the desktop.")
        else:
            print("pylogger_running.exe is on desktop already.")

        if not os.path.exists(target_monitor):
            shutil.copy(source_monitor, target_monitor)
            print("Create pylogger_monitor.exe on the desktop.")
        else:
            print("pylogger_monitor.exe is on desktop already.")

    if not args.startup and not args.desktop and not args.status:  # not arguments
        args.status = "start"

    if args.status == "start":
        current_exe = (
            os.popen("wmic process get description")
            .read()
            .strip()
            .replace(" ", "")
            .split("\n\n")
        )
        hashDict = Counter(current_exe)

        if (
            "pylogger_running.exe" in hashDict
            and hashDict["pylogger_running.exe"] > 0
        ):
            print("pylogger has started already.")
            return

        else:
            if args.debug == "False":
                subprocess.Popen(
                    "pylogger_running.exe", creationflags=subprocess.CREATE_NO_WINDOW
                )
                print("pylogger started")
            elif args.debug == "True":
                os.startfile("pylogger_running.exe")
                print("pylogger debug mode started")

    elif args.status == "stop":
        os.system("taskkill /im pylogger_running.exe /F /t")
        print("pylogger stopped")
    else:  # ignore
        return


if __name__ == "__main__":
    main_func()
