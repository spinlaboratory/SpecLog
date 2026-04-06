"""
SpecLog: The logging program for instrumentations

SpecLog: read configurations, get available devices, send command and save return.

Author: Yen-Chun Huang

Company: Bruker BioSpin
"""

from .device import *
import time
import datetime
import os
from .loggerConfig import *
from .debugLog import *


class SpecLog:
    def __init__(self, config_file: str = None):
        self.config = loggerConfig(config_file)
        self.debugLogger = debugLog(config_file).logger
        self.settings = self.config.settings
        self.commands = (
            self.config.commands
        )  # dictionary {model: {variable: {command, alias, min, max, static}}}
        self.device_config = self.config.devices

        self.log_dir = self.settings["log_folder_location"] + "/LOG/"
        self._checkDirectory()

        self.delay = int(self.settings["log_interval"])
        self.max_size = int(self.settings["save_file_size_kb"])

        self.connectDevices()
        self.reconnectDevices()
        
        self.data_by_variable = self._getDataDictByVariable(
            self.commands
        )  # initial empty dictionary for storing data
        
        self.header = self._makeLogHeader()
        self.last_query_time = None
        self.current_log_file = None
        self.warning = 0

    def log(self):
        """
        Send command to a valid device, analyze return and save data to log file

        It runs one time only.
        """
        # if not self.current_log_file:
        #     self.debugLogger.info("new log file created")
        #     self._createNewLog()

        now = time.time()
        if self.reconnectDevices():  # check the device connections
            self.debugLogger.info("A device is reconnected")
        if not self.last_query_time or now - self.last_query_time > self.delay:
            warning_level = 0
            self._setTimeInDataDictByVariable()  # update time
            devices_info = (
                self.devices.devices_info
            )  # dictionary: {model: {status, config_status, device, id_command}}
            for name, info in self.commands.items():
                delimiter = self.device_config[name]["delimiter"]
                index = self.device_config[name]["index"]
                device = devices_info[name]["device"]
                termination = self.device_config[name]["termination"]
                for variable in info.keys():
                    info[variable]['min'], info[variable]['max'], info[variable]['static']
                    if self.devices.checkDeviceStatus(
                        name
                    ):  # check the connection of a device
                        try:
                            command = info[variable]["command"]
                            device.write((command+termination).encode())  # send command to device
                            data_string = device.read_until(termination.encode()).decode()
                            data = self._returnStringConverter(
                                data_string, delimiter, index
                            )
                        except Exception as err:
                            self.devices.device_info["status"] = False
                            data = "nan"
                   
                    else:
                        data = "nan"  # write nan to not available data
                    self.data_by_variable[variable] = data

                    # check warning
                    if data == "nan":
                        warning_level = 2

                    elif info[variable]['static'] and float(data) != info[variable]['static']:
                        warning_level = 2
                    
                    else:
                        if info[variable]['min']:
                            if float(data) <= info[variable]['min'] * 1.05:
                                warning_level = max(warning_level, 1)
                            elif float(data) < info[variable]['min']:
                                warning_level = 2
                                

                        if info[variable]['max']:
                            if float(data) >= info[variable]['max'] * 0.95:
                                warning_level = max(warning_level, 1)
                            elif float(data) > info[variable]['max']:
                                warning_level = 2
                    self.warning = warning_level

            self.last_query_time = now

            # if self._checkFileSize():  # exceed the maximum file size
            #     if self._createNewLog():  # create log with header
            #         self.debugLogger.info("File size exceed, new log file created")

            self._saveData()

    def connectDevices(self):
        """
        Call DEVICE
        """
        self.devices = DEVICE(self.config, self.debugLogger)  # establish communication
        self.devices._getPorts()
        self.available_addresses = self.devices.deviceAddresses
        return True

    def reconnectDevices(self):
        restart_DEVICE = False
        self.devices._getPorts()
        for name in self.device_config.keys():
            address = self.device_config[name]["address"]

            if (
                address not in self.devices.deviceAddresses
                and address in self.available_addresses
            ):  # when a connection is loss
                # This step is to prevent the moment when the device is shown in the resource manager but connection fails
                self.available_addresses.remove(address)

            if (
                address in self.devices.deviceAddresses
                and address not in self.available_addresses
                and not self.devices.devices_info[name]["status"]
            ):
                restart_DEVICE = True

        if restart_DEVICE:
            del self.devices  # delete the DEVICE class
            return self.connectDevices()

        else:
            return False

    def _checkDirectory(self):
        if not os.path.exists(self.log_dir):
            os.mkdir(self.log_dir)
            return False
        return True

    def _findLog(self):
        """
        Find current log file
        
        """
        today = datetime.datetime.now().strftime("%Y%m%d")  # YYYYMMDD
        self.current_log_file = self.log_dir + "/log_" + today + ".csv"
        
        return "log_" + today + ".csv" in os.listdir(self.log_dir)

    def _createNewLog(self):
        """
        Create new log file in log directory
        """
        # now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")  # YYYYMMDDHMS

        with open(self.current_log_file, "w") as f:
            f.write(self.header)

        return True

    def _makeLogHeader(self):
        """
        Make a log header base on the data by variable dictionary

        Return:
            header (str) format: 'Date, Time, variable 1, variable 2.....'
        """
        list_of_items = list(self.data_by_variable.keys())
        header = ", ".join(list_of_items) + "\n"

        return header

    def _saveData(self):
        """
        Save current data to current log file

        """
        list_of_data = list(self.data_by_variable.values())
        data_string = ", ".join(list_of_data) + "\n"

        if not self._findLog():
            self._createNewLog()
        with open(self.current_log_file, "a") as f:
            f.write(data_string)

        return True

    # def _checkFileSize(self):
    #     """
    #     Check the size of file

    #     Return:
    #         bool: True if file is oversize
    #     """
    #     if os.path.getsize(self.current_log_file) > self.max_size * 1024:
    #         return True
    #     else:
    #         return False

    def _getDataDictByVariable(self, command_dict: dict):
        """
        Get the variable list based on the model and it's command dictionary
        Args:
            command_dict (dict): the command list for a device, {variable: {command, alias, min, max, static}}

        Returns:
            data_dict (dict): the data dictionary in format {variable: reading}

        """
        today = str(datetime.date.today())
        now = str(datetime.datetime.now().strftime("%H:%M:%S"))
        data_dict = {"Date": today, "Time": now}
        for info in command_dict.values():
            temp_dict = {key: None for key in info}
            data_dict = {**data_dict, **temp_dict}

        return data_dict

    def _returnStringConverter(self, string: str, delimiter: str, index: int):
        """
        Convert returned string and acquire data from it
        Args:
            delimiter (str): the delimiter for string analysis
            index (int): the data index

        Returns:
            data (string): return data in str
        """
        try:
            if delimiter:
                data = string.split(delimiter)[index]
            else:
                data = string.split()[index]
            data = data.replace(" ", "")  # remove white space
            data = data.replace("\n", "")
            data = data.replace("\t", "") 
            data = data.replace("\r", "") 
            data = data.strip()
        except:
            self.debugLogger.error("String Convert Fail: recived: %s, delimiter: %s, index: %s" %(string, delimiter, index))
        return data

    def _setTimeInDataDictByVariable(self):
        """
        Update the time in data dictionary by variable
        """
        today = str(datetime.date.today())
        now = str(datetime.datetime.now().strftime("%H:%M:%S"))
        self.data_by_variable["Date"] = today
        self.data_by_variable["Time"] = now
        return True

# if __name__ == '__main__':
#     SpecLog()
