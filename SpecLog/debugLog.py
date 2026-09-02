"""
This is debug log class for logger

Author: Yen-Chun Huang

Company: Bruker BioSpin
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
        self.logger.propagate = False

        # Reconfiguration should replace this class's handlers rather than
        # multiplying every subsequent log message.
        for handler in list(self.logger.handlers):
            if getattr(handler, "_speclog_handler", False):
                self.logger.removeHandler(handler)
                handler.close()

        ch = logging.FileHandler(str(logpath))
        ch._speclog_handler = True
        ch.setLevel(logging.INFO)
        ch2 = logging.StreamHandler()
        ch2._speclog_handler = True
        ch2.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - [%(filename)s:%(lineno)d] - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        ch2.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.addHandler(ch2)
