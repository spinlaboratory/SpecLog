"""
pyB12LOG: The logging program for instrumentations

Author: Yen-Chun Huang

Company: Bridge 12 Technologies, Inc
"""
import os
import pyvisa
from pyvisa.constants import Parity, StopBits
import time
import datetime
from config.config import CONFIG
from configparser import ConfigParser

rm = pyvisa.ResourceManager()

class DEVICE:
    def __init__(self, debugLogger):

        deviceConfigDirHome = CONFIG['CONFIG']['log_folder_location'][1:-1]
        self.fileSize = int(CONFIG['CONFIG']['save_file_size_kb']) * 1024

        self.deviceConfigDirFile = deviceConfigDirHome +'/B12TLOG_Config/device_config.cfg'
        self.deviceConfig = ConfigParser()

        self.commandConfigFile = deviceConfigDirHome +'/B12TLOG_Config/command.cfg'
        self.commandConfig = ConfigParser()

        self.logDir = deviceConfigDirHome + '/B12TLOG'

        self.debugLogger= debugLogger
        self.activeDevices = []
        self.activeAddresses = []
        self.queryItems = []
        self.newFile = 1

    def _update_connect(self):
        self.deviceConfig.read(self.deviceConfigDirFile)
        self.errorFlag = False # This is the flag to restart the resource manager
        for address in rm.list_resources():
            if self.deviceConfig[address]['device_status'] == 'True' and address not in self.activeAddresses: # if the device status is True and device is not connected yet
                serialSettingsDict = {}
                for item, val in self.deviceConfig[address].items():
                    exec("serialSettingsDict['%s'] = %s" %(item, val)) # assign value from config. Be careful about changing it
                try:
                    inst = rm.open_resource(serialSettingsDict['device_address'])
                    inst.baud_rate=serialSettingsDict['baud_rate']
                    inst.data_bits=serialSettingsDict['data_bits']
                    inst.flow_control=serialSettingsDict['flow_control']
                    inst.parity=serialSettingsDict['parity']
                    inst.stop_bits=serialSettingsDict['stop_bits']
                    inst.read_termination = serialSettingsDict['termination']
                    inst.write_termination = serialSettingsDict['termination']
  
                    device_id = inst.query(serialSettingsDict['id_command']).strip('\r').strip('\n').strip() # actually query ID from device
                    self.debugLogger.info('%s connected!' %device_id)

                    if not serialSettingsDict['device_manufacturer'] or not serialSettingsDict['model_number'] or not serialSettingsDict['serial_number']:
                        add_device_manufacturer = device_id.split(serialSettingsDict['split_sign'])[0]
                        add_model_number = device_id.split(serialSettingsDict['split_sign'])[1]
                        add_serial_number = device_id.split(serialSettingsDict['split_sign'])[2]
                        self.deviceConfig[address]['device_manufacturer'] = "'%s'" %add_device_manufacturer
                        self.deviceConfig[address]['model_number'] = "'%s'" %add_model_number
                        self.deviceConfig[address]['serial_number'] = "'%s'" %add_serial_number
                    
                    self.newFile = 1
                    self.activeDevices.append(inst)  
                    self.activeAddresses.append(address)         
                
                except Exception as err:
                    self.errorFlag = True
                    self.debugLogger.warn(err)
                    self.debugLogger.info('%s is inactive' %address)
                    self.deviceConfig[address]['device_status'] = 'False'
                    
                    if address in self.activeAddresses:
                        self.newFile = 1
                        self.activeDevices.remove(inst)
                        self.activeAddresses.remove(address) 

                with open(self.deviceConfigDirFile, 'w') as conf:
                    self.deviceConfig.write(conf)

        if self.errorFlag: # this will force whole program restart in logger.py
            raise ConnectionError('Connection Restarts')

    def log(self):
        self._update_connect()
        self.commandConfig.read(self.commandConfigFile)
        if self.newFile:
            for address in self.activeAddresses:
                model_number = self.deviceConfig[address]['model_number'].replace("'", '')
                if model_number in self.commandConfig.keys():
                    for key in self.commandConfig[model_number]:
                        if key not in self.queryItems:
                            self.queryItems.append(key) 
            
            now = datetime.datetime.now().strftime('%Y%m%d%H%M%S') #YYYYMMDDHMS
            self.logFile = self.logDir + '/' + 'log_' + now + '.csv'
            
            if self.activeAddresses:
                with open(self.logFile, 'w') as f:
                        f.write('Date, Time, %s' %', '.join(self.queryItems) + '\n')
                self.newFile = 0

        today = datetime.date.today()
        data = [str(today), str(datetime.datetime.now().strftime("%H:%M:%S"))]
        for index, (inst, address) in enumerate(zip(self.activeDevices, self.activeAddresses)):
            model = self.deviceConfig[address]['model_number'].replace("'", '')
            split_sign = self.deviceConfig[address]['split_sign'].replace("'", '')
            data_index = int(self.deviceConfig[address]['data_index'])
            if model in self.commandConfig.keys():
                for item, command in self.commandConfig[model].items():
                    try: 
                        data.append(inst.query(command).strip('\n').strip('\r').split(split_sign)[data_index])
                    except Exception as err:
                        self.debugLogger.info(err)
                        data.append('0')
                        self.newFile = 1
        if self.queryItems and self.activeAddresses:
            with open(self.logFile, 'a') as f:
                f.write('%s' %', '.join(data) + '\n')

            if os.path.getsize(self.logFile) > self.fileSize:
                self.newFile = 1             