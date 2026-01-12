"""
Test Continuous Sensor Reading
Tests the sensor connection with continuous reading and detailed error reporting
"""
import time
import sys
from datetime import datetime
from typing import Optional

# Import the sensor reader module
try:
    from core import sensor_reader
    from models import ConnectionConfig
    from utils.logger import setup_logger
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

# Setup logger
logger = setup_logger(__name__)

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_reading(reading: dict, count: int):
    """Print sensor reading in formatted way"""
    timestamp = reading.get("timestamp", "N/A")
    z_rms = reading.get("z_rms_mm_s", 0.0)
    x_rms = reading.get("x_rms_mm_s", 0.0)
    temp_c = reading.get("temp_c", 0.0)
    rpm = reading.get("rpm", 0.0)
    ok = reading.get("ok", False)
    
    status = "✓ OK" if ok else "✗ ERROR"
    
    print(f"\n[{count:04d}] {datetime.now().strftime('%H:%M:%S.%f')[:-3]} {status}")
    print(f"  Z-RMS: {z_rms:.3f} mm/s  |  X-RMS: {x_rms:.3f} mm/s")
    print(f"  Temp:  {temp_c:.1f}°C     |  RPM: {rpm:.0f}")
    
    # Check for additional data
    if reading.get("z_peak_accel_g") is not None:
        print(f"  Z-Peak: {reading.get('z_peak_accel_g', 0):.3f} G  |  X-Peak: {reading.get('x_peak_accel_g', 0):.3f} G")
    
    if not ok:
        error_msg = reading.get("error", "Unknown error")
        print(f"  ⚠️  Error: {error_msg}")

def test_continuous_reading(duration_seconds: int = 30, interval_seconds: float = 1.0):
    """
    Test continuous sensor reading
    
    Args:
        duration_seconds: How long to run the test (seconds)
        interval_seconds: Delay between readings (seconds)
    """
    print_header("CONTINUOUS SENSOR READING TEST")
    
    # Get default connection config
    config = ConnectionConfig()
    
    print(f"\n📋 Configuration:")
    print(f"  Port: {config.port}")
    print(f"  Baudrate: {config.baudrate}")
    print(f"  Slave ID: {config.slave_id}")
    print(f"  Timeout: {config.timeout_s}s")
    print(f"  Duration: {duration_seconds}s")
    print(f"  Interval: {interval_seconds}s")
    
    # Initialize sensor reader
    print(f"\n🔧 Initializing sensor reader...")
    try:
        sensor_reader.init_reader(config)
        print("  ✓ Sensor reader initialized successfully")
    except Exception as e:
        print(f"  ✗ Failed to initialize sensor reader: {e}")
        return False
    
    print(f"\n🚀 Starting continuous reading (Press Ctrl+C to stop early)...")
    print("-" * 70)
    
    # Statistics tracking
    total_reads = 0
    successful_reads = 0
    failed_reads = 0
    start_time = time.time()
    last_read_time = start_time
    
    try:
        while (time.time() - start_time) < duration_seconds:
            total_reads += 1
            
            try:
                # Read sensor once
                status, reading = sensor_reader.read_sensor_once()
                
                if status == sensor_reader.SensorStatus.OK and reading is not None:
                    if reading.get("ok", False):
                        successful_reads += 1
                        print_reading(reading, total_reads)
                    else:
                        failed_reads += 1
                        print_reading(reading, total_reads)
                else:
                    failed_reads += 1
                    print(f"\n[{total_reads:04d}] {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ✗ ERROR")
                    print(f"  Status: {status}")
                    print(f"  ⚠️  Failed to read sensor")
                
                # Calculate actual time taken
                current_time = time.time()
                elapsed = current_time - last_read_time
                last_read_time = current_time
                
                # Sleep for remaining interval time
                if elapsed < interval_seconds:
                    time.sleep(interval_seconds - elapsed)
                    
            except KeyboardInterrupt:
                print("\n\n⚠️  Test interrupted by user")
                break
            except Exception as e:
                failed_reads += 1
                print(f"\n[{total_reads:04d}] {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ✗ EXCEPTION")
                print(f"  ⚠️  Error: {e}")
                time.sleep(interval_seconds)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    
    # Print statistics
    print_header("TEST RESULTS")
    
    actual_duration = time.time() - start_time
    success_rate = (successful_reads / total_reads * 100) if total_reads > 0 else 0
    
    print(f"\n📊 Statistics:")
    print(f"  Duration: {actual_duration:.1f}s")
    print(f"  Total Reads: {total_reads}")
    print(f"  Successful: {successful_reads} ({success_rate:.1f}%)")
    print(f"  Failed: {failed_reads}")
    print(f"  Avg Rate: {total_reads / actual_duration:.2f} reads/sec")
    
    # Get connection health
    try:
        health = sensor_reader.get_health_stats()
        print(f"\n📈 Connection Health:")
        print(f"  Success Rate: {health.get('success_rate', 0) * 100:.1f}%")
        print(f"  Total Reads: {health.get('total_reads', 0)}")
        print(f"  Failed Reads: {health.get('failed_reads', 0)}")
        print(f"  Consecutive Failures: {health.get('consecutive_failures', 0)}")
        if health.get('last_error'):
            print(f"  Last Error: {health.get('last_error')}")
    except Exception as e:
        print(f"\n⚠️  Could not get connection health: {e}")
    
    print("\n" + "=" * 70)
    
    return success_rate > 50  # Consider test passed if >50% success rate

def test_single_read():
    """Test a single sensor read"""
    print_header("SINGLE SENSOR READ TEST")
    
    config = ConnectionConfig()
    
    print(f"\n📋 Configuration:")
    print(f"  Port: {config.port}")
    print(f"  Baudrate: {config.baudrate}")
    print(f"  Slave ID: {config.slave_id}")
    
    print(f"\n🔧 Initializing sensor reader...")
    try:
        sensor_reader.init_reader(config)
        print("  ✓ Sensor reader initialized")
    except Exception as e:
        print(f"  ✗ Failed to initialize: {e}")
        return False
    
    print(f"\n📖 Reading sensor...")
    try:
        status, reading = sensor_reader.read_sensor_once()
        
        if status == sensor_reader.SensorStatus.OK and reading is not None:
            print("  ✓ Read successful")
            print_reading(reading, 1)
            return reading.get("ok", False)
        else:
            print(f"  ✗ Read failed - Status: {status}")
            return False
            
    except Exception as e:
        print(f"  ✗ Exception during read: {e}")
        return False

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test continuous sensor reading")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds (default: 30)")
    parser.add_argument("--interval", type=float, default=1.0, help="Reading interval in seconds (default: 1.0)")
    parser.add_argument("--single", action="store_true", help="Run single read test only")
    
    args = parser.parse_args()
    
    try:
        if args.single:
            # Single read test
            success = test_single_read()
        else:
            # Continuous reading test
            success = test_continuous_reading(args.duration, args.interval)
        
        if success:
            print("\n✅ Test PASSED")
            sys.exit(0)
        else:
            print("\n❌ Test FAILED")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

if __name__ == "__main__":
    main()
