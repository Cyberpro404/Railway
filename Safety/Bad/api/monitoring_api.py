"""
Monitoring API endpoints for alerts and thresholds management.
Handles real-time alerts, historical data, and threshold configuration.
"""

import logging
import csv
import io
from typing import Dict, Optional
from datetime import datetime, timezone, timedelta
import uuid

from fastapi import HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from database.operational_db import get_db
from models import Alert, Thresholds, BandThreshold
from utils.logger import setup_logger
from utils.errors import ValidationError
from utils.validators import validate_threshold_pair
from config.settings import Config

logger = setup_logger(__name__)


class ThresholdsRequest(BaseModel):
    """Thresholds configuration request."""
    z_rms_mm_s_warning: float = Field(default=Config.DEFAULT_Z_RMS_WARNING_MM_S, ge=0)
    z_rms_mm_s_alarm: float = Field(default=Config.DEFAULT_Z_RMS_ALARM_MM_S, ge=0)
    x_rms_mm_s_warning: float = Field(default=Config.DEFAULT_X_RMS_WARNING_MM_S, ge=0)
    x_rms_mm_s_alarm: float = Field(default=Config.DEFAULT_X_RMS_ALARM_MM_S, ge=0)
    temp_c_warning: float = Field(default=Config.DEFAULT_TEMP_WARNING_C, ge=0)
    temp_c_alarm: float = Field(default=Config.DEFAULT_TEMP_ALARM_C, ge=0)
    band_thresholds: list = Field(default_factory=list)


def setup_monitoring_routes(app):
    """Setup all monitoring-related API routes."""
    
    # Global state for thresholds (should be moved to database in production)
    _thresholds = Thresholds()
    _alerts: dict[str, Alert] = {}
    _parameter_level: dict[str, str] = {}
    
    @app.get("/api/monitoring/thresholds", tags=["Monitoring"])
    def api_get_thresholds() -> Dict:
        """Get current alarm/warning thresholds."""
        try:
            return {
                "status": "ok",
                "data": _thresholds.dict()
            }
        except Exception as e:
            logger.error(f"Get thresholds error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get thresholds: " + str(e))
    
    @app.post("/api/monitoring/thresholds", tags=["Monitoring"])
    def api_set_thresholds(request: ThresholdsRequest) -> Dict:
        """
        Set alarm/warning thresholds.
        
        Configure threshold values for monitoring parameters.
        Alarm threshold must be >= warning threshold.
        """
        try:
            # Validate threshold pairs
            try:
                z_warn, z_alrm = validate_threshold_pair(
                    request.z_rms_mm_s_warning,
                    request.z_rms_mm_s_alarm,
                    "z_rms_mm_s"
                )
                x_warn, x_alrm = validate_threshold_pair(
                    request.x_rms_mm_s_warning,
                    request.x_rms_mm_s_alarm,
                    "x_rms_mm_s"
                )
                t_warn, t_alrm = validate_threshold_pair(
                    request.temp_c_warning,
                    request.temp_c_alarm,
                    "temp_c"
                )
            except ValidationError as e:
                logger.warning(f"Threshold validation error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            
            # Create thresholds object
            band_thresholds = []
            if request.band_thresholds:
                for bt in request.band_thresholds:
                    band_thresholds.append(BandThreshold(**bt))
            
            _thresholds = Thresholds(
                z_rms_mm_s_warning=z_warn,
                z_rms_mm_s_alarm=z_alrm,
                x_rms_mm_s_warning=x_warn,
                x_rms_mm_s_alarm=x_alrm,
                temp_c_warning=t_warn,
                temp_c_alarm=t_alrm,
                band_thresholds=band_thresholds
            )
            
            logger.info("Thresholds updated successfully")
            
            return {
                "status": "ok",
                "message": "Thresholds updated successfully",
                "data": _thresholds.dict()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Set thresholds error: {e}")
            raise HTTPException(status_code=500, detail="Failed to set thresholds: " + str(e))
    
    @app.get("/api/monitoring/alerts", tags=["Monitoring"])
    def api_get_alerts(limit: int = 100, status: Optional[str] = None) -> Dict:
        """
        Get alert history.
        
        Retrieve active and historical alerts with optional filtering.
        """
        try:
            # Get alerts from database
            db_alerts = get_db().get_alerts(since_seconds=86400)
            
            # Filter by status if specified
            if status:
                if status not in ('active', 'acknowledged', 'cleared'):
                    raise HTTPException(status_code=400, detail="Invalid status filter")
                db_alerts = [a for a in db_alerts if a.get('status') == status]
            
            # Sort by timestamp (newest first)
            db_alerts = sorted(db_alerts, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]
            
            return {
                "status": "ok",
                "data": {
                    "alerts": db_alerts,
                    "count": len(db_alerts)
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get alerts error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get alerts: " + str(e))
    
    @app.post("/api/monitoring/alerts/{alert_id}/acknowledge", tags=["Monitoring"])
    def api_acknowledge_alert(alert_id: str) -> Dict:
        """Acknowledge an active alert."""
        try:
            # Update alert status in database
            try:
                get_db().update_alert_status(alert_id, "acknowledged")
                logger.info(f"Alert {alert_id} acknowledged")
                
                return {
                    "status": "ok",
                    "message": f"Alert {alert_id} acknowledged"
                }
            except Exception as e:
                logger.warning(f"Failed to acknowledge alert: {e}")
                raise HTTPException(status_code=404, detail="Alert not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Acknowledge error: {e}")
            raise HTTPException(status_code=500, detail="Failed to acknowledge alert: " + str(e))
    
    @app.get("/api/monitoring/history", tags=["Monitoring"])
    def api_get_history(seconds: int = 600, limit: int = 3600) -> Dict:
        """
        Get sensor reading history.
        
        Retrieve historical sensor readings within the specified time range.
        """
        try:
            if seconds <= 0:
                raise HTTPException(status_code=400, detail="Seconds must be positive")
            if limit <= 0 or limit > 10000:
                raise HTTPException(status_code=400, detail="Limit must be between 1 and 10000")
            
            history = get_db().get_history(seconds=seconds)[:limit]
            
            return {
                "status": "ok",
                "data": {
                    "readings": history,
                    "count": len(history),
                    "duration_seconds": seconds
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get history error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get history: " + str(e))
    
    @app.get("/api/monitoring/alerts/export/csv", tags=["Monitoring"])
    def api_export_alerts_csv(since_seconds: int = 86400) -> PlainTextResponse:
        """Export alerts as CSV file."""
        try:
            if since_seconds <= 0:
                raise HTTPException(status_code=400, detail="Since seconds must be positive")
            
            alerts = get_db().get_alerts(since_seconds=since_seconds)
            
            # Create CSV
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=['id', 'timestamp', 'severity', 'parameter', 'value', 'threshold', 'message', 'status']
            )
            writer.writeheader()
            
            for alert in alerts:
                writer.writerow(alert)
            
            return PlainTextResponse(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=alerts.csv"}
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Export CSV error: {e}")
            raise HTTPException(status_code=500, detail="Failed to export alerts: " + str(e))
    
    @app.get("/api/monitoring/latest", tags=["Monitoring"])
    def api_get_latest() -> Dict:
        """Get the latest sensor reading."""
        try:
            latest = get_db().get_latest()
            
            if not latest:
                return {
                    "status": "no_data",
                    "data": None
                }
            
            return {
                "status": "ok",
                "data": latest
            }
        except Exception as e:
            logger.error(f"Get latest error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get latest reading: " + str(e))
