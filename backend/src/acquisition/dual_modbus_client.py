"""
Dual Connectivity Manager - Auto-switching between TCP/IP and RS485
Handles Modbus RTU (RS485) and Modbus TCP with automatic failover.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from collections import deque

from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.exceptions import ModbusException

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """Available connection types"""
    TCP = "tcp"
    SERIAL = "serial"
    NONE = "none"


class ConnectionState(Enum):
    """Connection state machine"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class ConnectionConfig:
    """Connection configuration for a single device"""
    # TCP settings
    tcp_host: str = "192.168.1.100"
    tcp_port: int = 502
    tcp_timeout: float = 3.0
    
    # Serial settings
    serial_port: str = "COM3"
    serial_baud: int = 19200
    serial_timeout: float = 3.0
    serial_bytesize: int = 8
    serial_parity: str = "N"
    serial_stopbits: int = 1
    
    # Modbus settings
    slave_id: int = 1
    
    # Failover settings
    primary_connection: ConnectionType = ConnectionType.TCP
    failover_enabled: bool = True
    health_check_interval: float = 5.0
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 30.0
    failover_threshold: int = 3  # Consecutive failures before failover


@dataclass
class ConnectionHealth:
    """Connection health metrics"""
    state: ConnectionState = ConnectionState.DISCONNECTED
    connection_type: ConnectionType = ConnectionType.NONE
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    total_reads: int = 0
    successful_reads: int = 0
    avg_response_time: float = 0.0
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    error_count: int = 0
    failovers: int = 0


class DualModbusClient:
    """
    Dual connectivity Modbus client with automatic failover.
    Primary: TCP/IP, Fallback: Serial RS485
    """
    
    # Safe register block for QM30VT2
    START_REGISTER = 45201
    NUM_REGISTERS = 22
    
    def __init__(self, device_id: str, config: ConnectionConfig):
        self.device_id = device_id
        self.config = config
        
        # Clients
        self.tcp_client: Optional[ModbusTcpClient] = None
        self.serial_client: Optional[ModbusSerialClient] = None
        
        # State
        self.health = ConnectionHealth()
        self._current_connection: ConnectionType = config.primary_connection
        self._reconnect_delay = config.reconnect_delay
        self._running = False
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._on_data: Optional[Callable[[Dict[str, Any]], None]] = None
        self._on_status_change: Optional[Callable[[ConnectionState], None]] = None
        self._on_failover: Optional[Callable[[ConnectionType], None]] = None
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        logger.info(f"DualModbusClient initialized for device {device_id}")
    
    def on_data(self, callback: Callable[[Dict[str, Any]], None]):
        """Register data callback"""
        self._on_data = callback
    
    def on_status_change(self, callback: Callable[[ConnectionState], None]):
        """Register status change callback"""
        self._on_status_change = callback
    
    def on_failover(self, callback: Callable[[ConnectionType], None]):
        """Register failover callback"""
        self._on_failover = callback
    
    async def start(self) -> bool:
        """Start the connectivity manager"""
        self._running = True
        
        # Attempt initial connection
        success = await self._connect_primary()
        if not success and self.config.failover_enabled:
            success = await self._connect_fallback()
        
        # Start health check loop
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        return success
    
    async def stop(self):
        """Stop the connectivity manager"""
        self._running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        await self._disconnect_all()
        logger.info(f"DualModbusClient stopped for device {self.device_id}")
    
    async def _connect_primary(self) -> bool:
        """Connect to primary interface"""
        if self.config.primary_connection == ConnectionType.TCP:
            return await self._connect_tcp()
        else:
            return await self._connect_serial()
    
    async def _connect_fallback(self) -> bool:
        """Connect to fallback interface"""
        fallback = (ConnectionType.SERIAL 
                   if self.config.primary_connection == ConnectionType.TCP 
                   else ConnectionType.TCP)
        
        if fallback == ConnectionType.TCP:
            return await self._connect_tcp()
        else:
            return await self._connect_serial()
    
    async def _connect_tcp(self) -> bool:
        """Connect via TCP/IP"""
        async with self._lock:
            try:
                self.health.state = ConnectionState.CONNECTING
                logger.info(f"[{self.device_id}] Connecting via TCP to {self.config.tcp_host}:{self.config.tcp_port}")
                
                if self.tcp_client:
                    self.tcp_client.close()
                
                self.tcp_client = ModbusTcpClient(
                    host=self.config.tcp_host,
                    port=self.config.tcp_port,
                    timeout=self.config.tcp_timeout,
                    retries=3
                )
                
                if self.tcp_client.connect():
                    self._current_connection = ConnectionType.TCP
                    self.health.state = ConnectionState.CONNECTED
                    self.health.connection_type = ConnectionType.TCP
                    self.health.last_success = datetime.now()
                    self.health.consecutive_failures = 0
                    self._reconnect_delay = self.config.reconnect_delay
                    
                    logger.info(f"[{self.device_id}] TCP connection established")
                    if self._on_status_change:
                        await asyncio.to_thread(self._on_status_change, ConnectionState.CONNECTED)
                    return True
                else:
                    logger.warning(f"[{self.device_id}] TCP connection failed")
                    return False
                    
            except Exception as e:
                logger.error(f"[{self.device_id}] TCP connection error: {e}")
                return False
    
    async def _connect_serial(self) -> bool:
        """Connect via Serial RS485"""
        async with self._lock:
            try:
                self.health.state = ConnectionState.CONNECTING
                logger.info(f"[{self.device_id}] Connecting via Serial to {self.config.serial_port}")
                
                if self.serial_client:
                    self.serial_client.close()
                
                self.serial_client = ModbusSerialClient(
                    port=self.config.serial_port,
                    baudrate=self.config.serial_baud,
                    timeout=self.config.serial_timeout,
                    bytesize=self.config.serial_bytesize,
                    parity=self.config.serial_parity,
                    stopbits=self.config.serial_stopbits,
                    retries=3
                )
                
                if self.serial_client.connect():
                    self._current_connection = ConnectionType.SERIAL
                    self.health.state = ConnectionState.CONNECTED
                    self.health.connection_type = ConnectionType.SERIAL
                    self.health.last_success = datetime.now()
                    self.health.consecutive_failures = 0
                    self._reconnect_delay = self.config.reconnect_delay
                    
                    logger.info(f"[{self.device_id}] Serial connection established")
                    if self._on_status_change:
                        await asyncio.to_thread(self._on_status_change, ConnectionState.CONNECTED)
                    return True
                else:
                    logger.warning(f"[{self.device_id}] Serial connection failed")
                    return False
                    
            except Exception as e:
                logger.error(f"[{self.device_id}] Serial connection error: {e}")
                return False
    
    async def _disconnect_all(self):
        """Disconnect all interfaces"""
        async with self._lock:
            if self.tcp_client:
                self.tcp_client.close()
                self.tcp_client = None
            if self.serial_client:
                self.serial_client.close()
                self.serial_client = None
            self.health.state = ConnectionState.DISCONNECTED
    
    async def read_registers(self) -> Optional[Dict[str, Any]]:
        """
        Read Modbus registers with automatic failover.
        Returns parsed sensor data or None on failure.
        """
        start_time = time.time()
        
        async with self._lock:
            result = None
            
            # Try current connection first
            if self._current_connection == ConnectionType.TCP:
                result = await self._read_tcp()
                if result is None and self.config.failover_enabled:
                    result = await self._failover_to_serial()
            else:
                result = await self._read_serial()
                if result is None and self.config.failover_enabled:
                    result = await self._failover_to_tcp()
            
            # Update health metrics
            response_time = time.time() - start_time
            self.health.response_times.append(response_time)
            self.health.total_reads += 1
            
            if result:
                self.health.successful_reads += 1
                self.health.last_success = datetime.now()
                self.health.consecutive_failures = 0
                self.health.avg_response_time = sum(self.health.response_times) / len(self.health.response_times)
                
                if self.health.state != ConnectionState.CONNECTED:
                    self.health.state = ConnectionState.CONNECTED
                    if self._on_status_change:
                        await asyncio.to_thread(self._on_status_change, ConnectionState.CONNECTED)
            else:
                self.health.consecutive_failures += 1
                self.health.last_failure = datetime.now()
                
                # Degrade state after threshold
                if self.health.consecutive_failures >= self.config.failover_threshold:
                    self.health.state = ConnectionState.DEGRADED
                    if self._on_status_change:
                        await asyncio.to_thread(self._on_status_change, ConnectionState.DEGRADED)
            
            return result
    
    async def _read_tcp(self) -> Optional[Dict[str, Any]]:
        """Read registers via TCP"""
        if not self.tcp_client or not self.tcp_client.is_socket_open():
            return None
        
        try:
            address = self.START_REGISTER - 40001
            result = self.tcp_client.read_holding_registers(
                address=address,
                count=self.NUM_REGISTERS,
                slave=self.config.slave_id
            )
            
            if result and not result.isError():
                return self._parse_registers(result.registers)
            return None
            
        except ModbusException as e:
            logger.debug(f"[{self.device_id}] TCP read error: {e}")
            return None
        except Exception as e:
            logger.debug(f"[{self.device_id}] TCP read exception: {e}")
            return None
    
    async def _read_serial(self) -> Optional[Dict[str, Any]]:
        """Read registers via Serial"""
        if not self.serial_client or not self.serial_client.is_socket_open():
            return None
        
        try:
            address = self.START_REGISTER - 40001
            result = self.serial_client.read_holding_registers(
                address=address,
                count=self.NUM_REGISTERS,
                slave=self.config.slave_id
            )
            
            if result and not result.isError():
                return self._parse_registers(result.registers)
            return None
            
        except ModbusException as e:
            logger.debug(f"[{self.device_id}] Serial read error: {e}")
            return None
        except Exception as e:
            logger.debug(f"[{self.device_id}] Serial read exception: {e}")
            return None
    
    async def _failover_to_serial(self) -> Optional[Dict[str, Any]]:
        """Failover from TCP to Serial"""
        logger.warning(f"[{self.device_id}] Initiating failover to Serial")
        
        # Mark TCP as failed temporarily
        self.health.failovers += 1
        
        # Try serial connection
        if await self._connect_serial():
            logger.info(f"[{self.device_id}] Failover to Serial successful")
            if self._on_failover:
                await asyncio.to_thread(self._on_failover, ConnectionType.SERIAL)
            return await self._read_serial()
        
        logger.error(f"[{self.device_id}] Failover to Serial failed")
        return None
    
    async def _failover_to_tcp(self) -> Optional[Dict[str, Any]]:
        """Failover from Serial to TCP"""
        logger.warning(f"[{self.device_id}] Initiating failover to TCP")
        
        self.health.failovers += 1
        
        if await self._connect_tcp():
            logger.info(f"[{self.device_id}] Failover to TCP successful")
            if self._on_failover:
                await asyncio.to_thread(self._on_failover, ConnectionType.TCP)
            return await self._read_tcp()
        
        logger.error(f"[{self.device_id}] Failover to TCP failed")
        return None
    
    def _parse_registers(self, registers: List[int]) -> Dict[str, Any]:
        """Parse Modbus registers into sensor data"""
        if len(registers) < 22:
            logger.warning(f"[{self.device_id}] Insufficient register data: {len(registers)}")
            return {}
        
        data = {
            # Primary fields
            "z_rms": round(registers[0] / 10000.0, 4),  # Z-Axis RMS Velocity (in/sec)
            "z_rms_mm": round(registers[1] / 1000.0, 3),  # Z-Axis RMS Velocity (mm/sec)
            "temp_f": round(registers[2] / 100.0, 1),  # Temperature (°F)
            "temperature": round(self._signed_word(registers[3]) / 100.0, 1),  # Temperature (°C)
            "x_rms": round(registers[4] / 10000.0, 4),  # X-Axis RMS Velocity (in/sec)
            "x_rms_mm": round(registers[5] / 1000.0, 3),  # X-Axis RMS Velocity (mm/sec)
            "z_peak_accel": round(registers[6] / 1000.0, 3),  # Z-Axis Peak Acceleration (G)
            "x_peak_accel": round(registers[7] / 1000.0, 3),  # X-Axis Peak Acceleration (G)
            "z_peak_freq": round(registers[8] / 10.0, 1),  # Z-Axis Peak Velocity Frequency (Hz)
            "x_peak_freq": round(registers[9] / 10.0, 1),  # X-Axis Peak Velocity Frequency (Hz)
            "z_rms_accel": round(registers[10] / 1000.0, 3),  # Z-Axis RMS Acceleration (G)
            "x_rms_accel": round(registers[11] / 1000.0, 3),  # X-Axis RMS Acceleration (G)
            "z_kurtosis": round(registers[12] / 1000.0, 3),  # Z-Axis Kurtosis
            "x_kurtosis": round(registers[13] / 1000.0, 3),  # X-Axis Kurtosis
            "z_crest_factor": round(registers[14] / 1000.0, 3),  # Z-Axis Crest Factor
            "x_crest_factor": round(registers[15] / 1000.0, 3),  # X-Axis Crest Factor
            "z_peak_vel_in": round(registers[16] / 10000.0, 4),  # Z-Axis Peak Velocity (in/sec)
            "z_peak_vel_mm": round(registers[17] / 1000.0, 3),  # Z-Axis Peak Velocity (mm/sec)
            "x_peak_vel_in": round(registers[18] / 10000.0, 4),  # X-Axis Peak Velocity (in/sec)
            "x_peak_vel_mm": round(registers[19] / 1000.0, 3),  # X-Axis Peak Velocity (mm/sec)
            "z_hf_rms_accel": round(registers[20] / 1000.0, 3),  # Z-Axis HF RMS Acceleration (G)
            "x_hf_rms_accel": round(registers[21] / 1000.0, 3),  # X-Axis HF RMS Acceleration (G)
            
            # Aliases for frontend compatibility
            "z_peak": round(registers[17] / 1000.0, 3),
            "x_peak": round(registers[19] / 1000.0, 3),
            "z_accel": round(registers[6] / 1000.0, 3),
            "x_accel": round(registers[7] / 1000.0, 3),
            "kurtosis": round(registers[12] / 1000.0, 3),
            "crest_factor": round(registers[14] / 1000.0, 3),
            "frequency": round(registers[8] / 10.0, 1),
            
            # Metadata
            "device_id": self.device_id,
            "timestamp": datetime.now().isoformat(),
            "connection_type": self._current_connection.value,
            "raw_registers": registers
        }
        
        return data
    
    @staticmethod
    def _signed_word(value: int) -> int:
        """Convert unsigned word to signed"""
        if value > 32767:
            return value - 65536
        return value
    
    async def _health_check_loop(self):
        """Background health check loop"""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                # Check if connection is healthy
                if self.health.state == ConnectionState.CONNECTED:
                    if self._current_connection == ConnectionType.TCP:
                        if not self.tcp_client or not self.tcp_client.is_socket_open():
                            logger.warning(f"[{self.device_id}] TCP connection lost, attempting reconnect")
                            if not await self._connect_tcp() and self.config.failover_enabled:
                                await self._failover_to_serial()
                    else:
                        if not self.serial_client or not self.serial_client.is_socket_open():
                            logger.warning(f"[{self.device_id}] Serial connection lost, attempting reconnect")
                            if not await self._connect_serial() and self.config.failover_enabled:
                                await self._failover_to_tcp()
                
                # Attempt to reconnect to primary if in fallback
                elif self.health.state == ConnectionState.DEGRADED or self.health.state == ConnectionState.FAILED:
                    logger.info(f"[{self.device_id}] Attempting to restore primary connection")
                    if self.config.primary_connection == ConnectionType.TCP:
                        if await self._connect_tcp():
                            logger.info(f"[{self.device_id}] Restored primary TCP connection")
                    else:
                        if await self._connect_serial():
                            logger.info(f"[{self.device_id}] Restored primary Serial connection")
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.device_id}] Health check error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        return {
            "device_id": self.device_id,
            "state": self.health.state.value,
            "connection_type": self.health.connection_type.value,
            "primary_connection": self.config.primary_connection.value,
            "failover_enabled": self.config.failover_enabled,
            "last_success": self.health.last_success.isoformat() if self.health.last_success else None,
            "last_failure": self.health.last_failure.isoformat() if self.health.last_failure else None,
            "consecutive_failures": self.health.consecutive_failures,
            "total_reads": self.health.total_reads,
            "successful_reads": self.health.successful_reads,
            "success_rate": round((self.health.successful_reads / max(1, self.health.total_reads)) * 100, 1),
            "avg_response_time_ms": round(self.health.avg_response_time * 1000, 1),
            "failovers": self.health.failovers
        }
