# Sensor Diagnostics Guide

## Problem: "Sensor Not Responding" Error

When you see the "sensor not responding" error, follow these steps:

## Quick Diagnostic Steps

### 1. Quick Status Check (Fastest)
```bash
python check_sensor.py
```
This quickly checks if the sensor is responding and shows the current reading.

### 2. Full Diagnostic (Recommended)
```bash
python diagnose_sensor.py
```
This runs a comprehensive diagnostic that:
- Detects all available COM ports
- Tests serial connection
- Tests Modbus communication
- Tries multiple Slave IDs
- Tests continuous reading
- Provides troubleshooting suggestions

### 3. Continuous Reading Test
```bash
# Run for 30 seconds (default)
python test_continuous_reading.py

# Run for custom duration
python test_continuous_reading.py --duration 60

# Run for custom duration with faster interval
python test_continuous_reading.py --duration 60 --interval 0.5

# Single read test only
python test_continuous_reading.py --single
```

## Common Issues and Solutions

### Issue 1: "No COM ports found"
**Solutions:**
- Check USB cable connection
- Check Device Manager to see if port appears
- Try a different USB port
- Restart the computer

### Issue 2: "Port in use" or "Access denied"
**Solutions:**
- Close any other programs that might be using the port
- Stop the main application if it's running
- Check Task Manager for Python processes
- Restart the computer if needed

### Issue 3: "No answer from slave" or "Modbus timeout"
**Solutions:**
- Verify sensor is powered on (check LED indicators)
- Check Slave ID configuration (try 1-5)
  - Most sensors default to Slave ID 1
  - Check sensor documentation or DIP switches
- Try different baudrates: 9600, 19200, 38400
- Check RS-485 wiring:
  - Verify A and B connections (may be swapped)
  - Check for loose connections
  - Ensure proper termination resistor for long cables

### Issue 4: "Intermittent failures" or "Unstable connection"
**Solutions:**
- Check cable quality (try a different cable)
- Reduce cable length if possible
- Add/check RS-485 termination resistor
- Check for electromagnetic interference near cables
- Reduce polling interval (increase delay between reads)
- Check sensor power supply stability

### Issue 5: "Wrong register values" or "Invalid data"
**Solutions:**
- Verify sensor model (QM30VT2 vs other models)
- Check sensor firmware version
- Verify register map matches your sensor
- Some registers may require sensor configuration

## Configuration in Your Application

After running diagnostics, update your configuration:

**File: `config/settings.py` or `models.py` ConnectionConfig**

```python
MODBUS_PORT = "COM5"          # From diagnostic output
MODBUS_BAUDRATE = 19200       # From diagnostic output
MODBUS_SLAVE_ID = 1           # From diagnostic output
MODBUS_TIMEOUT = 3.0          # Increase if timeouts occur
```

## Understanding the Output

### ✅ Success Indicators
- Green checkmarks (✓)
- "SENSOR RESPONDING"
- Reading values displayed
- High success rate (>90%)

### ⚠️ Warning Indicators
- Yellow warnings (⚠️)
- Partial success messages
- Some register reads failing
- Success rate between 50-90%

### ❌ Error Indicators
- Red X marks (✗/❌)
- "SENSOR NOT RESPONDING"
- "No answer from slave"
- Success rate below 50%

## Next Steps After Fixing

1. Run `check_sensor.py` to verify sensor is responding
2. Start your main application
3. Monitor the sensor readings in the UI
4. If problems persist, run full diagnostic again

## Getting Help

If diagnostics fail and you've tried all solutions:

1. Document the exact error messages
2. Note your hardware setup:
   - Sensor model
   - USB-to-RS485 adapter model
   - Cable length
   - Power supply specs
3. Save diagnostic output to a file:
   ```bash
   python diagnose_sensor.py > diagnostic_output.txt
   ```
4. Check sensor documentation for specific configuration requirements

## Automated Testing During Development

For continuous monitoring during development:

```bash
# Run continuous test in background
python test_continuous_reading.py --duration 3600 > sensor_test.log 2>&1 &
```

Check the log periodically to monitor sensor stability.
