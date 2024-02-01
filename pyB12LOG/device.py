"""
pyB12LOG: The logging program for instrumentations

devices.py: connect instruments and show the availability of devices

Author: Yen-Chun Huang

Company: Bridge 12 Technologies, Inc
"""

import pyvisa
from pyvisa.constants import Parity, StopBits
from .debugLog import *

class DEVICE:
    def __init__(self, config, debug_logger):
        self.devices_info = {}
        self.rm, self.deviceAddresses = self._getResourceManager()
        self.debug_logger = debug_logger
        self.device_config = config.devices
        self._setDevice()

        self.checkDeviceStatus()
    
    def _getResourceManager(self):
        rm = pyvisa.ResourceManager()
        
        if rm.last_status != 0: # clean last status when initial
            self.debug_logger.warning('The resource was taken')
            rm.close()
            rm = pyvisa.ResourceManager()
            self.debug_logger.warning('The resource has been closed and re-opened')

        deviceAddresses = rm.list_resources()

        return rm, deviceAddresses
        
    def _setDevice(self, name: str = None):
        '''
        Apply settings to a device and return availability:
        Args:
            name (str): the name of device
        Return:
            device_dict
            {connection_status (bool): the status of device communication
            device (pyVISA): the devices class for sending command
        '''
        if name:
            setting = self.device_config[name]
            self.debug_logger.info('Setting: %s' %name)
            status = setting['device_status']
            address = setting['address']
            baud_rate = setting['baud_rate']
            termination = setting['termination']
            data_bits = setting['data_bits']
            flow_control = setting['flow_control']
            parity = self._parity(setting['parity'])
            stop_bits = self._stopBits(setting['stop_bits'])
            id_command = setting['id_command']

            if address in self.deviceAddresses:
                device = self.rm.open_resource(address)
                device.baud_rate = baud_rate
                device.data_bits = data_bits
                if flow_control:
                    device.flow_control = flow_control
                device.read_termination = termination
                device.write_termination = termination
                if parity:
                    device.parity = parity
                if stop_bits:
                    device.stop_bits = stop_bits   
            
            else:
                device = None

            self.devices_info[name] = {'status': status, 'config_status': status, 'device': device, 'id_command': id_command}
            return True

        else:
            self.devices_info = {}
            for name in self.device_config.keys():
                self._setDevice(name)
    
    def checkDeviceStatus(self, name: str = None):
        if name:
            device_info = self.devices_info[name]
            id_command = device_info['id_command']
            device = device_info['device']
            try: 
                string = device.query(id_command)
                self.debug_logger.info('get %s from device %s' %(string, name))
                if not device_info['status']:
                    self.debug_logger.warning('%s is reconnected' % name)
                    device_info['status'] = True
                return True
            except Exception as err:
                self.debug_logger.error(err)
                if device_info['status']: # at the moment when status become disconnected
                    self.debug_logger.warning('%s is disconnected' % name)
                    device_info['status'] = False
                return False
                
        else:
            for name in self.devices_info.keys():
                if self.checkDeviceStatus(name):
                    self.debug_logger.info('%s is valid and connected' % name)
                else:
                    self.debug_logger.info('%s is invalid' % name)

    def _parity(self, parity):
        '''
        Get pyvisa constant parity
        '''
        if parity == None:
            return parity
        elif parity == 0:
            return Parity.none
        elif parity == 1:
            return Parity.odd
        elif parity == 2:
            return Parity.even
        elif parity == 3:
            return Parity.mark
        elif parity == 4:
            return Parity.space
        else:
            self.debug_logger.warning('Parity error')
            return None
    
    def _stopBits(self, stop_bits):
        if stop_bits == None:
            return stop_bits
        elif stop_bits == 10:
          return StopBits.one
        elif stop_bits == 15:
            return StopBits.one_and_a_half
        elif stop_bits == 20:
            return StopBits.two
        else:
            self.debug_logger.warning('Stop bits error')
            return None