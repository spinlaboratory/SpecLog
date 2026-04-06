"""
SpecLog: The logging program for instrumentations

devices.py: connect instruments and show the availability of devices

Author: Yen-Chun Huang

Company: Bridge 12 Technologies, Inc
"""

import serial
import serial.tools.list_ports

from .debugLog import *


class DEVICE:
    def __init__(self, config, debug_logger):
        self.devices_info = {}
        self._getPorts()
        self.debug_logger = debug_logger
        self.device_config = config.devices
        self._setDevice()

        self.checkDeviceStatus()

    def _getPorts(self):
        ports = serial.tools.list_ports.comports()
        self.deviceAddresses = []
        for port, desc, hwid in sorted(ports):
            self.deviceAddresses.append(port)

        return True

    def _setDevice(self, name: str = None):
        """
        Apply settings to a device and return availability:
        Args:
            name (str): the name of device
        Return:
            device_dict
            {connection_status (bool): the status of device communication
            device (pyVISA): the devices class for sending command
        """
        if name:
            setting = self.device_config[name]
            self.debug_logger.info("Setting: %s" % name)
            status = setting["device_status"]
            address = setting["address"]
            baud_rate = setting["baud_rate"]
            termination = setting["termination"]
            data_bits = setting["data_bits"]
            flow_control = setting["flow_control"]
            parity = self._parity(setting["parity"])
            stop_bits = self._stopBits(setting["stop_bits"])
            id_command = setting["id_command"]
            if address in self.deviceAddresses:

                device = serial.Serial(port=address, timeout=1)
                device.baudrate = baud_rate
                device.bytesize = data_bits
                if flow_control:
                    device.xonxoff = flow_control
                device.read_termination = termination
                device.write_termination = termination
                if parity:
                    device.parity = parity
                if stop_bits:
                    device.stopbits = stop_bits

            else:
                device = None

            self.devices_info[name] = {
                "status": status,
                "config_status": status,
                "device": device,
                "id_command": id_command,
                "termination": termination,
            }
            return True

        else:
            self.devices_info = {}
            for name in self.device_config.keys():
                self._setDevice(name)

    def checkDeviceStatus(self, name: str = None, init: bool = False):
        if name:
            device_info = self.devices_info[name]
            id_command = device_info["id_command"]
            device = device_info["device"]
            termination = device_info["termination"]
            try:
                if device_info["status"]:
                    device.write((id_command + termination).encode())
                    string = device.read_until(termination.encode()).decode()
                    
                else:
                    return False
                if init:
                    self.debug_logger.info("get %s from device %s" % (string, name))
                    self.debug_logger.info("%s is connected" % name)
                device_info["status"] = True
                return True

            except Exception as err:
                if device_info[
                    "status"
                ]:  # at the moment when status become disconnected
                    self.debug_logger.error(err)
                    self.debug_logger.warning("%s is disconnected" % name)
                    device_info["status"] = False
                return False

        else:
            for name in self.devices_info.keys():
                if self.checkDeviceStatus(name):
                    self.debug_logger.info("%s is valid and connected" % name)
                else:
                    self.debug_logger.info("%s is invalid" % name)

    def _parity(self, parity):
        """
        Get pyvisa constant parity
        """
        if parity == None:
            return parity
        elif parity == 0:
            return serial.PARITY_NONE
        elif parity == 1:
            return serial.PARITY_ODD
        elif parity == 2:
            return serial.PARITY_EVEN
        elif parity == 3:
            return serial.PARITY_MARK
        elif parity == 4:
            return serial.PARITY_SPACE
        else:
            self.debug_logger.warning("Parity error")
            return None

    def _stopBits(self, stop_bits):
        if stop_bits == None:
            return stop_bits
        elif stop_bits == 10:
            return serial.STOPBITS_ONE
        elif stop_bits == 15:
            return serial.STOPBITS_ONE_POINT_FIVE
        elif stop_bits == 20:
            return serial.STOPBITS_TWO
        else:
            self.debug_logger.warning("Stop bits error")
            return None
