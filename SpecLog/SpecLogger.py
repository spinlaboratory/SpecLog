"""
This is the python program to control SpecLog
"""

import os
import sys
import argparse
import shutil
import subprocess
from collections import Counter
from .SpecLog import *

# auto start and adding icon to desktop (public)
startup_folder = os.path.join(
    os.environ["APPDATA"],
    r"Microsoft\Windows\Start Menu\Programs\Startup"
)
desktop_folder = os.path.join(os.environ["USERPROFILE"], "Desktop")

source_running_logger = os.path.join(
    os.path.dirname(sys.executable), "scripts", "SpecLogger_running.exe"
)

source_monitor = os.path.join(
    os.path.dirname(sys.executable), "scripts", "pymonitor.exe"
)

def main_func():
    parser = argparse.ArgumentParser(prog="SpecLogger")
    parser.add_argument(
        "status",
        type=str,
        nargs="?",
        default=None,
        choices=["start", "stop"],
        help="To start/stop SpecLogger. If no argument, the SpecLogger will start by default",
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
        help="To enable/disable SpecLogger at startup.",
    )
    parser.add_argument(
        "-debug",
        type=str,
        default="False",
        choices=["True", "False"],
        help="To start debug console SpecLogger.",
    )
    args = parser.parse_args()

    if args.startup == "True":
        target = os.path.join(startup_folder, "SpecLogger_running.exe")
        if not os.path.exists(target):
            shutil.copy(source_running_logger, target)
            print("SpecLogger will run on startup.")
    elif args.startup == "False":
        if not os.path.exists(startup_folder + "/SpecLogger_running.exe"):
            print(startup_folder + "SpecLogger_running.exe")
            print("SpecLogger does not run on startup.")
        else:
            os.remove(startup_folder + "/SpecLogger_running.exe")
            print("SpecLogger will not run on startup.")

    if args.desktop == "True":
        target_logger = os.path.join(desktop_folder, "SpecLogger_running.exe")
        target_monitor = os.path.join(desktop_folder, "pymonitor.exe")

        if not os.path.exists(target_logger):
            shutil.copy(source_running_logger, target_logger)
            print("Create SpecLogger_running.exe on the desktop.")
        else:
            print("SpecLogger_running.exe is on desktop already.")

        if not os.path.exists(target_monitor):
            shutil.copy(source_monitor, target_monitor)
            print("Create pymonitor.exe on the desktop.")
        else:
            print("pymonitor.exe is on desktop already.")

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
            "SpecLogger_running.exe" in hashDict
            and hashDict["SpecLogger_running.exe"] > 0
        ):
            print("SpecLogger has started already.")
            return

        else:
            if args.debug == "False":
                subprocess.Popen(
                    "SpecLogger_running.exe", creationflags=subprocess.CREATE_NO_WINDOW
                )
                print("SpecLogger started")
            elif args.debug == "True":
                os.startfile("SpecLogger_running.exe")
                print("SpecLogger debug mode started")

    elif args.status == "stop":
        os.system("taskkill /im SpecLogger_running.exe /F /t")
        print("SpecLogger stopped")
    else:  # ignore
        return


if __name__ == "__main__":
    main_func()
