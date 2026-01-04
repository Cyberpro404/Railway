# Industrial Middleware for QM30VT2 Sensors
## Deterministic PLC-Friendly Design

**Version:** 1.0  
**Date:** January 1, 2026  
**Architecture Type:** PLC-First, Deterministic, Auditable  
**No ML / No Inference / No Predictive Logic**

---

## EXECUTIVE SUMMARY

This document defines a deterministic industrial middleware application for Banner QM30VT2 vibration sensors. The system operates in two distinct modes and enforces strict data scope, explicit configuration, and full traceability.

**Key Principle:** All data flows are visible, logged, and reversible. No silent failures or automatic assumptions.

---

## SYSTEM OVERVIEW

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 QM30VT2 Sensors (Field Layer)                   │
│                                                                 │
│  [Sensor #1]    [Sensor #2]    [Sensor #3]    [Sensor #4]      │
│  Modbus RTU     Modbus RTU     Modbus RTU     Modbus RTU        │
└─────────────────────────────────────────────────────────────────┘
         │                               │
         │                               │
         ▼ (Mode 1)                      ▼ (Mode 2)
    ┌──────────────┐              ┌──────────────┐
    │ PLC          │              │ DXM1000      │
    │ (Modbus RTU  │              │ Gateway      │
    │  Master)     │              │ (Modbus RTU  │
    │              │              │  Master)     │
    └──────────────┘              └──────────────┘
         │                               │
         │ TCP/IP (Tag Read)             │ Modbus TCP
         │ or OPC-UA                     │ or Serial
         │                               │
         └───────────────┬───────────────┘
                         │
                 ┌───────▼──────────┐
                 │  Industrial      │
                 │  Middleware      │
                 │  Application     │
                 │                  │
                 │  (This System)   │
                 └────────┬─────────┘
                          │
                ┌─────────┴──────────┬──────────────┐
                │                    │              │
                ▼                    ▼              ▼
          ┌──────────┐        ┌────────────┐  ┌─────────┐
          │ PLC      │        │ Database   │  │ UI      │
          │ Output   │        │ (Audit)    │  │ Tabs    │
          │ Tags     │        │            │  │         │
          └──────────┘        └────────────┘  └─────────┘
```

---

## SYSTEM MODES

### Mode 1: PLC as Data Source

**Scenario:** QM30VT2 sensors → PLC (Modbus RTU Master) → TCP/IP → Middleware

**Responsibilities:**
- Middleware reads PLC tags over TCP/IP (Modbus TCP, OPC-UA, or proprietary protocol)
- Middleware is **read-only** from the field layer
- Scaling and parameter mapping occur in PLC
- Middleware receives already-scaled data
- Middleware may forward data to a secondary PLC for archival/SCADA

**Configuration:**
- PLC IP address, port, timeout
- Tag name mapping (Z-RMS, X-Peak, Temperature, etc.)
- Read frequency
- Optional secondary PLC output

---

### Mode 2: DXM1000 as Data Source

**Scenario:** QM30VT2 sensors → DXM1000 (Modbus RTU Master) → Modbus TCP/Serial → Middleware

**Responsibilities:**
- Middleware polls DXM1000 for sensor data
- Middleware applies QM30VT2 register scaling (per Banner documentation)
- Middleware maintains register-to-parameter mapping
- Middleware optionally writes results to a PLC for SCADA integration
- Middleware logs all register reads and writes

**Configuration:**
- DXM1000 IP address, port, or serial port
- Modbus slave ID (configurable, 1–247)
- Sampling frequency
- PLC output address range and tag mapping (optional)

---

## DATA SCOPE: 22 QM30VT2 PARAMETERS (STRICT)

### Parameter Registry

| Index | Register(s) | Parameter Name | Unit | Type | Scale | Notes |
|-------|-------------|----------------|------|------|-------|-------|
| 1 | 40043 | Temperature | °C | int16 | 0.01 | Signed, direct read |
| 2 | 42403 | Z-Axis RMS Velocity | mm/s | uint16 | 0.001 | Unsigned |
| 3 | 42453 | X-Axis RMS Velocity | mm/s | uint16 | 0.001 | Unsigned |
| 4 | 42404 | Z-Axis Peak Velocity | mm/s | uint16 | 0.001 | Unsigned |
| 5 | 42454 | X-Axis Peak Velocity | mm/s | uint16 | 0.001 | Unsigned |
| 6 | 42406 | Z-Axis RMS Acceleration | g | uint16 | 0.001 | Unsigned |
| 7 | 42456 | X-Axis RMS Acceleration | g | uint16 | 0.001 | Unsigned |
| 8 | 42410 | Z-Axis HF RMS Acceleration | g | uint16 | 0.001 | High-frequency |
| 9 | 42460 | X-Axis HF RMS Acceleration | g | uint16 | 0.001 | High-frequency |
| 10 | 42408 | Z-Axis Crest Factor | – | uint16 | 0.001 | Unitless |
| 11 | 42458 | X-Axis Crest Factor | – | uint16 | 0.001 | Unitless |
| 12 | 42409 | Z-Axis Kurtosis | – | uint16 | 0.001 | Unitless |
| 13 | 42459 | X-Axis Kurtosis | – | uint16 | 0.001 | Unitless |
| 14–20 | 40004–40013 (simple bands) | Frequency Bands 1X–7X | – | float32 | – | Simple band RMS |
| 21–22 | 43501+ (extended bands) | Extended Band Data (Z, X) | – | float32 | – | Full spectral blocks |

**Constraint:** No additional parameters shall be read or calculated. All scaling must strictly follow official register documentation.

---

## DETERMINISTIC DATA ACQUISITION

### Read Cycle

```
Time=0:  ┌─ Read scalar values (13 registers, ~200ms)
         │  - Temperature
         │  - Z/X RMS velocity
         │  - Z/X Peak velocity
         │  - Z/X RMS acceleration
         │  - Z/X HF RMS acceleration
         │  - Z/X Crest factor
         │  - Z/X Kurtosis
         │
Time=200ms: ├─ Attempt extended band read (if supported)
         │  - Z-axis frequency block
         │  - X-axis frequency block
         │
Time=400ms: ├─ On failure, attempt simple band read
         │  - 7 frequency band values
         │
Time=500ms: ├─ Write to PLC (if Mode 2 + PLC output enabled)
         │
Time=500ms: └─ Record to audit database
            └─ Update connection health
```

**Timing:** Each cycle is deterministic. No threading or async for core reads.

---

## ADVANCED SENSOR CONFIGURATION MODULE

### Slave ID Configuration

**Location:** Register 40043 (read address), no direct write  
**Scope:** Modbus slave ID (1–247)  
**Rules:**
1. **Read-only by default** – User must enable Engineering Mode
2. **Explicit user confirmation required** for any change
3. **No background writes** – All changes logged with user ID and timestamp
4. **Disable when** field ownership is not permitted

**UI Flow:**
```
[Sensor Configuration Tab]
├─ Engineering Mode Toggle (OFF by default)
│  ├─ Password/PIN protection (optional)
│  └─ Enable/Disable button
│
├─ Slave ID Configuration (visible only if Engineering Mode = ON)
│  ├─ Current Slave ID: [Read-only display]
│  ├─ New Slave ID: [Input field, 1–247, validation]
│  ├─ Reason for Change: [Text field, required]
│  └─ [Confirm Change] [Cancel] buttons
│
├─ Change Log (visible always)
│  └─ [List of all slave ID changes with timestamp, user, reason]
```

### Threshold Configuration

**Scope:** Static numeric limits only  
**Rules:**
1. **No averaging, no filtering, no learning**
2. **Deterministic evaluation** – Same input always produces same output
3. **Cycle-based** – Evaluation happens on every read cycle
4. **User-defined and exportable** – All thresholds in configuration file

**Supported Thresholds:**

| Parameter | Comparison | Output |
|-----------|-----------|--------|
| Temperature | > upper_limit | Boolean alarm tag |
| Z RMS Velocity | > warning_limit | Numeric warning value |
| Z RMS Velocity | > alarm_limit | Numeric alarm value |
| X RMS Velocity | > warning_limit | Numeric warning value |
| X RMS Velocity | > alarm_limit | Numeric alarm value |
| Z RMS Acceleration | > limit | Boolean tag |
| X RMS Acceleration | > limit | Boolean tag |
| Z Kurtosis | > impact_threshold | Boolean tag (bearing fault indicator) |
| X Kurtosis | > impact_threshold | Boolean tag (bearing fault indicator) |

**Threshold Evaluation Logic:**
```python
def evaluate_threshold(parameter_value, threshold_config):
    """
    Deterministic threshold evaluation.
    Returns: {status: "OK"|"WARNING"|"ALARM", value: float, timestamp: ISO8601}
    """
    if parameter_value > threshold_config.alarm_limit:
        return {"status": "ALARM", "value": parameter_value}
    elif parameter_value > threshold_config.warning_limit:
        return {"status": "WARNING", "value": parameter_value}
    else:
        return {"status": "OK", "value": parameter_value}
```

**UI Flow:**
```
[Sensor Configuration Tab → Thresholds]
├─ Temperature
│  └─ Upper Limit (°C): [Input] [Save]
│
├─ Z-Axis RMS Velocity (mm/s)
│  ├─ Warning Limit: [Input] [Save]
│  └─ Alarm Limit: [Input] [Save]
│
├─ X-Axis RMS Velocity (mm/s)
│  ├─ Warning Limit: [Input] [Save]
│  └─ Alarm Limit: [Input] [Save]
│
├─ [Import from JSON] [Export to JSON]
└─ [Revert to Factory Defaults]
```

---

## PLC OUTPUT CONFIGURATION

### Tag Mapping

**Mode 1 (PLC as Source):**  
No output; middleware is read-only.

**Mode 2 (DXM1000 as Source):**  
Optional output to a secondary PLC for SCADA integration.

**Example Mapping:**
```json
{
  "plc_output_enabled": true,
  "plc_connection": {
    "address": "192.168.1.50",
    "port": 502,
    "timeout_s": 2.0
  },
  "tag_mapping": {
    "temperature_c": "Gandiva.Temperature",
    "z_rms_mm_s": "Gandiva.Z_RMS_Velocity",
    "x_rms_mm_s": "Gandiva.X_RMS_Velocity",
    "z_alarm_active": "Gandiva.Z_Alarm",
    "x_alarm_active": "Gandiva.X_Alarm",
    "connection_health": "Gandiva.Health_OK",
    "last_read_timestamp": "Gandiva.LastReadTime"
  }
}
```

---

## 7-TAB UI LAYOUT

### Tab 1: System Mode
- **Purpose:** Select PLC-as-source or DXM1000-as-source
- **Controls:**
  - Radio button: "PLC as Data Source"
  - Radio button: "DXM1000 as Data Source"
  - [Apply] [Revert to Last Known]
  - Status: Currently active mode
  - Warning: Changing mode requires system restart

### Tab 2: Source Connection
- **Purpose:** Configure active data source
- **Controls (PLC mode):**
  - PLC Type dropdown (Siemens S7, AB CompactLogix, Generic Modbus TCP, OPC-UA)
  - IP Address / Hostname
  - Port
  - Timeout (s)
  - Username/Password (if OPC-UA)
  - [Test Connection] [Connect] [Disconnect]
  
- **Controls (DXM1000 mode):**
  - DXM1000 Connection Type (Modbus TCP, Serial)
  - IP Address (Modbus TCP) or COM Port (Serial)
  - Port / Baud Rate
  - Slave ID (1–247)
  - [Test Connection] [Connect] [Disconnect]

### Tab 3: Sensor / Parameter Overview
- **Purpose:** Display real-time parameter values and status
- **Layout:**
  ```
  Temperature:     25.3 °C   [OK]
  Z RMS Velocity:  1.5 mm/s  [OK]
  X RMS Velocity:  0.8 mm/s  [OK]
  Z Peak Velocity: 3.2 mm/s  [OK]
  X Peak Velocity: 2.1 mm/s  [OK]
  Z RMS Accel:     0.05 g    [OK]
  X RMS Accel:     0.03 g    [OK]
  Z HF RMS Accel:  0.02 g    [OK]
  X HF RMS Accel:  0.01 g    [OK]
  Z Crest Factor:  4.2       [OK]
  X Crest Factor:  3.8       [OK]
  Z Kurtosis:      3.5       [OK]
  X Kurtosis:      3.2       [OK]
  Bands (Z):       [View] [Export]
  Bands (X):       [View] [Export]
  ```
- **Read Frequency Display:** "Last updated 5 seconds ago"

### Tab 4: PLC Output Configuration
- **Purpose:** Define where to write results (Mode 2 only)
- **Controls:**
  - Enable PLC Output: [Checkbox]
  - Output Destination (PLC IP, Port, Timeout)
  - [Configure Tag Mapping]
  - [Preview Mapping]
  - [Test Write]
  - Status: "Connected", "Disconnected", "Error"

### Tab 5: Tag / Register Mapping
- **Purpose:** Show register-to-parameter traceability
- **Layout:** Table with columns:
  | Register | Direct Addr | Param Name | Unit | Scale | Type | Read Count | Last Value | Status |
  |----------|----------|----------|------|-------|------|----------|----------|---------|
  | 40043 | 40043 | Temperature | °C | 0.01 | int16 | 1245 | 25.3 | OK |
  | 42403 | 42403 | Z RMS Vel. | mm/s | 0.001 | uint16 | 1245 | 1.5 | OK |
  | ... | ... | ... | ... | ... | ... | ... | ... | ... |

- **Controls:**
  - [Export as CSV]
  - [Export as JSON]
  - [Refresh Statistics]

### Tab 6: Connection Status & Diagnostics
- **Purpose:** Show health and communication metrics
- **Displays:**
  - **Source Connection:**
    - Status (Connected / Disconnected / Error)
    - Last successful read: 2s ago
    - Total reads: 5432
    - Failed reads: 2
    - Success rate: 99.96%
    - Last error: None
    - Average latency: 145ms
  
  - **PLC Output Connection (if enabled):**
    - Status (Connected / Disconnected / Error)
    - Last successful write: 3s ago
    - Total writes: 5430
    - Failed writes: 0
    - Success rate: 100%
  
  - **Slave ID Health:**
    - Current slave ID: 1
    - Last change: 2025-12-20 10:15:00 (User: admin, Reason: "Reconfiguration")
  
- **Controls:**
  - [Clear Error Log]
  - [Export Diagnostic Report]
  - [Restart Connection]

### Tab 7: System Info & Export
- **Purpose:** System metadata and configuration export
- **Displays:**
  - Application Version
  - System Start Time
  - Uptime
  - Configuration File Path
  - Database Path
  
- **Controls:**
  - [Export Configuration as JSON]
  - [Import Configuration from JSON]
  - [Export Audit Log as CSV]
  - [Factory Reset] (requires confirmation)
  - [View Changelog]

---

## CONFIGURATION MANAGEMENT

### Configuration File Structure

**File:** `gandiva_industrial_config.json`

```json
{
  "version": "1.0",
  "timestamp": "2026-01-01T10:30:00Z",
  "system_mode": "DXM1000",
  "source_connection": {
    "type": "DXM1000",
    "connection_method": "modbus_tcp",
    "host": "192.168.1.100",
    "port": 502,
    "timeout_s": 2.0,
    "slave_id": 1,
    "poll_interval_s": 1.0
  },
  "plc_output": {
    "enabled": true,
    "connection": {
      "type": "modbus_tcp",
      "host": "192.168.1.50",
      "port": 502,
      "timeout_s": 2.0
    },
    "tag_mapping": {
      "temperature_c": "Gandiva.Temperature",
      "z_rms_mm_s": "Gandiva.Z_RMS_Velocity"
    }
  },
  "thresholds": {
    "temperature_c_upper": 80.0,
    "z_rms_mm_s_warning": 3.0,
    "z_rms_mm_s_alarm": 5.0,
    "x_rms_mm_s_warning": 2.5,
    "x_rms_mm_s_alarm": 4.5,
    "z_kurtosis_impact": 6.0,
    "x_kurtosis_impact": 6.0
  },
  "engineering_mode": false,
  "audit_log_enabled": true,
  "diagnostics_export_path": "./diagnostics"
}
```

### Import/Export

**Export Steps:**
1. Gather all configuration from database
2. Include only user-facing parameters
3. Exclude internal IDs, passwords (encrypted)
4. Sign with application version and timestamp
5. Save as JSON

**Import Steps:**
1. Validate JSON schema
2. Verify version compatibility
3. Prompt user for confirmation
4. Log import action with user and timestamp
5. Apply configuration
6. Test connections

---

## CHANGE LOG AND AUDIT TRAIL

### Audit Entry Schema

```json
{
  "timestamp": "2026-01-01T10:30:15Z",
  "action": "slave_id_change",
  "user": "admin",
  "old_value": 1,
  "new_value": 2,
  "reason": "Sensor readdressed",
  "status": "success",
  "error_message": null,
  "ip_address": "192.168.1.200"
}
```

### Auditable Actions

1. **System Mode Change** – Log mode switch with user and timestamp
2. **Slave ID Change** – Log old/new slave ID, reason, user
3. **Threshold Update** – Log parameter, old/new values
4. **PLC Output Enable/Disable** – Log action and user
5. **Configuration Import** – Log file source and result
6. **Connection Failure** – Log error, register, timestamp
7. **Manual Read/Write** – Log register, value, user

---

## DIAGNOSTIC TRANSPARENCY

### Diagnostic Report (Export)

**File:** `gandiva_diagnostic_<timestamp>.json`

```json
{
  "report_timestamp": "2026-01-01T10:35:00Z",
  "system_uptime_s": 3600,
  "source_connection": {
    "status": "connected",
    "last_read_time": "2026-01-01T10:34:58Z",
    "total_reads": 3600,
    "failed_reads": 2,
    "success_rate": 0.9994,
    "avg_latency_ms": 145
  },
  "plc_output": {
    "status": "connected",
    "last_write_time": "2026-01-01T10:34:59Z",
    "total_writes": 3600,
    "failed_writes": 0
  },
  "register_statistics": [
    {
      "register": 40043,
      "param": "Temperature",
      "read_count": 3600,
      "last_value": 25.3,
      "min_value": 20.1,
      "max_value": 28.5,
      "avg_value": 24.8
    }
  ],
  "recent_errors": [
    {
      "timestamp": "2026-01-01T09:15:30Z",
      "register": 42403,
      "error": "Modbus timeout"
    }
  ]
}
```

---

## CONSTRAINTS & GUARANTEES

### Determinism

- Same sensor state → Same output every time
- No randomness in data acquisition
- No asynchronous background processes for core reads
- All timestamps deterministic per UTC

### Auditability

- Every action logged with user, timestamp, old/new values
- Change log queryable and exportable
- No silent failures
- All errors surface to UI

### Safety

- No automatic assumptions
- User must explicitly enable features
- Configuration changes require confirmation
- Field ownership enforced

### Compliance

- Vendor-neutral (works with any PLC)
- No firmware modification required
- Traceability from sensor register to PLC tag
- Exportable audit trail for compliance reviews

---

## NEXT STEPS

1. Implement data models (SystemMode, ConnectionConfig, ThresholdDefinition, SlaveIDConfig)
2. Build middleware layer for PLC/DXM1000 communication
3. Create Advanced Sensor Configuration module
4. Design and implement 7-tab UI layout
5. Implement configuration export/import
6. Build deterministic threshold evaluation engine
7. Create audit database schema
8. Implement diagnostic endpoints

---

**End of Architecture Document**
