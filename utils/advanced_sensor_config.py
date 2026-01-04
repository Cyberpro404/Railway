"""
Advanced Sensor Configuration Module.

Manages Modbus slave ID configuration, engineering mode, and change logging.
All changes are audited and require explicit user confirmation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Tuple
import logging
import hashlib

from models.industrial_models import (
    SlaveIDConfig,
    SlaveIDChange,
    AuditEntry,
)

logger = logging.getLogger(__name__)


class AdvancedSensorConfiguration:
    """
    Manages advanced sensor configuration with strict auditability.
    
    Features:
    - Explicit Modbus slave ID configuration (1-247)
    - Engineering mode with optional password protection
    - Complete change history with user attribution
    - Validation of all changes
    - Optional field ownership enforcement
    """

    def __init__(self, initial_config: SlaveIDConfig):
        """Initialize configuration manager."""
        self.config = initial_config
        self.audit_log: List[AuditEntry] = []
        self.logger = logger
        self.field_ownership_required = False  # Can be set externally

    # =========================================================================
    # ENGINEERING MODE MANAGEMENT
    # =========================================================================

    def enable_engineering_mode(
        self,
        password: Optional[str] = None,
        user: str = "system",
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Enable engineering mode.

        Args:
            password: Optional password for protection (will be hashed)
            user: User enabling mode (for audit)
            ip_address: IP address of user (for audit)

        Returns:
            (success, message)
        """
        if self.config.engineering_mode_enabled:
            return False, "Engineering mode already enabled"

        if self.field_ownership_required:
            return False, "Field ownership permission required (not granted)"

        old_state = self.config.engineering_mode_enabled
        self.config.engineering_mode_enabled = True

        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            self.config.password_hash = password_hash
            self.config.password_protected = True
            self.logger.info(f"Engineering mode enabled with password protection by {user}")
        else:
            self.config.password_protected = False
            self.logger.info(f"Engineering mode enabled without password by {user}")

        self._audit(
            action="engineering_mode_enable",
            user=user,
            old_value=str(old_state),
            new_value=str(True),
            status="success",
            ip_address=ip_address,
        )

        return True, "Engineering mode enabled"

    def disable_engineering_mode(
        self,
        user: str = "system",
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Disable engineering mode."""
        if not self.config.engineering_mode_enabled:
            return False, "Engineering mode not currently enabled"

        old_state = self.config.engineering_mode_enabled
        self.config.engineering_mode_enabled = False
        self.config.password_protected = False
        self.config.password_hash = None

        self.logger.info(f"Engineering mode disabled by {user}")

        self._audit(
            action="engineering_mode_disable",
            user=user,
            old_value=str(old_state),
            new_value=str(False),
            status="success",
            ip_address=ip_address,
        )

        return True, "Engineering mode disabled"

    def verify_password(self, password: str) -> bool:
        """Verify engineering mode password."""
        if not self.config.password_protected or not self.config.password_hash:
            return True  # No password protection

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == self.config.password_hash

    # =========================================================================
    # SLAVE ID MANAGEMENT
    # =========================================================================

    def request_slave_id_change(
        self,
        new_slave_id: int,
        reason: str,
        user: str,
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Request a slave ID change (creates pending change).

        Args:
            new_slave_id: New slave ID (1-247)
            reason: Reason for change (required for auditability)
            user: User requesting change
            ip_address: IP address of user

        Returns:
            (success, message)
        """
        if not self.config.engineering_mode_enabled:
            return False, "Engineering mode must be enabled to change slave ID"

        if self.field_ownership_required:
            return False, "Field ownership permission required"

        # Validate new slave ID
        error = self.config.validate_new_slave_id(new_slave_id)
        if error:
            self._audit(
                action="slave_id_change_request",
                user=user,
                old_value=str(self.config.current_slave_id),
                new_value=str(new_slave_id),
                reason=reason,
                status="failed",
                error_message=error,
                ip_address=ip_address,
            )
            return False, error

        if not reason or len(reason.strip()) == 0:
            return False, "Reason for change is required"

        # Create change record
        change = SlaveIDChange(
            timestamp=datetime.now(timezone.utc).isoformat(),
            old_slave_id=self.config.current_slave_id,
            new_slave_id=new_slave_id,
            user=user,
            reason=reason,
            status="pending",
            ip_address=ip_address,
        )

        self.config.record_change(change)

        self.logger.info(
            f"Slave ID change requested: {self.config.current_slave_id} → {new_slave_id} "
            f"(Reason: {reason}, User: {user})"
        )

        self._audit(
            action="slave_id_change_request",
            user=user,
            old_value=str(self.config.current_slave_id),
            new_value=str(new_slave_id),
            reason=reason,
            status="pending",
            ip_address=ip_address,
        )

        return True, f"Slave ID change requested: {self.config.current_slave_id} → {new_slave_id}"

    def confirm_slave_id_change(
        self,
        user: str,
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Confirm and apply the pending slave ID change.

        Args:
            user: User confirming the change
            ip_address: IP address of user

        Returns:
            (success, message)
        """
        if not self.config.change_log:
            return False, "No pending slave ID change"

        # Get the most recent pending change
        pending_change = None
        for change in reversed(self.config.change_log):
            if change.status == "pending":
                pending_change = change
                break

        if not pending_change:
            return False, "No pending slave ID change to confirm"

        old_id = self.config.current_slave_id
        new_id = pending_change.new_slave_id

        try:
            # Apply the change
            self.config.current_slave_id = new_id
            pending_change.status = "success"
            pending_change.ip_address = ip_address

            self.logger.warning(
                f"Slave ID changed: {old_id} → {new_id} by {user} "
                f"(Reason: {pending_change.reason})"
            )

            self._audit(
                action="slave_id_change_confirmed",
                user=user,
                old_value=str(old_id),
                new_value=str(new_id),
                reason=pending_change.reason,
                status="success",
                ip_address=ip_address,
            )

            return True, f"Slave ID changed: {old_id} → {new_id}"

        except Exception as e:
            pending_change.status = "failed"
            pending_change.error_message = str(e)
            self.logger.error(f"Failed to apply slave ID change: {e}")
            self._audit(
                action="slave_id_change_confirmed",
                user=user,
                old_value=str(old_id),
                new_value=str(new_id),
                status="failed",
                error_message=str(e),
                ip_address=ip_address,
            )
            return False, f"Failed to apply change: {e}"

    def cancel_pending_change(
        self,
        user: str,
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Cancel a pending slave ID change."""
        if not self.config.change_log:
            return False, "No pending changes"

        # Find and cancel the most recent pending change
        for change in reversed(self.config.change_log):
            if change.status == "pending":
                change.status = "cancelled"
                self.logger.info(f"Pending slave ID change cancelled by {user}")
                self._audit(
                    action="slave_id_change_cancelled",
                    user=user,
                    old_value=str(change.old_slave_id),
                    new_value=str(change.new_slave_id),
                    status="success",
                    ip_address=ip_address,
                )
                return True, "Pending change cancelled"

        return False, "No pending changes to cancel"

    def get_current_slave_id(self) -> int:
        """Get the current slave ID."""
        return self.config.current_slave_id

    # =========================================================================
    # CHANGE HISTORY & AUDIT
    # =========================================================================

    def get_change_history(self, limit: Optional[int] = None) -> List[SlaveIDChange]:
        """Get slave ID change history."""
        history = self.config.change_log
        if limit:
            return history[-limit:]
        return history

    def get_pending_change(self) -> Optional[SlaveIDChange]:
        """Get the pending slave ID change, if any."""
        for change in reversed(self.config.change_log):
            if change.status == "pending":
                return change
        return None

    def export_change_history(self) -> str:
        """Export change history as JSON."""
        import json
        changes = []
        for change in self.config.change_log:
            changes.append({
                "timestamp": change.timestamp,
                "old_slave_id": change.old_slave_id,
                "new_slave_id": change.new_slave_id,
                "user": change.user,
                "reason": change.reason,
                "status": change.status,
                "error_message": change.error_message,
                "ip_address": change.ip_address,
            })
        return json.dumps(changes, indent=2)

    def export_audit_log(self) -> str:
        """Export audit log as JSON."""
        import json
        entries = []
        for entry in self.audit_log:
            entries.append({
                "timestamp": entry.timestamp,
                "action": entry.action,
                "user": entry.user,
                "old_value": entry.old_value,
                "new_value": entry.new_value,
                "reason": entry.reason,
                "status": entry.status,
                "error_message": entry.error_message,
                "ip_address": entry.ip_address,
            })
        return json.dumps(entries, indent=2)

    # =========================================================================
    # INTERNAL AUDIT LOGGING
    # =========================================================================

    def _audit(
        self,
        action: str,
        user: str,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        reason: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Internal method to record audit entry."""
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            user=user,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            status=status,
            error_message=error_message,
            ip_address=ip_address,
        )
        self.audit_log.append(entry)

    # =========================================================================
    # CONFIGURATION VALIDATION
    # =========================================================================

    def get_configuration_summary(self) -> dict:
        """Get current configuration summary."""
        pending_change = self.get_pending_change()
        return {
            "current_slave_id": self.config.current_slave_id,
            "engineering_mode_enabled": self.config.engineering_mode_enabled,
            "password_protected": self.config.password_protected,
            "pending_change": {
                "old_slave_id": pending_change.old_slave_id,
                "new_slave_id": pending_change.new_slave_id,
                "reason": pending_change.reason,
                "user": pending_change.user,
                "timestamp": pending_change.timestamp,
            } if pending_change else None,
            "total_changes": len(self.config.change_log),
            "total_audit_entries": len(self.audit_log),
        }

    def get_status_report(self) -> str:
        """Get a human-readable status report."""
        pending = self.get_pending_change()
        summary = self.get_configuration_summary()

        report = "=== Sensor Configuration Status ===\n"
        report += f"Current Slave ID: {summary['current_slave_id']}\n"
        report += f"Engineering Mode: {'Enabled' if summary['engineering_mode_enabled'] else 'Disabled'}\n"
        report += f"Password Protected: {'Yes' if summary['password_protected'] else 'No'}\n"
        report += f"Field Ownership Required: {'Yes' if self.field_ownership_required else 'No'}\n"
        report += f"Total Configuration Changes: {summary['total_changes']}\n"
        report += f"Total Audit Entries: {summary['total_audit_entries']}\n"

        if pending:
            report += f"\nPending Change:\n"
            report += f"  {summary['pending_change']['old_slave_id']} → {summary['pending_change']['new_slave_id']}\n"
            report += f"  Reason: {summary['pending_change']['reason']}\n"
            report += f"  User: {summary['pending_change']['user']}\n"
            report += f"  Timestamp: {summary['pending_change']['timestamp']}\n"

        return report
