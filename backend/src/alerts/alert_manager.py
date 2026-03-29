"""
Alert Manager - Intelligent alerting system with hysteresis, aggregation, and notifications.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.database import AlertSeverity, AlertStatus, get_session_factory
from processing.defect_detector import DefectSignature, DefectType

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Alert classification types"""
    THRESHOLD = "threshold"
    DEFECT = "defect"
    SYSTEM = "system"
    CONNECTIVITY = "connectivity"


@dataclass
class AlertRule:
    """Configuration for alert generation"""
    alert_type: AlertType
    severity: AlertSeverity
    parameter: Optional[str] = None
    defect_type: Optional[DefectType] = None
    
    # Thresholds
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    hysteresis: float = 0.1  # 10% hysteresis
    
    # Aggregation
    aggregation_window_seconds: int = 60  # Group alerts within this window
    max_occurrences: int = 10  # Max alerts in window before aggregation
    
    # Escalation
    auto_escalate: bool = False
    escalation_delay_minutes: int = 30
    
    # Notification
    notify_immediately: bool = True
    min_severity_for_notification: AlertSeverity = AlertSeverity.WARNING


@dataclass
class ActiveAlert:
    """Currently active alert tracking"""
    alert_id: str
    rule: AlertRule
    device_id: str
    first_triggered: datetime
    last_triggered: datetime
    occurrence_count: int = 1
    current_value: Optional[float] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


class AlertManager:
    """
    Intelligent alerting system with:
    - Multi-level classification (Info, Warning, Critical)
    - Alert hysteresis (prevent spam from threshold oscillation)
    - Alert aggregation (combine related events)
    - Alert persistence and acknowledgment
    """
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self._active_alerts: Dict[str, ActiveAlert] = {}  # alert_key -> ActiveAlert
        self._alert_rules: List[AlertRule] = []
        self._aggregation_buffers: Dict[str, List[datetime]] = defaultdict(list)
        self._notification_callbacks: List[Callable[[Any], None]] = []
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Initialize default rules
        self._init_default_rules()
        
        logger.info("AlertManager initialized")
    
    def _init_default_rules(self):
        """Initialize default alert rules"""
        self._alert_rules = [
            # Threshold alerts
            AlertRule(
                alert_type=AlertType.THRESHOLD,
                severity=AlertSeverity.WARNING,
                parameter="z_rms_mm",
                warning_threshold=2.0,
                critical_threshold=4.0,
                hysteresis=0.2
            ),
            AlertRule(
                alert_type=AlertType.THRESHOLD,
                severity=AlertSeverity.WARNING,
                parameter="temperature",
                warning_threshold=50.0,
                critical_threshold=70.0,
                hysteresis=2.0
            ),
            # Defect alerts
            AlertRule(
                alert_type=AlertType.DEFECT,
                severity=AlertSeverity.WARNING,
                defect_type=DefectType.WHEEL_FLAT,
                min_severity_for_notification=AlertSeverity.WARNING
            ),
            AlertRule(
                alert_type=AlertType.DEFECT,
                severity=AlertSeverity.CRITICAL,
                defect_type=DefectType.BEARING_OUTER_RACE,
                min_severity_for_notification=AlertSeverity.WARNING
            ),
            AlertRule(
                alert_type=AlertType.DEFECT,
                severity=AlertSeverity.CRITICAL,
                defect_type=DefectType.BEARING_INNER_RACE,
                min_severity_for_notification=AlertSeverity.WARNING
            ),
            # Connectivity alerts
            AlertRule(
                alert_type=AlertType.CONNECTIVITY,
                severity=AlertSeverity.WARNING,
                notify_immediately=True
            ),
        ]
    
    async def start(self):
        """Start the alert manager"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("AlertManager started")
    
    async def stop(self):
        """Stop the alert manager"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("AlertManager stopped")
    
    def register_notification_callback(self, callback: Callable[[Any], None]):
        """Register callback for alert notifications"""
        self._notification_callbacks.append(callback)
    
    async def process_threshold_breach(
        self,
        device_id: str,
        parameter: str,
        value: float,
        threshold: float,
        severity: AlertSeverity
    ) -> Optional[ActiveAlert]:
        """
        Process a threshold breach and generate/manage alerts.
        
        Implements hysteresis to prevent alert spam from threshold oscillation.
        """
        # Find matching rule
        rule = self._find_rule(AlertType.THRESHOLD, parameter=parameter)
        if not rule:
            return None
        
        # Generate alert key
        alert_key = f"{device_id}:{parameter}:threshold"
        
        # Check if alert already active
        existing_alert = self._active_alerts.get(alert_key)
        
        if existing_alert:
            # Check if should clear (hysteresis)
            hysteresis_low = threshold * (1 - rule.hysteresis)
            
            if value < hysteresis_low:
                # Clear the alert
                await self._resolve_alert(alert_key, "Value returned to normal (hysteresis)")
                return None
            
            # Update existing alert
            existing_alert.last_triggered = datetime.now()
            existing_alert.current_value = value
            existing_alert.occurrence_count += 1
            
            # Check for escalation
            if rule.auto_escalate and severity == AlertSeverity.WARNING:
                elapsed = datetime.now() - existing_alert.first_triggered
                if elapsed > timedelta(minutes=rule.escalation_delay_minutes):
                    severity = AlertSeverity.CRITICAL
                    logger.warning(f"Alert escalated to CRITICAL: {alert_key}")
            
            await self._update_database_alert(existing_alert)
            return existing_alert
        
        else:
            # Check aggregation - should we create a new alert or aggregate?
            if self._should_aggregate(alert_key, rule):
                logger.debug(f"Aggregating alert: {alert_key}")
                return None
            
            # Create new alert
            new_alert = await self._create_alert(
                alert_key=alert_key,
                device_id=device_id,
                rule=rule,
                severity=severity,
                title=f"{parameter} Threshold Exceeded",
                message=f"{parameter} = {value:.3f} (threshold: {threshold:.3f})",
                current_value=value,
                threshold_value=threshold
            )
            
            return new_alert
    
    async def process_defect_detection(
        self,
        device_id: str,
        defect: DefectSignature
    ) -> Optional[ActiveAlert]:
        """Process a detected defect and generate alert"""
        # Find matching rule
        rule = self._find_rule(AlertType.DEFECT, defect_type=defect.defect_type)
        if not rule:
            # Use default rule
            rule = AlertRule(
                alert_type=AlertType.DEFECT,
                severity=AlertSeverity.WARNING if defect.severity_level <= 2 else AlertSeverity.CRITICAL,
                defect_type=defect.defect_type
            )
        
        # Map severity level to AlertSeverity
        if defect.severity_level <= 2:
            severity = AlertSeverity.WARNING
        else:
            severity = AlertSeverity.CRITICAL
        
        alert_key = f"{device_id}:{defect.defect_type.value}:defect"
        
        # Check if similar defect already active
        existing_alert = self._active_alerts.get(alert_key)
        
        if existing_alert:
            # Update existing
            existing_alert.last_triggered = datetime.now()
            existing_alert.occurrence_count += 1
            existing_alert.current_value = defect.confidence_score
            await self._update_database_alert(existing_alert)
            return existing_alert
        
        # Create new defect alert
        title = f"Defect Detected: {defect.defect_type.value.replace('_', ' ').title()}"
        message = (
            f"Confidence: {defect.confidence_score:.1f}%, "
            f"Severity: Level {defect.severity_level}, "
            f"Device: {device_id}"
        )
        
        new_alert = await self._create_alert(
            alert_key=alert_key,
            device_id=device_id,
            rule=rule,
            severity=severity,
            title=title,
            message=message,
            current_value=defect.confidence_score,
            metadata={
                "defect_type": defect.defect_type.value,
                "severity_level": defect.severity_level,
                "detected_frequency": defect.detected_frequency,
                "supporting_metrics": defect.supporting_metrics
            }
        )
        
        return new_alert
    
    async def process_connectivity_issue(
        self,
        device_id: str,
        issue_type: str,
        severity: AlertSeverity = AlertSeverity.WARNING
    ) -> Optional[ActiveAlert]:
        """Process connectivity issues"""
        rule = self._find_rule(AlertType.CONNECTIVITY)
        alert_key = f"{device_id}:connectivity:{issue_type}"
        
        existing_alert = self._active_alerts.get(alert_key)
        if existing_alert:
            existing_alert.last_triggered = datetime.now()
            existing_alert.occurrence_count += 1
            await self._update_database_alert(existing_alert)
            return existing_alert
        
        new_alert = await self._create_alert(
            alert_key=alert_key,
            device_id=device_id,
            rule=rule or AlertRule(alert_type=AlertType.CONNECTIVITY, severity=severity),
            severity=severity,
            title=f"Connectivity Issue: {issue_type}",
            message=f"Device {device_id} - {issue_type}"
        )
        
        return new_alert
    
    async def acknowledge_alert(
        self,
        alert_key: str,
        acknowledged_by: str,
        notes: str = ""
    ) -> bool:
        """Acknowledge an active alert"""
        alert = self._active_alerts.get(alert_key)
        if not alert:
            return False
        
        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now()
        
        # Update database
        session = self.db_session_factory()
        try:
            from storage.database import Alert as AlertModel
            db_alert = session.query(AlertModel).filter(
                AlertModel.id == alert.alert_id
            ).first()
            if db_alert:
                db_alert.acknowledged = True
                db_alert.acknowledged_by = acknowledged_by
                db_alert.acknowledged_at = datetime.now()
                db_alert.acknowledgment_notes = notes
                db_alert.status = AlertStatus.ACKNOWLEDGED
                session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
        finally:
            session.close()
    
    async def resolve_alert(self, alert_key: str, resolution_notes: str = "") -> bool:
        """Manually resolve an alert"""
        return await self._resolve_alert(alert_key, resolution_notes)
    
    async def _create_alert(
        self,
        alert_key: str,
        device_id: str,
        rule: AlertRule,
        severity: AlertSeverity,
        title: str,
        message: str,
        current_value: Optional[float] = None,
        threshold_value: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> ActiveAlert:
        """Create a new alert in database and memory"""
        alert_id = f"ALT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{device_id[:8]}"
        
        # Create in-memory tracking
        active_alert = ActiveAlert(
            alert_id=alert_id,
            rule=rule,
            device_id=device_id,
            first_triggered=datetime.now(),
            last_triggered=datetime.now(),
            current_value=current_value
        )
        self._active_alerts[alert_key] = active_alert
        
        # Persist to database
        session = self.db_session_factory()
        try:
            from storage.database import Alert as AlertModel
            
            db_alert = AlertModel(
                id=alert_id,
                alert_type=rule.alert_type.value,
                severity=severity,
                status=AlertStatus.ACTIVE,
                device_id=device_id,
                title=title,
                message=message,
                parameter=rule.parameter,
                current_value=current_value,
                threshold_value=threshold_value,
                hysteresis_low=threshold_value * (1 - rule.hysteresis) if threshold_value else None,
                hysteresis_high=threshold_value * (1 + rule.hysteresis) if threshold_value else None,
                metadata=metadata
            )
            session.add(db_alert)
            session.commit()
            
            logger.info(f"Alert created: {alert_id} - {title}")
            
            # Send notifications
            if rule.notify_immediately and severity.value >= rule.min_severity_for_notification.value:
                await self._send_notifications(active_alert, db_alert)
            
        except Exception as e:
            logger.error(f"Failed to create alert in database: {e}")
            session.rollback()
        finally:
            session.close()
        
        return active_alert
    
    async def _update_database_alert(self, active_alert: ActiveAlert):
        """Update alert in database"""
        session = self.db_session_factory()
        try:
            from storage.database import Alert as AlertModel
            
            db_alert = session.query(AlertModel).filter(
                AlertModel.id == active_alert.alert_id
            ).first()
            
            if db_alert:
                db_alert.last_occurrence = active_alert.last_triggered
                db_alert.occurrence_count = active_alert.occurrence_count
                db_alert.current_value = active_alert.current_value
                session.commit()
        except Exception as e:
            logger.error(f"Failed to update alert: {e}")
        finally:
            session.close()
    
    async def _resolve_alert(self, alert_key: str, resolution_notes: str = "") -> bool:
        """Resolve an active alert"""
        alert = self._active_alerts.pop(alert_key, None)
        if not alert:
            return False
        
        # Update database
        session = self.db_session_factory()
        try:
            from storage.database import Alert as AlertModel
            
            db_alert = session.query(AlertModel).filter(
                AlertModel.id == alert.alert_id
            ).first()
            
            if db_alert:
                db_alert.status = AlertStatus.RESOLVED
                db_alert.resolved_at = datetime.now()
                db_alert.resolution_notes = resolution_notes
                session.commit()
                logger.info(f"Alert resolved: {alert.alert_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False
        finally:
            session.close()
        
        return True
    
    def _find_rule(
        self,
        alert_type: AlertType,
        parameter: Optional[str] = None,
        defect_type: Optional[DefectType] = None
    ) -> Optional[AlertRule]:
        """Find matching alert rule"""
        for rule in self._alert_rules:
            if rule.alert_type != alert_type:
                continue
            
            if parameter and rule.parameter != parameter:
                continue
            
            if defect_type and rule.defect_type != defect_type:
                continue
            
            return rule
        
        return None
    
    def _should_aggregate(self, alert_key: str, rule: AlertRule) -> bool:
        """Check if alert should be aggregated"""
        now = datetime.now()
        window_start = now - timedelta(seconds=rule.aggregation_window_seconds)
        
        # Clean old entries
        self._aggregation_buffers[alert_key] = [
            t for t in self._aggregation_buffers[alert_key] if t > window_start
        ]
        
        # Add current occurrence
        self._aggregation_buffers[alert_key].append(now)
        
        # Check if exceeded max
        return len(self._aggregation_buffers[alert_key]) > rule.max_occurrences
    
    async def _send_notifications(self, active_alert: ActiveAlert, db_alert):
        """Send alert notifications via registered callbacks"""
        notification_data = {
            "alert_id": active_alert.alert_id,
            "severity": active_alert.rule.severity.value,
            "device_id": active_alert.device_id,
            "title": db_alert.title,
            "message": db_alert.message,
            "occurrence_count": active_alert.occurrence_count,
            "timestamp": datetime.now().isoformat()
        }
        
        for callback in self._notification_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(notification_data)
                else:
                    callback(notification_data)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")
    
    async def _cleanup_loop(self):
        """Periodic cleanup of old alerts"""
        while self._running:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._cleanup_old_alerts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
    
    async def _cleanup_old_alerts(self):
        """Clean up alerts that haven't occurred recently"""
        now = datetime.now()
        stale_threshold = now - timedelta(hours=24)
        
        to_remove = []
        for alert_key, alert in self._active_alerts.items():
            if alert.last_triggered < stale_threshold:
                to_remove.append(alert_key)
        
        for alert_key in to_remove:
            await self._resolve_alert(alert_key, "Auto-resolved: stale alert")
    
    def get_active_alerts(self, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get currently active alerts"""
        alerts = []
        for alert_key, alert in self._active_alerts.items():
            if device_id and alert.device_id != device_id:
                continue
            
            alerts.append({
                "alert_key": alert_key,
                "alert_id": alert.alert_id,
                "device_id": alert.device_id,
                "severity": alert.rule.severity.value,
                "type": alert.rule.alert_type.value,
                "first_triggered": alert.first_triggered.isoformat(),
                "last_triggered": alert.last_triggered.isoformat(),
                "occurrence_count": alert.occurrence_count,
                "current_value": alert.current_value,
                "acknowledged": alert.acknowledged,
                "acknowledged_by": alert.acknowledged_by
            })
        
        return sorted(alerts, key=lambda x: x["last_triggered"], reverse=True)
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert status"""
        summary = {
            "active_count": len(self._active_alerts),
            "critical_count": sum(1 for a in self._active_alerts.values() 
                                 if a.rule.severity == AlertSeverity.CRITICAL),
            "warning_count": sum(1 for a in self._active_alerts.values() 
                               if a.rule.severity == AlertSeverity.WARNING),
            "acknowledged_count": sum(1 for a in self._active_alerts.values() 
                                     if a.acknowledged),
            "by_device": defaultdict(int),
            "by_type": defaultdict(int)
        }
        
        for alert in self._active_alerts.values():
            summary["by_device"][alert.device_id] += 1
            summary["by_type"][alert.rule.alert_type.value] += 1
        
        return dict(summary)
