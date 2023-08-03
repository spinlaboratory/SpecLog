import pyvisa
from pyvisa.constants import StopBits, Parity
from devices import general 
import time
import logging
import os
from config.config import CONFIG, SEIRAL_CONFIG

class pyB12LOG:
    def __init__(self):
        self.timeDelay, self.logDir, self.fileSize = self.getConfig() 
        self.debugLogger = self.initDebugLog(self.logDir)

        self.deviceRegFile = self.logDir + '/device_reg.txt' # file to device registration 
        self.deviceRegDict = {} # dictionary to store information from device registration 
        self.initDeviceRegDict() # put information from device registration to dictionary

        self.validAddresses = []
        self.validDevices = []

        self.rm = pyvisa.ResourceManager()
        self.deviceAddresses = self.rm.list_resources()
        self.updateValidDevices(init = 1)
        self.lastCheckTime = time.time()

    def updateValidDevices(self, init = 0):
        deviceList = []
        addressList = []
        if init == 1:
            for address in self.deviceAddresses:
                device = general.DEVICE(address, self.rm, self.deviceRegDict, self.logDir, self.debugLogger, self.fileSize)
                self.historicalAddresses.append(address)
                self.historicalDevices.append(device)

                if device.device_id != None:
                    deviceList.append(device)
                    addressList.append(address)

                self.validDevices = deviceList
                self.validAddresses = addressList

        elif len(self.rm.list_resources()) > len(self.deviceAddresses):
            # a new device added
            self.debugLogger.warn('New Devices Detected')
            newDeviceAddressList = [addresses for addresses in self.rm.list_resources() if addresses not in self.deviceAddresses]
            
            # refresh resource manager
            self.rm.close()
            self.rm = pyvisa.ResourceManager()
            self.debugLogger.warn('Resource Manager Refreshed')

            for address in newDeviceAddressList:
                self.debugLogger.warn('%s Found!' %address)
                device = general.DEVICE(address, self.rm, self.deviceRegDict, self.logDir, self.debugLogger, self.fileSize)
                    
                if device.device_id != None:
                    deviceList.append(device)
                    addressList.append(address)

                self.validDevices = deviceList
                self.validAddresses = addressList
                self.deviceAddresses = self.rm.list_resources()
            
        elif len(self.rm.list_resources()) < len(self.deviceAddresses):
            # a device removed
            self.debugLogger.warn('Devices Removed')
            removedDeviceAddressList = [addresses for addresses in self.deviceAddresses if addresses not in self.rm.list_resources()]
            for address in removedDeviceAddressList:
                self.debugLogger.warn('%s Deleted!' %address)
                if address in self.validAddresses:
                    address_index = self.validAddresses.index(address)
                    device = self.validDevices[address_index]
                    device.disconnect()

                    del self.validAddresses[address_index]
                    del self.validDevices[address_index]
                    self.deviceAddresses = self.rm.list_resources()

    def initDeviceRegDict(self):
        ## get device registration
        ## dictionary format: {Address: [Address, Status, Manufacturer, Model, SN, BaudRate...]}
        try: # check device registration exists
            f = open(self.deviceRegFile, 'r') 
        except: # not exists, create new file
            self.debugLogger.info('Create New Device History') 
            f = open(self.deviceRegFile, 'w')
            index = 0
            string = ''
            for key in SEIRAL_CONFIG:
                for item, val in SEIRAL_CONFIG[key].items():
                    if index == 0:
                        string += '{:^50}'.format(item) + ','
                    else:
                        string += '{:^25}'.format(item) + ','               
                    index += 1
            print(string[:-1], file = f)
        f = open(self.deviceRegFile, 'r')
        line = f.readline().strip('\n').strip().replace(' ', '').split(',') # get header into dictionary
        self.deviceRegDict['items'] = line
        line = f.readline().strip('\n') # get dictionary keys
        while line != '': # run until the end of file
            line = line.strip().replace(' ', '').split(',') 
            self.deviceRegDict[line[0]] = line 
            line = f.readline().strip('\n')
        f.close()

    def log(self):
        self.updateValidDevices()
        if time.time() - self.lastCheckTime >= self.timeDelay:
            for device in self.validDevices:
                device.log()
            self.lastCheckTime = time.time()
    
    def getConfig(self):
        configKey = 'CONFIG'
        logDirHome = CONFIG[configKey]['log_folder_location'][1:-1]
        timeDelay = float(CONFIG[configKey]['log_interval'])
        fileSize = int(CONFIG[configKey]['save_file_size_kb']) * 1024

        listDir = os.listdir(logDirHome)
        logDir= logDirHome +'/B12TLOG/'
        if 'B12TLOG' not in listDir:
            os.mkdir(logDir)
        
        return timeDelay, logDir, fileSize

    def initDebugLog(self, logDir):
        logpath = logDir + '/debug_log.txt'
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
