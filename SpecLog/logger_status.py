"""Shared process-status checks for the interactive SpecLogger worker."""

import ctypes
import os


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
