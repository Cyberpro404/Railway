"""
Notifier - Email/SMS notification integration using SMTP and Twilio.
"""
import logging
import asyncio
import smtplib
import ssl
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    TwilioClient = None

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """SMTP email configuration"""
    smtp_host: str
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    from_address: str = ""
    

@dataclass
class SMSConfig:
    """Twilio SMS configuration"""
    account_sid: str
    auth_token: str
    from_number: str


@dataclass
class NotificationContact:
    """Contact information for notifications"""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    roles: List[str] = None  # viewer, operator, admin
    notify_sms: bool = False
    notify_email: bool = True


class Notifier:
    """
    Notification service supporting Email (SMTP) and SMS (Twilio).
    """
    
    def __init__(self):
        self.email_config: Optional[EmailConfig] = None
        self.sms_config: Optional[SMSConfig] = None
        self.contacts: List[NotificationContact] = []
        self._smtp_pool: Optional[smtplib.SMTP] = None
        self._twilio_client: Optional[Any] = None
        
        # Notification history
        self._notification_history: List[Dict[str, Any]] = []
        self._max_history = 1000
        
        logger.info("Notifier initialized")
    
    def configure_email(self, config: EmailConfig):
        """Configure email notifications"""
        self.email_config = config
        logger.info(f"Email configured: {config.smtp_host}:{config.smtp_port}")
    
    def configure_sms(self, config: SMSConfig):
        """Configure SMS notifications"""
        if not TWILIO_AVAILABLE:
            logger.warning("Twilio not available. Install with: pip install twilio")
            return
        
        self.sms_config = config
        try:
            self._twilio_client = TwilioClient(config.account_sid, config.auth_token)
            logger.info("SMS configured with Twilio")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio: {e}")
            self._twilio_client = None
    
    def add_contact(self, contact: NotificationContact):
        """Add notification contact"""
        self.contacts.append(contact)
        logger.info(f"Added contact: {contact.name}")
    
    async def send_alert_notification(
        self,
        alert_data: Dict[str, Any],
        severity_threshold: str = "warning"
    ) -> Dict[str, Any]:
        """
        Send alert notifications to relevant contacts.
        
        Args:
            alert_data: Alert information
            severity_threshold: Minimum severity to trigger notification
            
        Returns:
            Notification results
        """
        results = {
            "email_sent": 0,
            "email_failed": 0,
            "sms_sent": 0,
            "sms_failed": 0,
            "errors": []
        }
        
        severity = alert_data.get("severity", "info")
        
        # Check severity threshold
        severity_levels = {"info": 0, "warning": 1, "critical": 2}
        if severity_levels.get(severity, 0) < severity_levels.get(severity_threshold, 1):
            return results
        
        # Determine who to notify
        contacts_to_notify = self._get_contacts_for_severity(severity)
        
        for contact in contacts_to_notify:
            # Send email
            if contact.notify_email and contact.email and self.email_config:
                try:
                    await self._send_email_alert(contact.email, alert_data)
                    results["email_sent"] += 1
                except Exception as e:
                    results["email_failed"] += 1
                    results["errors"].append(f"Email to {contact.email}: {str(e)}")
            
            # Send SMS
            if contact.notify_sms and contact.phone and self._twilio_client:
                try:
                    await self._send_sms_alert(contact.phone, alert_data)
                    results["sms_sent"] += 1
                except Exception as e:
                    results["sms_failed"] += 1
                    results["errors"].append(f"SMS to {contact.phone}: {str(e)}")
        
        # Log notification
        self._log_notification(alert_data, results)
        
        return results
    
    def _get_contacts_for_severity(self, severity: str) -> List[NotificationContact]:
        """Get contacts that should be notified for given severity"""
        contacts = []
        
        for contact in self.contacts:
            # Admin gets everything
            if "admin" in (contact.roles or []):
                contacts.append(contact)
            # Operator gets warning and critical
            elif "operator" in (contact.roles or []) and severity in ["warning", "critical"]:
                contacts.append(contact)
            # Critical goes to everyone
            elif severity == "critical":
                contacts.append(contact)
        
        return contacts
    
    async def _send_email_alert(self, to_address: str, alert_data: Dict[str, Any]):
        """Send email alert notification"""
        if not self.email_config:
            raise ValueError("Email not configured")
        
        config = self.email_config
        
        # Build email content
        subject = f"[{alert_data.get('severity', 'ALERT').upper()}] Railway Monitoring Alert"
        
        html_body = self._build_email_html(alert_data)
        text_body = self._build_email_text(alert_data)
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.from_address
        msg["To"] = to_address
        
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        
        # Send via SMTP
        await asyncio.to_thread(self._send_smtp, config, msg, to_address)
        
        logger.info(f"Email alert sent to {to_address}")
    
    def _send_smtp(self, config: EmailConfig, msg: MIMEMultipart, to_address: str):
        """Synchronous SMTP send"""
        context = ssl.create_default_context()
        
        with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
            if config.use_tls:
                server.starttls(context=context)
            
            if config.username and config.password:
                server.login(config.username, config.password)
            
            server.sendmail(config.from_address, to_address, msg.as_string())
    
    async def _send_sms_alert(self, to_number: str, alert_data: Dict[str, Any]):
        """Send SMS alert notification via Twilio"""
        if not self._twilio_client or not self.sms_config:
            raise ValueError("SMS not configured")
        
        # Build SMS content (must be concise)
        severity = alert_data.get("severity", "ALERT").upper()
        title = alert_data.get("title", "Alert")
        device = alert_data.get("device_id", "Unknown")
        
        body = f"[{severity}] {title} - Device: {device}"
        
        # Send via Twilio
        await asyncio.to_thread(
            self._send_twilio_sms,
            self.sms_config.from_number,
            to_number,
            body
        )
        
        logger.info(f"SMS alert sent to {to_number}")
    
    def _send_twilio_sms(self, from_number: str, to_number: str, body: str):
        """Synchronous Twilio SMS send"""
        self._twilio_client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )
    
    def _build_email_html(self, alert_data: Dict[str, Any]) -> str:
        """Build HTML email body"""
        severity = alert_data.get("severity", "warning")
        color = {"info": "#3498db", "warning": "#f39c12", "critical": "#e74c3c"}.get(severity, "#95a5a6")
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; 
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden;">
                <div style="background-color: {color}; color: white; padding: 20px;">
                    <h1 style="margin: 0; font-size: 24px;">Railway Monitoring Alert</h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px; text-transform: uppercase;">
                        {severity} Severity
                    </p>
                </div>
                <div style="padding: 20px;">
                    <h2 style="color: #2c3e50; margin-top: 0;">{alert_data.get('title', 'Alert')}</h2>
                    <p style="color: #34495e; line-height: 1.6;">{alert_data.get('message', '')}</p>
                    
                    <table style="width: 100%; margin-top: 20px; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #ecf0f1; font-weight: bold; 
                                       color: #7f8c8d;">Device ID</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ecf0f1; color: #2c3e50;">
                                {alert_data.get('device_id', 'Unknown')}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #ecf0f1; font-weight: bold; 
                                       color: #7f8c8d;">Occurrences</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ecf0f1; color: #2c3e50;">
                                {alert_data.get('occurrence_count', 1)}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #ecf0f1; font-weight: bold; 
                                       color: #7f8c8d;">Timestamp</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ecf0f1; color: #2c3e50;">
                                {alert_data.get('timestamp', datetime.now().isoformat())}
                            </td>
                        </tr>
                    </table>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ecf0f1; 
                                font-size: 12px; color: #95a5a6;">
                        <p>This is an automated alert from the Railway Rolling Stock Condition Monitoring System.</p>
                        <p>Please log into the dashboard to acknowledge this alert and view detailed information.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def _build_email_text(self, alert_data: Dict[str, Any]) -> str:
        """Build plain text email body"""
        text = f"""
RAILWAY MONITORING ALERT
========================

Severity: {alert_data.get('severity', 'WARNING').upper()}
Title: {alert_data.get('title', 'Alert')}
Message: {alert_data.get('message', '')}

Device ID: {alert_data.get('device_id', 'Unknown')}
Occurrences: {alert_data.get('occurrence_count', 1)}
Timestamp: {alert_data.get('timestamp', datetime.now().isoformat())}

---
This is an automated alert from the Railway Rolling Stock Condition Monitoring System.
Please log into the dashboard to acknowledge this alert and view detailed information.
"""
        return text
    
    def _log_notification(self, alert_data: Dict[str, Any], results: Dict[str, Any]):
        """Log notification to history"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "alert_id": alert_data.get("alert_id"),
            "severity": alert_data.get("severity"),
            "results": results
        }
        
        self._notification_history.append(log_entry)
        
        # Trim history
        if len(self._notification_history) > self._max_history:
            self._notification_history = self._notification_history[-self._max_history:]
    
    def get_notification_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent notification history"""
        return self._notification_history[-limit:]
    
    async def send_test_notification(self, contact: NotificationContact) -> Dict[str, bool]:
        """Send test notification to verify configuration"""
        results = {"email": False, "sms": False}
        
        test_alert = {
            "alert_id": "TEST-001",
            "severity": "warning",
            "title": "Test Notification",
            "message": "This is a test notification from the Railway Monitoring System.",
            "device_id": "TEST-DEVICE",
            "occurrence_count": 1,
            "timestamp": datetime.now().isoformat()
        }
        
        if contact.email and self.email_config:
            try:
                await self._send_email_alert(contact.email, test_alert)
                results["email"] = True
            except Exception as e:
                logger.error(f"Test email failed: {e}")
        
        if contact.phone and self._twilio_client:
            try:
                await self._send_sms_alert(contact.phone, test_alert)
                results["sms"] = True
            except Exception as e:
                logger.error(f"Test SMS failed: {e}")
        
        return results
