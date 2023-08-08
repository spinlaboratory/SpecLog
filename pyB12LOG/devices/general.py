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
        self.file_size = int(CONFIG['CONFIG']['save_file_size_kb']) * 1024
        self.deviceConfigDirFile = deviceConfigDirHome +'/B12TLOG_Config/device_config.cfg'
        self.deviceConfig = ConfigParser()

        self.commandConfigFile = deviceConfigDirHome +'/B12TLOG_Config/command.cfg'
        self.commandConfig = ConfigParser()

        self.logDir = deviceConfigDirHome + '/B12TLOG'

        self.debugLogger= debugLogger
        self.active_devices = []
        self.active_addresses = []
        self.query_items = []
        self.new_file = 1

    def update_connect(self):
        self.deviceConfig.read(self.deviceConfigDirFile)
        self.error_flag = False # This is the flag to restart the resource manager
        for address in rm.list_resources():
            if self.deviceConfig[address]['device_status'] == 'True' and address not in self.active_addresses: # if the device status is True and device is not connected yet
                serial_settings_dict = {}
                for item, val in self.deviceConfig[address].items():
                    exec("serial_settings_dict['%s'] = %s" %(item, val)) # assign value from config. Be careful about changing it
                try:
                    inst = rm.open_resource(serial_settings_dict['device_address'])
                    inst.baud_rate=serial_settings_dict['baud_rate']
                    inst.data_bits=serial_settings_dict['data_bits']
                    inst.flow_control=serial_settings_dict['flow_control']
                    inst.parity=serial_settings_dict['parity']
                    inst.stop_bits=serial_settings_dict['stop_bits']
                    inst.read_termination = serial_settings_dict['termination']
                    inst.write_termination = serial_settings_dict['termination']
  
                    device_id = inst.query(serial_settings_dict['id_command']).strip('\r').strip('\n').strip() # actually query ID from device
                    self.debugLogger.info('%s connected!' %device_id)

                    if not serial_settings_dict['device_manufacturer'] or not serial_settings_dict['model_number'] or not serial_settings_dict['serial_number']:
                        add_device_manufacturer = device_id.split(serial_settings_dict['split_sign'])[0]
                        add_model_number = device_id.split(serial_settings_dict['split_sign'])[1]
                        add_serial_number = device_id.split(serial_settings_dict['split_sign'])[2]
                        self.deviceConfig[address]['device_manufacturer'] = "'%s'" %add_device_manufacturer
                        self.deviceConfig[address]['model_number'] = "'%s'" %add_model_number
                        self.deviceConfig[address]['serial_number'] = "'%s'" %add_serial_number
                    
                    self.new_file = 1
                    self.active_devices.append(inst)  
                    self.active_addresses.append(address)         
                
                except Exception as err:
                    self.error_flag = True
                    self.debugLogger.warn(err)
                    self.debugLogger.info('%s is inactive' %address)
                    self.deviceConfig[address]['device_status'] = 'False'
                    
                    if address in self.active_addresses:
                        self.new_file = 1
                        self.active_devices.remove(inst)
                        self.active_addresses.remove(address) 

                with open(self.deviceConfigDirFile, 'w') as conf:
                    self.deviceConfig.write(conf)

        if self.error_flag: # this will force whole program restart in logger.py
            raise ConnectionError('Connection Restarts')

    def log(self):
        self.update_connect()
        self.commandConfig.read(self.commandConfigFile)
        if self.new_file:
            for address in self.active_addresses:
                model_number = self.deviceConfig[address]['model_number'].replace("'", '')
                if model_number in self.commandConfig.keys():
                    for key in self.commandConfig[model_number]:
                        if key not in self.query_items:
                            self.query_items.append(key) 
            
            now = datetime.datetime.now().strftime('%Y%m%d%H%M%S') #YYYYMMDDHMS
            self.logFile = self.logDir + '/' + 'log_' + now + '.csv'
            
            if self.active_addresses:
                with open(self.logFile, 'w') as f:
                        f.write('Date, Time, %s' %', '.join(self.query_items) + '\n')
                self.new_file = 0

        today = datetime.date.today()
        data = [str(today), str(datetime.datetime.now().strftime("%H:%M:%S"))]
        for index, (inst, address) in enumerate(zip(self.active_devices, self.active_addresses)):
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
                        self.new_file = 1
        if self.query_items and self.active_addresses:
            with open(self.logFile, 'a') as f:
                f.write('%s' %', '.join(data) + '\n')

            if os.path.getsize(self.logFile) > self.file_size:
                self.new_file = 1             