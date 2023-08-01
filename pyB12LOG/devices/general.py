import datetime
from config.config import COMMAND

commonBaudRate = [9600, 19200, 38400, 57600, 115200]

class DEVICE:
    def __init__(self, deviceAddress, rm, deviceHistory, logDir, debugLogger):
        self.deviceHistoryStatus = False
        self.logDir = logDir
        self.deviceReg = self.logDir + '/device_reg.csv'
        self.debugLogger = debugLogger
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
        self.categorize(COMMAND)
        self.log(init = 1) # only check when init
        
    def connect(self, rm): 
        if self.deviceHistoryStatus and not self.deviceStatus:
            return
        else:
            self.device = rm.open_resource(self.deviceAddress)
        
        if not self.baudRate:
            print(self.deviceAddress, 'Found! Trying baud rate...')
            for baudRate in commonBaudRate:
                self.device.baud_rate = baudRate
                self.baudRate = baudRate
                try:
                    deviceID = self.device.query("*IDN?").strip('\n').strip('\r')  
                    break
                except:
                    self.debugLogger.warn('%s baud rate is change to %d' %(self.device, baudRate))
                    pass
        else:
            self.device.baud_rate = self.baudRate
        try:
            self.deviceID = self.device.query("*IDN?").strip('\n').strip('\r')
            self.deviceStatus = True
            print(self.deviceID, 'Connected!')
        except Exception as err:
            self.debugLogger.info(err)
            self.debugLogger.warn('%s is not a valid device' %self.deviceAddress,)

        if not self.deviceHistoryStatus:
            if self.deviceStatus:
                self.deviceID = self.device.query("*IDN?").strip('\n').strip('\r')
                self.deviceManufacturer = self.deviceID.split(',')[0]
                self.modelNumber = self.deviceID.split(',')[1]
                self.serialNumber = self.deviceID.split(',')[2]

            f = open(self.deviceReg, 'a')
            print(self.deviceAddress, end = ',', file = f)
            print(self.deviceStatus, end = ',', file = f)
            if self.deviceStatus:
                for item in [self.deviceManufacturer, self.modelNumber, self.serialNumber, self.baudRate]:
                    print(item, end = ',', file = f)
            print(file = f)
            f.close()
                
    def reconnect(self, rm):
        self.device = rm.open_resource(self.deviceAddress)
        self.device.baud_rate = self.baudRate
        if self.device.query("*IDN?"):
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

    def log(self , init = 0):
        if self.deviceID != None and self.logDictStatus and self.deviceStatus:
            today = datetime.date.today()
            if init:
                try:
                    f = open(self.logDir + '/' + str(today.year) + '_' + str(self.deviceManufacturer) + '_' + str(str(self.modelNumber)) + '.csv', 'r') # try to open a file if exist
                    header = f.readline() # try to read header, no header will goes to except routine)
                    if header.strip() != self.deviceID.strip():
                        raise ValueError
                    f.close()
                except:
                    f = open(self.logDir + '/' + str(today.year) + '_' + str(self.deviceManufacturer) + '_' + str(str(self.modelNumber)) + '.csv', 'a')
                    print(self.deviceID, file = f)
                    print('Date, Time, ' + ', '.join(self.queryLogDict.keys()), file = f)
                    f.close()

            else:
                string = str(today) + ', ' + str(datetime.datetime.now().strftime("%H:%M:%S"))+ ', '
                f = open(self.logDir + '/' + str(today.year) + '_' + str(self.deviceManufacturer) + '_' + str(str(self.modelNumber)) + '.csv', 'a')
                try:
                    for command in self.queryLogDict.values():
                        string += (self.device.query(command).strip('\n').strip('\r') + ', ')
                    string = string[:-2] # remove last commas
                    print(string, file = f)
                except Exception as err:
                    self.debugLogger.warn(err)
                
                f.close()