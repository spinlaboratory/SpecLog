"""
This is debug log class for logger

Author: Yen-Chun Huang

Company: Bridge 12 Technologies. Inc
"""

import logging
from .loggerConfig import *
import os


class debugLog:
    def __init__(self, config_file: str = None):
        config = loggerConfig(config_file)
        settings = config.settings
        log_dir = settings["log_folder_location"] + "/LOG/"

        if not os.path.exists(log_dir):
            os.mkdir(log_dir)

        logpath = log_dir + "/debug_log.txt"
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        ch = logging.FileHandler(str(logpath))
        ch.setLevel(logging.INFO)
        ch2 = logging.StreamHandler()
        ch2.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - [%(filename)s:%(lineno)d] - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        ch2.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.addHandler(ch2)
