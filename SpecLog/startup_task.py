"""Shared Windows Task Scheduler definition for SpecLogger."""

import os


TASK_NAME = "SpecLogger"
TASK_SCHEDULER = os.path.join(
    os.environ.get("SystemRoot", r"C:\Windows"), "System32", "schtasks.exe"
)
POWERSHELL = os.path.join(
    os.environ.get("SystemRoot", r"C:\Windows"),
    "System32",
    "WindowsPowerShell",
    "v1.0",
    "powershell.exe",
)


def query_arguments(xml=False):
    arguments = ["/Query", "/TN", TASK_NAME]
    if xml:
        arguments.append("/XML")
    return arguments


def control_arguments(action):
    if action not in {"start", "stop"}:
        raise ValueError(f"Unsupported task action: {action}")
    return ["/Run" if action == "start" else "/End", "/TN", TASK_NAME]


def create_arguments(executable):
    return [
        "/Create",
        "/TN",
        TASK_NAME,
        "/TR",
        f'"{executable}"',
        "/SC",
        "ONSTART",
        "/DELAY",
        "0000:30",
        "/RU",
        "SYSTEM",
        "/RL",
        "HIGHEST",
        "/F",
    ]


def disable_arguments():
    return ["/Change", "/TN", TASK_NAME, "/DISABLE"]


def state_arguments():
    return [
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        f"$task = Get-ScheduledTask -TaskName '{TASK_NAME}' "
        "-ErrorAction Stop; [Console]::Out.Write([int]$task.State)",
    ]
