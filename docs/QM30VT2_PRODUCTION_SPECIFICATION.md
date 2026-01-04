# Banner QM30VT2 Modbus RTU Data Acquisition System
## Production-Grade Specification & Implementation Guide

**Document Version:** 1.0  
**Target Device:** Banner QM30VT2 Vibration & Temperature Sensor  
**Protocol:** Modbus RTU over RS-485  
**Interface:** USB-RS485 Converter (transparent serial bridge)

---

## 1. SYSTEM ARCHITECTURE

### 1.1 Communication Stack

```
┌─────────────────────────────────────────────────┐
│           Application Layer                     │
│  • Predictive Maintenance Logic                 │
│  • ISO 10816 Classification                     │
│  • Trend Analysis & Fault Detection             │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│           Data Processing Layer                 │
│  • Register Scaling & Type Conversion           │
│  • Band Energy Extraction                       │
│  • JSON/CSV Serialization                       │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│           Modbus Protocol Layer                 │
│  • Function Code 03 (Read Holding Registers)    │
│  • CRC-16 Validation                            │
│  • Retry Logic & Timeout Handling               │
│  • Frame Assembly/Disassembly                   │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│           Serial Transport Layer                │
│  • RS-485 via USB-Serial Converter              │
│  • Baud: 19.2 kbps (default)                    │
│  • 8N1 (default) or configurable                │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│           Physical Layer                        │
│  • RS-485 Differential Signaling (A/B)          │
│  • Half-Duplex (Direction Control via RTS)      │
│  • Termination: 120Ω if cable > 10m             │
└─────────────────────────────────────────────────┘
```

### 1.2 Thread Safety Model

- **Global Reader Instance:** Single threaded access via mutex
- **Polling Loop:** Async task with configurable interval (0.5–2.0s recommended)
- **Error State:** Thread-safe last-error tracking for diagnostics
- **Connection Lifecycle:** Explicit init/cleanup on port contention

---

## 2. COMPLETE REGISTER MAP

### 2.1 Address Convention

**CRITICAL:** QM30VT2 documentation uses **1-based direct addresses** (4xxxx notation).  
Modbus protocol uses **0-based register offsets**.

**Conversion Formula:**
```
Modbus Register Address = Direct Address - 40001
```

Example:
- Direct Address 42403 → Modbus Register 2402
- Direct Address 40043 → Modbus Register 42

### 2.2 Primary Scalar Registers (Always Available)

| Direct Addr | Modbus Offset | Parameter                  | Data Type    | Scaling   | Unit   | Range         |
|-------------|---------------|----------------------------|--------------|-----------|--------|---------------|
| **40043**   | 42            | Temperature                | INT16        | ÷ 100     | °C     | -40 to +85    |
| **42403**   | 2402          | Z-axis RMS Velocity        | UINT16       | ÷ 1000    | mm/s   | 0 to 65.535   |
| **42404**   | 2403          | Z-axis Peak Velocity       | UINT16       | ÷ 1000    | mm/s   | 0 to 65.535   |
| **42453**   | 2452          | X-axis RMS Velocity        | UINT16       | ÷ 1000    | mm/s   | 0 to 65.535   |
| **42454**   | 2453          | X-axis Peak Velocity       | UINT16       | ÷ 1000    | mm/s   | 0 to 65.535   |

### 2.3 Extended Acceleration Registers (Sensor Dependent)

| Direct Addr | Modbus Offset | Parameter                     | Data Type | Scaling | Unit | Notes                    |
|-------------|---------------|-------------------------------|-----------|---------|------|--------------------------|
| **42406**   | 2405          | Z-axis RMS Acceleration       | UINT16    | ÷ 1000  | g    | Check sensor capability  |
| **42456**   | 2455          | X-axis RMS Acceleration       | UINT16    | ÷ 1000  | g    | Check sensor capability  |
| **42410**   | 2409          | Z-axis HF RMS Accel (1-4 kHz) | UINT16    | ÷ 1000  | g    | High-frequency component |
| **42460**   | 2459          | X-axis HF RMS Accel (1-4 kHz) | UINT16    | ÷ 1000  | g    | High-frequency component |

### 2.4 Statistical Parameters (Bearing Diagnostics)

| Direct Addr | Modbus Offset | Parameter            | Data Type | Scaling | Unit      | Diagnostic Use                |
|-------------|---------------|----------------------|-----------|---------|-----------|-------------------------------|
| **42408**   | 2407          | Z-axis Crest Factor  | UINT16    | ÷ 1000  | -         | Impact detection              |
| **42458**   | 2457          | X-axis Crest Factor  | UINT16    | ÷ 1000  | -         | Impact detection              |
| **42409**   | 2408          | Z-axis Kurtosis      | UINT16    | ÷ 1000  | -         | Early bearing fault indicator |
| **42459**   | 2458          | X-axis Kurtosis      | UINT16    | ÷ 1000  | -         | Early bearing fault indicator |

### 2.5 Spectral Band Registers (Extended - Not All Sensors)

**Z-axis Band Block:** Starting at 43501 (200 registers)  
**X-axis Band Block:** Starting at 43701 (200 registers)

**Structure per band:**
- 20 bands × 5 floats × 2 registers (32-bit IEEE 754) = 200 registers total

**Band Layout (per band = 10 registers):**
```
Offset  | Float Parameter       | Unit
--------|----------------------|--------
+0,+1   | Total RMS            | mm/s or g
+2,+3   | Peak RMS             | mm/s or g
+4,+5   | Peak Frequency       | Hz
+6,+7   | Peak RPM             | RPM
+8,+9   | Bin Index            | (integer as float)
```

**Fallback - Simple Bands (40004-40013):**
If extended bands unavailable, use basic band registers:
- 40004-40005: Band 1× (32-bit float)
- 40006-40007: Band 2× (32-bit float)
- 40008-40009: Band 3× (32-bit float)
- 40010-40011: Band 5× (32-bit float)
- 40012-40013: Band 7× (32-bit float)

---

## 3. REGISTER ACCESS PATTERNS

### 3.1 Optimal Polling Strategy

**Block Read Approach (Recommended):**
1. **Core Parameters Block** (40043 + scalars): 1 transaction
2. **Extended Acceleration Block**: 1 transaction (if supported)
3. **Statistical Block**: 1 transaction (if supported)
4. **Band Blocks**: 2 transactions (Z + X axes)

**Total Transactions:** 4–6 per polling cycle

**Timing Constraints:**
- Minimum inter-transaction delay: 10ms (RS-485 turnaround)
- Maximum frame timeout: 1000ms
- Polling interval: 500ms–2000ms (application dependent)

### 3.2 Chunked Reads for Large Blocks

Modbus RTU maximum: **125 registers per transaction**

For 200-register band blocks:
```python
# Chunk 1: Registers 0–124 (125 registers)
chunk1 = read_holding_registers(start=43501, count=125)

# Chunk 2: Registers 125–199 (75 registers)
chunk2 = read_holding_registers(start=43626, count=75)
```

### 3.3 Retry Logic

```
FOR attempt = 1 TO max_retries:
    TRY:
        result = modbus_read(...)
        RETURN result
    CATCH timeout:
        IF attempt < max_retries:
            WAIT exponential_backoff(attempt)
        ELSE:
            LOG error
            RAISE timeout_exception
    CATCH crc_error:
        LOG "CRC failure - possible EMI or wiring issue"
        RETRY
    CATCH illegal_address:
        LOG "Register not supported by sensor firmware"
        SKIP register
        RETURN partial_data
```

---

## 4. DATA SCALING & TYPE CONVERSION

### 4.1 Integer to Engineering Units

```python
def scale_temperature(raw: int) -> float:
    """40043: INT16, scale ÷100"""
    return float(raw) / 100.0  # Example: 2350 → 23.50°C

def scale_rms_velocity(raw: int) -> float:
    """42403, 42453: UINT16, scale ÷1000"""
    return float(raw) / 1000.0  # Example: 1234 → 1.234 mm/s

def scale_acceleration(raw: int) -> float:
    """42406, 42456: UINT16, scale ÷1000"""
    return float(raw) / 1000.0  # Example: 500 → 0.500 g

def scale_crest_factor(raw: int) -> float:
    """42408, 42458: UINT16, scale ÷1000"""
    return float(raw) / 1000.0  # Example: 3200 → 3.200
```

### 4.2 32-bit Float Parsing (Big-Endian)

```python
import struct

def parse_float32_be(word_hi: int, word_lo: int) -> float:
    """
    Convert two 16-bit registers to IEEE 754 float.
    
    Args:
        word_hi: High word (first register)
        word_lo: Low word (second register)
    
    Returns:
        Decoded float value
    """
    # Pack as big-endian unsigned shorts
    bytes_data = struct.pack(">HH", word_hi & 0xFFFF, word_lo & 0xFFFF)
    # Unpack as big-endian float
    return struct.unpack(">f", bytes_data)[0]
```

**Usage:**
```python
# Read band total RMS (registers 43501-43502)
regs = read_holding_registers(start=43501, count=2)
total_rms = parse_float32_be(regs[0], regs[1])
```

---

## 5. FAULT DETECTION & ERROR HANDLING

### 5.1 Communication Error Taxonomy

| Error Type            | Modbus Exception | Cause                              | Action                          |
|-----------------------|------------------|------------------------------------|---------------------------------|
| **No Response**       | Timeout          | Slave offline, wrong ID, bus fault | Retry → log → mark stale        |
| **CRC Mismatch**      | CRC Error        | EMI, loose connection, termination | Retry → check wiring            |
| **Illegal Function**  | Exception 01     | Sensor doesn't support FC 03       | Check sensor model              |
| **Illegal Address**   | Exception 02     | Register not implemented           | Skip register → mark unavail    |
| **Illegal Data**      | Exception 03     | Invalid write (not applicable)     | -                               |
| **Slave Busy**        | Exception 06     | Sensor processing previous request | Retry after delay               |

### 5.2 Connection Health Monitoring

**Startup Smoke Test:**
```python
def smoke_test(slave_id: int) -> bool:
    """Test communication with single known-good register."""
    try:
        temp = read_register(40043, decimals=2, signed=True)
        if -50.0 < temp < 150.0:  # Sanity check
            return True
    except:
        return False
    return False
```

**Continuous Health Tracking:**
```python
class ConnectionHealth:
    def __init__(self):
        self.consecutive_failures = 0
        self.total_reads = 0
        self.failed_reads = 0
        self.last_success_time = None
    
    def record_success(self):
        self.consecutive_failures = 0
        self.total_reads += 1
        self.last_success_time = time.time()
    
    def record_failure(self):
        self.consecutive_failures += 1
        self.total_reads += 1
        self.failed_reads += 1
    
    @property
    def success_rate(self) -> float:
        if self.total_reads == 0:
            return 0.0
        return (self.total_reads - self.failed_reads) / self.total_reads
```

### 5.3 Diagnostic Logging

**Hex Frame Logging:**
```python
def log_modbus_frame(direction: str, frame: bytes):
    """
    Log raw Modbus frames for diagnostics.
    
    Example Output:
    [TX] 01 03 09 62 00 01 25 F1
    [RX] 01 03 02 09 C4 B8 FA
    """
    hex_str = ' '.join(f'{b:02X}' for b in frame)
    logger.debug(f"[{direction}] {hex_str}")
```

---

## 6. PREDICTIVE MAINTENANCE ALGORITHMS

### 6.1 ISO 10816 Vibration Severity Classification

**Applies to:** RMS velocity (mm/s)

```python
class ISO10816Zone:
    """ISO 10816-1 vibration severity zones for machinery."""
    
    @staticmethod
    def classify(rms_mm_s: float, machine_class: str = "class_II") -> str:
        """
        Machine Class II: Medium machines (15–75 kW)
        mounted on rigid foundations
        
        Returns: "good", "satisfactory", "unsatisfactory", "unacceptable"
        """
        if machine_class == "class_II":
            if rms_mm_s < 2.3:
                return "good"           # Zone A
            elif rms_mm_s < 7.1:
                return "satisfactory"   # Zone B
            elif rms_mm_s < 11.2:
                return "unsatisfactory" # Zone C
            else:
                return "unacceptable"   # Zone D
        
        # Add classes I, III, IV as needed
        raise ValueError(f"Unsupported machine class: {machine_class}")
```

### 6.2 Bearing Fault Indicators

**Crest Factor Analysis:**
```python
def analyze_crest_factor(cf_z: float, cf_x: float) -> dict:
    """
    Crest Factor = Peak / RMS
    
    Normal Range: 2.5 – 4.0
    Rising CF (>5.0): Early bearing wear (spalling initiation)
    High CF (>8.0): Advanced bearing defect (localized faults)
    """
    status = {
        "z_axis": "normal",
        "x_axis": "normal",
        "alert": False,
        "message": ""
    }
    
    if cf_z > 8.0 or cf_x > 8.0:
        status["alert"] = True
        status["message"] = "CRITICAL: High crest factor detected - inspect bearing immediately"
    elif cf_z > 5.0 or cf_x > 5.0:
        status["alert"] = True
        status["message"] = "WARNING: Elevated crest factor - early bearing wear suspected"
    
    if cf_z > 5.0:
        status["z_axis"] = "warning" if cf_z < 8.0 else "critical"
    if cf_x > 5.0:
        status["x_axis"] = "warning" if cf_x < 8.0 else "critical"
    
    return status
```

**Kurtosis Analysis:**
```python
def analyze_kurtosis(kurt_z: float, kurt_x: float) -> dict:
    """
    Kurtosis measures "peakedness" of vibration signal.
    
    Normal: 2.8 – 3.2 (Gaussian)
    Low (<2.0): Rounded/worn surfaces
    High (>4.0): Impulsive events (bearing spalls, cracks)
    Very High (>8.0): Severe localized defect
    """
    status = {
        "z_axis": "normal",
        "x_axis": "normal",
        "alert": False,
        "message": ""
    }
    
    if kurt_z > 8.0 or kurt_x > 8.0:
        status["alert"] = True
        status["message"] = "CRITICAL: Extremely high kurtosis - severe bearing defect"
    elif kurt_z > 4.0 or kurt_x > 4.0:
        status["alert"] = True
        status["message"] = "WARNING: Elevated kurtosis - inspect for bearing faults"
    
    return status
```

**High-Frequency RMS Acceleration:**
```python
def analyze_hf_rms(hf_z: float, hf_x: float, baseline: dict) -> dict:
    """
    HF RMS (1-4 kHz) detects early bearing defects before they
    appear in velocity spectrum.
    
    Trend Analysis:
    - >50% increase from baseline: Investigate
    - >100% increase: Urgent inspection required
    """
    z_increase = (hf_z - baseline["hf_z"]) / baseline["hf_z"] * 100
    x_increase = (hf_x - baseline["hf_x"]) / baseline["hf_x"] * 100
    
    if z_increase > 100 or x_increase > 100:
        return {
            "alert": True,
            "severity": "critical",
            "message": f"HF RMS doubled: Z={z_increase:.1f}%, X={x_increase:.1f}%"
        }
    elif z_increase > 50 or x_increase > 50:
        return {
            "alert": True,
            "severity": "warning",
            "message": f"HF RMS increase: Z={z_increase:.1f}%, X={x_increase:.1f}%"
        }
    
    return {"alert": False}
```

---

## 7. CONFIGURATION MANAGEMENT

### 7.1 Modbus Configuration Registers (Write)

**WARNING:** Writing configuration requires Function Code 06 (Write Single Register) or 16 (Write Multiple Registers). Verify sensor supports before attempting.

| Direct Addr | Parameter           | Values                          |
|-------------|---------------------|---------------------------------|
| 40201       | Baud Rate           | 0=9600, 1=19200, 2=38400, etc. |
| 40202       | Parity              | 0=None, 1=Even, 2=Odd           |
| 40203       | Slave ID            | 1–247                           |
| 40204       | Rotational Speed    | RPM (for spectral band calcs)   |

**Example - Set Baud Rate:**
```python
def set_sensor_baudrate(new_baud: int) -> bool:
    """
    Write baud rate register and power cycle sensor to apply.
    
    Args:
        new_baud: 9600, 19200, 38400, 57600, 115200
    
    Returns:
        True if write succeeded (sensor must be power cycled)
    """
    baud_map = {9600: 0, 19200: 1, 38400: 2, 57600: 3, 115200: 4}
    if new_baud not in baud_map:
        raise ValueError(f"Invalid baud rate: {new_baud}")
    
    value = baud_map[new_baud]
    write_single_register(40201, value, function_code=6)
    logger.info(f"Baud rate set to {new_baud} - POWER CYCLE SENSOR to apply")
    return True
```

---

## 8. DATA OUTPUT FORMATS

### 8.1 JSON Structure (Industrial Naming)

```json
{
  "timestamp": "2026-01-01T12:00:00.000Z",
  "connection": {
    "port": "COM5",
    "slave_id": 1,
    "baudrate": 19200
  },
  "temperature": {
    "celsius": 45.2,
    "fahrenheit": 113.4,
    "status": "normal"
  },
  "vibration": {
    "z_axis": {
      "rms_velocity_mm_s": 2.345,
      "peak_velocity_mm_s": 8.123,
      "rms_acceleration_g": 0.512,
      "hf_rms_acceleration_g": 0.089,
      "crest_factor": 3.465,
      "kurtosis": 3.102,
      "iso10816_zone": "good"
    },
    "x_axis": {
      "rms_velocity_mm_s": 1.987,
      "peak_velocity_mm_s": 6.543,
      "rms_acceleration_g": 0.432,
      "hf_rms_acceleration_g": 0.076,
      "crest_factor": 3.295,
      "kurtosis": 2.987,
      "iso10816_zone": "good"
    }
  },
  "spectral_bands": {
    "z_axis": [
      {
        "band_number": 1,
        "multiple": "1×",
        "total_rms": 0.845,
        "peak_rms": 0.723,
        "peak_frequency_hz": 29.5,
        "peak_rpm": 1770
      }
    ],
    "x_axis": [...]
  },
  "diagnostics": {
    "bearing_health": {
      "status": "normal",
      "crest_factor_alert": false,
      "kurtosis_alert": false,
      "hf_trend_alert": false
    },
    "communication": {
      "success_rate": 0.998,
      "consecutive_failures": 0,
      "last_error": null
    }
  }
}
```

### 8.2 CSV Format (Flat Structure for SCADA)

```csv
timestamp,temp_c,z_rms_mm_s,x_rms_mm_s,z_peak_mm_s,x_peak_mm_s,z_rms_g,x_rms_g,z_hf_rms_g,x_hf_rms_g,z_crest_factor,x_crest_factor,z_kurtosis,x_kurtosis,z_iso10816,x_iso10816
2026-01-01T12:00:00Z,45.2,2.345,1.987,8.123,6.543,0.512,0.432,0.089,0.076,3.465,3.295,3.102,2.987,good,good
```

---

## 9. INTEGRATION GUIDELINES

### 9.1 SCADA Integration

**OPC UA Server Template:**
```
Root
├── Device
│   ├── Temperature (°C)
│   ├── VibrationZ
│   │   ├── RMS (mm/s)
│   │   ├── Peak (mm/s)
│   │   ├── CrestFactor
│   │   └── ISO10816Zone
│   └── VibrationX
│       ├── RMS (mm/s)
│       ├── Peak (mm/s)
│       ├── CrestFactor
│       └── ISO10816Zone
└── Diagnostics
    ├── ConnectionHealth
    └── LastError
```

### 9.2 REST API Endpoints

```
GET  /api/sensor/latest       → Current reading (JSON)
GET  /api/sensor/history?seconds=3600  → Historical data
GET  /api/sensor/diagnostics  → Connection health
POST /api/sensor/configure    → Set parameters
GET  /api/sensor/bands/{axis} → Spectral data
```

---

## 10. VALIDATION & TESTING

### 10.1 Unit Test Checklist

- [ ] Register address conversion (4xxxx → 0-based)
- [ ] Scaling factor application (all 22 parameters)
- [ ] Signed/unsigned integer handling
- [ ] 32-bit float parsing (big-endian)
- [ ] CRC calculation validation
- [ ] Timeout & retry logic
- [ ] Thread-safe access patterns
- [ ] Error classification (timeout vs CRC vs exception)

### 10.2 Integration Test Scenarios

1. **Cold Start:** Power on sensor → verify smoke test → full poll cycle
2. **Cable Disconnect:** Unplug RS-485 mid-poll → verify timeout → reconnect → resume
3. **Wrong Slave ID:** Change ID → verify "no response" → restore → verify recovery
4. **Partial Register Support:** Disable extended bands → verify fallback to simple bands
5. **EMI Injection:** Induce CRC errors → verify retry → log diagnostics

---

## 11. DEPLOYMENT CHECKLIST

### Pre-Deployment

- [ ] Verify sensor DIP switch settings (Slave ID, baud rate)
- [ ] Confirm RS-485 wiring: A→A, B→B (not swapped)
- [ ] Install termination resistor if cable > 10m
- [ ] Test with known-good Modbus scanner (ModbusPoll, QModMaster)
- [ ] Validate all 22 registers return sane values
- [ ] Baseline crest factor, kurtosis for trend analysis

### Post-Deployment

- [ ] Monitor communication success rate (target: >99.5%)
- [ ] Set up alerting for:
  - Consecutive failures > 3
  - ISO 10816 zone transitions
  - Crest factor excursions
  - HF RMS trend deviations
- [ ] Log hex frames for first 24h (diagnostics)
- [ ] Establish baseline for predictive maintenance

---

## 12. TROUBLESHOOTING DECISION TREE

```
NO RESPONSE?
├─ Wrong slave ID → Verify DIP switches
├─ Wrong baud rate → Try 9600, 19200, 38400
├─ Wrong parity → Try N, E, O
├─ Cable fault → Check A/B continuity
└─ Port busy → Close other applications

CRC ERRORS?
├─ EMI → Shield cable, add ferrites
├─ Termination → Add 120Ω resistor at ends
└─ Loose connection → Reseat terminals

ILLEGAL ADDRESS?
├─ Register not supported → Check firmware version
└─ Update register map for sensor model

VALUES OUT OF RANGE?
├─ Wrong scaling → Verify ÷1000 vs ÷100
├─ Signed vs unsigned → Check INT16 vs UINT16
└─ Byte order → Verify big-endian assumption
```

---

## APPENDIX A: EXAMPLE DECODED OUTPUT

### Complete Reading (All 22 Parameters)

```
═══════════════════════════════════════════════════════════════
BANNER QM30VT2 READING @ 2026-01-01 12:00:00 UTC
Port: COM5 | Slave: 1 | Baud: 19200 | Success Rate: 99.8%
═══════════════════════════════════════════════════════════════

TEMPERATURE
───────────────────────────────────────────────────────────────
  Celsius:     45.23 °C
  Fahrenheit:  113.41 °F
  Status:      NORMAL

Z-AXIS VIBRATION
───────────────────────────────────────────────────────────────
  RMS Velocity:              2.345 mm/s
  Peak Velocity:             8.123 mm/s
  RMS Acceleration:          0.512 g
  HF RMS Acceleration:       0.089 g (1-4 kHz)
  Crest Factor:              3.465
  Kurtosis:                  3.102
  ISO 10816 Classification:  GOOD (Zone A)

X-AXIS VIBRATION
───────────────────────────────────────────────────────────────
  RMS Velocity:              1.987 mm/s
  Peak Velocity:             6.543 mm/s
  RMS Acceleration:          0.432 g
  HF RMS Acceleration:       0.076 g (1-4 kHz)
  Crest Factor:              3.295
  Kurtosis:                  2.987
  ISO 10816 Classification:  GOOD (Zone A)

SPECTRAL BANDS (Z-AXIS)
───────────────────────────────────────────────────────────────
  Band  Multiple  Total RMS  Peak RMS  Peak Freq  Peak RPM
  ────  ────────  ─────────  ────────  ─────────  ────────
    1      1×      0.845      0.723      29.5      1770
    2      2×      0.312      0.287      59.0      3540
    3      3×      0.156      0.134      88.5      5310
    5      5×      0.089      0.076     147.5      8850
    7      7×      0.054      0.043     206.5     12390

PREDICTIVE MAINTENANCE DIAGNOSTICS
───────────────────────────────────────────────────────────────
  Bearing Health:     ✓ NORMAL
  Crest Factor:       ✓ Within range (2.5-4.0)
  Kurtosis:           ✓ Gaussian distribution (2.8-3.2)
  HF Trend:           ✓ Stable (baseline ±10%)
  Overall Status:     ✓ NO ACTIONABLE FAULTS

COMMUNICATION DIAGNOSTICS
───────────────────────────────────────────────────────────────
  Consecutive Failures:  0
  Total Reads:           12847
  Failed Reads:          23
  Success Rate:          99.82%
  Last Error:            None
═══════════════════════════════════════════════════════════════
```

---

**END OF SPECIFICATION**

