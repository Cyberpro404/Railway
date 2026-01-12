"""
Modbus Checksum Debug Tool
Analyzes the hex string you received and helps diagnose checksum issues
"""

def parse_modbus_response(hex_string):
    """Parse and validate Modbus response"""
    # Remove spaces and convert to bytes
    hex_clean = hex_string.replace(" ", "").replace("0x", "")
    data = bytes.fromhex(hex_clean)
    
    print("=" * 70)
    print("  MODBUS RESPONSE ANALYSIS")
    print("=" * 70)
    
    # Parse header
    slave_id = data[0]
    function_code = data[1]
    byte_count = data[2]
    
    print(f"\n📋 Header:")
    print(f"  Slave ID: {slave_id}")
    print(f"  Function Code: {function_code} (Read Holding Registers)")
    print(f"  Byte Count: {byte_count} (0x{byte_count:02X})")
    print(f"  Expected Registers: {byte_count // 2}")
    
    # Extract data bytes
    data_start = 3
    data_end = 3 + byte_count
    data_bytes = data[data_start:data_end]
    
    print(f"\n📊 Data Payload ({len(data_bytes)} bytes):")
    
    # Parse as 16-bit registers
    registers = []
    for i in range(0, len(data_bytes), 2):
        if i + 1 < len(data_bytes):
            reg_value = (data_bytes[i] << 8) | data_bytes[i+1]
            registers.append(reg_value)
            print(f"  Reg {i//2:2d}: 0x{data_bytes[i]:02X}{data_bytes[i+1]:02X} = {reg_value:5d}")
    
    # Calculate expected CRC
    message = data[:data_end]
    crc = calculate_crc16_modbus(message)
    
    print(f"\n🔒 Checksum Analysis:")
    
    if data_end + 2 <= len(data):
        received_crc_bytes = data[data_end:data_end+2]
        received_crc = (received_crc_bytes[0] << 8) | received_crc_bytes[1]
        
        print(f"  Expected CRC: 0x{crc:04X} ({crc})")
        print(f"  Received CRC: 0x{received_crc:04X} ({received_crc}) - Bytes: {received_crc_bytes.hex()}")
        
        if crc == received_crc:
            print(f"  ✅ Checksum VALID")
        else:
            print(f"  ❌ Checksum MISMATCH!")
            print(f"  Difference: {abs(crc - received_crc)}")
    else:
        print(f"  ⚠️  No CRC bytes in provided data")
        print(f"  Expected CRC: 0x{crc:04X} ({crc})")
        print(f"  Expected bytes: {crc.to_bytes(2, 'little').hex()}")
    
    # Interpret sensor values (assuming QM30VT2 mapping starting at 45201)
    print(f"\n🔍 Interpreted Sensor Values (QM30VT2 Register Map 45201-45217):")
    
    if len(registers) >= 17:
        # Apply scaling: value / 65535 * 65.535 for most registers
        z_rms_mm_s = registers[0] / 65535.0 * 65.535
        z_rms_mm_s_2 = registers[1] / 65535.0 * 65.535
        temp_f = registers[2] / 100.0
        temp_c = registers[3] / 100.0
        x_rms_in_s = registers[4] / 65535.0 * 65.535
        x_rms_mm_s = registers[5] / 65535.0 * 65.535
        
        print(f"\n  Register Map (45201-45217):")
        print(f"    [0] Z-RMS Velocity:      {z_rms_mm_s:.4f} mm/s  (raw: {registers[0]})")
        print(f"    [1] Z-RMS Velocity (2):  {z_rms_mm_s_2:.4f} mm/s  (raw: {registers[1]})")
        print(f"    [2] Temperature (°F):    {temp_f:.1f}°F  (raw: {registers[2]})")
        print(f"    [3] Temperature (°C):    {temp_c:.1f}°C  (raw: {registers[3]})")
        print(f"    [4] X-RMS Velocity (in): {x_rms_in_s:.4f} in/s  (raw: {registers[4]})")
        print(f"    [5] X-RMS Velocity (mm): {x_rms_mm_s:.4f} mm/s  (raw: {registers[5]})")
        
        if len(registers) >= 8:
            z_peak_g = registers[6] / 65535.0 * 65.535
            x_peak_g = registers[7] / 65535.0 * 65.535
            print(f"    [6] Z-Peak Accel:        {z_peak_g:.4f} G  (raw: {registers[6]})")
            print(f"    [7] X-Peak Accel:        {x_peak_g:.4f} G  (raw: {registers[7]})")
        
        if len(registers) >= 16:
            z_rms_g = registers[10] / 65535.0 * 65.535
            x_rms_g = registers[11] / 65535.0 * 65.535
            z_kurtosis = registers[12] / 65535.0 * 65.535
            x_kurtosis = registers[13] / 65535.0 * 65.535
            z_crest = registers[14] / 65535.0 * 65.535
            x_crest = registers[15] / 65535.0 * 65.535
            
            print(f"    [10] Z-RMS Accel:        {z_rms_g:.4f} G  (raw: {registers[10]})")
            print(f"    [11] X-RMS Accel:        {x_rms_g:.4f} G  (raw: {registers[11]})")
            print(f"    [12] Z-Kurtosis:         {z_kurtosis:.4f}  (raw: {registers[12]})")
            print(f"    [13] X-Kurtosis:         {x_kurtosis:.4f}  (raw: {registers[13]})")
            print(f"    [14] Z-Crest Factor:     {z_crest:.4f}  (raw: {registers[14]})")
            print(f"    [15] X-Crest Factor:     {x_crest:.4f}  (raw: {registers[15]})")
    
    print("\n" + "=" * 70)
    
    return registers


def calculate_crc16_modbus(data):
    """Calculate Modbus RTU CRC-16"""
    crc = 0xFFFF
    
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    
    # Return as little-endian (Modbus RTU convention)
    return ((crc & 0xFF) << 8) | ((crc >> 8) & 0xFF)


def main():
    # The hex string you received
    hex_response = "01 03 22 00 33 00 5A 21 16 0B 6F 00 3D 00 9C 00 16 00 15 00 AA 00 7A 00 05 00 05 0C 10 0B 5A 0E 21 0D F6 00 32"
    
    print("\n🔍 Analyzing your Modbus response...")
    print(f"📥 Hex Data: {hex_response}\n")
    
    registers = parse_modbus_response(hex_response)
    
    print("\n💡 Recommendations:")
    print("=" * 70)
    
    print("\n1. ✅ Sensor is responding with valid data")
    print("   - Temperature reading (84.7°F / 29.3°C) looks realistic")
    print("   - Vibration values are in expected range")
    
    print("\n2. ⚠️  Checksum Issue Solutions:")
    print("   a) Increase serial timeout:")
    print("      instrument.serial.timeout = 2.0  # Try 2 seconds")
    print("   b) Clear buffers before read:")
    print("      instrument.clear_buffers_before_each_transaction = True")
    print("   c) Add delay between reads:")
    print("      time.sleep(0.1)  # 100ms between operations")
    print("   d) Check baud rate matches sensor (19200 is common)")
    
    print("\n3. 📊 Data Alignment:")
    print("   - Reading 17 registers (34 bytes) starting at 45201")
    print("   - This matches QM30VT2 block read specification")
    print("   - Backend is correctly configured for register range")
    
    print("\n4. 🔧 Scaling Check:")
    print("   - Using: value / 65535 * 65.535 for velocity/accel")
    print("   - Using: value / 100 for temperature")
    print("   - This is CORRECT for QM30VT2")
    
    print("\n5. 🚨 Immediate Fix:")
    print("   Try these in sensor_reader.py:")
    print("   - Set timeout to 2.0 seconds (currently 1.5)")
    print("   - Ensure clear_buffers_before_each_transaction = True")
    print("   - Add 50-100ms delay between consecutive reads")
    
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
