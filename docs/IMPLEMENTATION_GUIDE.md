# Industrial Middleware Implementation Guide
## PLC-Friendly Deterministic Sensor Data Acquisition

**Version:** 1.0  
**Date:** January 1, 2026  
**Status:** Architecture & Components Complete

---

## EXECUTIVE SUMMARY

This document provides a comprehensive implementation guide for transforming the Gandiva system from an ML-driven predictive platform into a **deterministic, PLC-friendly industrial middleware** application for Banner QM30VT2 sensors.

**Key Deliverables:**
1. ✅ Architecture design document (INDUSTRIAL_MIDDLEWARE_ARCHITECTURE.md)
2. ✅ Data models (models/industrial_models.py) – SystemMode, Connections, Thresholds, SlaveID
3. ✅ Threshold evaluation engine (utils/threshold_engine.py) – Deterministic, no learning
4. ✅ Advanced Sensor Configuration (utils/advanced_sensor_config.py) – Slave ID, Engineering Mode
5. ✅ Configuration management (utils/config_manager.py) – Export/Import/Audit
6. ✅ 7-tab UI (frontend/industrial_middleware.html) – Complete layout
7. ✅ Diagnostic API endpoints (api/industrial_diagnostics_api.py) – Health, Config, Audit
8. ✅ Data models incorporating 22 QM30VT2 parameters (strict scope)

---

## COMPONENT OVERVIEW

### 1. Architecture Document
**File:** `docs/INDUSTRIAL_MIDDLEWARE_ARCHITECTURE.md`

Contains:
- System modes (PLC vs. DXM1000)
- Data scope (22 parameters, strict scaling)
- Deterministic data acquisition workflow
- Advanced Sensor Configuration requirements
- 7-tab UI specification
- Configuration management design
- Audit and change logging
- Constraints and guarantees

### 2. Data Models
**File:** `models/industrial_models.py`

Classes:
- `SystemMode` – Enum: PLC_SOURCE, DXM1000_SOURCE, UNCONFIGURED
- `ConnectionType` – Enum: MODBUS_TCP, MODBUS_RTU, OPC_UA, etc.
- `ParameterStatus` – Enum: OK, WARNING, ALARM, TIMEOUT, ERROR
- `QM30VT2Parameter` – Dataclass defining single parameter (register, scaling, limits)
- `QM30VT2_PARAMETER_REGISTRY` – Dictionary of all 22 parameters
- `SourceConnection` – Configuration for PLC or DXM1000
- `PLCOutputConnection` – Optional PLC output configuration
- `ThresholdDefinition` – Static threshold for deterministic evaluation
- `ThresholdConfiguration` – Collection of thresholds with timestamp
- `SlaveIDConfig` – Modbus slave ID with change tracking
- `SlaveIDChange` – Single change record (with user, reason, timestamp)
- `AuditEntry` – Single audit log entry (immutable)
- `ConnectionDiagnostic` – Health metrics for a connection
- `DiagnosticSnapshot` – Complete system diagnostic snapshot
- `IndustrialMiddlewareConfig` – Top-level configuration bundle

**Usage Example:**
```python
from models.industrial_models import (
    IndustrialMiddlewareConfig,
    SystemMode,
    SourceConnection,
    ConnectionType,
    ThresholdConfiguration,
)

# Create configuration
config = IndustrialMiddlewareConfig(
    system_mode=SystemMode.DXM1000_SOURCE,
    source_connection=SourceConnection(
        mode=SystemMode.DXM1000_SOURCE,
        connection_type=ConnectionType.MODBUS_TCP,
        host="192.168.1.100",
        port=502,
        slave_id=1,
    ),
)

# Validate
errors = config.validate()
if not errors:
    print("Configuration is valid")

# Export
json_str = config.to_json()
```

### 3. Deterministic Threshold Engine
**File:** `utils/threshold_engine.py`

Classes:
- `ThresholdEvaluationResult` – Result of evaluating a single parameter
- `CycleEvaluationResult` – Result of evaluating all thresholds in a cycle
- `DeterministicThresholdEngine` – Evaluation engine
- `ThresholdPLCTagGenerator` – Generates PLC output tags from results

**Guarantees:**
- Same input always produces same output
- No state, no learning, no filtering
- Deterministic cycle-based evaluation
- Full traceability of all breaches
- Factory defaults based on ISO 10816

**Usage Example:**
```python
from utils.threshold_engine import (
    DeterministicThresholdEngine,
    create_default_threshold_config,
)

# Create engine
config = create_default_threshold_config()
engine = DeterministicThresholdEngine(config)

# Update threshold
success, msg = engine.update_threshold(
    "z_rms_mm_s",
    warning_limit=2.5,
    alarm_limit=5.0,
    description="Z-axis vibration limit"
)

# Evaluate parameters
parameters = {
    "temperature_c": 25.3,
    "z_rms_mm_s": 1.8,
    "x_rms_mm_s": 1.5,
}
result = engine.evaluate_parameters(parameters)

print(f"Status: {result.overall_status}")  # OK, WARNING, or ALARM
print(f"Alarms: {result.alarm_count}")
print(f"Warnings: {result.warning_count}")

# Generate PLC tags
generator = ThresholdPLCTagGenerator()
plc_tags = generator.generate_plc_tags(result)
# Example: {"Z_RMS_MMS_Value": 1.8, "Z_RMS_MMS_Status": 0, ...}
```

### 4. Advanced Sensor Configuration
**File:** `utils/advanced_sensor_config.py`

Classes:
- `AdvancedSensorConfiguration` – Complete sensor configuration manager

**Features:**
- Engineering mode with optional password protection
- Slave ID management (1-247)
- Request/confirm/cancel workflow for changes
- Complete audit trail
- Change history export (JSON, CSV)
- Validation of all changes
- Field ownership enforcement (optional)

**Usage Example:**
```python
from models.industrial_models import SlaveIDConfig
from utils.advanced_sensor_config import AdvancedSensorConfiguration

# Initialize
config = AdvancedSensorConfiguration(
    initial_config=SlaveIDConfig(current_slave_id=1)
)

# Enable engineering mode
success, msg = config.enable_engineering_mode(
    password="mypassword",
    user="admin",
    ip_address="192.168.1.200"
)

# Request slave ID change
success, msg = config.request_slave_id_change(
    new_slave_id=2,
    reason="Sensor readdressed to avoid conflict",
    user="admin",
    ip_address="192.168.1.200"
)

# View pending change
pending = config.get_pending_change()
if pending:
    print(f"Pending: {pending.old_slave_id} → {pending.new_slave_id}")

# Confirm the change
success, msg = config.confirm_slave_id_change(
    user="admin",
    ip_address="192.168.1.200"
)

# Export history
history_json = config.export_change_history()
audit_json = config.export_audit_log()
```

### 5. Configuration Management
**File:** `utils/config_manager.py`

Classes:
- `ConfigurationManager` – Complete configuration lifecycle management

**Features:**
- Full configuration export (JSON, with signing)
- Configuration import with validation
- Version compatibility checking
- Backup and restore functionality
- Audit trail for all import/export
- Dry-run mode for imports
- CSV/JSON audit log export

**Usage Example:**
```python
from utils.config_manager import ConfigurationManager
from models.industrial_models import IndustrialMiddlewareConfig

config = IndustrialMiddlewareConfig()
mgr = ConfigurationManager(config)

# Export
json_content, filename = mgr.export_full_configuration(
    user="admin",
    description="Pre-deployment backup"
)
# Save to file

# Import with dry-run
success, msg, report = mgr.import_configuration(
    json_content=json_content,
    user="admin",
    dry_run=True  # Only validate
)

if success and report["valid"]:
    # Apply for real
    success, msg, _ = mgr.import_configuration(
        json_content=json_content,
        user="admin",
        dry_run=False
    )

# Export audit log
audit_csv = mgr.export_audit_log_csv()
```

### 6. 7-Tab UI
**File:** `frontend/industrial_middleware.html`

Tabs:
1. **System Mode** – Select PLC-as-source or DXM1000-as-source
2. **Source Connection** – Configure data source (host, port, slave ID, etc.)
3. **Sensor Overview** – Real-time display of all 22 parameters
4. **PLC Output Configuration** – Optional PLC output settings
5. **Tag / Register Mapping** – Traceability table with register → parameter mapping
6. **Connection Status & Diagnostics** – Health metrics, error log, restart controls
7. **System Info & Export** – Version info, configuration management, audit export

**Advanced Tab:**
- **Sensor Configuration** – Engineering mode, slave ID, thresholds, safety toggles

All tabs use:
- Dark theme (industrial standard)
- Responsive layout
- Status indicators (OK/Warning/Error)
- Form validation
- Export/Import controls

### 7. Diagnostic API Endpoints
**File:** `api/industrial_diagnostics_api.py`

Endpoints (all under `/api/industrial/`):

**Health & Status:**
- `GET /health/source` – Source connection health
- `GET /health/plc-output` – PLC output health
- `GET /health/system` – Overall system health

**Configuration:**
- `GET /config/status` – Current configuration status
- `GET /config/export` – Export configuration
- `POST /config/import` – Import configuration (with dry-run)

**Slave ID Management:**
- `GET /config/slave-id` – Current slave ID status
- `POST /config/slave-id/request-change` – Request change
- `POST /config/slave-id/confirm-change` – Confirm pending change
- `POST /config/slave-id/cancel-change` – Cancel pending change
- `GET /config/slave-id/history` – Change history

**Threshold Management:**
- `GET /config/thresholds` – All thresholds
- `POST /config/thresholds/update` – Update single threshold
- `POST /config/thresholds/export` – Export as JSON
- `POST /config/thresholds/import` – Import from JSON
- `POST /config/thresholds/reset` – Reset to factory defaults

**Audit Log:**
- `GET /audit/entries` – Audit log entries (with filtering)
- `GET /audit/export` – Export audit log (JSON or CSV)
- `POST /audit/clear` – Clear audit log (irreversible)

**Diagnostics:**
- `GET /diagnostics/snapshot` – Complete diagnostic snapshot
- `GET /diagnostics/export` – Export diagnostic report

**Connection Testing:**
- `POST /connection/test-source` – Test source connection
- `POST /connection/test-plc-output` – Test PLC output connection
- `POST /connection/restart` – Restart all connections

**System Info:**
- `GET /system/info` – System information
- `POST /system/reset-factory` – Factory reset (requires confirmation)

**Statistics:**
- `GET /statistics/register-reads` – Register read statistics
- `GET /statistics/threshold-evaluations` – Threshold evaluation statistics

---

## INTEGRATION CHECKLIST

### Phase 1: Data Models & Core Logic
- [x] Create `models/industrial_models.py` with all data classes
- [x] Create `utils/threshold_engine.py` with deterministic evaluation
- [x] Create `utils/advanced_sensor_config.py` with slave ID management
- [x] Create `utils/config_manager.py` with export/import

### Phase 2: UI & API Scaffolding
- [x] Create `frontend/industrial_middleware.html` with all 7 tabs
- [x] Create `api/industrial_diagnostics_api.py` with all endpoints

### Phase 3: Implementation (TODO)
- [ ] Implement sensor data acquisition (PLC and DXM1000 modes)
- [ ] Implement threshold evaluation in read cycle
- [ ] Implement PLC output tag writing
- [ ] Connect UI to backend API
- [ ] Implement connection health tracking
- [ ] Wire up configuration persistence (database)
- [ ] Implement audit log database storage
- [ ] Test all determinism guarantees
- [ ] Create integration tests

### Phase 4: Deployment
- [ ] Package application (Windows .exe, Docker)
- [ ] Documentation for system administrators
- [ ] Training for maintenance teams
- [ ] Commissioning checklist

---

## DESIGN PRINCIPLES

### 1. Determinism
- Same sensor state → Same output every time
- No randomness, no async for core reads
- Synchronous read cycle with fixed timing
- All timestamps UTC ISO8601

### 2. Auditability
- Every action logged (user, timestamp, old/new values)
- Change log queryable and exportable
- No silent failures
- All errors surface to UI
- Field ownership tracking optional but supported

### 3. PLC-First
- Works with any PLC vendor
- No firmware modification required
- Strict register-to-tag mapping
- Simple data types (boolean, numeric)
- Configurable output tags

### 4. Scope Control
- Only 22 documented QM30VT2 parameters
- No additional analytics or derived values
- Strict scaling per register documentation
- No ML, no inference, no prediction

### 5. Configuration as Code
- All configuration exportable as JSON
- Version-controlled backups
- Import with validation
- Dry-run mode for testing

---

## NEXT STEPS FOR IMPLEMENTATION

### Step 1: Set Up Basic Middleware Layer
Create a new module `core/industrial_middleware.py` that:
- Reads from data source (PLC or DXM1000)
- Applies threshold evaluation
- Optionally writes to PLC output
- Tracks connection health
- Records audit entries

### Step 2: Implement Data Source Drivers
Create mode-specific drivers:
- `core/plc_reader.py` – Reads from PLC (Modbus TCP, OPC-UA, etc.)
- `core/dxm1000_reader.py` – Polls DXM1000 (Modbus TCP/RTU)

Both must:
- Return dict with 22 parameters
- Track read latency
- Record connection health
- Log errors deterministically

### Step 3: Integrate with Sensor Read Cycle
Modify `main.py` polling loop to:
- Call middleware layer instead of direct sensor reads
- Run threshold evaluation
- Generate PLC tags
- Record audit entries
- Update diagnostics

### Step 4: Implement PLC Output
Create `core/plc_writer.py` that:
- Writes threshold results to PLC
- Handles write failures gracefully
- Tracks write latency
- Logs all writes to audit

### Step 5: Connect UI to Backend
Update `frontend/industrial_middleware.html` to:
- Call `/api/industrial/` endpoints
- Populate tabs with real data
- Enable form submissions
- Show live status updates

### Step 6: Database Persistence
Create tables for:
- Configuration snapshots
- Audit log entries
- Connection diagnostics
- Threshold evaluation history

### Step 7: Testing & Validation
- Unit tests for threshold engine
- Integration tests for data flow
- Determinism verification (same input → same output)
- PLC communication tests

---

## EXAMPLE: Complete Data Flow

```
┌─ Read Cycle Starts (every 5 seconds)
│
├─ Source Connection (PLC or DXM1000)
│  ├─ Read 22 QM30VT2 parameters
│  ├─ Apply register scaling
│  ├─ Return {temp_c: 25.3, z_rms_mm_s: 1.5, ...}
│  └─ Record connection health (success/failure, latency)
│
├─ Threshold Evaluation
│  ├─ Compare each parameter to thresholds
│  ├─ Determine status (OK, Warning, Alarm)
│  ├─ Log any breaches to audit trail
│  └─ Return {z_rms_mm_s: {status: OK, value: 1.5}, ...}
│
├─ PLC Output (if enabled)
│  ├─ Generate PLC tags from threshold results
│  ├─ Write tags to output PLC
│  ├─ Record write health
│  └─ Log all writes to audit
│
├─ Audit Logging
│  ├─ Record threshold evaluations
│  ├─ Log any errors
│  ├─ Track slave ID changes
│  └─ Persist to database
│
├─ Diagnostics Update
│  ├─ Update connection health stats
│  ├─ Update register read count
│  ├─ Calculate success rate
│  └─ Update last error info
│
└─ API Available
   ├─ GET /api/industrial/health/source
   ├─ GET /api/industrial/diagnostics/snapshot
   ├─ GET /api/industrial/config/slave-id
   └─ GET /api/industrial/audit/entries
```

---

## CONFIGURATION EXAMPLE

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
    "poll_interval_s": 5.0
  },
  "plc_output": {
    "enabled": true,
    "connection": {
      "type": "modbus_tcp",
      "host": "192.168.1.50",
      "port": 502,
      "timeout_s": 2.0
    }
  },
  "thresholds": {
    "temperature_c_upper": 80.0,
    "z_rms_mm_s_warning": 2.3,
    "z_rms_mm_s_alarm": 7.1,
    "x_rms_mm_s_warning": 2.3,
    "x_rms_mm_s_alarm": 7.1
  },
  "engineering_mode": false,
  "audit_log_enabled": true
}
```

---

## CONCLUSION

This implementation delivers a **deterministic, PLC-friendly industrial middleware system** for Banner QM30VT2 sensors with:

✅ Strict data scope (22 parameters)  
✅ Deterministic threshold evaluation  
✅ Advanced sensor configuration with auditing  
✅ Full configuration export/import  
✅ 7-tab professional UI  
✅ Comprehensive diagnostic API  
✅ No ML, no inference, no hidden automation  

The architecture is **vendor-neutral**, **fully auditable**, and ready for integration with any PLC system.

---

**End of Implementation Guide**
