import os
import pyvisa
from pyvisa.constants import Parity, StopBits
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
        self.update_connect()
        self.log()

    def update_connect(self):
        self.deviceConfig.read(self.deviceConfigDirFile)
        for address in rm.list_resources():
            if self.deviceConfig[address]['device_status'] == 'True' and address not in self.active_addresses:
                for item, val in self.deviceConfig[address].items():
                    exec("%s = %s" %(item, val), globals()) # assign value from config. Be careful about changing it
                try:
                    inst = rm.open_resource(device_address)
                    inst.baud_rate=baud_rate
                    inst.data_bits=data_bits
                    inst.flow_control=flow_control 
                    inst.parity=parity
                    inst.stop_bits=stop_bits
                    inst.read_termination = termination
                    inst.write_termination = termination
  
                    device_id = inst.query(id_command).strip('\r').strip('\n').strip()

                    if not device_manufacturer or not model_number or not serial_number:
                        add_device_manufacturer = device_id.split(split_sign)[0]
                        add_model_number = device_id.split(split_sign)[1]
                        add_serial_number = device_id.split(split_sign)[2]
                        self.deviceConfig[address]['device_manufacturer'] = "'%s'" %add_device_manufacturer
                        self.deviceConfig[address]['model_number'] = "'%s'" %add_model_number
                        self.deviceConfig[address]['serial_number'] = "'%s'" %add_serial_number
                    
                    self.new_file = 1
                    self.active_devices.append(inst)  
                    self.active_addresses.append(address)         
                
                except Exception as err:
                    self.debugLogger.info('%s is inactive' %address)
                    self.deviceConfig[address]['device_status'] = 'False'
                    
                    if address in self.active_addresses:
                        self.new_file = 1
                        self.active_devices.remove(inst)
                        self.active_addresses.remove(address) 

                with open(self.deviceConfigDirFile, 'w') as conf:
                    self.deviceConfig.write(conf)

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
                    except:
                        data.append(0)
                        self.new_file = 1
        if self.query_items and self.active_addresses:
            with open(self.logFile, 'a') as f:
                f.write('%s' %', '.join(data) + '\n')

            if os.path.getsize(self.logFile) > self.file_size:
                self.new_file = 1             