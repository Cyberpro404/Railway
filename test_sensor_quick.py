"""
Test Sensor Once - No persistent connection
Quick test that properly releases the port after reading
"""
import sys
from datetime import datetime

try:
    import minimalmodbus
    from models import ConnectionConfig
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def main():
    print("\n" + "=" * 60)
    print("  SENSOR QUICK TEST")
    print("=" * 60)
    
    config = ConnectionConfig()
    
    print(f"\n📋 Configuration:")
    print(f"  Port: {config.port}")
    print(f"  Baudrate: {config.baudrate}")
    print(f"  Slave ID: {config.slave_id}")
    
    print(f"\n📖 Reading sensor...")
    
    try:
        # Create instrument with close_port_after_each_call=True
        instrument = minimalmodbus.Instrument(
            config.port, 
            config.slave_id, 
            close_port_after_each_call=True  # Releases port after each read
        )
        instrument.serial.baudrate = config.baudrate
        instrument.serial.bytesize = config.bytesize
        instrument.serial.parity = minimalmodbus.serial.PARITY_NONE if config.parity == 'N' else minimalmodbus.serial.PARITY_EVEN
        instrument.serial.stopbits = config.stopbits
        instrument.serial.timeout = config.timeout_s
        instrument.mode = minimalmodbus.MODE_RTU
        instrument.clear_buffers_before_each_transaction = True
        
        # Read primary registers (45201-45206)
        print("  Reading Z-RMS (45201)...")
        z_rms_raw = instrument.read_register(45201 - 40001, number_of_decimals=0, functioncode=3, signed=False)
        z_rms = z_rms_raw / 65535 * 65.535
        
        print("  Reading X-RMS (45206)...")
        x_rms_raw = instrument.read_register(45206 - 40001, number_of_decimals=0, functioncode=3, signed=False)
        x_rms = x_rms_raw / 65535 * 65.535
        
        print("  Reading Temperature (45204)...")
        temp_raw = instrument.read_register(45204 - 40001, number_of_decimals=0, functioncode=3, signed=False)
        temp_c = temp_raw / 100.0
        
        print("\n  ✅ SENSOR RESPONDING!")
        print(f"\n  Reading at {datetime.now().strftime('%H:%M:%S')}:")
        print(f"    Z-RMS:  {z_rms:.3f} mm/s  (raw: {z_rms_raw})")
        print(f"    X-RMS:  {x_rms:.3f} mm/s  (raw: {x_rms_raw})")
        print(f"    Temp:   {temp_c:.1f} °C     (raw: {temp_raw})")
        
        return True
        
    except Exception as e:
        print(f"  ❌ SENSOR ERROR!")
        print(f"  Error: {e}")
        return False
    
    finally:
        print("\n" + "=" * 60 + "\n")

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted")
        sys.exit(130)
