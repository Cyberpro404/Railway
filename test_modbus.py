"""
Quick Modbus Connection Test
Tests basic communication with the sensor
"""
import minimalmodbus
import serial.tools.list_ports
import time

print("=" * 60)
print("MODBUS CONNECTION TEST")
print("=" * 60)

# 1. List available COM ports
print("\n1. Available COM Ports:")
print("-" * 60)
ports = list(serial.tools.list_ports.comports())
if not ports:
    print("   [ERROR] No COM ports found!")
else:
    for p in ports:
        print(f"   ✓ {p.device}: {p.description}")

# 2. Test connection parameters
PORT = "COM5"  # Change this if needed
SLAVE_ID = 1
BAUDRATE = 19200
TIMEOUT = 3.0

print(f"\n2. Testing Connection:")
print("-" * 60)
print(f"   Port: {PORT}")
print(f"   Slave ID: {SLAVE_ID}")
print(f"   Baudrate: {BAUDRATE}")
print(f"   Timeout: {TIMEOUT}s")

try:
    # 3. Initialize instrument
    print("\n3. Initializing Modbus instrument...")
    print("-" * 60)
    instrument = minimalmodbus.Instrument(PORT, SLAVE_ID, close_port_after_each_call=False)
    instrument.serial.baudrate = BAUDRATE
    instrument.serial.bytesize = 8
    instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
    instrument.serial.stopbits = 1
    instrument.serial.timeout = TIMEOUT
    instrument.mode = minimalmodbus.MODE_RTU
    instrument.clear_buffers_before_each_transaction = True
    print("   ✓ Instrument initialized")

    # Helper function to read with retries
    def read_with_retry(reg_addr, reg_name, decimals=0, signed=False, scale=1.0):
        """Read register with retry logic"""
        for attempt in range(3):
            try:
                if attempt > 0:
                    time.sleep(0.1 * attempt)  # Increasing delay
                
                # Convert direct address to register address
                registeraddress = reg_addr - 40001 if reg_addr < 50000 else reg_addr - 40001
                raw = instrument.read_register(registeraddress, number_of_decimals=0, functioncode=3, signed=signed)
                value = raw * scale
                print(f"   ✓ {reg_name} ({reg_addr}): {value:.3f} [RAW: {raw}]")
                return value
            except Exception as e:
                if attempt == 2:
                    print(f"   ✗ {reg_name} ({reg_addr}): FAILED - {e}")
                    return None
        return None

    # 4. Test basic register reads
    print("\n4. Testing Register Reads:")
    print("-" * 60)
    
    read_with_retry(40043, "Temperature °C", signed=True, scale=0.01)
    time.sleep(0.05)
    read_with_retry(42403, "Z-axis RMS mm/s", signed=False, scale=0.001)
    time.sleep(0.05)
    read_with_retry(42453, "X-axis RMS mm/s", signed=False, scale=0.001)

    print("\n" + "=" * 60)
    print("TEST COMPLETED - Check results above")
    print("=" * 60)

except Exception as e:
    print(f"\n   ✗ CRITICAL ERROR: {e}")
    print("\nTroubleshooting:")
    print("   1. Check if sensor is powered on")
    print("   2. Verify USB cable is connected")
    print("   3. Check COM port in Device Manager")
    print("   4. Try different Slave ID (1-5)")
    print("   5. Verify baudrate setting on sensor")
    print("=" * 60)
