"""Shared process-status checks for the interactive SpecLogger worker."""

import ctypes
import os
import time


LOGGER_MUTEX_NAME = "Local\\SpecLog.SpecLogger"


def is_logger_running():
    """Return whether the logger mutex is visible in the current session."""
    if os.name != "nt":
        return False
    synchronize = 0x00100000
    handle = ctypes.windll.kernel32.OpenMutexW(
        synchronize, False, LOGGER_MUTEX_NAME
    )
    if not handle:
        return False
    ctypes.windll.kernel32.CloseHandle(handle)
    return True


def has_recent_log_activity(path, log_interval):
    """Return whether a log file was updated within the logger grace period."""
    try:
        age = time.time() - os.path.getmtime(path)
        interval = max(1.0, float(log_interval))
    except (OSError, TypeError, ValueError):
        return False
    return age <= max(5.0, interval * 2.5)
