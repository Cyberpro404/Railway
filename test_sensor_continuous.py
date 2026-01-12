"""
Continuous Sensor Reading Test (No Persistent Connection)
Tests continuous reading while properly releasing port between reads
"""
import sys
import time
from datetime import datetime

try:
    import minimalmodbus
    from models import ConnectionConfig
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def read_sensor_once(instrument):
    """Read sensor data once"""
    try:
        # Read primary data
        z_rms_raw = instrument.read_register(45201 - 40001, number_of_decimals=0, functioncode=3, signed=False)
        z_rms = z_rms_raw / 65535 * 65.535
        
        x_rms_raw = instrument.read_register(45206 - 40001, number_of_decimals=0, functioncode=3, signed=False)
        x_rms = x_rms_raw / 65535 * 65.535
        
        temp_raw = instrument.read_register(45204 - 40001, number_of_decimals=0, functioncode=3, signed=False)
        temp_c = temp_raw / 100.0
        
        return {
            'ok': True,
            'z_rms': z_rms,
            'x_rms': x_rms,
            'temp_c': temp_c
        }
    except Exception as e:
        return {
            'ok': False,
            'error': str(e)
        }

def main(duration=30, interval=1.0):
    print("\n" + "=" * 70)
    print("  CONTINUOUS SENSOR READING TEST")
    print("=" * 70)
    
    config = ConnectionConfig()
    
    print(f"\n📋 Configuration:")
    print(f"  Port: {config.port}")
    print(f"  Baudrate: {config.baudrate}")
    print(f"  Slave ID: {config.slave_id}")
    print(f"  Duration: {duration}s")
    print(f"  Interval: {interval}s")
    
    # Create instrument (closes port after each call)
    instrument = minimalmodbus.Instrument(
        config.port, 
        config.slave_id, 
        close_port_after_each_call=True
    )
    instrument.serial.baudrate = config.baudrate
    instrument.serial.bytesize = config.bytesize
    instrument.serial.parity = minimalmodbus.serial.PARITY_NONE if config.parity == 'N' else minimalmodbus.serial.PARITY_EVEN
    instrument.serial.stopbits = config.stopbits
    instrument.serial.timeout = config.timeout_s
    instrument.mode = minimalmodbus.MODE_RTU
    instrument.clear_buffers_before_each_transaction = True
    
    print(f"\n🚀 Starting continuous reading (Press Ctrl+C to stop)...")
    print("-" * 70)
    
    count = 0
    success = 0
    failed = 0
    start_time = time.time()
    
    try:
        while (time.time() - start_time) < duration:
            count += 1
            read_start = time.time()
            
            result = read_sensor_once(instrument)
            
            if result['ok']:
                success += 1
                print(f"[{count:03d}] {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ✓ "
                      f"Z:{result['z_rms']:6.3f} X:{result['x_rms']:6.3f} T:{result['temp_c']:5.1f}°C")
            else:
                failed += 1
                print(f"[{count:03d}] {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ✗ "
                      f"ERROR: {result['error']}")
            
            # Sleep for remaining interval
            elapsed = time.time() - read_start
            if elapsed < interval:
                time.sleep(interval - elapsed)
                
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    
    # Print results
    print("\n" + "=" * 70)
    print("  TEST RESULTS")
    print("=" * 70)
    
    actual_duration = time.time() - start_time
    success_rate = (success / count * 100) if count > 0 else 0
    
    print(f"\n📊 Statistics:")
    print(f"  Duration: {actual_duration:.1f}s")
    print(f"  Total Reads: {count}")
    print(f"  Successful: {success} ({success_rate:.1f}%)")
    print(f"  Failed: {failed}")
    print(f"  Avg Rate: {count / actual_duration:.2f} reads/sec")
    
    if success_rate >= 95:
        print("\n  ✅ EXCELLENT - Sensor is stable and responding well!")
        status = 0
    elif success_rate >= 80:
        print("\n  ⚠️  GOOD - Minor issues but generally working")
        status = 0
    elif success_rate >= 50:
        print("\n  ⚠️  WARNING - Connection is unstable")
        status = 1
    else:
        print("\n  ❌ FAILED - Too many errors, check connection")
        status = 1
    
    print("\n" + "=" * 70 + "\n")
    return status

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test continuous sensor reading")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    parser.add_argument("--interval", type=float, default=1.0, help="Reading interval in seconds")
    
    args = parser.parse_args()
    
    try:
        sys.exit(main(args.duration, args.interval))
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
