# Acquisition module - Modbus client and multi-device management
from .dual_modbus_client import DualModbusClient, ConnectionConfig, ConnectionType, ConnectionState
from .multi_device_manager import MultiDXMManager, DeviceInfo, UnifiedData

__all__ = [
    'DualModbusClient',
    'ConnectionConfig',
    'ConnectionType',
    'ConnectionState',
    'MultiDXMManager',
    'DeviceInfo',
    'UnifiedData'
]
