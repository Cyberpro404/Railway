"""Test COM5 connectivity"""
import serial
import time

port = "COM5"
baudrate = 19200

print(f"Testing {port} at {baudrate} baud...")

try:
    ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=3
    )
    
    print(f"✓ Successfully opened {port}")
    print(f"  Is open: {ser.is_open}")
    print(f"  Port: {ser.port}")
    print(f"  Baudrate: {ser.baudrate}")
    
    time.sleep(1)
    
    # Try to read some data
    print("\nAttempting to read data...")
    data = ser.read(10)
    print(f"  Read {len(data)} bytes: {data.hex() if data else '(no data)'}")
    
    ser.close()
    print(f"\n✓ {port} is working correctly!")
    
except serial.SerialException as e:
    print(f"\n✗ Failed to open {port}: {e}")
except Exception as e:
    print(f"\n✗ Unexpected error: {e}")
