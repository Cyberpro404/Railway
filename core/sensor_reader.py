"""
Sensor reader module with frequency parameter support and comprehensive error handling.
Handles Modbus communication with vibration sensors.

===============================================================================
MODBUS REGISTER MAP - QM30VT2 STYLE VIBRATION SENSOR
===============================================================================

HARDWARE TROUBLESHOOTING CHECKLIST (verify these if getting "no answer"):
    [ ] Slave ID / Unit ID matches sensor DIP switches (default: 1)
    [ ] Baud rate matches (common: 9600, 19200, 38400)
    [ ] Parity matches (common: None, Even)
    [ ] Stop bits matches (common: 1 or 2)
    [ ] Register type: Holding Registers (function code 3) vs Input Registers (fc 4)
    [ ] Address style: 1-based "direct" addresses (40001 = register 0)
    [ ] RS-485 termination resistor if long cable
    [ ] Correct A/B wiring (some devices swap)

⚠️ CORRECTED REGISTER MAP - QM30VT2 ALIASED ADDRESSES (45201-45217)
    EMERGENCY FIX APPLIED - SINGLE BLOCK READ with CORRECT SCALING
    
    SCALING FORMULA: value / 65535 * 65.535 (for ALL registers except temperature)
    
    PRIMARY DATA BLOCK (45201-45217): Read as SINGLE BLOCK of 17 registers
        45201[0]:  Z RMS Velocity     Scale: / 65535 * 65.535 = mm/s
        45202[1]:  Z RMS Velocity     Scale: / 65535 * 65.535 = mm/s (duplicate)
        45203[2]:  Temperature        Scale: / 100 = °F
        45204[3]:  Temperature        Scale: / 100 = °C
        45205[4]:  X RMS Velocity     Scale: / 65535 * 65.535 = in/s
        45206[5]:  X RMS Velocity     Scale: / 65535 * 65.535 = mm/s
        45207[6]:  Z Peak Accel       Scale: / 65535 * 65.535 = G
        45208[7]:  X Peak Accel       Scale: / 65535 * 65.535 = G
        45211[10]: Z RMS Accel        Scale: / 65535 * 65.535 = G
        45212[11]: X RMS Accel        Scale: / 65535 * 65.535 = G
        45213[12]: Z Kurtosis         Scale: / 65535 * 65.535
        45214[13]: X Kurtosis         Scale: / 65535 * 65.535
        45215[14]: Z Crest Factor     Scale: / 65535 * 65.535
        45216[15]: X Crest Factor     Scale: / 65535 * 65.535
    
    SYSTEM CONFIG REGISTERS:
        46101:     Baud Rate          (0=9600, 1=19200, 2=38400)
        46102:     Parity             (0=None, 1=Odd, 2=Even)
        46103:     Slave ID           (1-247)
        42601:     Rotational Speed   RPM
        42602:     Rotational Speed   Hz

LEGACY REGISTERS (⚠️ DISABLED - Not configured):
    43501-43700:   Spectral bands (DISABLED - require FFT pre-configuration)
    40004-40013:   Simple bands (DISABLED - deprecated)
    
⚠️ DO NOT POLL 43501+ registers unless FFT bands are pre-configured in sensor firmware!

NOTE: Using aliased addresses (45xxx) is more reliable than legacy addresses.
===============================================================================
"""

from __future__ import annotations

import struct
import threading
import time
import logging
from datetime import datetime, timezone
from typing import Literal, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import minimalmodbus

from models import BandMeasurement, ConnectionConfig, SensorReading
from utils.logger import setup_logger
from utils.errors import SensorError, ConnectionError
from utils.validators import validate_frequency
from config.settings import Config

logger = setup_logger(__name__)

# =============================================================================
# MODBUS CONFIGURATION CONSTANTS
# =============================================================================

# Track whether extended bands are supported (auto-detected on first failure)
_extended_bands_supported = True
_extended_bands_check_done = False

# Hex frame logging flag (can be enabled for diagnostics)
_hex_logging_enabled = False


def enable_hex_logging(enabled: bool = True):
    """
    Enable/disable hex frame logging for diagnostics.
    
    When enabled, logs raw Modbus frames for troubleshooting.
    
    Args:
        enabled: True to enable, False to disable
    """
    global _hex_logging_enabled
    _hex_logging_enabled = enabled
    if enabled:
        logger.info("Hex frame logging enabled")
    else:
        logger.info("Hex frame logging disabled")


def _log_modbus_frame(direction: str, frame: bytes):
    """
    Log raw Modbus frame in hex format.
    
    Args:
        direction: "TX" for transmit, "RX" for receive
        frame: Raw frame bytes
    """
    if _hex_logging_enabled:
        hex_str = ' '.join(f'{b:02X}' for b in frame)
        logger.debug(f"[{direction}] {hex_str}")


class SensorStatus(Enum):
    """Sensor status enumeration."""
    OK = "ok"
    ERROR = "error"
    NOT_INITIALIZED = "not_initialized"


class SensorReaderError(SensorError):
    """Sensor reader specific error."""
    pass


class ConnectionHealth:
    """
    Connection health tracking for diagnostics.
    
    Tracks success rate, consecutive failures, and communication statistics.
    """
    
    def __init__(self):
        """Initialize health tracker."""
        self.consecutive_failures = 0
        self.total_reads = 0
        self.failed_reads = 0
        self.last_success_time: Optional[float] = None
        self.last_error: Optional[str] = None
        self.last_error_time: Optional[float] = None
    
    def record_success(self):
        """Record successful read."""
        self.consecutive_failures = 0
        self.total_reads += 1
        self.last_success_time = time.time()
    
    def record_failure(self, error_msg: str = ""):
        """Record failed read."""
        self.consecutive_failures += 1
        self.total_reads += 1
        self.failed_reads += 1
        self.last_error = error_msg
        self.last_error_time = time.time()
    
    @property
    def success_rate(self) -> float:
        """Get success rate (0.0 to 1.0)."""
        if self.total_reads == 0:
            return 0.0
        return (self.total_reads - self.failed_reads) / self.total_reads
    
    def get_stats(self) -> Dict[str, any]:
        """Get health statistics."""
        return {
            "consecutive_failures": self.consecutive_failures,
            "total_reads": self.total_reads,
            "failed_reads": self.failed_reads,
            "success_rate": self.success_rate,
            "last_success_time": self.last_success_time,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time,
            "uptime_hours": (time.time() - self.last_success_time) / 3600 if self.last_success_time else 0
        }


_DIRECT_HOLDING_BASE = 40001

# Default frequency (Hz) - can be overridden
DEFAULT_FREQUENCY_HZ = 3200.0


def _direct_to_registeraddress(direct_address: int) -> int:
    """Convert direct register address to Modbus register address."""
    if direct_address < _DIRECT_HOLDING_BASE:
        raise ValueError(f"Direct register address must be >= {_DIRECT_HOLDING_BASE}: {direct_address}")
    return direct_address - _DIRECT_HOLDING_BASE


@dataclass
class _BandBlockLayout:
    """Layout information for frequency band data blocks."""
    start_direct: int
    bands: int = 20
    floats_per_band: int = 5
    
    @property
    def registers_per_band(self) -> int:
        return self.floats_per_band * 2
    
    @property
    def total_registers(self) -> int:
        return self.bands * self.registers_per_band


# DISABLED - Spectral bands not configured (43501-43700 require FFT pre-configuration)
# _DEFAULT_Z_BANDS = _BandBlockLayout(start_direct=43501)
# _DEFAULT_X_BANDS = _BandBlockLayout(start_direct=43701)


class SensorReader:
    """Handles sensor communication via Modbus RTU."""
    
    def __init__(self, config: ConnectionConfig, frequency_hz: float = DEFAULT_FREQUENCY_HZ):
        """
        Initialize sensor reader.
        
        Args:
            config: Connection configuration
            frequency_hz: Sampling frequency in Hz
            
        Raises:
            SensorReaderError: If initialization fails
        """
        try:
            validate_frequency(frequency_hz)
            self._frequency_hz = frequency_hz
            self._config = config
            self._instrument = self._init_instrument(config)
            self._health = ConnectionHealth()
            logger.info(f"Sensor reader initialized with frequency {frequency_hz} Hz")
        except Exception as e:
            logger.error(f"Failed to initialize sensor reader: {e}")
            raise SensorReaderError(f"Initialization failed: {e}") from e
    
    @staticmethod
    def _init_instrument(config: ConnectionConfig) -> minimalmodbus.Instrument:
        """
        Initialize Modbus instrument.
        
        Args:
            config: Connection configuration
            
        Returns:
            Configured Modbus instrument
            
        Raises:
            SensorReaderError: If instrument initialization fails
        """
        try:
            instrument = minimalmodbus.Instrument(
                config.port,
                config.slave_id,
                close_port_after_each_call=False
            )
            instrument.mode = minimalmodbus.MODE_RTU
            instrument.serial.baudrate = config.baudrate  # Default: 19200
            instrument.serial.bytesize = config.bytesize
            instrument.serial.stopbits = config.stopbits
            # CRITICAL MODBUS SETTINGS - QM30VT2 optimized
            # INCREASED TIMEOUT to fix checksum errors - sensor needs more time
            instrument.serial.timeout = 2.5  # Increased from 1.5 to 2.5 for reliability
            instrument.clear_buffers_before_each_transaction = True
            
            # Configure parity
            if config.parity == "N":
                instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
            elif config.parity == "E":
                instrument.serial.parity = minimalmodbus.serial.PARITY_EVEN
            elif config.parity == "O":
                instrument.serial.parity = minimalmodbus.serial.PARITY_ODD
            else:
                raise ValueError(f"Unsupported parity: {config.parity}")
            
            logger.info(f"Modbus instrument initialized on {config.port} (slave {config.slave_id})")
            return instrument
        except Exception as e:
            logger.error(f"Failed to initialize Modbus instrument on {config.port}: {e}")
            # Make sure to clean up serial port connections on failure
            try:
                if 'instrument' in locals() and hasattr(instrument, 'serial') and instrument.serial.is_open:
                    instrument.serial.close()
            except:
                pass
            raise SensorReaderError(f"Modbus init failed on {config.port}: {e}") from e
    
    @property
    def config(self) -> ConnectionConfig:
        """Get current configuration."""
        return self._config
    
    @property
    def frequency_hz(self) -> float:
        """Get current sampling frequency in Hz."""
        return self._frequency_hz
    
    @property
    def health(self) -> ConnectionHealth:
        """Get connection health tracker."""
        return self._health
    
    def get_health_stats(self) -> Dict[str, any]:
        """Get connection health statistics."""
        return self._health.get_stats()
    
    def set_frequency(self, frequency_hz: float) -> None:
        """
        Set sampling frequency.
        
        Args:
            frequency_hz: New frequency in Hz
            
        Raises:
            SensorReaderError: If frequency is invalid
        """
        try:
            validate_frequency(frequency_hz)
            self._frequency_hz = frequency_hz
            logger.info(f"Frequency set to {frequency_hz} Hz")
        except Exception as e:
            logger.error(f"Failed to set frequency: {e}")
            raise SensorReaderError(f"Invalid frequency: {e}") from e
    
    def _read_register(
        self,
        direct_address: int,
        decimals: int,
        signed: bool,
        retries: int = Config.SENSOR_READ_RETRY_COUNT
    ) -> float:
        """
        Read a single register with retry logic.
        
        Args:
            direct_address: Direct register address
            decimals: Number of decimal places
            signed: Whether value is signed
            retries: Number of retries on failure
            
        Returns:
            Register value as float
            
        Raises:
            SensorReaderError: If read fails after retries
        """
        registeraddress = _direct_to_registeraddress(direct_address)
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                if attempt > 0:
                    time.sleep(Config.SENSOR_RETRY_DELAY_MS / 1000.0 * attempt)
                
                return self._instrument.read_register(
                    registeraddress=registeraddress,
                    number_of_decimals=decimals,
                    functioncode=3,
                    signed=signed,
                )
            except Exception as e:
                last_error = e
                logger.debug(f"Register read attempt {attempt + 1} failed: {e}")
                
                if attempt == retries:
                    raise SensorReaderError(
                        f"Failed to read register {direct_address} after {retries + 1} attempts: {e}"
                    ) from e
    
    def read_scalar_values(self) -> dict:
        """
        ⚠️ EMERGENCY FIX APPLIED - CORRECT QM30VT2 REGISTER MAPPING
        
        Read scalar sensor values using SINGLE BLOCK READ: 45201-45217 (17 registers)
        
        CORRECTED SCALING FORMULA: value / 65535 * 65.535 (for ALL registers)
        
        Register Map:
        45201[0]: Z RMS Velocity (mm/s)
        45202[1]: Z RMS Velocity duplicate (mm/s) 
        45203[2]: Temperature (°F)
        45204[3]: Temperature (°C)
        45205[4]: X RMS Velocity (in/s)
        45206[5]: X RMS Velocity (mm/s)
        45207[6]: Z Peak Accel (G)
        45208[7]: X Peak Accel (G)
        45211[10]: Z RMS Accel (G)
        45212[11]: X RMS Accel (G)
        45213[12]: Z Kurtosis
        45214[13]: X Kurtosis
        45215[14]: Z Crest Factor
        45216[15]: X Crest Factor
        
        Returns:
            Dictionary of scalar measurements
        Raises:
            SensorReaderError: If read fails
        """
        try:
            # ✅ EMERGENCY FIX: SINGLE BLOCK READ - 17 registers starting at 45201
            # Convert aliased address 45201 to 0-based: 45201 - 40001 = 5200
            register_address = 45201 - _DIRECT_HOLDING_BASE  # 5200
            raw_data = self._instrument.read_registers(
                registeraddress=register_address,
                number_of_registers=17,  # Read full block (45201-45217)
                functioncode=3
            )
            
            # ✅ CORRECTED SCALING: value / 65535 * 65.535 for ALL registers (except temperature)
            scalars = {
                # Core vibration metrics
                "z_rms_mm_s": float(raw_data[0]) / 65535.0 * 65.535,      # 45201[0]
                "z_rms_mm_s_2": float(raw_data[1]) / 65535.0 * 65.535,    # 45202[1]
                "temp_f": float(raw_data[2]) / 100.0,                     # 45203[2] - divide by 100
                "temp_c": float(raw_data[3]) / 100.0,                     # 45204[3] - divide by 100
                "x_rms_in_s": float(raw_data[4]) / 65535.0 * 65.535,      # 45205[4]
                "x_rms_mm_s": float(raw_data[5]) / 65535.0 * 65.535,      # 45206[5]
                
                # Peak acceleration
                "z_peak_g": float(raw_data[6]) / 65535.0 * 65.535,        # 45207[6]
                "x_peak_g": float(raw_data[7]) / 65535.0 * 65.535,        # 45208[7]
                
                # RMS acceleration (indices 10, 11 in 17-register block)
                "z_rms_g": float(raw_data[10]) / 65535.0 * 65.535,        # 45211[10]
                "x_rms_g": float(raw_data[11]) / 65535.0 * 65.535,        # 45212[11]
                
                # Statistical features
                "z_kurtosis": float(raw_data[12]) / 65535.0 * 65.535,     # 45213[12]
                "x_kurtosis": float(raw_data[13]) / 65535.0 * 65.535,     # 45214[13]
                "z_crest": float(raw_data[14]) / 65535.0 * 65.535,        # 45215[14]
                "x_crest": float(raw_data[15]) / 65535.0 * 65.535,        # 45216[15]
                
                # Frequency (from configuration, not sensor)
                "frequency_hz": self._frequency_hz,
            }

            logger.debug(f"✅ SAFE READ SUCCESS: Z_RMS={scalars['z_rms_mm_s']:.4f} mm/s, "
                        f"Temp={scalars['temp_c']:.1f}°C, X_RMS={scalars['x_rms_mm_s']:.4f} mm/s")

            return scalars
            
        except Exception as e:
            logger.error(f"❌ REGISTER READ FAILED: {e}")
            logger.error(f"   Check: Baudrate={self._instrument.serial.baudrate}, "
                        f"SlaveID={self._instrument.address}, Port={self._instrument.serial.port}")
            raise
    
    @staticmethod
    def _regs_to_float_be(word_hi: int, word_lo: int, word_swap: bool) -> float:
        """Convert register words to float (big-endian)."""
        if word_swap:
            word_hi, word_lo = word_lo, word_hi
        payload = struct.pack(">HH", word_hi & 0xFFFF, word_lo & 0xFFFF)
        return float(struct.unpack(">f", payload)[0])
    
    def _read_register_block(self, start_direct: int, count: int) -> list[int]:
        """Read a block of registers, chunking if necessary for Modbus limit."""
        MAX_REGISTERS_PER_READ = 125  # Modbus protocol limit
        start_addr = _direct_to_registeraddress(start_direct)
        
        try:
            # If count is within limit, read directly
            if count <= MAX_REGISTERS_PER_READ:
                return self._instrument.read_registers(
                    registeraddress=start_addr,
                    number_of_registers=count,
                    functioncode=3
                )
            
            # Otherwise, read in chunks
            result: list[int] = []
            remaining = count
            current_addr = start_addr
            
            while remaining > 0:
                chunk_size = min(remaining, MAX_REGISTERS_PER_READ)
                chunk = self._instrument.read_registers(
                    registeraddress=current_addr,
                    number_of_registers=chunk_size,
                    functioncode=3
                )
                result.extend(chunk)
                current_addr += chunk_size
                remaining -= chunk_size
            
            return result
        except Exception as e:
            logger.error(f"Failed to read register block {start_direct}: {e}")
            raise SensorReaderError(f"Register block read failed: {e}") from e

    def _parse_band_block(
        self,
        regs: list[int],
        axis: Literal["z", "x"],
        layout: _BandBlockLayout,
        word_swap: bool
    ) -> list[BandMeasurement]:
        """Parse frequency band data block."""
        expected = layout.total_registers
        if len(regs) != expected:
            raise SensorReaderError(
                f"Unexpected band block size for {axis}: got {len(regs)}, expected {expected}"
            )
        
        out: list[BandMeasurement] = []
        regs_per_band = layout.registers_per_band
        
        for i in range(layout.bands):
            base = i * regs_per_band
            floats: list[float] = []
            for j in range(layout.floats_per_band):
                k = base + j * 2
                floats.append(self._regs_to_float_be(regs[k], regs[k + 1], word_swap=word_swap))
            
            total_rms, peak_rms, peak_freq_hz, peak_rpm, bin_index_f = floats
            out.append({
                "band_number": i + 1,
                "axis": axis,
                "multiple": i + 1,
                "total_rms": float(total_rms),
                "peak_rms": float(peak_rms),
                "peak_freq_hz": float(peak_freq_hz),
                "peak_rpm": float(peak_rpm),
                "bin_index": int(round(bin_index_f)),
            })
        
        return out
    
    def read_band_values(self) -> tuple[Optional[list[BandMeasurement]], Optional[list[BandMeasurement]]]:
        """
        Read frequency band values for both axes.
        
        DISABLED: Spectral band registers (43501+) require FFT pre-configuration
        in Banner's software. Since these are not configured, always return None
        to avoid communication errors.
        
        To enable: Configure frequency bands in Banner software, then uncomment
        the code below and update _extended_bands_supported = True.
        
        Returns:
            Tuple of (None, None) - bands disabled
        """
        # Spectral bands are not configured - skip entirely
        return None, None
    
    def read_simple_bands(self) -> Optional[Dict[str, float]]:
        """
        Read simple band values from basic registers (40004-40013).
        Fallback when extended band registers (43501+) are not available.
        
        Returns:
            Dict with band_1x through band_7x, or None if read fails.
        """
        try:
            # Simple band registers: 40004-40013 (5 bands x 2 regs each = 10 registers)
            # Using 0-based addressing: start at register 3 (40004-40001=3)
            regs = self._instrument.read_registers(
                registeraddress=3,  # 40004 in 0-based
                number_of_registers=10,
                functioncode=3
            )
            # Parse 32-bit floats (Big-Endian, no word swap)
            def parse_float(hi: int, lo: int) -> float:
                payload = struct.pack(">HH", hi & 0xFFFF, lo & 0xFFFF)
                return struct.unpack(">f", payload)[0]
            # Return all bands, even if some are not supported by all sensors
            return {
                "band_1x": parse_float(regs[0], regs[1]),
                "band_2x": parse_float(regs[2], regs[3]),
                "band_3x": parse_float(regs[4], regs[5]),
                "band_5x": parse_float(regs[6], regs[7]),
                "band_7x": parse_float(regs[8], regs[9]),
            }
        except Exception as e:
            # Don't log every failure - simple bands may not be supported either
            logger.debug(f"Simple bands not available: {e}")
            return None
    
    def read_sensor_once(self) -> tuple[SensorStatus, Optional[SensorReading]]:
        """
        Perform a single complete sensor read.
        
        Returns:
            Tuple of (status, reading)
            
        The reading dict includes an 'ok' field:
            ok=True:  All critical values read successfully
            ok=False: Critical read failed, do NOT use for ML
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        try:
            # Test connection with temperature register
            try:
                self._read_register(40043, decimals=2, signed=True, retries=1)
            except SensorReaderError as e:
                logger.warning(f"Connection test failed, attempting reconnect: {e}")
                self._health.record_failure(f"Connection test failed: {e}")
                try:
                    self._instrument = self._init_instrument(self._config)
                except Exception:
                    self._health.record_failure("Reconnection failed")
                    return SensorStatus.ERROR, {
                        "ok": False,
                        "error": "Connection failed - no response from sensor",
                        "timestamp": timestamp
                    }
            
            # Read scalar values (RMS, peak, temperature)
            # Read scalar values (RMS, peak, temperature)
            # Retry up to 3 times for checksum errors
            max_attempts = 3
            scalars = None
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    scalars = self.read_scalar_values()
                    # Small delay to let sensor settle - helps with checksum reliability
                    time.sleep(0.05)  # 50ms delay
                    break  # Success, exit retry loop
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    is_checksum_error = any(keyword in error_msg for keyword in 
                                           ['checksum', 'crc', 'check failed'])
                    
                    if is_checksum_error and attempt < max_attempts - 1:
                        logger.warning(f"Checksum error on attempt {attempt + 1}/{max_attempts}, retrying...")
                        time.sleep(0.1)  # Wait 100ms before retry
                        continue
                    else:
                        # Final attempt or non-checksum error
                        break
            
            if scalars is None:
                self._health.record_failure(f"Scalar read failed: {last_error}")
                return SensorStatus.ERROR, {
                    "ok": False,
                    "error": f"Failed to read scalar values: {last_error}",
                    "timestamp": timestamp
                }
            
            # Try extended band values first (43501+) - will auto-skip if not supported
            bands_z, bands_x = self.read_band_values()
            
            # If extended bands not available, try simple bands (only log once)
            simple_bands = None
            if bands_z is None:
                simple_bands = self.read_simple_bands()
            
            # Extract ML features from bands
            band_features = self._extract_band_features(bands_z, simple_bands)
            
            # Build reading with ok status
            reading = {
                "ok": True,
                "timestamp": timestamp,
                **scalars,
                "bands_z": bands_z if bands_z else [],
                "bands_x": bands_x if bands_x else [],
                **band_features,  # band_1x, band_2x, etc.
            }
            
            # If no band data at all, mark as partial (ok but with warning)
            if bands_z is None and simple_bands is None:
                reading["band_warning"] = "No band data available - check sensor registers"
            
            # Record successful read
            self._health.record_success()
            
            return SensorStatus.OK, reading
            
        except Exception as e:
            logger.error(f"Sensor read failed: {e}")
            self._health.record_failure(str(e))
            return SensorStatus.ERROR, {
                "ok": False,
                "error": str(e),
                "timestamp": timestamp
            }
    
    def _extract_band_features(self, bands_z: Optional[list], simple_bands: Optional[dict]) -> dict:
        """
        Extract ML feature values from band data.
        
        Args:
            bands_z: Extended Z-axis bands (list of BandMeasurement) or None
            simple_bands: Simple band dict {band_1x: ..., band_2x: ...} or None
            
        Returns:
            Dict with band_1x, band_2x, band_3x, band_5x, band_7x
        """
        # Default to zeros (but caller should check ok status before using for ML)
        result = {
            "band_1x": 0.0,
            "band_2x": 0.0,
            "band_3x": 0.0,
            "band_5x": 0.0,
            "band_7x": 0.0,
        }
        
        if simple_bands:
            # Use simple band values directly
            result.update(simple_bands)
        elif bands_z and len(bands_z) >= 7:
            # Extract from extended bands (use total_rms for each band)
            # Band indices: 0=1x, 1=2x, 2=3x, 4=5x, 6=7x
            result["band_1x"] = bands_z[0].get("total_rms", 0.0) if isinstance(bands_z[0], dict) else getattr(bands_z[0], 'total_rms', 0.0)
            result["band_2x"] = bands_z[1].get("total_rms", 0.0) if isinstance(bands_z[1], dict) else getattr(bands_z[1], 'total_rms', 0.0)
            result["band_3x"] = bands_z[2].get("total_rms", 0.0) if isinstance(bands_z[2], dict) else getattr(bands_z[2], 'total_rms', 0.0)
            result["band_5x"] = bands_z[4].get("total_rms", 0.0) if isinstance(bands_z[4], dict) else getattr(bands_z[4], 'total_rms', 0.0)
            result["band_7x"] = bands_z[6].get("total_rms", 0.0) if isinstance(bands_z[6], dict) else getattr(bands_z[6], 'total_rms', 0.0)
        
        return result


# Global reader instance
_reader: Optional[SensorReader] = None
_lock = threading.Lock()
_last_error: Optional[str] = None
_last_error_time: Optional[str] = None


def _set_last_error(error_message: str) -> None:
    """Set the last error message."""
    global _last_error, _last_error_time
    _last_error = error_message
    _last_error_time = datetime.now(timezone.utc).isoformat()


def get_last_error() -> tuple[Optional[str], Optional[str]]:
    """Get the last error message and timestamp."""
    return _last_error, _last_error_time


def init_reader(config: ConnectionConfig, frequency_hz: float = DEFAULT_FREQUENCY_HZ) -> None:
    """
    Initialize the global sensor reader.
    
    Args:
        config: Connection configuration
        frequency_hz: Sampling frequency in Hz
        
    Raises:
        SensorReaderError: If initialization fails
    """
    global _reader
    with _lock:
        if _reader is not None:
            try:
                _reader._instrument.serial.close()
            except Exception:
                pass
        
        try:
            _reader = SensorReader(config, frequency_hz)
        except Exception as e:
            logger.error(f"Failed to initialize reader: {e}")
            raise


def get_reader() -> SensorReader:
    """
    Get the global sensor reader instance.
    
    Raises:
        SensorReaderError: If reader not initialized
    """
    if _reader is None:
        raise SensorReaderError("Sensor reader not initialized")
    return _reader


def read_scalar_values() -> dict:
    """Read scalar sensor values."""
    with _lock:
        return get_reader().read_scalar_values()


def read_band_values() -> tuple[list[BandMeasurement], list[BandMeasurement]]:
    """Read frequency band values."""
    with _lock:
        return get_reader().read_band_values()


def read_sensor_once() -> tuple[SensorStatus, Optional[SensorReading]]:
    """Perform a single sensor read."""
    with _lock:
        try:
            return get_reader().read_sensor_once()
        except Exception as e:
            logger.error(f"Sensor read error: {e}")
            _set_last_error(str(e))
            return SensorStatus.ERROR, None


def set_frequency(frequency_hz: float) -> None:
    """
    Set the sampling frequency for the sensor.
    
    Args:
        frequency_hz: New frequency in Hz
        
    Raises:
        SensorReaderError: If frequency is invalid
    """
    with _lock:
        try:
            get_reader().set_frequency(frequency_hz)
        except Exception as e:
            logger.error(f"Failed to set frequency: {e}")
            raise


def get_frequency() -> float:
    """Get the current sampling frequency."""
    with _lock:
        return get_reader().frequency_hz


def get_health_stats() -> Dict[str, any]:
    """Get connection health statistics."""
    with _lock:
        try:
            return get_reader().get_health_stats()
        except SensorReaderError:
            return {
                "consecutive_failures": 0,
                "total_reads": 0,
                "failed_reads": 0,
                "success_rate": 0.0,
                "last_success_time": None,
                "last_error": "Sensor not initialized",
                "last_error_time": None,
                "uptime_hours": 0
            }

