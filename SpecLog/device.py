"""Device management and transport protocol implementations."""

from abc import ABC, abstractmethod
import threading
import time
from typing import Any, Mapping

import serial
import serial.tools.list_ports


class DeviceProtocol(ABC):
    """Transport boundary used by :class:`DEVICE`.

    New transports, such as Ethernet, implement this interface and are added
    to DEVICE's protocol registry. The logger never needs to access a raw
    transport connection.
    """

    @abstractmethod
    def refresh(self) -> None:
        """Refresh transport discovery state."""

    @abstractmethod
    def available_addresses(self) -> list[str]:
        """Return addresses currently reachable by this transport."""

    @abstractmethod
    def connect(self, settings: Mapping[str, Any]) -> Any:
        """Create and return a transport-specific connection."""

    @abstractmethod
    def query(
        self, connection: Any, command: str, termination: str
    ) -> str:
        """Send a command and return the decoded response."""

    @abstractmethod
    def close(self, connection: Any) -> None:
        """Close a transport-specific connection."""

    def is_available(self, address: str) -> bool:
        return address in self.available_addresses()


class SerialProtocol(DeviceProtocol):
    """USB/COM serial implementation of the device transport interface."""

    PARITIES = {
        None: None,
        0: serial.PARITY_NONE,
        1: serial.PARITY_ODD,
        2: serial.PARITY_EVEN,
        3: serial.PARITY_MARK,
        4: serial.PARITY_SPACE,
    }
    STOP_BITS = {
        None: None,
        10: serial.STOPBITS_ONE,
        15: serial.STOPBITS_ONE_POINT_FIVE,
        20: serial.STOPBITS_TWO,
    }

    def __init__(self):
        self._addresses = []
        self.refresh()

    def refresh(self) -> None:
        self._addresses = [
            port for port, _description, _hwid
            in sorted(serial.tools.list_ports.comports())
        ]

    def available_addresses(self) -> list[str]:
        return list(self._addresses)

    def connect(self, settings: Mapping[str, Any]):
        parity = self.PARITIES.get(settings["parity"])
        stop_bits = self.STOP_BITS.get(settings["stop_bits"])
        if settings["parity"] not in self.PARITIES:
            raise ValueError("Invalid serial parity")
        if settings["stop_bits"] not in self.STOP_BITS:
            raise ValueError("Invalid serial stop bits")

        options = {
            "port": settings["address"],
            "timeout": 1,
            "baudrate": settings["baud_rate"],
            "bytesize": settings["data_bits"],
            "xonxoff": bool(settings["flow_control"]),
        }
        if parity is not None:
            options["parity"] = parity
        if stop_bits is not None:
            options["stopbits"] = stop_bits
        return serial.Serial(**options)

    def query(self, connection, command: str, termination: str) -> str:
        connection.write((command + termination).encode())
        return connection.read_until(termination.encode()).decode()

    def close(self, connection) -> None:
        connection.close()


class DEVICE:
    def __init__(
        self,
        config,
        debug_logger,
        protocols=None,
        retry_max_seconds: float = 30.0,
        stabilization_seconds: float = 1.0,
    ):
        self.debug_logger = debug_logger
        self.device_config = config.devices
        self.retry_max_seconds = retry_max_seconds
        self.stabilization_seconds = stabilization_seconds
        self._lock = threading.RLock()
        if protocols is None:
            serial_protocol = SerialProtocol()
            protocols = {
                "serial": serial_protocol,
                "usb": serial_protocol,
            }
        self.protocols = {
            name.lower(): protocol for name, protocol in protocols.items()
        }
        self.device_info = {}
        self._getPorts()
        self._setDevice()
        self.checkDeviceStatus()

    def register_protocol(self, name: str, protocol: DeviceProtocol) -> None:
        """Register or replace a transport for subsequently configured devices."""
        self.protocols[name.lower()] = protocol

    def _getPorts(self):
        """Refresh transports and retain the legacy serial-address attribute."""
        # The USB and serial names normally refer to the same instance.
        unique_protocols = {id(item): item for item in self.protocols.values()}
        for protocol in unique_protocols.values():
            protocol.refresh()
        serial_protocol = self.protocols.get("serial")
        self.deviceAddresses = (
            serial_protocol.available_addresses() if serial_protocol else []
        )
        return True

    def _setDevice(self, name: str = None):
        if name is None:
            self.device_info = {}
            for device_name in self.device_config:
                self._setDevice(device_name)
            return True

        settings = self.device_config[name]
        protocol_name = settings.get("protocol", "serial").lower()
        if protocol_name not in self.protocols:
            raise ValueError(
                f"Unknown protocol {protocol_name!r} for device {name!r}"
            )

        self.debug_logger.info("Setting: %s", name)
        protocol = self.protocols[protocol_name]
        configured = settings["device_status"]
        self.device_info[name] = {
            "status": False,
            "config_status": configured,
            "device": None,
            "protocol": protocol,
            "protocol_name": protocol_name,
            "id_command": settings["id_command"],
            "termination": settings["termination"],
            "state": "disabled" if not configured else "disconnected",
            "last_error": None,
            "retry_count": 0,
            "next_retry_time": 0.0,
            "was_available": protocol.is_available(settings["address"]),
        }
        if configured and self.device_info[name]["was_available"]:
            self._connect(name)
        return True

    def _retry_delay(self, retry_count: int) -> float:
        return min(self.retry_max_seconds, 2 ** max(0, retry_count - 1))

    def _disconnect(self, name: str, error=None, schedule_retry=True) -> None:
        """Close and discard a connection so a poisoned handle is never reused."""
        with self._lock:
            info = self.device_info[name]
            connection = info["device"]
            if connection is not None:
                try:
                    info["protocol"].close(connection)
                except Exception as close_error:
                    self.debug_logger.warning(
                        "Failed to close device %s: %s", name, close_error
                    )
            info["device"] = None
            info["status"] = False
            info["last_error"] = str(error) if error is not None else None
            if schedule_retry and info["config_status"]:
                info["retry_count"] += 1
                delay = self._retry_delay(info["retry_count"])
                info["next_retry_time"] = time.monotonic() + delay
                info["state"] = "retry_wait"
            else:
                info["state"] = (
                    "disabled" if not info["config_status"] else "disconnected"
                )

    def _connect(self, name: str) -> bool:
        with self._lock:
            info = self.device_info[name]
            settings = self.device_config[name]
            info["state"] = "connecting"
            try:
                info["device"] = info["protocol"].connect(settings)
                info["status"] = True
                info["state"] = "connected"
                info["last_error"] = None
                return True
            except Exception as error:
                self.debug_logger.error(
                    "Could not open device %s at %s: %s",
                    name,
                    settings["address"],
                    error,
                )
                self._disconnect(name, error)
                return False

    def query(self, name: str, command: str) -> str:
        with self._lock:
            info = self.device_info[name]
            connection = info["device"]
            if not info["status"] or connection is None:
                raise ConnectionError(f"Device {name!r} is not connected")
            try:
                return info["protocol"].query(
                    connection, command, info["termination"]
                )
            except Exception as error:
                self.debug_logger.error("Device %s query failed: %s", name, error)
                self._disconnect(name, error)
                raise

    def checkDeviceStatus(self, name: str = None, init: bool = False):
        if name is None:
            for device_name in self.device_info:
                if self.checkDeviceStatus(device_name):
                    self.debug_logger.info(
                        "%s is valid and connected", device_name
                    )
                else:
                    self.debug_logger.warning(
                        "%s is invalid; check its connection and settings",
                        device_name,
                    )
            return None

        info = self.device_info[name]
        if not info["config_status"] or info["device"] is None:
            info["status"] = False
            return False
        try:
            # Use the transport abstraction for the identification query too.
            info["status"] = True
            response = self.query(name, info["id_command"])
            if init:
                self.debug_logger.info("get %s from device %s", response, name)
            return True
        except Exception as error:
            self.debug_logger.warning("%s is disconnected: %s", name, error)
            return False

    def reconnectDevices(self) -> bool:
        """Recover disconnected devices, including still-enumerated COM ports."""
        with self._lock:
            self._getPorts()
            now = time.monotonic()
            reconnected = False
            for name, settings in self.device_config.items():
                info = self.device_info[name]
                if not info["config_status"]:
                    continue

                protocol = info["protocol"]
                address = settings["address"]
                available = protocol.is_available(address)

                if not available:
                    if info["device"] is not None:
                        self._disconnect(name, "device is no longer available")
                    info["was_available"] = False
                    continue

                if not info["was_available"]:
                    # Enumeration can precede readiness of the VCP interface.
                    info["next_retry_time"] = max(
                        info["next_retry_time"],
                        now + self.stabilization_seconds,
                    )
                info["was_available"] = True

                # A false status means the handle is suspect even if Windows
                # continues to list the COM port.
                if info["device"] is not None and not info["status"]:
                    self._disconnect(name, info["last_error"])

                if (
                    info["device"] is None
                    and now >= info["next_retry_time"]
                    and self._connect(name)
                    and self.checkDeviceStatus(name, init=True)
                ):
                    info["retry_count"] = 0
                    info["next_retry_time"] = 0.0
                    reconnected = True

            return reconnected

    def close(self) -> None:
        """Close every device connection owned by this manager."""
        with self._lock:
            for name in self.device_info:
                self._disconnect(name, schedule_retry=False)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
