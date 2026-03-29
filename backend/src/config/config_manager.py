"""
Configuration Manager - JSON/YAML config loading and validation.
"""
import logging
import yaml
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field, asdict
from pydantic import BaseModel, Field, validator
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

logger = logging.getLogger(__name__)


class DXMDeviceConfig(BaseModel):
    """Configuration for a single DXM device"""
    device_id: str
    name: str
    location: str = ""
    coach_id: str = ""
    sensor_type: str = "QM30VT2"
    
    # Connection settings
    primary_connection: str = "tcp"  # tcp or serial
    tcp_host: str = "192.168.1.100"
    tcp_port: int = 502
    serial_port: str = "COM3"
    serial_baud: int = 19200
    slave_id: int = 1
    failover_enabled: bool = True


class ProcessingConfigModel(BaseModel):
    """Signal processing configuration"""
    baseline_window_size: int = 300
    temp_compensation_enabled: bool = True
    temp_reference: float = 25.0
    temp_coefficient: float = 0.02
    speed_normalization_enabled: bool = False
    reference_speed_kmh: float = 60.0


class DefectDetectionConfig(BaseModel):
    """Defect detection thresholds"""
    wheel_flat_kurtosis_threshold: float = 3.0
    wheel_flat_peak_threshold: float = 10.0
    bearing_hf_threshold: float = 2.0
    bearing_kurtosis_threshold: float = 3.5
    imbalance_rms_threshold: float = 4.0
    min_confidence: float = 60.0


class AlertRuleConfig(BaseModel):
    """Alert rule configuration"""
    alert_type: str  # threshold, defect, connectivity
    severity: str  # info, warning, critical
    parameter: Optional[str] = None
    defect_type: Optional[str] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    hysteresis: float = 0.1
    notify_email: bool = True
    notify_sms: bool = False


class EmailNotificationConfig(BaseModel):
    """Email notification settings"""
    enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    from_address: str = ""


class SMSNotificationConfig(BaseModel):
    """SMS notification settings"""
    enabled: bool = False
    account_sid: str = ""
    auth_token: str = ""
    from_number: str = ""


class NotificationContactConfig(BaseModel):
    """Contact for notifications"""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    roles: List[str] = Field(default_factory=lambda: ["operator"])
    notify_sms: bool = False
    notify_email: bool = True


class SystemConfig(BaseModel):
    """Main system configuration"""
    # System settings
    system_name: str = "Railway Rolling Stock Monitoring"
    polling_interval_seconds: float = 1.0
    data_retention_days: int = 90
    
    # Devices
    devices: List[DXMDeviceConfig] = Field(default_factory=list)
    
    # Processing
    processing: ProcessingConfigModel = Field(default_factory=ProcessingConfigModel)
    
    # Defect detection
    defect_detection: DefectDetectionConfig = Field(default_factory=DefectDetectionConfig)
    
    # Alert rules
    alert_rules: List[AlertRuleConfig] = Field(default_factory=list)
    
    # Notifications
    email: EmailNotificationConfig = Field(default_factory=EmailNotificationConfig)
    sms: SMSNotificationConfig = Field(default_factory=SMSNotificationConfig)
    contacts: List[NotificationContactConfig] = Field(default_factory=list)
    
    # Database
    database_url: str = "sqlite:///./railway_monitoring.db"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    @validator('devices')
    def validate_devices(cls, v):
        """Ensure at least one device is configured"""
        if not v:
            logger.warning("No devices configured")
        return v


class ConfigFileHandler(FileSystemEventHandler):
    """Watchdog handler for config file changes"""
    
    def __init__(self, config_manager: 'ConfigManager'):
        self.config_manager = config_manager
        self._debounce_timer: Optional[threading.Timer] = None
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path == str(self.config_manager.config_path):
            # Debounce rapid file changes
            if self._debounce_timer:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(1.0, self._reload_config)
            self._debounce_timer.start()
    
    def _reload_config(self):
        logger.info("Config file changed, reloading...")
        self.config_manager.reload_config()


class ConfigManager:
    """
    Configuration manager with file watching and hot-reload support.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config: SystemConfig = SystemConfig()
        self._observer: Optional[Observer] = None
        self._reload_callbacks: List[callable] = []
        
        # Load initial config
        self.load_config()
    
    def load_config(self) -> SystemConfig:
        """Load configuration from file"""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            logger.info("Creating default configuration...")
            self._create_default_config()
            return self.config
        
        try:
            with open(self.config_path, 'r') as f:
                if self.config_path.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            self.config = SystemConfig.parse_obj(data)
            logger.info(f"Configuration loaded from {self.config_path}")
            
            # Validate configuration
            self._validate_config()
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            logger.warning("Using default configuration")
        
        return self.config
    
    def reload_config(self) -> SystemConfig:
        """Reload configuration from file (hot-reload)"""
        old_config = self.config.copy() if hasattr(self.config, 'copy') else None
        
        self.load_config()
        
        # Notify callbacks
        for callback in self._reload_callbacks:
            try:
                callback(self.config, old_config)
            except Exception as e:
                logger.error(f"Config reload callback failed: {e}")
        
        return self.config
    
    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            data = self.config.dict()
            
            with open(self.config_path, 'w') as f:
                if self.config_path.suffix in ['.yaml', '.yml']:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
                else:
                    json.dump(data, f, indent=2)
            
            logger.info(f"Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def start_file_watching(self):
        """Start watching config file for changes"""
        if self._observer:
            return
        
        handler = ConfigFileHandler(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.config_path.parent), recursive=False)
        self._observer.start()
        
        logger.info(f"Started watching config file: {self.config_path}")
    
    def stop_file_watching(self):
        """Stop watching config file"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Stopped config file watching")
    
    def on_reload(self, callback: callable):
        """Register callback for config reload events"""
        self._reload_callbacks.append(callback)
    
    def get_device_config(self, device_id: str) -> Optional[DXMDeviceConfig]:
        """Get configuration for specific device"""
        for device in self.config.devices:
            if device.device_id == device_id:
                return device
        return None
    
    def add_device(self, device_config: DXMDeviceConfig) -> bool:
        """Add a new device configuration"""
        # Check for duplicates
        if self.get_device_config(device_config.device_id):
            logger.warning(f"Device {device_config.device_id} already exists")
            return False
        
        self.config.devices.append(device_config)
        return self.save_config()
    
    def remove_device(self, device_id: str) -> bool:
        """Remove a device configuration"""
        original_len = len(self.config.devices)
        self.config.devices = [d for d in self.config.devices if d.device_id != device_id]
        
        if len(self.config.devices) < original_len:
            return self.save_config()
        return False
    
    def update_device(self, device_id: str, updates: Dict[str, Any]) -> bool:
        """Update device configuration"""
        device = self.get_device_config(device_id)
        if not device:
            return False
        
        for key, value in updates.items():
            if hasattr(device, key):
                setattr(device, key, value)
        
        return self.save_config()
    
    def _create_default_config(self):
        """Create default configuration file"""
        self.config = SystemConfig(
            devices=[
                DXMDeviceConfig(
                    device_id="DXM-001",
                    name="Coach 1 Axle Box 1",
                    location="Coach 1 - Axle 1",
                    coach_id="C001",
                    primary_connection="tcp",
                    tcp_host="192.168.1.100"
                )
            ],
            alert_rules=[
                AlertRuleConfig(
                    alert_type="threshold",
                    severity="warning",
                    parameter="z_rms_mm",
                    warning_threshold=2.0,
                    critical_threshold=4.0
                ),
                AlertRuleConfig(
                    alert_type="threshold",
                    severity="warning",
                    parameter="temperature",
                    warning_threshold=50.0,
                    critical_threshold=70.0
                )
            ],
            contacts=[
                NotificationContactConfig(
                    name="Maintenance Team",
                    email="maintenance@railway.com",
                    roles=["operator", "admin"]
                )
            ]
        )
        
        self.save_config()
    
    def _validate_config(self):
        """Validate configuration settings"""
        # Check for device ID uniqueness
        device_ids = [d.device_id for d in self.config.devices]
        if len(device_ids) != len(set(device_ids)):
            logger.error("Duplicate device IDs found in configuration")
        
        # Validate connection settings
        for device in self.config.devices:
            if device.primary_connection not in ['tcp', 'serial']:
                logger.warning(f"Invalid primary_connection for {device.device_id}: {device.primary_connection}")
        
        logger.info("Configuration validation complete")
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export configuration to dictionary"""
        return self.config.dict()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for display"""
        return {
            "system_name": self.config.system_name,
            "device_count": len(self.config.devices),
            "polling_interval": self.config.polling_interval_seconds,
            "data_retention_days": self.config.data_retention_days,
            "email_enabled": self.config.email.enabled,
            "sms_enabled": self.config.sms.enabled,
            "contact_count": len(self.config.contacts),
            "alert_rule_count": len(self.config.alert_rules)
        }
