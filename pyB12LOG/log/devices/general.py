import pyvisa
import os
import datetime
import time
import logging

import pathlib

logpath=pathlib.Path(__file__).parent.parent.parent.joinpath('logs/debug_log.txt')
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

commonBaudRate = [9600, 19200, 38400, 57600, 115200]

class DEVICE:
    def __init__(self, deviceAddress, rm, deviceHistory, LOG_CONFIG, loc):
        self.deviceHistoryStatus = False
        self.loc = loc
        self.deviceAddress = deviceAddress
        self.deviceID = None
        self.deviceManufacturer = None
        self.modelNumber = None
        self.serialNumber = None
        self.deviceStatus = False
        self.baudRate = None

        if deviceAddress in deviceHistory:
            deviceInfo = deviceHistory[deviceAddress][:-1]
            self.deviceHistoryStatus = True
            self.deviceStatus = deviceInfo[1] == 'True'
            if self.deviceStatus:
                self.deviceManufacturer = deviceInfo[2]
                self.modelNumber = deviceInfo[3]
                self.serialNumber = deviceInfo[4]
                self.baudRate = int(deviceInfo[5])
            
        self.deviceGroup = None
        self.queryLogDict = {} # The log dictionary
        self.logDictStatus = False

        self.connect(rm)
        self.categorize(LOG_CONFIG)
        self.log(init = 1) # only check when init
        
    def connect(self, rm): 
        if self.deviceHistoryStatus and not self.deviceStatus:
            return
        else:
            self.inst = rm.open_resource(self.deviceAddress)
        
        if not self.baudRate:
            print(self.deviceAddress, 'Found! Trying baud rate...')
            for baudRate in commonBaudRate:
                self.inst.baud_rate = baudRate
                self.baudRate = baudRate
                try:
                    print(baudRate)
                    deviceID = self.inst.query("*IDN?").strip('\n').strip('\r')  
                    break
                except:
                    pass
        else:
            self.inst.baud_rate = self.baudRate
        try:
            self.deviceID = self.inst.query("*IDN?").strip('\n').strip('\r')
            self.deviceStatus = True
            print(self.deviceID, 'Connected!')
        except Exception as err:
            print(err)
            logger.info(err)
            print(self.deviceAddress,'is not a valid instrumentation')

        if not self.deviceHistoryStatus:
            if self.deviceStatus:
                self.deviceID = self.inst.query("*IDN?").strip('\n').strip('\r')
                self.deviceManufacturer = self.deviceID.split(',')[0]
                self.modelNumber = self.deviceID.split(',')[1]
                self.serialNumber = self.deviceID.split(',')[2]

            f = open(self.loc, 'a')
            print(self.deviceAddress, end = ',', file = f)
            print(self.deviceStatus, end = ',', file = f)
            if self.deviceStatus:
                for item in [self.deviceManufacturer, self.modelNumber, self.serialNumber, self.baudRate]:
                    print(item, end = ',', file = f)
            print(file = f)
            f.close()
                
    def reconnect(self, rm):
        self.inst = rm.open_resource(self.deviceAddress)
        self.inst.baud_rate = self.baudRate
        if self.inst.query("*IDN?"):
            self.deviceStatus = True
            print(self.modelNumber, 'Reconnected!')
        else:
            self.deviceStatus = False
            print(self.modelNumber, 'Reconnection Fails!')
    
    def disconnect(self):
        self.deviceStatus = False
        print(self.modelNumber, 'Disconnected!')

    def categorize(self, LOG_CONFIG):
        try:
            if self.deviceID != None:
                devicesGroups = LOG_CONFIG.getlist('DEVICES', 'family_group',fallback=None)
                devicesKeywords = LOG_CONFIG.getlist('DEVICES', 'keywords',fallback=None)
                
                # find family
                for index, (keyword, group) in enumerate(zip(devicesKeywords, devicesGroups)): # get the family
                    if keyword in self.modelNumber:
                        self.deviceGroup = group
                        break

                devicesMember = LOG_CONFIG.getlist(self.deviceGroup, 'member',fallback=None)
                numberOfChannelList = LOG_CONFIG.getlist(self.deviceGroup, 'number_of_channel',fallback=None)
                startChannel = LOG_CONFIG.get(self.deviceGroup, 'start_channel',fallback=None)

                for index, (name, number_of_channel) in enumerate(zip(devicesMember, numberOfChannelList)): # get number of channel          
                    if name.strip() in self.modelNumber:
                        break

                currentChannel = int(startChannel)
                while currentChannel <= int(number_of_channel):
                    for key, val in LOG_CONFIG[self.deviceGroup + ':Commands'].items():
                        self.queryLogDict[key + ' ' + str(currentChannel)] = val.strip() + str(currentChannel)                
                    currentChannel += 1

                self.logDictStatus = True
        except Exception as err:
            print(self.modelNumber, 'does not have config file.')

    def log(self , init = 0):
        if self.deviceID != None and self.logDictStatus and self.deviceStatus:
            today = datetime.date.today()
            if init:
                try:
                    f = open('./logs/' + str(today.year) + '_' + str(self.deviceManufacturer) + '_' + str(str(self.modelNumber)) + '.csv', 'r') # try to open a file if exist
                    header = f.readline() # try to read header, no header will goes to except routine)
                    if header.strip() != self.deviceID.strip():
                        raise ValueError
                    f.close()
                except:
                    f = open('./logs/' + str(today.year) + '_' + str(self.deviceManufacturer) + '_' + str(str(self.modelNumber)) + '.csv', 'a')
                    print(self.deviceID, file = f)
                    print('Date, Time, ' + ','.join(self.queryLogDict.keys()), file = f)
                    f.close()

            else:
                string = str(today) + ', ' + str(datetime.datetime.now().strftime("%H:%M:%S"))+ ', '
                f = open('./logs/' + str(today.year) + '_' + str(self.deviceManufacturer) + '_' + str(str(self.modelNumber)) + '.csv', 'a')
                try:
                    for command in self.queryLogDict.values():
                        string += (self.inst.query(command).strip('\n') + ', ')
                    print(string, file = f)

                except Exception as err:
                    print(err)
                
                f.close()