"""
Enhanced Database Schema for Railway Rolling Stock Condition Monitoring System.
Supports multi-DXM, defect detection, intelligent alerts, and event logging.
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, 
    ForeignKey, Enum, JSON, Index, LargeBinary
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
import enum
import logging

logger = logging.getLogger(__name__)
Base = declarative_base()


class AlertSeverity(enum.Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(enum.Enum):
    """Alert lifecycle status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class ConnectionType(enum.Enum):
    """Connection types for DXM devices"""
    TCP = "tcp"
    SERIAL = "serial"


class DefectType(enum.Enum):
    """Types of detected defects"""
    WHEEL_FLAT = "wheel_flat"
    BEARING_OUTER_RACE = "bearing_outer_race"
    BEARING_INNER_RACE = "bearing_inner_race"
    BEARING_BALL = "bearing_ball"
    IMBALANCE = "imbalance"
    MISALIGNMENT = "misalignment"
    LOOSENESS = "looseness"
    GEAR_FAULT = "gear_fault"


class Device(Base):
    """DXM Device registry"""
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    location = Column(String)
    coach_id = Column(String, index=True)
    sensor_type = Column(String, default="QM30VT2")
    
    # Connection settings
    primary_connection = Column(Enum(ConnectionType), default=ConnectionType.TCP)
    tcp_host = Column(String)
    tcp_port = Column(Integer, default=502)
    serial_port = Column(String)
    serial_baud = Column(Integer, default=19200)
    slave_id = Column(Integer, default=1)
    failover_enabled = Column(Boolean, default=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), 
                       onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    raw_data = relationship("RawData", back_populates="device", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="device", cascade="all, delete-orphan")
    
    __table_args__ = (Index('idx_device_coach', 'coach_id', 'device_id'),)


class RawData(Base):
    """Raw sensor data from all devices (high-resolution logging)"""
    __tablename__ = "raw_data"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Vibration data
    z_rms = Column(Float)
    z_rms_mm = Column(Float)
    x_rms = Column(Float)
    x_rms_mm = Column(Float)
    z_peak = Column(Float)
    x_peak = Column(Float)
    z_accel = Column(Float)
    x_accel = Column(Float)
    z_rms_accel = Column(Float)
    x_rms_accel = Column(Float)
    
    # Advanced metrics
    z_kurtosis = Column(Float)
    x_kurtosis = Column(Float)
    z_crest_factor = Column(Float)
    x_crest_factor = Column(Float)
    z_hf_rms_accel = Column(Float)
    x_hf_rms_accel = Column(Float)
    
    # Environmental
    temperature = Column(Float)
    temp_f = Column(Float)
    
    # Frequency data
    z_peak_freq = Column(Float)
    x_peak_freq = Column(Float)
    
    # Connection metadata
    connection_type = Column(Enum(ConnectionType))
    response_time_ms = Column(Float)
    data_quality = Column(Float)
    
    # Raw registers (for debugging)
    raw_registers = Column(JSON)
    
    # Relationship
    device = relationship("Device", back_populates="raw_data")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_raw_data_time_range', 'device_id', 'timestamp'),
        Index('idx_raw_data_timestamp', 'timestamp'),
    )


class ProcessedData(Base):
    """Processed and normalized sensor data"""
    __tablename__ = "processed_data"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=False, index=True)
    raw_data_id = Column(Integer, ForeignKey("raw_data.id"))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Normalized values
    z_rms_normalized = Column(Float)
    x_rms_normalized = Column(Float)
    temperature_compensated = Column(Float)
    
    # Baseline references
    z_rms_baseline = Column(Float)
    x_rms_baseline = Column(Float)
    baseline_window_size = Column(Integer)
    
    # Speed normalization (if train speed available)
    train_speed_kmh = Column(Float)
    speed_normalized = Column(Boolean, default=False)
    
    # Derived metrics
    overall_rms = Column(Float)
    vibration_trend = Column(Float)
    temperature_trend = Column(Float)
    
    # Spectral bands (if available)
    spectral_band_1 = Column(Float)  # 1-10 Hz
    spectral_band_2 = Column(Float)  # 10-50 Hz
    spectral_band_3 = Column(Float)  # 50-100 Hz
    spectral_band_4 = Column(Float)  # 100-500 Hz
    spectral_band_5 = Column(Float)  # 500+ Hz
    
    # Health scores
    bearing_health = Column(Float)
    overall_health = Column(Float)


class DefectDetection(Base):
    """Defect detection results"""
    __tablename__ = "defect_detections"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Detection results
    defect_type = Column(Enum(DefectType), nullable=False)
    confidence_score = Column(Float, nullable=False)  # 0-100%
    severity_level = Column(Integer, nullable=False)  # 1-5
    
    # Detection parameters
    detected_frequency = Column(Float)
    amplitude = Column(Float)
    threshold_exceeded = Column(Float)
    
    # Supporting data
    supporting_metrics = Column(JSON)  # Dict of metrics that triggered detection
    spectral_signature = Column(JSON)  # Spectral analysis data
    
    # Validation
    validated = Column(Boolean, default=False)
    validated_by = Column(String)
    validated_at = Column(DateTime)
    notes = Column(Text)
    
    __table_args__ = (
        Index('idx_defect_device_time', 'device_id', 'timestamp'),
        Index('idx_defect_type', 'defect_type', 'confidence_score'),
    )


class Alert(Base):
    """Enhanced alert system with lifecycle management"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String, nullable=False, index=True)  # threshold, defect, system
    severity = Column(Enum(AlertSeverity), nullable=False, index=True)
    status = Column(Enum(AlertStatus), default=AlertStatus.ACTIVE, index=True)
    
    # Source
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=True)
    defect_detection_id = Column(Integer, ForeignKey("defect_detections.id"), nullable=True)
    
    # Alert details
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    parameter = Column(String)
    current_value = Column(Float)
    threshold_value = Column(Float)
    
    # Hysteresis tracking
    hysteresis_low = Column(Float)  # Lower threshold for clearing
    hysteresis_high = Column(Float)  # Upper threshold for triggering
    
    # Aggregation
    aggregation_group = Column(String)  # Group related alerts
    related_alerts = Column(JSON)  # List of related alert IDs
    occurrence_count = Column(Integer, default=1)
    first_occurrence = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_occurrence = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Acknowledgment
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String)
    acknowledged_at = Column(DateTime)
    acknowledgment_notes = Column(Text)
    
    # Resolution
    resolved_at = Column(DateTime)
    resolved_by = Column(String)
    resolution_notes = Column(Text)
    
    # Notifications
    notifications_sent = Column(JSON, default=list)  # List of notification attempts
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_alert_status_time', 'status', 'created_at'),
        Index('idx_alert_device_active', 'device_id', 'status'),
    )


class Event(Base):
    """System and sensor events (high-resolution event logging)"""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)  # anomaly, connection_change, threshold_breach
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Event details
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.INFO)
    description = Column(Text)
    
    # Context data (10 seconds before/after)
    pre_event_data = Column(JSON)  # Array of data points before event
    post_event_data = Column(JSON)  # Array of data points after event
    event_snapshot = Column(JSON)  # Full data at event moment
    
    # Related entities
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    defect_id = Column(Integer, ForeignKey("defect_detections.id"), nullable=True)
    
    # Metadata
    event_metadata = Column(JSON)
    
    # Relationship
    device = relationship("Device", back_populates="events")
    
    __table_args__ = (
        Index('idx_event_device_time', 'device_id', 'timestamp'),
        Index('idx_event_type_time', 'event_type', 'timestamp'),
    )


class SystemStatus(Base):
    """System health and status logging"""
    __tablename__ = "system_status"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # CPU/Memory metrics
    cpu_percent = Column(Float)
    memory_percent = Column(Float)
    memory_available_mb = Column(Float)
    
    # Disk metrics
    disk_percent = Column(Float)
    disk_free_gb = Column(Float)
    
    # Network metrics
    network_sent_mb = Column(Float)
    network_recv_mb = Column(Float)
    network_errors = Column(Integer)
    
    # Application metrics
    active_connections = Column(Integer)
    websocket_clients = Column(Integer)
    database_size_mb = Column(Float)
    
    # Component health
    acquisition_health = Column(Float)
    processing_health = Column(Float)
    storage_health = Column(Float)
    api_health = Column(Float)
    
    # Log aggregation
    error_count_last_hour = Column(Integer)
    warning_count_last_hour = Column(Integer)


class ThresholdConfig(Base):
    """Configurable thresholds per device and parameter"""
    __tablename__ = "threshold_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=True)  # NULL = global default
    parameter = Column(String, nullable=False, index=True)
    
    # Threshold values
    warning_low = Column(Float)
    warning_high = Column(Float)
    critical_low = Column(Float)
    critical_high = Column(Float)
    
    # Hysteresis
    hysteresis = Column(Float, default=0.1)  # 10% hysteresis by default
    
    # Defect-specific thresholds
    defect_type = Column(Enum(DefectType), nullable=True)
    
    # Adaptive settings
    adaptive_enabled = Column(Boolean, default=False)
    adaptive_window_minutes = Column(Integer, default=60)
    adaptive_sigma = Column(Float, default=3.0)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_threshold_device_param', 'device_id', 'parameter'),
    )


class DataExport(Base):
    """Data export tracking"""
    __tablename__ = "data_exports"
    
    id = Column(Integer, primary_key=True, index=True)
    export_id = Column(String, unique=True, nullable=False)
    
    # Export parameters
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    device_ids = Column(JSON)  # List of devices or None for all
    data_types = Column(JSON)  # List: raw, processed, events, alerts
    format = Column(String, default="csv")  # csv, json
    
    # Status
    status = Column(String, default="pending")  # pending, processing, completed, failed
    progress_percent = Column(Float, default=0.0)
    
    # File info
    file_path = Column(String)
    file_size_bytes = Column(Integer)
    row_count = Column(Integer)
    
    # Request info
    requested_by = Column(String)
    requested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime)
    error_message = Column(Text)


class NotificationConfig(Base):
    """Notification settings"""
    __tablename__ = "notification_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    notification_type = Column(String, nullable=False)  # email, sms, webhook
    
    # SMTP settings for email
    smtp_host = Column(String)
    smtp_port = Column(Integer, default=587)
    smtp_username = Column(String)
    smtp_password = Column(String)  # Should be encrypted in production
    smtp_tls = Column(Boolean, default=True)
    from_address = Column(String)
    
    # SMS settings (Twilio)
    twilio_account_sid = Column(String)
    twilio_auth_token = Column(String)  # Should be encrypted
    twilio_from_number = Column(String)
    
    # Webhook settings
    webhook_url = Column(String)
    webhook_headers = Column(JSON)
    
    # Alert filtering
    min_severity = Column(Enum(AlertSeverity), default=AlertSeverity.WARNING)
    alert_types = Column(JSON)  # List of alert types to notify
    device_filter = Column(JSON)  # List of device IDs or None for all
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Database setup functions
def create_enhanced_engine(db_url: str = "sqlite:///./railway_monitoring.db"):
    """Create database engine with optimized settings"""
    engine = create_engine(
        db_url,
        connect_args={
            "check_same_thread": False,
            "timeout": 30
        },
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )
    return engine


def init_enhanced_db(engine):
    """Initialize all tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Enhanced database initialized")


def get_session_factory(engine):
    """Get session factory"""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
