"""
This is the python program to control SpecLog
"""

import os
import sys
import argparse
import shutil
import subprocess
from .SpecLog import *
from .startup_task import (
    TASK_SCHEDULER,
    control_arguments,
    create_arguments,
    disable_arguments,
    query_arguments,
)

# System-start task and desktop shortcuts (public)
desktop_folder = os.path.join(os.environ["USERPROFILE"], "Desktop")

source_running_logger = os.path.join(
    os.path.dirname(sys.executable), "scripts", "SpecLogger_running.exe"
)

source_monitor = os.path.join(
    os.path.dirname(sys.executable), "scripts", "SpecMonitor_running.exe"
)


def _run_task_scheduler(arguments, runner=None):
    runner = runner or subprocess.run
    return runner(
        [TASK_SCHEDULER, *arguments],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def configure_startup(enabled, executable=None, runner=None):
    """Create/enable or disable the no-login SpecLogger startup task."""
    executable = os.path.abspath(executable or source_running_logger)
    if enabled:
        if not os.path.isfile(executable):
            raise RuntimeError(f"SpecLogger runner was not found: {executable}")
        result = _run_task_scheduler(
            create_arguments(executable),
            runner,
        )
        success_message = "SpecLogger will run at system startup without login."
    else:
        query = _run_task_scheduler(
            query_arguments(), runner
        )
        if query.returncode:
            return "SpecLogger startup task is not installed."
        result = _run_task_scheduler(
            disable_arguments(), runner
        )
        success_message = "SpecLogger startup task is disabled."

    if result.returncode:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            details
            or "Windows Task Scheduler rejected the request. Run as administrator."
        )
    return success_message


def control_scheduled_logger(action, runner=None):
    """Start or stop SpecLogger exclusively through Windows Task Scheduler."""
    query = _run_task_scheduler(
        query_arguments(), runner
    )
    if query.returncode:
        details = (query.stderr or query.stdout).strip()
        raise RuntimeError(
            details
            or "The SpecLogger scheduled task is not installed or is unavailable. "
            "Enable startup first with 'SpecLogger -startup True'."
        )
    result = _run_task_scheduler(
        control_arguments(action), runner
    )
    if result.returncode:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            details
            or "Windows Task Scheduler rejected the request. Run as administrator."
        )
    return (
        "SpecLogger scheduled task start requested."
        if action == "start"
        else "SpecLogger scheduled task stopped."
    )

def _build_parser():
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
        help="To enable/disable SpecLogger at startup without login.",
    )
    parser.add_argument(
        "-debug",
        type=str,
        default="False",
        choices=["True", "False"],
        help="To start debug console SpecLogger.",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Open the public SpecLog configuration editor.",
    )
    return parser


def main_func(argv=None):
    args = _build_parser().parse_args(argv)

    if args.config:
        from .config_editor import main_func as open_config_editor

        return open_config_editor()

    if args.startup is not None:
        try:
            print(configure_startup(args.startup == "True"))
        except RuntimeError as error:
            print(f"Could not configure SpecLogger startup: {error}", file=sys.stderr)
            return 1

    if args.desktop == "True":
        target_logger = os.path.join(desktop_folder, "SpecLogger_running.exe")
        target_monitor = os.path.join(desktop_folder, "SpecMonitor.exe")

        if not os.path.exists(target_logger):
            shutil.copy(source_running_logger, target_logger)
            print("Create SpecLogger_running.exe on the desktop.")
        else:
            print("SpecLogger_running.exe is on desktop already.")

        if not os.path.exists(target_monitor):
            shutil.copy(source_monitor, target_monitor)
            print("Create SpecMonitor.exe on the desktop.")
        else:
            print("SpecMonitor.exe is on desktop already.")

    if not args.startup and not args.desktop and not args.status:  # not arguments
        args.status = "start"

    if args.status in {"start", "stop"}:
        try:
            task_message = control_scheduled_logger(args.status)
        except RuntimeError as error:
            print(f"Could not control SpecLogger scheduled task: {error}", file=sys.stderr)
            return 1
        print(task_message)
        return 0


if __name__ == "__main__":
    main_func()
