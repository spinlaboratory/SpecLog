import os
from pyvisa.constants import Parity, StopBits
import datetime
from config.config import COMMAND, SEIRAL_CONFIG

common_baud_rate = [9600, 19200, 38400, 57600, 115200]

class DEVICE:
    def __init__(self, device_address, rm, deviceRegDict, logDir, debugLogger, fileSize):
        self.deviceRegDictStatus = False
        self.logDir = logDir
        self.deviceRegFile = self.logDir + '/device_reg.txt'
        self.debugLogger = debugLogger
        self.device_id = None

        if device_address in deviceRegDict: # check if device address is saved in device registration dictionary. The device address is the key.
            self.deviceRegDictStatus = True # because the device found, this value is set to True
            deviceInfo = deviceRegDict[device_address] # skip the 'Address' in the value
            index = 0
            for key in SEIRAL_CONFIG:
                for item, val in SEIRAL_CONFIG[key].items():
                    # print(item, deviceInfo[index])
                    try:
                        exec("self." + "%s = %s" %(item, deviceInfo[index]))
                    except:
                        exec("self." + "%s = '%s'" %(item, deviceInfo[index]))
                    index += 1
        else:
            # some default settings. They can be overwritten by 'deviceRegFile' if information exists.
            for key in SEIRAL_CONFIG:
                for item, val in SEIRAL_CONFIG[key].items():
                    exec("self." + "%s = %s" %(item, val)) # execute lines defined in config
            
        self.queryLogDict = {} # The log dictionary
        self.logDictStatus = False
        
        # splitter to split return strings
        self.splitter = ',' if self.split_sign.strip() == 'default' else self.split_sign.strip()

        self.connect(rm)
        self.categorize(COMMAND)

        self.fileSize = fileSize # the maximum saved file size.  
        self.log(init = 1) # only check when init
        
    def connect(self, rm): 
        if self.deviceRegDictStatus and not self.device_status: # the device info is in device registration , and device is set to invalid (disable)
            return
        else:
            self.device = rm.open_resource(self.device_address) # open rm for valid device or unknown device
            self.setSerial()

        try:
            self.device_id = self.device.query(self.id_command).strip('\n').strip('\r') # try to check communication again
            self.device_status = True # device connected and device is valid
            print(self.device_address, 'Connected!')
            print(self.id_command, ': ', self.device_id)

        except Exception as err:
            self.debugLogger.info(err)
            self.debugLogger.warn('%s is not a valid device or need to change serial configuration' %self.device_address,)
        
        if not self.deviceRegDictStatus: # if device info is not in device registration, then save the new device info to registration
            if self.device_status and self.device_id:
                try:
                    self.device_manufacturer = self.device_id.split(self.splitter)[0]
                    self.model_number = self.device_id.split(self.splitter)[1]
                    self.serial_number = self.device_id.split(self.splitter)[2]
                except:
                    self.device_status, self.device_manufacturer, self.model_number, self.serial_number = False, None, None, None
                    self.debugLogger.warn('%s does not have a valid ID. Please update in device_reg.txt' %self.device_address)
            
            f = open(self.deviceRegFile, 'a')
            index = 0
            string = ''
            for key in SEIRAL_CONFIG:
                for item, val in SEIRAL_CONFIG[key].items():
                    if index == 0:
                        string += '{:^50}'.format(str(eval('self.' + item))) + ','
                    else:
                        string += '{:^25}'.format(str(eval('self.' + item))) + ','  
                    index += 1
            print(string[:-1], file = f)
            f.close()
                
    def reconnect(self, rm):
        self.device = rm.open_resource(self.device_address)
        self.device.baud_rate = self.baud_rate
        self.setSerial()

        if self.device.query(self.id_command):
            self.device_status = True
            print(self.model_number, 'Reconnected!')
        else:
            self.device_status = False
            print(self.model_number, 'Reconnection Fails!')
    
    def disconnect(self):
        self.device_status = False
        print(self.model_number, 'Disconnected!')


    def categorize(self, COMMAND):
        if self.device_id:            
            try:
                for key, val in COMMAND[self.model_number].items():
                    self.queryLogDict[key.strip()] = val.strip()
                self.logDictStatus = True
            except Exception as err:
                self.debugLogger.warn(err)
                self.debugLogger.info('%s does not have config file.' %self.model_number)
    
    def setSerial(self):
        self.setTermination()
        self.setParity()
        self.setStopBits()

        # other configurations
        self.device.flow_control = self.flow_control
        self.device.data_bits = self.data_bits
            
    def setTermination(self):
        self.endSign = self.termination.replace('fl', '\n')
        self.endSign = self.endSign.replace('cr', '\r')
        self.device.write_termination = self.endSign
        self.device.read_termination = self.endSign
        
    def setParity(self):
        '''
        even = 2
        mark = 3
        none = 0
        odd = 1
        space = 4
        '''

        if self.parity == 2:
            self.device.parity = Parity.even

        elif self.parity == 3:
            self.devive.parity = Parity.mark
        
        elif self.parity == 1:
            self.device.parity = Parity.odd

        elif self.parity == 4:
            self.device.parity = Parity.space

        elif self.parity == 0:
            self.device.parity = Parity.none

        else:
            self.debugLogger.info('Parity Incorrect')
            raise TypeError('Parity Incorrect')
    
    def setStopBits(self):
        '''
        one = 10
        one_and_a_half = 15
        two = 20
        '''

        if self.stop_bits == 10:
            self.device.stop_bits = StopBits.one
        elif self.stop_bits == 15:
            self.device.stop_bits = StopBits.one_and_a_half
        elif self.stop_bits == 20:
            self.device.stop_bits = StopBits.two
        else:
            self.debugLogger.info('Stop bits Incorrect')
            raise TypeError('Stop bits Incorrect')

    def log(self , init = 0):
        if self.device_id and self.logDictStatus and self.device_status:
            today = datetime.date.today()
            if init or self.createFile:
                now = datetime.datetime.now().strftime('%Y%m%d%H%M%S') #YYYYMMDDHMS
                self.fileName = self.logDir + '/' + str(self.device_manufacturer) + '_' + str(self.model_number) + '_' + now + '.csv'
                f = open(self.fileName, 'a')
                print('Date, Time, ' + ', '.join(self.queryLogDict.keys()), file = f)
                f.close()
                self.createFile = False
            
            else:
                string = str(today) + ', ' + str(datetime.datetime.now().strftime("%H:%M:%S"))+ ', '
                f = open(self.fileName, 'a')
                try:
                    for command in self.queryLogDict.values():
                        string += (self.device.query(command).strip('\n').strip('\r').split(self.splitter)[self.data_index] + ', ')
                    string = string[:-2] # remove last commas
                    print(string, file = f)
                except Exception as err:
                    self.debugLogger.warn(err)
                
                f.close()

                if os.path.getsize(self.fileName) > self.fileSize:
                    self.createFile = True