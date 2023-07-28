import pyvisa
import csv
from devices import general 
import time
from config.config import LOG_CONFIG
import logging
import pathlib


logpath=pathlib.Path(__file__).parent.parent.joinpath('logs/debug_log.txt')
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

class pyB12LOG:
    def __init__(self, timeDelay = 5, loc = './logs/inst_history.csv'):
        self.loc = loc
        self.deviceHistory = {}
        self.initInstHistory()

        self.validAddresses = []
        self.validDevices = []

        self.historicalAddresses = []
        self.historicalDevices = []

        self.rm = pyvisa.ResourceManager()
        self.deviceAddresses = self.rm.list_resources()
        self.updateValidDevices(init = 1)
        self.timeDelay = timeDelay # delay time for each logging, unit s
        self.lastCheckTime = time.time()

    def updateValidDevices(self, init = 0):
        deviceList = []
        addressList = []
        if init == 1:
            for address in self.deviceAddresses:
                device = general.DEVICE(address, self.rm, self.deviceHistory, LOG_CONFIG, self.loc)
                self.historicalAddresses.append(address)
                self.historicalDevices.append(device)

                if device.deviceID != None:
                    deviceList.append(device)
                    addressList.append(address)

                self.validDevices = deviceList
                self.validAddresses = addressList

        elif len(self.rm.list_resources()) > len(self.deviceAddresses):
            # a new device added

            newDeviceAddressList = [addresses for addresses in self.rm.list_resources() if addresses not in self.deviceAddresses]
            # refresh resource manager
            self.rm.close()
            self.rm = pyvisa.ResourceManager()

            for address in newDeviceAddressList:
                if address in self.historicalAddresses:
                    device = self.historicalDevices[self.historicalAddresses.index(address)]
                    device.reconnect(self.rm)
                    
                else:
                    device = general.DEVICE(address, self.rm, LOG_CONFIG, self.loc)
                    self.historicalAddresses.append(address)
                    self.historicalDevices.append(device)
                    
                if device.deviceID != None:
                    deviceList.append(device)
                    addressList.append(address)

                self.validDevices = deviceList
                self.validAddresses = addressList
                self.deviceAddresses = self.rm.list_resources()
            
        elif len(self.rm.list_resources()) < len(self.deviceAddresses):
            # a device removed
            removedDeviceAddressList = [addresses for addresses in self.deviceAddresses if addresses not in self.rm.list_resources()]
            for address in removedDeviceAddressList:
                if address in self.validAddresses:
                    address_index = self.validAddresses.index(address)
                    device = self.validDevices[address_index]
                    device.disconnect()

                    del self.validAddresses[address_index]
                    del self.validDevices[address_index]
                    self.deviceAddresses = self.rm.list_resources()
                else:
                    pass
        else:
            pass

    def initInstHistory(self):
        ## get system instrumentation history
        try:
            f = open(self.loc, 'r')
        except:
            print('Create New Instrumentations History')
            f = open(self.loc, 'w')
            print('Address,Status,Manufacturer,Model,SN,BaudRate', file = f)
        f = open(self.loc, 'r')
        
        line = f.readline().strip('\n')
        while line != '':
            line = line.strip().split(',')
            self.deviceHistory[line[0]] = line
            line = f.readline().strip('\n')
        f.close()

    def log(self):
        self.updateValidDevices()
        if time.time() - self.lastCheckTime >= self.timeDelay:
            for device in self.validDevices:
                device.log()
            self.lastCheckTime = time.time()
        
            
log = pyB12LOG(timeDelay = 1)
while(1):
    try:
        log.log()
    except:
        log = pyB12LOG(timeDelay = 1)
        log.log()