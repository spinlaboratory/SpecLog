import os
import datetime
from config.config import COMMAND

commonBaudRate = [9600, 19200, 38400, 57600, 115200]

class DEVICE:
    def __init__(self, deviceAddress, rm, deviceRegDict, logDir, debugLogger, fileSize):
        self.deviceRegDictStatus = False
        self.logDir = logDir
        self.deviceRegFile = self.logDir + '/device_reg.txt'
        self.debugLogger = debugLogger

        # some default settings. They can be overwritten by 'deviceRegFile' if information exists.
        self.deviceAddress = deviceAddress # also for searching in deviceRegFile
        self.deviceID = None
        self.deviceManufacturer = None
        self.modelNumber = None
        self.serialNumber = None
        self.deviceStatus = False
        self.baudRate = None
        self.idCommand = '*IDN?' # the default command sent to device to check validation 
        self.termination = 'fl' # the default read/write termination, can be change to '\r' or '\n\r'
        self.splitSign = 'default' # the default split sign for query return. It can be different
        self.dataIndex = 0 # the index of data from return after splits. 
        # eg. if return is '$TEA, 059, 000, 000', after splitting it, it will become ['$TEA', '059', '000', '000'], and '059' is the wanted value  

        if deviceAddress in deviceRegDict: # check if device address is saved in device registration dictionary. The device address is the key.
            deviceInfo = deviceRegDict[deviceAddress][:-1] # skip the 'Address' in the value
            self.deviceRegDictStatus = True # because the device found, this value is set to True
            self.deviceStatus = deviceInfo[1] == 'True' # device status (valid or not)
            if self.deviceStatus: # if True, overwrite device information from device registration
                self.deviceManufacturer = deviceInfo[2]
                self.modelNumber = deviceInfo[3]
                self.serialNumber = deviceInfo[4]
                self.baudRate = int(deviceInfo[5])
                self.idCommand = deviceInfo[6].strip()
                self.termination = deviceInfo[7].strip()
                self.splitSign = deviceInfo[8].strip()
                self.dataIndex = int(deviceInfo[9])
            
        self.queryLogDict = {} # The log dictionary
        self.logDictStatus = False
        
        # splitter to split return strings
        self.splitter = ',' if self.splitSign.strip() == 'default' else self.splitSign.strip()

        self.connect(rm)
        self.categorize(COMMAND)

        self.fileSize = fileSize # the maximum saved file size.  
        self.log(init = 1) # only check when init
        
    def connect(self, rm): 
        if self.deviceRegDictStatus and not self.deviceStatus: # the device info is in device registration , and device is set to invalid (disable)
            return
        else:
            self.device = rm.open_resource(self.deviceAddress) # open rm for valid device or unknown device
            self.setTermination() # set write read termination from device registration

        if not self.baudRate: # this check the baud rate for unknown device. If the device is valid, the baud rate is saved in device registration
            print(self.deviceAddress, 'Found! Trying baud rate...')
            for baudRate in commonBaudRate:
                self.device.baud_rate = baudRate
                self.baudRate = baudRate
                try:
                    self.device.query(self.idCommand).strip('\n').strip('\r')  
                    break
                except:
                    self.debugLogger.warn('%s baud rate is change to %d' %(self.device, baudRate))
                    pass
        else:
            self.device.baud_rate = self.baudRate # setting baud rate from device registration 

        try:
            self.deviceID = self.device.query(self.idCommand).strip('\n').strip('\r') # try to check communication again
            self.deviceStatus = True # device connected and device is valid
            print(self.modelNumber, 'Connected!')

        except Exception as err:
            self.debugLogger.info(err)
            self.debugLogger.warn('%s is not a valid device' %self.deviceAddress,)

        if not self.deviceRegDictStatus: # if device info is not in device registration, then save the new device info to registration
            if self.deviceStatus:
                self.deviceID = self.device.query(self.idCommand).strip('\n').strip('\r')
                self.deviceManufacturer = self.deviceID.split(self.splitter)[0]
                self.modelNumber = self.deviceID.split(self.splitter)[1]
                self.serialNumber = self.deviceID.split(self.splitter)[2]

            f = open(self.deviceRegFile, 'a')
            for item in [self.deviceAddress, self.deviceStatus, self.deviceManufacturer, self.modelNumber, self.serialNumber, self.baudRate, self.idCommand, self.termination, self.splitSign, self.dataIndex]:
                print(item, end = ',', file = f)
            print(file = f)
            f.close()
                
    def reconnect(self, rm):
        self.device = rm.open_resource(self.deviceAddress)
        self.device.baud_rate = self.baudRate
        self.setTermination() # set write read termination from device registration

        if self.device.query(self.idCommand):
            self.deviceStatus = True
            print(self.modelNumber, 'Reconnected!')
        else:
            self.deviceStatus = False
            print(self.modelNumber, 'Reconnection Fails!')
    
    def disconnect(self):
        self.deviceStatus = False
        print(self.modelNumber, 'Disconnected!')

    def categorize(self, COMMAND):
        if self.deviceID:            
            try:
                for key, val in COMMAND[self.modelNumber].items():
                    self.queryLogDict[key.strip()] = val.strip()
                self.logDictStatus = True
            except Exception as err:
                self.debugLogger.warn(err)
                self.debugLogger.info('%s does not have config file.' %self.modelNumber)
    
    def setTermination(self):
        self.endSign = self.termination.replace('fl', '\n')
        self.endSign = self.endSign.replace('cr', '\r')
        self.device.write_termination = self.endSign
        self.device.read_termination = self.endSign
        

    def log(self , init = 0):
        if self.deviceID != None and self.logDictStatus and self.deviceStatus:
            today = datetime.date.today()
            if init or self.createFile:
                now = datetime.datetime.now().strftime('%Y%m%d%H%M%S') #YYYYMMDDHMS
                self.fileName = self.logDir + '/' + str(self.deviceManufacturer) + '_' + str(self.modelNumber) + '_' + now + '.csv'
                f = open(self.fileName, 'a')
                print('Date, Time, ' + ', '.join(self.queryLogDict.keys()), file = f)
                f.close()
                self.createFile = False
            
            else:
                string = str(today) + ', ' + str(datetime.datetime.now().strftime("%H:%M:%S"))+ ', '
                f = open(self.fileName, 'a')
                try:
                    for command in self.queryLogDict.values():
                        string += (self.device.query(command).strip('\n').strip('\r').split(self.splitter)[self.dataIndex] + ', ')
                    string = string[:-2] # remove last commas
                    print(string, file = f)
                except Exception as err:
                    self.debugLogger.warn(err)
                
                f.close()

                if os.path.getsize(self.fileName) > self.fileSize:
                    self.createFile = True