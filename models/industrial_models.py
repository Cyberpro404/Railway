"""
Industrial middleware data models.

Defines:
- SystemMode (PLC vs. DXM1000)
- ConnectionConfig (source and PLC output)
- ThresholdDefinition (deterministic static limits)
- SlaveIDConfig (Modbus slave ID management)
- AuditEntry (change log)
- ParameterDefinition (the 22 QM30VT2 parameters)
- DiagnosticSnapshot (health metrics)
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import json


class SystemMode(Enum):
    """Middleware system mode."""
    PLC_SOURCE = "plc_as_source"
    DXM1000_SOURCE = "dxm1000_as_source"
    UNCONFIGURED = "unconfigured"


class ConnectionType(Enum):
    """Data source connection type."""
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    OPC_UA = "opc_ua"
    SIEMENS_S7 = "siemens_s7"
    AB_COMPACTLOGIX = "ab_compactlogix"
    GENERIC_PLC = "generic_plc"


class ParameterStatus(Enum):
    """Per-parameter health status."""
    OK = "ok"
    WARNING = "warning"
    ALARM = "alarm"
    TIMEOUT = "timeout"
    ERROR = "error"


# =============================================================================
# QM30VT2 PARAMETER REGISTRY (22 Parameters - Strict Scope)
# =============================================================================

@dataclass
class QM30VT2Parameter:
    """Definition of a single QM30VT2 parameter."""
    index: int
    name: str
    register: int  # Modbus register address
    direct_address: int  # Direct address (40000 + offset)
    unit: str
    data_type: str  # "int16", "uint16", "float32"
    scale: float
    min_allowed: float
    max_allowed: float
    description: str

    def apply_scale(self, raw_value: float) -> float:
        """Apply register scaling to raw value."""
        return raw_value * self.scale


# Registry of all 22 parameters
QM30VT2_PARAMETER_REGISTRY = {
    "temperature_c": QM30VT2Parameter(
        index=1,
        name="Temperature",
        register=40043,
        direct_address=40043,
        unit="°C",
        data_type="int16",
        scale=0.01,
        min_allowed=-40.0,
        max_allowed=85.0,
        description="Sensor temperature"
    ),
    "z_rms_mm_s": QM30VT2Parameter(
        index=2,
        name="Z-Axis RMS Velocity",
        register=42403,
        direct_address=42403,
        unit="mm/s",
        data_type="uint16",
        scale=0.001,
        min_allowed=0.0,
        max_allowed=65.535,
        description="Z-axis RMS velocity"
    ),
    "x_rms_mm_s": QM30VT2Parameter(
        index=3,
        name="X-Axis RMS Velocity",
        register=42453,
        direct_address=42453,
        unit="mm/s",
        data_type="uint16",
        scale=0.001,
        min_allowed=0.0,
        max_allowed=65.535,
        description="X-axis RMS velocity"
    ),
    "z_peak_mm_s": QM30VT2Parameter(
        index=4,
        name="Z-Axis Peak Velocity",
        register=42404,
        direct_address=42404,
        unit="mm/s",
        data_type="uint16",
        scale=0.001,
        min_allowed=0.0,
        max_allowed=65.535,
        description="Z-axis peak velocity"
    ),
    "x_peak_mm_s": QM30VT2Parameter(
        index=5,
        name="X-Axis Peak Velocity",
        register=42454,
        direct_address=42454,
        unit="mm/s",
        data_type="uint16",
        scale=0.001,
        min_allowed=0.0,
        max_allowed=65.535,
        description="X-axis peak velocity"
    ),
    "z_rms_g": QM30VT2Parameter(
        index=6,
        name="Z-Axis RMS Acceleration",
        register=42406,
        direct_address=42406,
        unit="g",
        data_type="uint16",
        scale=0.001,
        min_allowed=0.0,
        max_allowed=65.535,
        description="Z-axis RMS acceleration"
    ),
    "x_rms_g": QM30VT2Parameter(
        index=7,
        name="X-Axis RMS Acceleration",
        register=42456,
        direct_address=42456,
        unit="g",
        data_type="uint16",
        scale=0.001,
        min_allowed=0.0,
        max_allowed=65.535,
        description="X-axis RMS acceleration"
    ),
    "z_hf_rms_g": QM30VT2Parameter(
        index=8,
        name="Z-Axis HF RMS Acceleration",
        register=42410,
        direct_address=42410,
        unit="g",
        data_type="uint16",
        scale=0.001,
        min_allowed=0.0,
        max_allowed=65.535,
        description="Z-axis high-frequency RMS acceleration"
    ),
    "x_hf_rms_g": QM30VT2Parameter(
        index=9,
        name="X-Axis HF RMS Acceleration",
        register=42460,
        direct_address=42460,
        unit="g",
        data_type="uint16",
        scale=0.001,
        min_allowed=0.0,
        max_allowed=65.535,
        description="X-axis high-frequency RMS acceleration"
    ),
    "z_crest_factor": QM30VT2Parameter(
        index=10,
        name="Z-Axis Crest Factor",
        register=42408,
        direct_address=42408,
        unit="–",
        data_type="uint16",
        scale=0.001,
        min_allowed=0.0,
        max_allowed=65.535,
        description="Z-axis crest factor (unitless)"
    ),
    "x_crest_factor": QM30VT2Parameter(
        index=11,
        name="X-Axis Crest Factor",
        register=42458,
        direct_address=42458,
        unit="–",
        data_type="uint16",
        scale=0.001,
        min_allowed=0.0,
        max_allowed=65.535,
        description="X-axis crest factor (unitless)"
    ),
    "z_kurtosis": QM30VT2Parameter(
        index=12,
        name="Z-Axis Kurtosis",
        register=42409,
        direct_address=42409,
        unit="–",
        data_type="uint16",
        scale=0.001,
        min_allowed=0.0,
        max_allowed=65.535,
        description="Z-axis kurtosis (unitless)"
    ),
    "x_kurtosis": QM30VT2Parameter(
        index=13,
        name="X-Axis Kurtosis",
        register=42459,
        direct_address=42459,
        unit="–",
        data_type="uint16",
        scale=0.001,
        min_allowed=0.0,
        max_allowed=65.535,
        description="X-axis kurtosis (unitless)"
    ),
    # Bands and extended bands stored as metadata; not directly read here
}


# =============================================================================
# CONNECTION CONFIGURATION
# =============================================================================

@dataclass
class SourceConnection:
    """Configuration for data source (PLC or DXM1000)."""
    mode: SystemMode
    connection_type: ConnectionType
    host: Optional[str] = None
    port: Optional[int] = None
    com_port: Optional[str] = None  # For serial connections
    baudrate: Optional[int] = None
    timeout_s: float = 2.0
    username: Optional[str] = None
    password: Optional[str] = None  # Should be encrypted at rest
    poll_interval_s: float = 1.0
    slave_id: int = 1  # Modbus slave ID (1-247)

    def validate(self) -> List[str]:
        """Validate configuration. Returns list of errors."""
        errors = []
        if self.mode == SystemMode.UNCONFIGURED:
            errors.append("System mode not configured")
        if self.timeout_s <= 0:
            errors.append("Timeout must be positive")
        if self.poll_interval_s <= 0:
            errors.append("Poll interval must be positive")
        if not (1 <= self.slave_id <= 247):
            errors.append("Slave ID must be 1-247")
        if self.connection_type == ConnectionType.MODBUS_TCP and not self.host:
            errors.append("Modbus TCP requires host")
        if self.connection_type == ConnectionType.MODBUS_RTU and not self.com_port:
            errors.append("Modbus RTU requires COM port")
        return errors


@dataclass
class PLCOutputConnection:
    """Configuration for optional PLC output (Mode 2 only)."""
    enabled: bool = False
    connection_type: ConnectionType = ConnectionType.MODBUS_TCP
    host: Optional[str] = None
    port: Optional[int] = None
    timeout_s: float = 2.0
    username: Optional[str] = None
    password: Optional[str] = None

    def validate(self) -> List[str]:
        """Validate configuration."""
        errors = []
        if not self.enabled:
            return errors
        if not self.host:
            errors.append("PLC output host required when enabled")
        if self.timeout_s <= 0:
            errors.append("PLC output timeout must be positive")
        return errors


# =============================================================================
# THRESHOLD CONFIGURATION
# =============================================================================

@dataclass
class ThresholdDefinition:
    """Static threshold for a parameter (deterministic, no learning)."""
    parameter_name: str
    warning_limit: Optional[float] = None
    alarm_limit: Optional[float] = None
    enabled: bool = True
    description: str = ""

    def evaluate(self, value: float) -> ParameterStatus:
        """Deterministic threshold evaluation."""
        if not self.enabled:
            return ParameterStatus.OK
        if self.alarm_limit is not None and value > self.alarm_limit:
            return ParameterStatus.ALARM
        if self.warning_limit is not None and value > self.warning_limit:
            return ParameterStatus.WARNING
        return ParameterStatus.OK


@dataclass
class ThresholdConfiguration:
    """Complete threshold configuration."""
    thresholds: Dict[str, ThresholdDefinition] = field(default_factory=dict)
    created_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_modified: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_threshold(self, param: str, threshold: ThresholdDefinition) -> None:
        """Add or update a threshold."""
        self.thresholds[param] = threshold
        self.last_modified = datetime.now(timezone.utc).isoformat()

    def evaluate_all(self, parameters: Dict[str, float]) -> Dict[str, ParameterStatus]:
        """Evaluate all thresholds against parameter values."""
        results = {}
        for param_name, param_value in parameters.items():
            if param_name in self.thresholds:
                results[param_name] = self.thresholds[param_name].evaluate(param_value)
            else:
                results[param_name] = ParameterStatus.OK
        return results


# =============================================================================
# SLAVE ID CONFIGURATION (ADVANCED)
# =============================================================================

@dataclass
class SlaveIDConfig:
    """Modbus slave ID configuration with change tracking."""
    current_slave_id: int = 1
    engineering_mode_enabled: bool = False
    password_protected: bool = False
    password_hash: Optional[str] = None  # SHA-256 of password if enabled
    change_log: List['SlaveIDChange'] = field(default_factory=list)

    def validate_new_slave_id(self, new_id: int) -> Optional[str]:
        """Validate new slave ID. Returns error message or None."""
        if not (1 <= new_id <= 247):
            return "Slave ID must be 1-247"
        if new_id == self.current_slave_id:
            return "New slave ID is same as current"
        return None

    def record_change(self, change: 'SlaveIDChange') -> None:
        """Record a slave ID change in the log."""
        self.change_log.append(change)


@dataclass
class SlaveIDChange:
    """Single slave ID change record."""
    timestamp: str  # ISO8601
    old_slave_id: int
    new_slave_id: int
    user: str
    reason: str
    status: str  # "pending", "success", "failed"
    error_message: Optional[str] = None
    ip_address: Optional[str] = None


# =============================================================================
# AUDIT ENTRY
# =============================================================================

@dataclass
class AuditEntry:
    """Single audit log entry (immutable)."""
    timestamp: str  # ISO8601, UTC
    action: str  # "threshold_change", "slave_id_change", "connection_change", etc.
    user: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    parameter: Optional[str] = None
    reason: Optional[str] = None
    status: str = "success"  # "success", "failed"
    error_message: Optional[str] = None
    ip_address: Optional[str] = None

    @staticmethod
    def now() -> str:
        """Get current UTC ISO8601 timestamp."""
        return datetime.now(timezone.utc).isoformat()


# =============================================================================
# DIAGNOSTIC SNAPSHOT
# =============================================================================

@dataclass
class ConnectionDiagnostic:
    """Health metrics for a connection."""
    status: str  # "connected", "disconnected", "error"
    last_successful_operation: Optional[str] = None  # ISO8601 timestamp
    total_operations: int = 0
    failed_operations: int = 0
    last_error: Optional[str] = None
    last_error_timestamp: Optional[str] = None
    avg_latency_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0-1.0)."""
        if self.total_operations == 0:
            return 0.0
        return (self.total_operations - self.failed_operations) / self.total_operations


@dataclass
class RegisterStatistic:
    """Statistics for a single register."""
    register: int
    param_name: str
    read_count: int = 0
    failed_reads: int = 0
    last_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    avg_value: Optional[float] = None


@dataclass
class DiagnosticSnapshot:
    """Complete system diagnostic snapshot."""
    report_timestamp: str  # ISO8601
    system_uptime_s: int
    source_connection: ConnectionDiagnostic
    plc_output_connection: Optional[ConnectionDiagnostic] = None
    register_statistics: Dict[str, RegisterStatistic] = field(default_factory=dict)
    recent_errors: List[Dict[str, Any]] = field(default_factory=list)
    slave_id_changes_recent: List[SlaveIDChange] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "report_timestamp": self.report_timestamp,
            "system_uptime_s": self.system_uptime_s,
            "source_connection": asdict(self.source_connection),
            "plc_output_connection": asdict(self.plc_output_connection) if self.plc_output_connection else None,
            "register_statistics": {k: asdict(v) for k, v in self.register_statistics.items()},
            "recent_errors": self.recent_errors,
            "slave_id_changes_recent": [asdict(c) for c in self.slave_id_changes_recent],
        }


# =============================================================================
# CONFIGURATION BUNDLE
# =============================================================================

@dataclass
class IndustrialMiddlewareConfig:
    """Complete configuration for the middleware system."""
    version: str = "1.0"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    system_mode: SystemMode = SystemMode.UNCONFIGURED
    source_connection: Optional[SourceConnection] = None
    plc_output_connection: Optional[PLCOutputConnection] = None
    thresholds: ThresholdConfiguration = field(default_factory=ThresholdConfiguration)
    slave_id_config: SlaveIDConfig = field(default_factory=SlaveIDConfig)
    audit_log_enabled: bool = True
    audit_entries: List[AuditEntry] = field(default_factory=list)

    def validate(self) -> List[str]:
        """Validate entire configuration."""
        errors = []
        if self.system_mode == SystemMode.UNCONFIGURED:
            errors.append("System mode not configured")
        if self.source_connection:
            errors.extend(self.source_connection.validate())
        if self.plc_output_connection:
            errors.extend(self.plc_output_connection.validate())
        return errors

    def to_json(self) -> str:
        """Export to JSON (sensitive fields excluded)."""
        config_dict = {
            "version": self.version,
            "timestamp": self.timestamp,
            "system_mode": self.system_mode.value,
            "source_connection": {
                "mode": self.source_connection.mode.value,
                "connection_type": self.source_connection.connection_type.value,
                "host": self.source_connection.host,
                "port": self.source_connection.port,
                "com_port": self.source_connection.com_port,
                "baudrate": self.source_connection.baudrate,
                "timeout_s": self.source_connection.timeout_s,
                "poll_interval_s": self.source_connection.poll_interval_s,
                "slave_id": self.source_connection.slave_id,
            } if self.source_connection else None,
            "plc_output_connection": {
                "enabled": self.plc_output_connection.enabled,
                "connection_type": self.plc_output_connection.connection_type.value,
                "host": self.plc_output_connection.host,
                "port": self.plc_output_connection.port,
                "timeout_s": self.plc_output_connection.timeout_s,
            } if self.plc_output_connection else None,
            "thresholds": {
                name: {
                    "warning_limit": t.warning_limit,
                    "alarm_limit": t.alarm_limit,
                    "enabled": t.enabled,
                    "description": t.description,
                } for name, t in self.thresholds.thresholds.items()
            },
            "slave_id_config": {
                "current_slave_id": self.slave_id_config.current_slave_id,
                "engineering_mode_enabled": self.slave_id_config.engineering_mode_enabled,
            },
            "audit_log_enabled": self.audit_log_enabled,
        }
        return json.dumps(config_dict, indent=2)
