"""
This is configuration file for logger

The class has name: 'loggerConfig'. It has one following functions:

Read a configuration file to create settings dictionary, devices dictionary and command dictionary

Logger will use the three dictionaries.

Author: Yen-Chun Huang

Company: Bridge 12 Technologies. Inc
"""

import time
import os
from .config.config import (
    CONFIG,
)  # this will automatically duplicate the config file to default folder
from configparser import ConfigParser

device_default = {
    "device_status": False,
    "address": None,
    "id_command": "*IDN?",
    "baud_rate": 9600,
    "termination": "\n",
    "data_bits": 8,
    "flow_control": None,
    "parity": None,
    "stop_bits": None,
    "delimiter": ",",
    "index": 0,
}

# command format in config file: variable: command, alias, min, max, static
command_default = {
    "command": None,
    "alias": None,
    "min": None,
    "max": None,
    "static": None,
    "bits": None,
    "bit_static": None,
    "indicators": None,
    "indicators_reverse": None
}


class loggerConfig:
    def __init__(self, config_file: str = None):
        """
        config_dir (str): the directory to the config file

        """
        self.config, self.config_file = self._getConfig(config_file)

        self.settings = self._getSettings()
        self.devices = self._getDevices()
        self.commands = self._getCommands()

    def _getConfig(self, config_file):
        if config_file:
            config_dir = os.path.dirname(config_file)  # get directory
            config_name = os.path.basename(config_file)  # get file name

        else:
            # default directory and file name
            config_dir = CONFIG["SETTINGS"]["log_folder_location"] + "/B12TLOG_Config/"
            config_name = "config.cfg"
            config_file = config_dir + config_name

        config = ConfigParser()
        config.read(config_file)
        return config, config_file

    def _getSettings(self):
        """ """
        settings = {}
        for key, value in self.config["SETTINGS"].items():
            if value.isdigit() or value in ["True", "False", "None"]:
                settings[key] = eval(value)
            else:
                settings[key] = value
        return settings

    def _getDevices(self):
        devices = {}
        for section in self.config.keys():
            if section not in ["DEFAULT", "SETTINGS"]:
                temp_dict = {}  # new dictionary for devices
                for key in device_default.keys():
                    if key in self.config[section].keys():
                        if key in [
                            "device_status",
                            "baud_rate",
                            "flow_control",
                            "parity",
                            "stop_bits",
                            "data_bits",
                            "index",
                        ]:
                            temp_dict[key] = eval(self.config[section][key])
                        elif key == "termination":
                            termination = self._getTermination(
                                self.config[section][key]
                            )
                            temp_dict[key] = termination
                        else:
                            temp_dict[key] = self.config[section][key]

                temp_dict = {**device_default, **temp_dict}
                devices[section] = temp_dict

        return devices

    def _getCommands(self):
        commands = {}
        for section in self.config.keys():
            if section not in ["DEFAULT", "SETTINGS"]:
                temp_dict = {}  # new dictionary for commands
                for key in self.config[section].keys():
                    if (
                        key not in device_default.keys()
                    ):  # in key in config section but not for device settings
                        command_info = self._command_analysis(self.config[section][key])
                        temp_dict[key] = command_info  # use variable as key

                commands[section] = temp_dict
        return commands

    def _command_analysis(self, command_string: str):
        """
        Arg:
            command_string (str): a command string with the format in config file: variable: command, alias, min, max, static

        Return:
            command_info (dict): the prepared dict with the same format as command_default

        """
        command_info = command_default.copy()
        command_list = command_string.split(", ")
        for index, item in enumerate(command_list):
            item = item.strip()  # remove leading and tailing white space
            if index == 0:
                command_info["command"] = item

            else:
                key, value = item.split("=")  # get key and value from item
                key = key.strip()  # remove leading and tailing white space
                value = value.strip()  # remove leading and tailing white space

                if key == "alias":
                    command_info["alias"] = value

                elif key == 'bit_static':
                    command_info['bit_static'] = str(value)
                else:
                    command_info[key] = eval(value)
        
        if command_info['indicators']:
            command_info['indicators_reverse'] = [False] * len(command_info['indicators'])
            for i in range(len(command_info['indicators'])):
                if '*' in command_info['indicators'][i]:
                    command_info['indicators_reverse'][i] = True
                    command_info['indicators'][i] = command_info['indicators'][i].replace('*', '')

        return command_info

    def _getTermination(self, termination: str):
        """
        Return CR or Lf in string

        Args:
            termination (str): CR, LF, CRLF or LFCR

        Return:
            termination (str): termination in string with backslash
        """

        if termination.replace("LF", "").replace("CR", ""):
            self.debugLog.error("Termination is not valid")
            raise ValueError("Termination is not valid")
        eval_termination = termination.replace("LF", "\n").replace("CR", "\r")

        return eval_termination


if __name__ == "__main__":
    config = loggerConfig()
