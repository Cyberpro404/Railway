"""
Quick Sensor Status Check
Quickly check if sensor is responding and get current reading
"""
import sys
from datetime import datetime

try:
    from core import sensor_reader
    from models import ConnectionConfig
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Run this from the project root directory")
    sys.exit(1)

def main():
    print("\n" + "=" * 60)
    print("  QUICK SENSOR STATUS CHECK")
    print("=" * 60)
    
    # Use default configuration
    config = ConnectionConfig()
    
    print(f"\n📋 Configuration:")
    print(f"  Port: {config.port}")
    print(f"  Baudrate: {config.baudrate}")
    print(f"  Slave ID: {config.slave_id}")
    print(f"  Timeout: {config.timeout_s}s")
    
    # Initialize sensor
    print(f"\n🔧 Initializing sensor...")
    try:
        sensor_reader.init_reader(config)
        print("  ✓ Initialized")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False
    
    # Read sensor
    print(f"\n📖 Reading sensor...")
    try:
        status, reading = sensor_reader.read_sensor_once()
        
        if status == sensor_reader.SensorStatus.OK and reading is not None:
            ok = reading.get("ok", False)
            
            if ok:
                print("  ✅ SENSOR RESPONDING!")
                print(f"\n  Current Reading ({datetime.now().strftime('%H:%M:%S')}):")
                print(f"    Z-RMS:  {reading.get('z_rms_mm_s', 0):.3f} mm/s")
                print(f"    X-RMS:  {reading.get('x_rms_mm_s', 0):.3f} mm/s")
                print(f"    Temp:   {reading.get('temp_c', 0):.1f} °C")
                
                # Show additional data if available
                if reading.get('z_peak_accel_g') is not None:
                    print(f"    Z-Peak: {reading.get('z_peak_accel_g', 0):.3f} G")
                if reading.get('x_peak_accel_g') is not None:
                    print(f"    X-Peak: {reading.get('x_peak_accel_g', 0):.3f} G")
                if reading.get('rpm') is not None:
                    print(f"    RPM:    {reading.get('rpm', 0):.0f}")
                
                return True
            else:
                print("  ❌ SENSOR ERROR!")
                error_msg = reading.get("error", "Unknown error")
                print(f"  Error: {error_msg}")
                return False
        else:
            print("  ❌ SENSOR NOT RESPONDING!")
            print(f"  Status: {status}")
            
            # Check for last error
            last_error, last_error_time = sensor_reader.get_last_error()
            if last_error:
                print(f"  Last Error: {last_error}")
                if last_error_time:
                    print(f"  Error Time: {last_error_time}")
            
            return False
            
    except Exception as e:
        print(f"  ❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print("\n" + "=" * 60 + "\n")

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Crash: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
