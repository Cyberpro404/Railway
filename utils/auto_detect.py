"""
Auto-detection module for COM ports and Modbus slave IDs.
Automatically scans and finds connected vibration sensors.
"""

import logging
import time
from typing import List, Optional, Tuple
import minimalmodbus

try:
    from serial.tools import list_ports
except ImportError:
    list_ports = None

logger = logging.getLogger(__name__)

# Common slave IDs to try
DEFAULT_SLAVE_IDS = [1, 2, 3, 4, 5, 10, 247]

# Common baud rates for QM30VT2 sensors
DEFAULT_BAUD_RATES = [19200, 9600, 38400, 57600, 115200]

# Test register address (temperature register at 40043)
TEST_REGISTER = 42  # 40043 - 40001 = 42


def scan_com_ports() -> List[dict]:
    """
    Scan all available COM ports on the system.
    
    Returns:
        List of port information dictionaries
    """
    if list_ports is None:
        logger.error("pyserial not available for port scanning")
        return []
    
    try:
        ports = list_ports.comports()
        result = []
        for port in ports:
            result.append({
                "port": port.device,
                "description": port.description or "Unknown",
                "hwid": port.hwid or "",
                "manufacturer": getattr(port, 'manufacturer', None) or ""
            })
        logger.info(f"Found {len(result)} COM ports")
        return result
    except Exception as e:
        logger.error(f"Error scanning COM ports: {e}")
        return []


def test_connection(port: str, slave_id: int, baudrate: int = 19200, 
                   parity: str = 'N', timeout: float = 0.5) -> bool:
    """
    Test if a sensor responds on the given port and slave ID.
    
    Args:
        port: COM port name
        slave_id: Modbus slave ID to test
        baudrate: Baud rate
        parity: Parity setting
        timeout: Response timeout in seconds
        
    Returns:
        True if sensor responds, False otherwise
    """
    try:
        instrument = minimalmodbus.Instrument(port, slave_id, close_port_after_each_call=True)
        instrument.mode = minimalmodbus.MODE_RTU
        instrument.serial.baudrate = baudrate
        instrument.serial.parity = parity
        instrument.serial.bytesize = 8
        instrument.serial.stopbits = 1
        instrument.serial.timeout = timeout
        
        # Try to read temperature register (40043)
        value = instrument.read_register(TEST_REGISTER, functioncode=3)
        
        # If we get here, we successfully communicated
        logger.info(f"✓ Found sensor on {port} (Slave ID {slave_id}, Baud {baudrate})")
        return True
        
    except Exception as e:
        # Silent failure for scanning
        return False


def auto_detect_sensor(ports: Optional[List[str]] = None, 
                       slave_ids: Optional[List[int]] = None,
                       baud_rates: Optional[List[int]] = None,
                       max_attempts: int = 3) -> Optional[dict]:
    """
    Automatically detect a connected vibration sensor.
    
    Args:
        ports: List of COM ports to scan (None = scan all)
        slave_ids: List of slave IDs to try (None = use defaults)
        baud_rates: List of baud rates to try (None = use defaults)
        max_attempts: Maximum connection attempts per configuration
        
    Returns:
        Dictionary with connection details if found, None otherwise
    """
    logger.info("🔍 Starting auto-detection of vibration sensor...")
    
    # Get ports to scan
    if ports is None:
        available_ports = scan_com_ports()
        ports = [p["port"] for p in available_ports]
    
    if not ports:
        logger.warning("No COM ports found")
        return None
    
    # Use defaults if not specified
    if slave_ids is None:
        slave_ids = DEFAULT_SLAVE_IDS
    
    if baud_rates is None:
        baud_rates = DEFAULT_BAUD_RATES
    
    logger.info(f"Scanning {len(ports)} port(s), {len(slave_ids)} slave ID(s), {len(baud_rates)} baud rate(s)")
    
    # Try each combination
    for port in ports:
        logger.info(f"Testing port: {port}")
        
        for baudrate in baud_rates:
            for slave_id in slave_ids:
                try:
                    if test_connection(port, slave_id, baudrate):
                        result = {
                            "port": port,
                            "slave_id": slave_id,
                            "baudrate": baudrate,
                            "parity": "N",
                            "detected": True
                        }
                        logger.info(f"✅ Sensor detected: {result}")
                        return result
                except Exception as e:
                    continue
    
    logger.warning("❌ No sensor detected")
    return None


def quick_detect_sensor() -> Optional[dict]:
    """
    Quick detection using most common settings.
    
    Returns:
        Connection details if found, None otherwise
    """
    # Try only most common settings for speed
    return auto_detect_sensor(
        slave_ids=[1, 2],
        baud_rates=[19200, 9600],
        max_attempts=1
    )


def detailed_detect_sensor() -> Optional[dict]:
    """
    Thorough detection scanning all possible configurations.
    
    Returns:
        Connection details if found, None otherwise
    """
    return auto_detect_sensor(
        slave_ids=DEFAULT_SLAVE_IDS,
        baud_rates=DEFAULT_BAUD_RATES,
        max_attempts=2
    )
