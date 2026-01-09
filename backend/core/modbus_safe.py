"""
Safe Modbus Client - ONLY reads registers 45201-45217
Prevents any access to 43501 or other restricted registers
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException

# Import serial tools with proper error handling
try:
    from serial.tools import list_ports
except ImportError:
    # pyserial not installed - create a fallback
    class MockListPorts:
        @staticmethod
        def comports():
            # Return empty list if pyserial not available
            return []
    
    list_ports = MockListPorts()
    
    list_ports = MockListPorts()

logger = logging.getLogger(__name__)

class ModbusClient:
    """Safe Modbus client that only accesses register block 45201-45217"""
    
    # SAFE REGISTER BLOCK - ONLY THESE REGISTERS
    START_REGISTER = 45201
    NUM_REGISTERS = 17
    
    def __init__(self):
        self.client: Optional[AsyncModbusSerialClient] = None
        self.port: Optional[str] = None
        self.baud: int = 19200
        self.slave_id: int = 1
        self.connected: bool = False
        self.connect_time: Optional[datetime] = None
        self.last_poll: Optional[datetime] = None
        self.packet_loss_count: int = 0
        self.total_polls: int = 0
        self.auto_reconnect: bool = True
        
    async def connect(self, port: str, baud: int = 19200, slave_id: int = 1) -> bool:
        """Connect to Modbus RTU device"""
        try:
            self.port = port
            self.baud = baud
            self.slave_id = slave_id
            
            self.client = AsyncModbusSerialClient(
                port=port,
                baudrate=baud,
                timeout=1.0,
                retries=3
            )
            
            if await self.client.connect():
                self.connected = True
                self.connect_time = datetime.now()
                logger.info(f"Connected to Modbus: {port} @ {baud} baud, Slave ID: {slave_id}")
                return True
            else:
                logger.error(f"Failed to connect to {port}")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Modbus device"""
        if self.client:
            self.client.close()
            self.connected = False
            self.connect_time = None
            logger.info("Modbus disconnected")
    
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.connected and self.client is not None
    
    async def scan_ports(self) -> List[str]:
        """Scan available COM ports"""
        ports = []
        try:
            # Try to use pyserial's list_ports
            port_list = list_ports.comports()
            for port in port_list:
                if hasattr(port, 'device'):
                    ports.append(port.device)
                elif hasattr(port, 'name'):
                    ports.append(port.name)
        except (AttributeError, ImportError, Exception) as e:
            logger.warning(f"Could not scan ports with pyserial: {e}")
            # Fallback: return common COM ports based on OS
            import platform
            if platform.system() == 'Windows':
                # Common COM ports on Windows
                for i in range(1, 21):
                    ports.append(f'COM{i}')
            else:
                # Common serial ports on Linux/Mac
                ports = ['/dev/ttyUSB0', '/dev/ttyACM0', '/dev/ttyS0']
        return ports
    
    async def read_safe_registers(self) -> Optional[Dict[str, Any]]:
        """
        Read ONLY the safe register block 45201-45217
        Returns scaled sensor data
        """
        if not self.is_connected():
            return None
        
        try:
            # Read 17 registers starting at 45201
            # Note: pymodbus uses 0-based addressing, so 45201 becomes 45200
            result = await self.client.read_holding_registers(
                address=self.START_REGISTER - 1,  # Convert to 0-based
                count=self.NUM_REGISTERS,
                slave=self.slave_id
            )
            
            if result.isError():
                self.packet_loss_count += 1
                self.total_polls += 1
                logger.warning(f"Modbus read error: {result}")
                return None
            
            # Parse registers
            registers = result.registers
            
            # Scale values according to specification
            # Velocity: register_value / 65535 * 65.535 mm/s
            # Temperature: register_value / 100 °C
            
            z_rms = (registers[0] / 65535.0) * 65.535 if len(registers) > 0 else 0.0
            x_rms = (registers[1] / 65535.0) * 65.535 if len(registers) > 1 else 0.0
            z_peak = (registers[2] / 65535.0) * 65.535 if len(registers) > 2 else 0.0
            x_peak = (registers[3] / 65535.0) * 65.535 if len(registers) > 3 else 0.0
            z_accel = (registers[4] / 65535.0) * 65.535 if len(registers) > 4 else 0.0
            x_accel = (registers[5] / 65535.0) * 65.535 if len(registers) > 5 else 0.0
            temperature = registers[6] / 100.0 if len(registers) > 6 else 0.0
            
            # Additional registers (7-16) for future use
            raw_data = registers[7:17] if len(registers) > 7 else []
            
            self.last_poll = datetime.now()
            self.total_polls += 1
            
            return {
                "z_rms": round(z_rms, 3),
                "x_rms": round(x_rms, 3),
                "z_peak": round(z_peak, 3),
                "x_peak": round(x_peak, 3),
                "z_accel": round(z_accel, 3),
                "x_accel": round(x_accel, 3),
                "temperature": round(temperature, 1),
                "raw_registers": raw_data,
                "timestamp": self.last_poll.isoformat()
            }
            
        except ModbusException as e:
            self.packet_loss_count += 1
            self.total_polls += 1
            logger.error(f"Modbus exception: {e}")
            return None
        except Exception as e:
            self.packet_loss_count += 1
            self.total_polls += 1
            logger.error(f"Unexpected error reading registers: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        uptime_seconds = 0
        if self.connect_time:
            uptime = datetime.now() - self.connect_time
            uptime_seconds = int(uptime.total_seconds())
        
        packet_loss = 0.0
        if self.total_polls > 0:
            packet_loss = (self.packet_loss_count / self.total_polls) * 100.0
        
        return {
            "connected": self.connected,
            "port": self.port,
            "baud": self.baud,
            "slave_id": self.slave_id,
            "uptime_seconds": uptime_seconds,
            "last_poll": self.last_poll.isoformat() if self.last_poll else None,
            "packet_loss": round(packet_loss, 2),
            "auto_reconnect": self.auto_reconnect,
            "total_polls": self.total_polls,
            "successful_polls": self.total_polls - self.packet_loss_count
        }

