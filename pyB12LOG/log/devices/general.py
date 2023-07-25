import pyvisa
import os
import datetime

class DEVICE:
    def __init__(self, deviceAddress, rm, LOG_CONFIG):    
        self.deviceID = None
        self.deviceAddress = deviceAddress 
        self.deviceManufacturer = None
        self.modelNumber = None
        self.serialNumber = None
        self.firmwareDate = None
        self.deviceGroup = None
        self.queryLogDict = {} # The log dictionary

        try: 
            self.inst = rm.open_resource(deviceAddress)
            deviceID = self.inst.query("*IDN?").strip('\n')
            self.deviceAddress = deviceAddress
            self.deviceID = deviceID
            #IEEE-488 IDN? format <manufacturer>, <model number>, <serial number>, <firmware date> 
            self.deviceManufacturer = deviceID.split(',')[0]
            self.modelNumber = deviceID.split(',')[1]
            self.serialNumber = deviceID.split(',')[2]
            self.firmwareDate = deviceID.split(',')[3]
        except:
            pass

        self.categorize(LOG_CONFIG)
        self.log(init = 1) # only check when init

    def categorize(self, LOG_CONFIG):
        if self.deviceID != None:
            devicesGroups = LOG_CONFIG.getlist('DEVICES', 'family_group',fallback=None)
            devicesKeywords = LOG_CONFIG.getlist('DEVICES', 'keywords',fallback=None)
            for index, (keyword, family_group) in enumerate(zip(devicesKeywords, devicesGroups)): # get the family
                if keyword in self.modelNumber:
                    break
            
            self.deviceGroup = family_group
            devicesMember = LOG_CONFIG.getlist(family_group, 'member',fallback=None)
            numberOfChannelList = LOG_CONFIG.getlist(family_group, 'number_of_channel',fallback=None)
            startChannel = LOG_CONFIG.get(family_group, 'start_channel',fallback=None)

            for index, (name, number_of_channel) in enumerate(zip(devicesMember, numberOfChannelList)): # get number of channel          
                if name.strip() in self.modelNumber:
                    break

            currentChannel = int(startChannel)
            while currentChannel <= int(number_of_channel):
                for key, val in LOG_CONFIG[family_group + ':Commands'].items():
                    self.queryLogDict[key + ' ' + str(currentChannel)] = val.strip() + str(currentChannel)                
                currentChannel += 1

    def log(self , init = 0):
        if self.deviceID != None:
            today = datetime.date.today()
            if init:
                try:
                    f = open('./logs/' + str(today.year) + '_' + str(self.deviceID) + '.csv', 'r') # try to open a file if exist
                    header = f.readline() # try to read header, no header will goes to except routine)
                    if header.strip() != self.deviceID.strip():
                        raise ValueError
                    f.close()
                except:
                    f = open('./logs/' + str(today.year) + '_' + str(self.deviceID) + '.csv', 'a')
                    print(self.deviceID, file = f)
                    print('Date, Time, ' + ','.join(self.queryLogDict.keys()), file = f)
                    f.close()

            else:
                string = str(today) + ', ' + str(datetime.datetime.now().strftime("%H:%M:%S"))+ ', '
                f = open('./logs/' + str(today.year) + '_' + str(self.deviceID) + '.csv', 'a')
                try:
                    for command in self.queryLogDict.values():
                        string += (self.inst.query(command).strip('\n') + ', ')
                    print(string, file = f)

                except:
                    pass
                
                f.close()