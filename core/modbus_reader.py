"""
Project Gandiva - Modbus Sensor Reader
======================================

This module handles communication with Banner QM30VT2-style vibration sensors
over Modbus RTU (RS-485) or Modbus TCP.

Register Map (QM30VT2-style sensor):
------------------------------------
Holding Registers (Function Code 03):

  Address | Description                | Unit/Scale      | Data Type
  --------|----------------------------|-----------------|------------
  40001   | RMS Velocity               | 0.01 mm/s       | UINT16
  40002   | Peak Acceleration          | 0.001 g         | UINT16
  40003   | Frequency (dominant)       | 0.1 Hz          | UINT16
  40004   | Band 1X Energy             | 0.01 (ratio)    | UINT16
  40005   | Band 2X Energy             | 0.01 (ratio)    | UINT16
  40006   | Band 3X Energy             | 0.01 (ratio)    | UINT16
  40007   | Band 5X Energy             | 0.01 (ratio)    | UINT16
  40008   | Band 7X Energy             | 0.01 (ratio)    | UINT16
  40009   | Temperature                | 0.1 °C          | INT16
  40010   | Sensor Status              | Bitmask         | UINT16

Status Register Bits:
  Bit 0: Sensor OK (1=OK, 0=Fault)
  Bit 1: Overload warning
  Bit 2: Temperature warning
  Bit 3-15: Reserved

Note: Modbus addresses are 0-indexed in pymodbus, so register 40001 = address 0
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

# Try to import pymodbus
try:
    from pymodbus.client import ModbusSerialClient, ModbusTcpClient
    from pymodbus.exceptions import ModbusException
    PYMODBUS_AVAILABLE = True
except ImportError:
    PYMODBUS_AVAILABLE = False
    logger.warning("pymodbus not installed. Install with: pip install pymodbus")


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class ModbusConfig:
    """Configuration for Modbus connection."""
    # Connection type: "rtu" or "tcp"
    connection_type: str = "rtu"
    
    # RTU settings (serial port)
    port: str = "COM5"          # Windows: COM3, Linux: /dev/ttyUSB0
    baudrate: int = 19200       # QM30VT2 default: 19200
    bytesize: int = 8
    parity: str = "N"           # N=None, E=Even, O=Odd
    stopbits: int = 1
    
    # TCP settings
    host: str = "192.168.1.100"
    tcp_port: int = 502
    
    # Modbus settings
    slave_id: int = 1           # Unit/slave address
    timeout: float = 1.0        # Seconds
    retries: int = 3
    retry_delay: float = 0.1    # Seconds between retries


@dataclass
class RegisterMap:
    """Modbus register addresses (0-indexed for pymodbus)."""
    # Base address for holding registers (40001 in Modbus = address 0)
    RMS_VELOCITY: int = 0       # 40001
    PEAK_ACCEL: int = 1         # 40002
    FREQUENCY: int = 2          # 40003
    BAND_1X: int = 3            # 40004
    BAND_2X: int = 4            # 40005
    BAND_3X: int = 5            # 40006
    BAND_5X: int = 6            # 40007
    BAND_7X: int = 7            # 40008
    TEMPERATURE: int = 8        # 40009
    STATUS: int = 9             # 40010
    
    # Number of registers to read in one batch
    TOTAL_REGISTERS: int = 10


@dataclass
class ScalingFactors:
    """Scaling factors to convert raw values to engineering units."""
    RMS_VELOCITY: float = 0.01      # Raw * 0.01 = mm/s
    PEAK_ACCEL: float = 0.001       # Raw * 0.001 = g
    FREQUENCY: float = 0.1          # Raw * 0.1 = Hz
    BAND_ENERGY: float = 0.01       # Raw * 0.01 = ratio
    TEMPERATURE: float = 0.1        # Raw * 0.1 = °C


class SensorStatus(Enum):
    """Sensor status flags."""
    OK = 0
    OVERLOAD = 1
    TEMP_WARNING = 2
    FAULT = 3


# =============================================================================
# SENSOR DATA
# =============================================================================

@dataclass
class SensorReading:
    """Container for sensor reading data."""
    timestamp: float = 0.0
    rms: float = 0.0                # mm/s
    peak: float = 0.0               # g
    frequency: float = 0.0          # Hz
    band_1x: float = 0.0
    band_2x: float = 0.0
    band_3x: float = 0.0
    band_5x: float = 0.0
    band_7x: float = 0.0
    temperature: float = 0.0        # °C
    status: int = 0
    status_ok: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "rms": round(self.rms, 3),
            "peak": round(self.peak, 4),
            "frequency": round(self.frequency, 1),
            "band_1x": round(self.band_1x, 3),
            "band_2x": round(self.band_2x, 3),
            "band_3x": round(self.band_3x, 3),
            "band_5x": round(self.band_5x, 3),
            "band_7x": round(self.band_7x, 3),
            "temperature": round(self.temperature, 1),
            "status": self.status,
            "status_ok": self.status_ok,
            "error": self.error
        }
    
    def get_features(self) -> list:
        """Get feature vector for ML model."""
        return [
            self.rms,
            self.peak,
            self.band_1x,
            self.band_2x,
            self.band_3x,
            self.band_5x,
            self.band_7x,
            self.temperature
        ]


# =============================================================================
# MODBUS READER CLASS
# =============================================================================

class ModbusReader:
    """
    Modbus reader for QM30VT2-style vibration sensors.
    
    Usage:
        reader = ModbusReader(config)
        reader.connect()
        reading = reader.read_sensor()
        reader.disconnect()
    """
    
    def __init__(self, config: Optional[ModbusConfig] = None):
        """Initialize the Modbus reader."""
        self.config = config or ModbusConfig()
        self.registers = RegisterMap()
        self.scaling = ScalingFactors()
        self.client = None
        self.connected = False
        self._last_good_reading: Optional[SensorReading] = None
        self._consecutive_errors = 0
        self._max_consecutive_errors = 5
        
    def connect(self) -> bool:
        """
        Establish Modbus connection.
        
        Returns:
            bool: True if connection successful
        """
        if not PYMODBUS_AVAILABLE:
            logger.error("pymodbus not available")
            return False
            
        try:
            if self.config.connection_type == "rtu":
                self.client = ModbusSerialClient(
                    port=self.config.port,
                    baudrate=self.config.baudrate,
                    bytesize=self.config.bytesize,
                    parity=self.config.parity,
                    stopbits=self.config.stopbits,
                    timeout=self.config.timeout
                )
            elif self.config.connection_type == "tcp":
                self.client = ModbusTcpClient(
                    host=self.config.host,
                    port=self.config.tcp_port,
                    timeout=self.config.timeout
                )
            else:
                raise ValueError(f"Unknown connection type: {self.config.connection_type}")
            
            self.connected = self.client.connect()
            
            if self.connected:
                logger.info(f"Connected to Modbus sensor ({self.config.connection_type})")
            else:
                logger.error("Failed to connect to Modbus sensor")
                
            return self.connected
            
        except Exception as e:
            logger.exception(f"Connection error: {e}")
            self.connected = False
            return False
    
    def disconnect(self) -> None:
        """Close Modbus connection."""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None
        self.connected = False
        logger.info("Disconnected from Modbus sensor")
    
    def _read_registers_with_retry(self) -> Optional[list]:
        """
        Read registers with retry logic.
        
        Returns:
            List of register values or None on failure
        """
        if not self.client or not self.connected:
            return None
            
        last_error = None
        
        for attempt in range(self.config.retries):
            try:
                # Read all registers in one batch for efficiency
                result = self.client.read_holding_registers(
                    address=0,  # Starting address
                    count=self.registers.TOTAL_REGISTERS,
                    slave=self.config.slave_id
                )
                
                if result.isError():
                    last_error = f"Modbus error: {result}"
                    logger.warning(f"Read attempt {attempt + 1} failed: {last_error}")
                else:
                    return result.registers
                    
            except ModbusException as e:
                last_error = f"Modbus exception: {e}"
                logger.warning(f"Read attempt {attempt + 1} exception: {e}")
            except Exception as e:
                last_error = f"Unexpected error: {e}"
                logger.warning(f"Read attempt {attempt + 1} unexpected error: {e}")
            
            if attempt < self.config.retries - 1:
                time.sleep(self.config.retry_delay)
        
        logger.error(f"All {self.config.retries} read attempts failed: {last_error}")
        return None
    
    def _convert_signed_int16(self, value: int) -> int:
        """Convert unsigned 16-bit to signed 16-bit."""
        if value >= 32768:
            return value - 65536
        return value
    
    def _decode_status(self, status_raw: int) -> tuple:
        """
        Decode status register.
        
        Returns:
            tuple: (status_ok, status_flags)
        """
        sensor_ok = (status_raw & 0x01) == 1
        overload = (status_raw & 0x02) != 0
        temp_warning = (status_raw & 0x04) != 0
        
        return sensor_ok and not overload, status_raw
    
    def read_sensor(self) -> SensorReading:
        """
        Read all sensor values and return a SensorReading object.
        
        If read fails, returns last good reading with error flag,
        or a default reading if no good reading exists.
        
        Returns:
            SensorReading: Current or last-known sensor values
        """
        reading = SensorReading(timestamp=time.time())
        
        # Check connection
        if not self.connected:
            if not self.connect():
                reading.error = "Not connected to sensor"
                reading.status_ok = False
                self._consecutive_errors += 1
                return self._handle_read_error(reading)
        
        # Read registers
        registers = self._read_registers_with_retry()
        
        if registers is None:
            reading.error = "Failed to read registers"
            reading.status_ok = False
            self._consecutive_errors += 1
            return self._handle_read_error(reading)
        
        try:
            # Parse register values with scaling
            reg = self.registers
            scale = self.scaling
            
            # RMS Velocity (mm/s)
            reading.rms = registers[reg.RMS_VELOCITY] * scale.RMS_VELOCITY
            
            # Peak Acceleration (g)
            reading.peak = registers[reg.PEAK_ACCEL] * scale.PEAK_ACCEL
            
            # Dominant Frequency (Hz)
            reading.frequency = registers[reg.FREQUENCY] * scale.FREQUENCY
            
            # Frequency Band Energies (ratios)
            reading.band_1x = registers[reg.BAND_1X] * scale.BAND_ENERGY
            reading.band_2x = registers[reg.BAND_2X] * scale.BAND_ENERGY
            reading.band_3x = registers[reg.BAND_3X] * scale.BAND_ENERGY
            reading.band_5x = registers[reg.BAND_5X] * scale.BAND_ENERGY
            reading.band_7x = registers[reg.BAND_7X] * scale.BAND_ENERGY
            
            # Temperature (°C) - signed value
            temp_raw = self._convert_signed_int16(registers[reg.TEMPERATURE])
            reading.temperature = temp_raw * scale.TEMPERATURE
            
            # Status
            reading.status_ok, reading.status = self._decode_status(registers[reg.STATUS])
            
            # Success - reset error counter and save as last good reading
            self._consecutive_errors = 0
            self._last_good_reading = reading
            
            logger.debug(f"Read OK: RMS={reading.rms:.2f}, Peak={reading.peak:.3f}, "
                        f"Temp={reading.temperature:.1f}°C")
            
            return reading
            
        except Exception as e:
            reading.error = f"Parse error: {e}"
            reading.status_ok = False
            self._consecutive_errors += 1
            logger.exception(f"Error parsing registers: {e}")
            return self._handle_read_error(reading)
    
    def _handle_read_error(self, failed_reading: SensorReading) -> SensorReading:
        """
        Handle read errors by returning last good reading or the failed reading.
        """
        # If we have a recent good reading, return it with error flag
        if self._last_good_reading and self._consecutive_errors < self._max_consecutive_errors:
            result = SensorReading(
                timestamp=time.time(),
                rms=self._last_good_reading.rms,
                peak=self._last_good_reading.peak,
                frequency=self._last_good_reading.frequency,
                band_1x=self._last_good_reading.band_1x,
                band_2x=self._last_good_reading.band_2x,
                band_3x=self._last_good_reading.band_3x,
                band_5x=self._last_good_reading.band_5x,
                band_7x=self._last_good_reading.band_7x,
                temperature=self._last_good_reading.temperature,
                status=self._last_good_reading.status,
                status_ok=False,
                error=f"{failed_reading.error} (using last good value)"
            )
            logger.warning(f"Using last good reading due to error: {failed_reading.error}")
            return result
        
        # Too many consecutive errors or no good reading available
        if self._consecutive_errors >= self._max_consecutive_errors:
            logger.error(f"Too many consecutive errors ({self._consecutive_errors}), "
                        "attempting reconnect")
            self.disconnect()
            self.connect()
        
        return failed_reading
    
    def get_status(self) -> Dict[str, Any]:
        """Get reader status information."""
        return {
            "connected": self.connected,
            "connection_type": self.config.connection_type,
            "port": self.config.port if self.config.connection_type == "rtu" else f"{self.config.host}:{self.config.tcp_port}",
            "slave_id": self.config.slave_id,
            "consecutive_errors": self._consecutive_errors,
            "has_last_good_reading": self._last_good_reading is not None
        }


# =============================================================================
# SIMULATED READER (for testing without hardware)
# =============================================================================

class SimulatedModbusReader:
    """
    Simulated Modbus reader for testing without hardware.
    Generates realistic vibration data patterns.
    """
    
    def __init__(self, config: Optional[ModbusConfig] = None):
        """Initialize simulated reader."""
        self.config = config or ModbusConfig()
        self.connected = False
        self._sample_count = 0
        self._fault_mode = "normal"  # normal, expansion_gap, crack
        
        # Base values for normal operation
        self._base_values = {
            "rms": 1.5,
            "peak": 4.0,
            "frequency": 120.0,
            "band_1x": 0.8,
            "band_2x": 0.3,
            "band_3x": 0.2,
            "band_5x": 0.1,
            "band_7x": 0.05,
            "temperature": 42.0
        }
        
        import numpy as np
        self._np = np
    
    def connect(self) -> bool:
        """Simulate connection."""
        self.connected = True
        logger.info("Simulated sensor connected")
        return True
    
    def disconnect(self) -> None:
        """Simulate disconnection."""
        self.connected = False
        logger.info("Simulated sensor disconnected")
    
    def set_fault_mode(self, mode: str) -> None:
        """Set simulation fault mode: normal, expansion_gap, crack"""
        self._fault_mode = mode
        logger.info(f"Simulation fault mode set to: {mode}")
    
    def read_sensor(self) -> SensorReading:
        """Generate simulated sensor reading."""
        self._sample_count += 1
        np = self._np
        
        # Add some time-varying noise
        t = self._sample_count * 0.1
        noise = np.random.normal(0, 0.1)
        
        reading = SensorReading(timestamp=time.time())
        
        if self._fault_mode == "normal":
            # Normal operation - low, stable values
            reading.rms = self._base_values["rms"] + noise * 0.3
            reading.peak = self._base_values["peak"] + noise
            reading.band_1x = self._base_values["band_1x"] + abs(noise) * 0.2
            reading.band_2x = self._base_values["band_2x"] + abs(noise) * 0.1
            reading.band_3x = self._base_values["band_3x"] + abs(noise) * 0.05
            reading.band_5x = self._base_values["band_5x"] + abs(noise) * 0.03
            reading.band_7x = self._base_values["band_7x"] + abs(noise) * 0.02
            
        elif self._fault_mode == "expansion_gap":
            # Expansion gap - periodic spike pattern, low frequency dominant
            spike = 3.0 if (self._sample_count % 20) < 3 else 0
            reading.rms = self._base_values["rms"] + spike + noise * 0.5
            reading.peak = self._base_values["peak"] + spike * 2 + noise
            reading.band_1x = 2.5 + spike + abs(noise) * 0.3  # High 1X
            reading.band_2x = 0.5 + abs(noise) * 0.1
            reading.band_3x = 0.3 + abs(noise) * 0.05
            reading.band_5x = 0.15 + abs(noise) * 0.03
            reading.band_7x = 0.08 + abs(noise) * 0.02
            
        elif self._fault_mode == "crack":
            # Crack - high frequency content, erratic pattern
            erratic = np.random.exponential(1.0)
            reading.rms = 4.5 + erratic + noise
            reading.peak = 12.0 + erratic * 3 + noise * 2
            reading.band_1x = 2.0 + abs(noise) * 0.4
            reading.band_2x = 1.5 + abs(noise) * 0.3
            reading.band_3x = 1.8 + erratic * 0.5  # High 3X
            reading.band_5x = 1.5 + erratic * 0.4  # High 5X
            reading.band_7x = 1.2 + erratic * 0.3  # High 7X
            
        else:
            # Other fault - mixed pattern
            reading.rms = 3.5 + noise
            reading.peak = 10.0 + noise * 2
            reading.band_1x = 1.5 + abs(noise) * 0.3
            reading.band_2x = 1.2 + abs(noise) * 0.25
            reading.band_3x = 1.0 + abs(noise) * 0.2
            reading.band_5x = 0.8 + abs(noise) * 0.15
            reading.band_7x = 0.5 + abs(noise) * 0.1
        
        # Common values
        reading.frequency = self._base_values["frequency"] + np.random.normal(0, 5)
        reading.temperature = self._base_values["temperature"] + np.sin(t * 0.1) * 2 + noise
        reading.status_ok = True
        reading.status = 1
        
        # Ensure non-negative
        for attr in ["rms", "peak", "band_1x", "band_2x", "band_3x", "band_5x", "band_7x"]:
            setattr(reading, attr, max(0.01, getattr(reading, attr)))
        
        return reading
    
    def get_status(self) -> Dict[str, Any]:
        """Get simulated reader status."""
        return {
            "connected": self.connected,
            "connection_type": "simulated",
            "port": "SIMULATED",
            "slave_id": 1,
            "consecutive_errors": 0,
            "has_last_good_reading": True,
            "fault_mode": self._fault_mode
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_reader(config: Optional[ModbusConfig] = None, 
                  simulated: bool = False) -> ModbusReader:
    """
    Create a Modbus reader instance.
    
    Args:
        config: Modbus configuration
        simulated: If True, create a simulated reader for testing
        
    Returns:
        ModbusReader or SimulatedModbusReader instance
    """
    if simulated:
        return SimulatedModbusReader(config)
    return ModbusReader(config)


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    # Test with simulated reader
    logging.basicConfig(level=logging.DEBUG)
    
    print("Testing ModbusReader (simulated mode)...")
    reader = create_reader(simulated=True)
    reader.connect()
    
    for mode in ["normal", "expansion_gap", "crack"]:
        reader.set_fault_mode(mode)
        print(f"\n=== Mode: {mode} ===")
        for i in range(3):
            reading = reader.read_sensor()
            print(f"  RMS: {reading.rms:.2f}, Peak: {reading.peak:.2f}, "
                  f"Bands: [{reading.band_1x:.2f}, {reading.band_2x:.2f}, "
                  f"{reading.band_3x:.2f}, {reading.band_5x:.2f}, {reading.band_7x:.2f}]")
    
    reader.disconnect()
    print("\nTest complete!")
