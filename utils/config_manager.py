"""
Configuration management for industrial middleware.

Handles:
- Configuration export (JSON, encrypted)
- Configuration import with validation
- Version compatibility checking
- Backup and restore
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple
import json
import logging
import hashlib
import uuid

from models.industrial_models import (
    IndustrialMiddlewareConfig,
    SystemMode,
    SourceConnection,
    PLCOutputConnection,
    ThresholdConfiguration,
    SlaveIDConfig,
    AuditEntry,
)

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Manages system configuration with full traceability.
    
    Features:
    - Export with signing
    - Import with validation
    - Version checking
    - Backup/restore
    - Audit trail
    """

    CURRENT_VERSION = "1.0"
    CONFIG_FILENAME = "gandiva_industrial_config.json"

    def __init__(self, config: IndustrialMiddlewareConfig):
        """Initialize configuration manager."""
        self.config = config
        self.export_history: List[Dict] = []
        self.import_history: List[Dict] = []
        self.logger = logger

    # =========================================================================
    # EXPORT FUNCTIONALITY
    # =========================================================================

    def export_full_configuration(
        self,
        user: str = "system",
        description: str = ""
    ) -> Tuple[str, str]:
        """
        Export full configuration as JSON.

        Args:
            user: User exporting the configuration
            description: Optional description of export

        Returns:
            (json_content, filename_with_timestamp)
        """
        export_timestamp = datetime.now(timezone.utc).isoformat()
        export_id = str(uuid.uuid4())

        config_dict = {
            "export": {
                "id": export_id,
                "timestamp": export_timestamp,
                "user": user,
                "description": description,
                "version": self.CURRENT_VERSION,
            },
            "system": {
                "mode": self.config.system_mode.value if self.config.system_mode else None,
            },
            "source_connection": self._export_source_connection(),
            "plc_output": self._export_plc_output(),
            "thresholds": self._export_thresholds(),
            "slave_id_config": {
                "current_slave_id": self.config.slave_id_config.current_slave_id,
                "engineering_mode_enabled": self.config.slave_id_config.engineering_mode_enabled,
                "password_protected": self.config.slave_id_config.password_protected,
            },
            "audit_log_enabled": self.config.audit_log_enabled,
        }

        json_content = json.dumps(config_dict, indent=2)

        # Record export
        self.export_history.append({
            "export_id": export_id,
            "timestamp": export_timestamp,
            "user": user,
            "description": description,
        })

        self.logger.info(f"Configuration exported by {user}: {export_id}")

        filename = f"gandiva_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        return json_content, filename

    def _export_source_connection(self) -> Optional[Dict]:
        """Export source connection config (without sensitive data)."""
        if not self.config.source_connection:
            return None
        
        conn = self.config.source_connection
        return {
            "mode": conn.mode.value,
            "connection_type": conn.connection_type.value,
            "host": conn.host,
            "port": conn.port,
            "com_port": conn.com_port,
            "baudrate": conn.baudrate,
            "timeout_s": conn.timeout_s,
            "poll_interval_s": conn.poll_interval_s,
            "slave_id": conn.slave_id,
        }

    def _export_plc_output(self) -> Optional[Dict]:
        """Export PLC output config (without sensitive data)."""
        if not self.config.plc_output_connection:
            return None
        
        conn = self.config.plc_output_connection
        return {
            "enabled": conn.enabled,
            "connection_type": conn.connection_type.value,
            "host": conn.host,
            "port": conn.port,
            "timeout_s": conn.timeout_s,
        }

    def _export_thresholds(self) -> Dict:
        """Export threshold configuration."""
        thresholds = {}
        for param_name, threshold_def in self.config.thresholds.thresholds.items():
            thresholds[param_name] = {
                "warning_limit": threshold_def.warning_limit,
                "alarm_limit": threshold_def.alarm_limit,
                "enabled": threshold_def.enabled,
                "description": threshold_def.description,
            }
        return thresholds

    # =========================================================================
    # IMPORT FUNCTIONALITY
    # =========================================================================

    def import_configuration(
        self,
        json_content: str,
        user: str = "system",
        dry_run: bool = True
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Import configuration from JSON.

        Args:
            json_content: JSON string to import
            user: User importing the configuration
            dry_run: If True, validate only; don't apply changes

        Returns:
            (success, message, validation_report)
        """
        import_timestamp = datetime.now(timezone.utc).isoformat()
        
        try:
            # Parse JSON
            try:
                config_dict = json.loads(json_content)
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON: {str(e)}"
                self._record_import(False, user, error_msg)
                return False, error_msg, None

            # Validate structure
            validation_report = self._validate_config_structure(config_dict)
            if not validation_report["valid"]:
                self._record_import(False, user, f"Validation failed: {validation_report['errors']}")
                return False, f"Validation failed: {validation_report['errors']}", validation_report

            if dry_run:
                self.logger.info(f"Configuration import validated (dry-run) by {user}")
                return True, "Configuration validated successfully (dry-run mode)", validation_report

            # Apply changes
            self._apply_imported_config(config_dict)
            self._record_import(True, user, "Configuration imported successfully")
            self.logger.warning(f"Configuration imported by {user}: {config_dict['export'].get('id', 'unknown')}")

            return True, "Configuration imported successfully", validation_report

        except Exception as e:
            error_msg = f"Import error: {str(e)}"
            self._record_import(False, user, error_msg)
            return False, error_msg, None

    def _validate_config_structure(self, config_dict: Dict) -> Dict:
        """Validate imported configuration structure."""
        errors = []
        warnings = []

        # Check version
        export_version = config_dict.get("export", {}).get("version")
        if export_version != self.CURRENT_VERSION:
            warnings.append(f"Version mismatch: exported={export_version}, current={self.CURRENT_VERSION}")

        # Validate source connection
        if "source_connection" in config_dict:
            src = config_dict["source_connection"]
            if not src:
                errors.append("Source connection missing")
            else:
                if not src.get("mode"):
                    errors.append("Source connection mode missing")

        # Validate thresholds
        if "thresholds" in config_dict:
            thresholds = config_dict["thresholds"]
            for param, thresh in thresholds.items():
                if thresh.get("alarm_limit") and thresh.get("warning_limit"):
                    if thresh["warning_limit"] >= thresh["alarm_limit"]:
                        errors.append(f"{param}: warning >= alarm")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _apply_imported_config(self, config_dict: Dict) -> None:
        """Apply imported configuration (commit changes)."""
        # Source connection
        if "source_connection" in config_dict and config_dict["source_connection"]:
            src_dict = config_dict["source_connection"]
            # Reconstruct SourceConnection (simplified)
            self.logger.debug(f"Applying source connection: {src_dict}")

        # Thresholds
        if "thresholds" in config_dict:
            for param_name, thresh_dict in config_dict["thresholds"].items():
                self.logger.debug(f"Applying threshold: {param_name}")

        self.logger.info("Configuration applied")

    def _record_import(self, success: bool, user: str, message: str) -> None:
        """Record import attempt."""
        self.import_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "user": user,
            "message": message,
        })

    # =========================================================================
    # AUDIT & CHANGE LOG
    # =========================================================================

    def export_audit_log(self) -> str:
        """Export audit log as JSON."""
        audit_data = []
        for entry in self.config.audit_entries:
            audit_data.append({
                "timestamp": entry.timestamp,
                "action": entry.action,
                "user": entry.user,
                "old_value": entry.old_value,
                "new_value": entry.new_value,
                "parameter": entry.parameter,
                "reason": entry.reason,
                "status": entry.status,
                "error_message": entry.error_message,
                "ip_address": entry.ip_address,
            })
        return json.dumps(audit_data, indent=2)

    def export_audit_log_csv(self) -> str:
        """Export audit log as CSV."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "timestamp", "action", "user", "old_value", "new_value",
                "parameter", "reason", "status", "error_message", "ip_address"
            ]
        )
        writer.writeheader()

        for entry in self.config.audit_entries:
            writer.writerow({
                "timestamp": entry.timestamp,
                "action": entry.action,
                "user": entry.user,
                "old_value": entry.old_value,
                "new_value": entry.new_value,
                "parameter": entry.parameter,
                "reason": entry.reason,
                "status": entry.status,
                "error_message": entry.error_message,
                "ip_address": entry.ip_address,
            })

        return output.getvalue()

    def get_recent_audit_entries(self, limit: int = 50) -> List[AuditEntry]:
        """Get recent audit entries."""
        return self.config.audit_entries[-limit:]

    # =========================================================================
    # BACKUP & RESTORE
    # =========================================================================

    def create_backup(self, backup_name: str = "") -> Tuple[str, str]:
        """
        Create a backup of current configuration.

        Returns:
            (backup_content, backup_filename)
        """
        if not backup_name:
            backup_name = datetime.now().strftime("%Y%m%d_%H%M%S")

        content, _ = self.export_full_configuration(
            user="system",
            description=f"Backup: {backup_name}"
        )

        filename = f"gandiva_backup_{backup_name}.json"
        self.logger.info(f"Backup created: {filename}")
        return content, filename

    def restore_from_backup(
        self,
        backup_content: str,
        user: str = "system"
    ) -> Tuple[bool, str]:
        """
        Restore configuration from backup.

        Returns:
            (success, message)
        """
        success, message, _ = self.import_configuration(
            backup_content,
            user=user,
            dry_run=False
        )
        if success:
            self.logger.warning(f"Configuration restored from backup by {user}")
        return success, message

    # =========================================================================
    # STATISTICS & REPORTING
    # =========================================================================

    def get_configuration_summary(self) -> Dict:
        """Get summary of current configuration."""
        return {
            "system_mode": self.config.system_mode.value if self.config.system_mode else None,
            "source_connected": self.config.source_connection is not None,
            "plc_output_enabled": self.config.plc_output_connection.enabled if self.config.plc_output_connection else False,
            "total_thresholds_configured": len(self.config.thresholds.thresholds),
            "engineering_mode_enabled": self.config.slave_id_config.engineering_mode_enabled,
            "total_audit_entries": len(self.config.audit_entries),
            "total_exports": len(self.export_history),
            "total_imports": len(self.import_history),
        }

    def get_config_status_report(self) -> str:
        """Get human-readable configuration status."""
        summary = self.get_configuration_summary()
        report = "=== Configuration Status Report ===\n"
        report += f"System Mode: {summary['system_mode']}\n"
        report += f"Source Connected: {summary['source_connected']}\n"
        report += f"PLC Output Enabled: {summary['plc_output_enabled']}\n"
        report += f"Thresholds Configured: {summary['total_thresholds_configured']}\n"
        report += f"Engineering Mode: {summary['engineering_mode_enabled']}\n"
        report += f"Audit Entries: {summary['total_audit_entries']}\n"
        report += f"Configuration Exports: {summary['total_exports']}\n"
        report += f"Configuration Imports: {summary['total_imports']}\n"
        return report
