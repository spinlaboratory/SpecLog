import pyvisa
from devices import general 
import time
from config.config import LOG_CONFIG

class pyB12LOG:
    def __init__(self, timeDelay = 5):
        self.validAddresses = []
        self.validDevices = []

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
                device = general.DEVICE(address, self.rm, LOG_CONFIG)
                if device.deviceID != None:
                    deviceList.append(device)
                    addressList.append(address)

                self.validDevices = deviceList
                self.validAddresses = addressList

        elif len(self.rm.list_resources()) > len(self.deviceAddresses):
            # a new device added
            newDeviceAddressList = [addresses for addresses in self.rm.list_resources() if addresses not in self.deviceAddresses]
            for address in newDeviceAddressList:
                device = general.DEVICE(address, self.rm, LOG_CONFIG)
                if device.deviceID != None:
                    deviceList.append(device)
                    addressList.append(address)
                    print(device.modelNumber, 'Connected!')

                self.validDevices = deviceList
                self.validAddresses = addressList
                self.deviceAddresses = self.rm.list_resources()
            
        elif len(self.rm.list_resources()) < len(self.deviceAddresses):
            # a device removed
            removedDeviceAddressList = [addresses for addresses in self.deviceAddresses if addresses not in self.rm.list_resources()]
            for address in removedDeviceAddressList:
                if address in self.validAddresses:
                    address_index = self.validAddresses.index(address)
                    print(self.validDevices[address_index].modelNumber, 'Disconnected!')
                    del self.validAddresses[address_index]
                    del self.validDevices[address_index]
                    self.deviceAddresses = self.rm.list_resources()
                else:
                    pass
        else:
            pass


    def log(self):
        self.updateValidDevices()
        if time.time() - self.lastCheckTime >= self.timeDelay:
            for device in self.validDevices:
                device.log()
            self.lastCheckTime = time.time()
            
log = pyB12LOG(timeDelay = 1)
while(1):
    log.log()