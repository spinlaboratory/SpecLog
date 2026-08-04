"""Command-line controller for starting SpecMonitor."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


def _build_parser():
    parser = argparse.ArgumentParser(prog="SpecMonitor")
    parser.add_argument(
        "number_of_file",
        type=int,
        nargs="?",
        default=10,
        help="Number of recent files to plot in real time",
    )
    parser.add_argument(
        "-debug",
        type=str,
        default="False",
        choices=["True", "False"],
        help="Start SpecMonitor with a visible debug console",
    )
    return parser


def _runner_path():
    runner = shutil.which("SpecMonitor_running")
    if runner:
        return runner
    suffix = ".exe" if os.name == "nt" else ""
    return str(Path(sys.argv[0]).resolve().parent / f"SpecMonitor_running{suffix}")


def main_func(argv=None):
    args = _build_parser().parse_args(argv)
    monitor_args = [str(args.number_of_file)]

    if args.debug == "True":
        # Run in this console process so exceptions and diagnostic output stay
        # visible to the operator.
        from .run_monitor import main_func as run_monitor

        return run_monitor(monitor_args)

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    subprocess.Popen(
        [_runner_path(), *monitor_args],
        creationflags=creationflags,
    )
    print("SpecMonitor started")


if __name__ == "__main__":
    main_func()
