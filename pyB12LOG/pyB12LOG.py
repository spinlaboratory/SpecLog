"""
pyB12LOG: The logging program for instrumentations

Author: Yen-Chun Huang

Company: Bridge 12 Technologies, Inc
"""

import pyvisa
from .general import *
import time
import logging
import os
from .config.config import CONFIG, SEIRAL_CONFIG
from configparser import ConfigParser

class pyB12LOG:
    def __init__(self):
        self.timeDelay, self.logDir, self.fileSize = self._getLogSettings() 
        self.debugLogger = self.initDebugLog()

        self.rm = pyvisa.ResourceManager()
        self.deviceAddresses = self.rm.list_resources()

        self._getDeviceConfig()
        self.lastCheckTime = time.time()
        self.device = DEVICE(self.debugLogger)
        self.firstLog = True
        
    def _getDeviceConfig(self):
        # To find device config file
        self.deviceConfig = ConfigParser()

        # Find device config path
        configKey = 'CONFIG'
        deviceConfigDirHome = CONFIG[configKey]['log_folder_location'][1:-1]
        self.deviceConfigDir= deviceConfigDirHome +'/B12TLOG_Config/'
        listDir = os.listdir(self.deviceConfigDir)

        # Create device config if not exists
        if 'device_config.cfg' not in listDir:

            # Put current available addresses and required items for serial communication to list
            items = []
            for key in SEIRAL_CONFIG:
                items.extend([item for item in SEIRAL_CONFIG[key].keys()])
            
            # List cannot be modified in config
            self.deviceConfig['GENERAL'] = {
                'device_addresses': ", ".join(list(self.deviceAddresses)),
                'items': ", ".join(items),            
            }

            # initial with current device info
            for address in self.deviceAddresses:
                self.deviceConfig[address] = {}
                for key in SEIRAL_CONFIG:
                    self.deviceConfig[address] = {**self.deviceConfig[address],
                        **{item: val for item, val in SEIRAL_CONFIG[key].items() 
                    }}
                self.deviceConfig[address]['device_address'] = "'%s'"%address
            with open(self.deviceConfigDir+'/device_config.cfg', 'w') as conf:
                self.deviceConfig.write(conf)
        
        else:
            self._updateDeviceConfig()

    def _updateDeviceConfig(self):
        # To update device config file 
        self.deviceConfig.read(self.deviceConfigDir + '/device_config.cfg')
        self.deviceAddresses = self.rm.list_resources()

        # if addresses in config file is different from current available address
        if self.deviceConfig['GENERAL']["device_addresses"] != ", ".join(list(self.deviceAddresses)):
            # update the device addresses in config file
            self.deviceConfig['GENERAL']["device_addresses"] = ", ".join(list(self.deviceAddresses))

            # new device appear
            for address in self.deviceAddresses:
                if address not in self.deviceConfig.sections():
                    self.deviceConfig[address] = {}
                    for key in SEIRAL_CONFIG:
                        self.deviceConfig[address] = {
                            **self.deviceConfig[address],
                            **{item: val for item, val in SEIRAL_CONFIG[key].items()} 
                        }
                    self.deviceConfig[address]['device_address'] = "'%s'"%address
            
                with open(self.deviceConfigDir+'/device_config.cfg', 'w') as conf:
                    self.deviceConfig.write(conf)
    def log(self):
        self._updateDeviceConfig()
        if time.time() - self.lastCheckTime > self.timeDelay:
            self.logStartTime = time.time()
            self.device.log()
            self.lastCheckTime = time.time()
            self.logDeltaTime = self.lastCheckTime - self.logStartTime
            
            if self.firstLog:
                self.debugLogger.info('Log interval of %0.1f s. Logging takes %0.1f s to complete.' %(self.timeDelay, self.logDeltaTime))
                self.firstLog = False
            if self.logDeltaTime > self.timeDelay:
                self.debugLogger.info('Log interval of %0.1f s is too short. Logging takes %0.1f s to complete. Log interval is set to %0.1f s.' %(self.timeDelay, self.logDeltaTime, self.logDeltaTime + 0.1))
                self.timeDelay = self.logDeltaTime + 0.1
            
    def _getLogSettings(self):
        configKey = 'CONFIG'
        logDirHome = CONFIG[configKey]['log_folder_location'][1:-1]
        timeDelay = float(CONFIG[configKey]['log_interval'])
        fileSize = int(CONFIG[configKey]['save_file_size_kb']) * 1024

        listDir = os.listdir(logDirHome)
        logDir= logDirHome +'/B12TLOG/'
        if 'B12TLOG' not in listDir:
            os.mkdir(logDir)
        
        return timeDelay, logDir, fileSize

    def initDebugLog(self):
        logpath = self.logDir + '/debug_log.txt'
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        ch = logging.FileHandler(str(logpath))
        ch.setLevel(logging.INFO)
        ch2 = logging.StreamHandler()
        ch2.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        ch2.setFormatter(formatter)
        logger.addHandler(ch)
        logger.addHandler(ch2)

        return logger
