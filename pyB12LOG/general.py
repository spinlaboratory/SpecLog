"""
pyB12LOG: The logging program for instrumentations

general.py: connect instruments, querying data and writing to files

Author: Yen-Chun Huang

Company: Bridge 12 Technologies, Inc
"""
import os
import pyvisa
from pyvisa.constants import Parity, StopBits
import time
import datetime
from .config.config import CONFIG
from configparser import ConfigParser

rm = pyvisa.ResourceManager()

class DEVICE:
    def __init__(self, debugLogger):

        self.debugLogger= debugLogger
        self.deviceConfigDirHome = CONFIG['CONFIG']['log_folder_location'][1:-1]
        self.fileSize = int(CONFIG['CONFIG']['save_file_size_kb']) * 1024

        self.deviceConfigDirFile = self.deviceConfigDirHome +'/B12TLOG_Config/device_config.cfg'
        self.deviceConfig = ConfigParser()

        self.commandConfigFile = self.deviceConfigDirHome +'/B12TLOG_Config/command.cfg'
        self.commandConfig = ConfigParser()
        self._update_command() 

        self.detailFile = self.deviceConfigDirHome +'/B12TLOG_Config/device_detail.cfg'
        self.detail= ConfigParser(allow_no_value = True)
        self._create_detail()
        self._update_detail()
        self.logDir = self.deviceConfigDirHome + '/B12TLOG'

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

                with open(self.deviceConfigDirFile, 'w') as conf: ## Change configuration file
                    self.deviceConfig.write(conf)
            
            # When the device is off
            if self.deviceConfig[address]['device_status'] == 'False' and address in self.activeAddresses: # if the device status is False and in active device
                self.newFile = 1
                self.activeDevices.remove(inst)
                self.activeAddresses.remove(address) 

        if self.errorFlag: # this will force whole program restart in logger.py
            raise ConnectionError('Connection Restarted')

    def _update_command(self):
        self.commandConfig.read(self.commandConfigFile)
    
    def _create_detail(self):
        list_of_item = ['ALIAS', 'VALUE', 'VISIBILITY']
        # if detail file is not existing, generate new file
        if 'device_detail.cfg' not in os.listdir(self.deviceConfigDirHome +'/B12TLOG_Config/'):
            detail = open(self.detailFile, 'a')
            for item in list_of_item:
                detail.write('[%s]\n' %item)
            detail.close()

        self.detail.read(self.detailFile)    
        # check detail file is valid: list_of_item should be included in the 
        detail_valid = True
        for item in list_of_item:
            if item not in list(self.detail.keys()):
                detail_valid = False

        if not detail_valid: 
            # backup the comprise file and create a new one
            os.rename(self.detailFile, self.deviceConfigDirHome +'/B12TLOG_Config/device_detail_compromised.cfg')
            self.detail= ConfigParser(allow_no_value = True) # refresh the detail variable
            self._create_detail() # repeat the function itself
            self.debugLogger.info('Detail file is compromised. New file is created')

    def _update_detail(self):
        # update the detail along with the command config file
        self.detail.read(self.detailFile)
        save_detail = False
        for value in self.commandConfig.values():
            for key in value.keys():
                if key not in self.detail['ALIAS']:
                    self.detail['ALIAS'][key] = key
                    save_detail = True                   
                
                value_kws = ['_min', '_max', '_static']
                for kw in value_kws:
                    if key + kw not in self.detail['VALUE']:
                        self.detail['VALUE'][key + kw] = None
                        save_detail = True

                if key not in self.detail['VISIBILITY']:
                    self.detail['VISIBILITY'][key] = 'True'
                    save_detail = True

        if save_detail: # write to file only when the command changes while logger is running
            with open(self.detailFile, 'w') as conf:
                self.detail.write(conf)

    def log(self):
        self._update_connect()
        self._update_command()
        self._update_detail()
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
        data = {'Date': str(today), 'Time': str(datetime.datetime.now().strftime("%H:%M:%S"))}
        for inst, address in zip(self.activeDevices, self.activeAddresses):
            model = self.deviceConfig[address]['model_number'].replace("'", '')
            split_sign = self.deviceConfig[address]['split_sign'].replace("'", '')
            data_index = int(self.deviceConfig[address]['data_index'])
            if model in self.commandConfig.keys():
                for item, command in self.commandConfig[model].items():
                    try: 
                        data[item.strip()] = inst.query(command).strip('\n').strip('\r').split(split_sign)[data_index]
                    except Exception as err: # this handles the issue that devices disconnected during the query
                        self.debugLogger.info(err)
                        data[item.strip()] = 'nan'
                        self.newFile = 1
        if self.queryItems and self.activeAddresses:
            with open(self.logFile, 'a') as f:
                f.write('%s' %', '.join(list(data.values())) + '\n')

            if os.path.getsize(self.logFile) > self.fileSize:
                self.newFile = 1             