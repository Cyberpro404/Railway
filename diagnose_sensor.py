"""
Sensor Diagnostic Tool
Comprehensive diagnostics for sensor connectivity issues
"""
import sys
import time
import serial
import serial.tools.list_ports
import minimalmodbus

def print_section(title: str):
    """Print formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def check_com_ports():
    """Check available COM ports"""
    print_section("1. COM PORT DETECTION")
    
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("  ❌ No COM ports found!")
        print("\n  Troubleshooting:")
        print("    - Check USB cable connection")
        print("    - Check Device Manager for COM port")
        print("    - Try a different USB port")
        return None
    
    print(f"  ✓ Found {len(ports)} COM port(s):\n")
    for i, port in enumerate(ports, 1):
        print(f"    [{i}] {port.device}")
        print(f"        Description: {port.description}")
        print(f"        Hardware ID: {port.hwid}")
        if "USB" in port.hwid.upper():
            print(f"        ⭐ USB Device Detected")
        print()
    
    return [p.device for p in ports]

def test_serial_connection(port: str, baudrate: int = 19200):
    """Test basic serial connection"""
    print_section(f"2. SERIAL CONNECTION TEST - {port}")
    
    print(f"  Testing: {port} @ {baudrate} baud")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=3
        )
        
        print(f"  ✓ Port opened successfully")
        print(f"    - Is Open: {ser.is_open}")
        print(f"    - Port: {ser.port}")
        print(f"    - Baudrate: {ser.baudrate}")
        print(f"    - Timeout: {ser.timeout}s")
        
        # Check if we can write/read
        time.sleep(0.5)
        
        # Try to read any data
        ser.reset_input_buffer()
        data = ser.read(10)
        
        if data:
            print(f"  ✓ Data available: {len(data)} bytes")
            print(f"    Hex: {data.hex()}")
        else:
            print(f"  ⚠️  No data received (this may be normal)")
        
        ser.close()
        return True
        
    except serial.SerialException as e:
        print(f"  ❌ Failed to open port: {e}")
        print("\n  Troubleshooting:")
        print("    - Port may be in use by another application")
        print("    - Check if the sensor is powered on")
        print("    - Try closing other programs using the port")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False

def test_modbus_connection(port: str, slave_id: int = 1, baudrate: int = 19200):
    """Test Modbus RTU connection"""
    print_section(f"3. MODBUS RTU TEST - {port}")
    
    print(f"  Configuration:")
    print(f"    Port: {port}")
    print(f"    Slave ID: {slave_id}")
    print(f"    Baudrate: {baudrate}")
    print(f"    Parity: None")
    print(f"    Stop Bits: 1")
    print(f"    Timeout: 3s")
    
    try:
        # Initialize Modbus instrument
        instrument = minimalmodbus.Instrument(port, slave_id, close_port_after_each_call=False)
        instrument.serial.baudrate = baudrate
        instrument.serial.bytesize = 8
        instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
        instrument.serial.stopbits = 1
        instrument.serial.timeout = 3.0
        instrument.mode = minimalmodbus.MODE_RTU
        instrument.clear_buffers_before_each_transaction = True
        
        print("\n  ✓ Modbus instrument initialized")
        
        # Test reading various registers
        test_registers = [
            (45201, "Z RMS Velocity (45201)"),
            (45203, "Temperature F (45203)"),
            (45204, "Temperature C (45204)"),
            (42403, "Z RMS Legacy (42403)"),
        ]
        
        print("\n  Testing register reads:")
        success_count = 0
        
        for reg_addr, description in test_registers:
            try:
                # Convert direct address to register address
                registeraddress = reg_addr - 40001
                raw = instrument.read_register(registeraddress, number_of_decimals=0, functioncode=3, signed=False)
                print(f"    ✓ {description}: {raw} (0x{raw:04X})")
                success_count += 1
                time.sleep(0.05)  # Small delay between reads
            except Exception as e:
                print(f"    ✗ {description}: Failed - {e}")
        
        print(f"\n  📊 Result: {success_count}/{len(test_registers)} registers read successfully")
        
        if success_count == 0:
            print("\n  ⚠️  No registers could be read!")
            print("  Possible issues:")
            print("    - Incorrect Slave ID (try 1-5)")
            print("    - Wrong baudrate (try 9600, 19200, 38400)")
            print("    - Sensor not powered on")
            print("    - Wrong register addresses")
            print("    - Cable connection issues")
            return False
        elif success_count < len(test_registers):
            print("\n  ⚠️  Partial success - some registers failed")
            print("  This may be normal if sensor doesn't support all registers")
            return True
        else:
            print("\n  ✅ All registers read successfully!")
            return True
        
    except Exception as e:
        print(f"\n  ❌ Modbus connection failed: {e}")
        print("\n  Troubleshooting:")
        print("    - Verify sensor is powered on")
        print("    - Check Slave ID setting (DIP switches or config)")
        print("    - Try different baudrates: 9600, 19200, 38400")
        print("    - Check RS-485 wiring (A/B may be swapped)")
        print("    - Ensure RS-485 termination resistor if using long cable")
        return False

def test_continuous_reads(port: str, slave_id: int = 1, baudrate: int = 19200, count: int = 10):
    """Test continuous reading"""
    print_section(f"4. CONTINUOUS READING TEST - {port}")
    
    print(f"  Reading {count} samples...")
    
    try:
        instrument = minimalmodbus.Instrument(port, slave_id, close_port_after_each_call=False)
        instrument.serial.baudrate = baudrate
        instrument.serial.bytesize = 8
        instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
        instrument.serial.stopbits = 1
        instrument.serial.timeout = 3.0
        instrument.mode = minimalmodbus.MODE_RTU
        instrument.clear_buffers_before_each_transaction = True
        
        success = 0
        failed = 0
        
        for i in range(count):
            try:
                # Read Z RMS velocity
                raw = instrument.read_register(45201 - 40001, number_of_decimals=0, functioncode=3, signed=False)
                value = raw / 65535 * 65.535  # Scale to mm/s
                print(f"    [{i+1:02d}] Z-RMS: {value:.3f} mm/s [RAW: {raw}]")
                success += 1
                time.sleep(0.1)
            except Exception as e:
                print(f"    [{i+1:02d}] ✗ Failed: {e}")
                failed += 1
                time.sleep(0.5)
        
        print(f"\n  📊 Result: {success}/{count} reads successful ({success/count*100:.0f}%)")
        
        if success == count:
            print("  ✅ Continuous reading working perfectly!")
            return True
        elif success > count * 0.5:
            print("  ⚠️  Some reads failed - connection may be unstable")
            return True
        else:
            print("  ❌ Too many failures - connection is unreliable")
            return False
            
    except Exception as e:
        print(f"\n  ❌ Test failed: {e}")
        return False

def main():
    """Main diagnostic routine"""
    print("\n" + "█" * 70)
    print("  SENSOR DIAGNOSTIC TOOL")
    print("  Comprehensive sensor connectivity diagnostics")
    print("█" * 70)
    
    # Step 1: Check COM ports
    ports = check_com_ports()
    
    if not ports:
        print("\n❌ FAILED: No COM ports available")
        sys.exit(1)
    
    # If multiple ports, ask user to select
    if len(ports) > 1:
        print("\n  Multiple ports detected. Please select one:")
        for i, port in enumerate(ports, 1):
            print(f"    [{i}] {port}")
        
        try:
            choice = input("\n  Enter port number (or press Enter for COM5): ").strip()
            if choice:
                selected_port = ports[int(choice) - 1]
            else:
                selected_port = "COM5"
        except:
            selected_port = "COM5"
    else:
        selected_port = ports[0]
    
    print(f"\n  Using port: {selected_port}")
    
    # Step 2: Test serial connection
    if not test_serial_connection(selected_port):
        print("\n❌ FAILED: Serial connection test failed")
        sys.exit(1)
    
    # Step 3: Test Modbus connection
    print("\n  Testing different Slave IDs...")
    modbus_success = False
    working_slave_id = 1
    
    for slave_id in [1, 2, 3, 4, 5]:
        print(f"\n  Trying Slave ID: {slave_id}")
        if test_modbus_connection(selected_port, slave_id=slave_id):
            modbus_success = True
            working_slave_id = slave_id
            break
    
    if not modbus_success:
        print("\n❌ FAILED: Modbus connection test failed for all Slave IDs")
        print("\n  Next steps:")
        print("    1. Verify sensor is powered on")
        print("    2. Check sensor configuration (DIP switches or software config)")
        print("    3. Try different baudrates: 9600, 19200, 38400")
        sys.exit(1)
    
    # Step 4: Test continuous reads
    if not test_continuous_reads(selected_port, slave_id=working_slave_id, count=10):
        print("\n⚠️  WARNING: Continuous reading test had issues")
        print("  Connection may be unstable")
    
    # Final summary
    print_section("DIAGNOSTIC SUMMARY")
    
    print(f"\n  ✅ Sensor detected and working!")
    print(f"\n  Recommended configuration:")
    print(f"    Port: {selected_port}")
    print(f"    Baudrate: 19200")
    print(f"    Slave ID: {working_slave_id}")
    print(f"    Parity: None")
    print(f"    Stop Bits: 1")
    
    print("\n  You can now use this configuration in your application.")
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Diagnostic interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n💥 Diagnostic crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
