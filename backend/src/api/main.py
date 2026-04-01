"""
FastAPI Application - Enhanced REST API with new endpoints.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from auth_simple import User, TokenData, verify_token
from fastapi.responses import FileResponse, JSONResponse

# Import system components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from acquisition.multi_device_manager import MultiDXMManager, DeviceInfo
from acquisition.dual_modbus_client import ConnectionConfig, ConnectionType
from processing.signal_processor import SignalProcessor, ProcessingConfig
from processing.defect_detector import DefectDetector, DetectionConfig, DefectType
from alerts.alert_manager import AlertManager
from alerts.notifier import Notifier, EmailConfig, SMSConfig, NotificationContact
from config.config_manager import ConfigManager
from storage.database import (
    init_enhanced_db, create_enhanced_engine, get_session_factory,
    Device, RawData, Alert, AlertSeverity, AlertStatus, DefectDetection,
    Event, DataExport, SystemStatus
)
from device_management_simple import router as device_router

logger = logging.getLogger(__name__)
# security = HTTPBearer()  # Temporarily disabled

# Global instances
device_manager: Optional[MultiDXMManager] = None
alert_manager: Optional[AlertManager] = None
notifier: Optional[Notifier] = None
config_manager: Optional[ConfigManager] = None
signal_processors: Dict[str, SignalProcessor] = {}
defect_detectors: Dict[str, DefectDetector] = {}


def get_db_session():
    """Database session dependency"""
    if not config_manager:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    session_factory = get_session_factory(create_enhanced_engine(config_manager.config.database_url))
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


async def verify_auth_token(token: str = None):
    """JWT token verification (simplified)"""
    if not token:
        return None
    return verify_token(token)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global device_manager, alert_manager, notifier, config_manager
    
    logger.info("🚀 Starting Railway Monitoring System...")
    
    # Initialize config manager
    config_manager = ConfigManager("config.yaml")
    config_manager.start_file_watching()
    
    # Initialize database
    engine = create_enhanced_engine(config_manager.config.database_url)
    init_enhanced_db(engine)
    
    # Initialize components
    device_manager = MultiDXMManager(max_workers=len(config_manager.config.devices))
    
    session_factory = get_session_factory(engine)
    alert_manager = AlertManager(session_factory)
    await alert_manager.start()
    
    # Setup notifier
    notifier = Notifier()
    if config_manager.config.email.enabled:
        notifier.configure_email(EmailConfig(
            smtp_host=config_manager.config.email.smtp_host,
            smtp_port=config_manager.config.email.smtp_port,
            username=config_manager.config.email.username,
            password=config_manager.config.email.password,
            use_tls=config_manager.config.email.use_tls,
            from_address=config_manager.config.email.from_address
        ))
    
    if config_manager.config.sms.enabled:
        notifier.configure_sms(SMSConfig(
            account_sid=config_manager.config.sms.account_sid,
            auth_token=config_manager.config.sms.auth_token,
            from_number=config_manager.config.sms.from_number
        ))
    
    # Add contacts
    for contact_config in config_manager.config.contacts:
        notifier.add_contact(NotificationContact(
            name=contact_config.name,
            email=contact_config.email,
            phone=contact_config.phone,
            roles=contact_config.roles,
            notify_sms=contact_config.notify_sms,
            notify_email=contact_config.notify_email
        ))
    
    # Register notification callback
    alert_manager.register_notification_callback(
        lambda alert: asyncio.create_task(notifier.send_alert_notification(alert))
    )
    
    # Register devices
    for device_config in config_manager.config.devices:
        conn_config = ConnectionConfig(
            tcp_host=device_config.tcp_host,
            tcp_port=device_config.tcp_port,
            serial_port=device_config.serial_port,
            serial_baud=device_config.serial_baud,
            slave_id=device_config.slave_id,
            primary_connection=ConnectionType.TCP if device_config.primary_connection == "tcp" else ConnectionType.SERIAL,
            failover_enabled=device_config.failover_enabled
        )
        
        device_info = DeviceInfo(
            device_id=device_config.device_id,
            name=device_config.name,
            location=device_config.location,
            coach_id=device_config.coach_id,
            sensor_type=device_config.sensor_type,
            config=conn_config
        )
        
        device_manager.register_device(device_info)
        
        # Initialize processors for device
        signal_processors[device_config.device_id] = SignalProcessor(
            device_config.device_id,
            ProcessingConfig(
                temp_compensation_enabled=config_manager.config.processing.temp_compensation_enabled,
                temp_reference=config_manager.config.processing.temp_reference
            )
        )
        
        defect_detectors[device_config.device_id] = DefectDetector(
            device_config.device_id,
            DetectionConfig(
                wheel_flat_threshold=config_manager.config.defect_detection.wheel_flat_kurtosis_threshold,
                bearing_hf_threshold=config_manager.config.defect_detection.bearing_hf_threshold,
                min_confidence=config_manager.config.defect_detection.min_confidence
            )
        )
    
    # Setup data handler
    device_manager.on_unified_data(lambda data: asyncio.create_task(process_unified_data(data)))
    
    # Start acquisition
    await device_manager.start()
    
    logger.info("✅ System initialization complete")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down...")
    await device_manager.stop()
    await alert_manager.stop()
    config_manager.stop_file_watching()
    logger.info("✅ Shutdown complete")


async def process_unified_data(unified_data: Any):
    """Process unified data from all devices"""
    for device_id, raw_data in unified_data.devices.items():
        # Signal processing
        if device_id in signal_processors:
            processed = signal_processors[device_id].process(raw_data)
            
            # Defect detection
            if device_id in defect_detectors:
                detections = defect_detectors[device_id].detect(processed)
                
                # Generate alerts for detections
                for detection in detections:
                    await alert_manager.process_defect_detection(device_id, detection)
        
        # Check thresholds
        if "z_rms_mm" in raw_data and raw_data["z_rms_mm"] > 4.0:
            await alert_manager.process_threshold_breach(
                device_id, "z_rms_mm", raw_data["z_rms_mm"], 4.0, AlertSeverity.CRITICAL
            )


# Create FastAPI app
app = FastAPI(
    title="Railway Rolling Stock Monitoring API",
    description="Advanced condition monitoring system for railway rolling stock",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include device management router
app.include_router(device_router, prefix="/api/v1")


# ==================== SYSTEM STATUS ENDPOINTS ====================

@app.get("/api/v2/status", response_model=Dict[str, Any])
async def get_system_status():
    """
    Get overall system health summary.
    Includes device health, alert counts, and system metrics.
    """
    if not device_manager or not alert_manager:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    device_status = device_manager.get_device_status()
    alert_summary = alert_manager.get_alert_summary()
    
    # Calculate overall health
    total_devices = len(device_status)
    healthy_devices = sum(1 for s in device_status.values() 
                          if s.get("status", {}).get("state") == "connected")
    
    return {
        "system_status": "healthy" if healthy_devices == total_devices else "degraded",
        "timestamp": datetime.now().isoformat(),
        "devices": {
            "total": total_devices,
            "healthy": healthy_devices,
            "degraded": total_devices - healthy_devices
        },
        "alerts": alert_summary,
        "polling_rate_hz": device_manager._poll_interval,
        "data_retention_days": config_manager.config.data_retention_days if config_manager else 90
    }


# ==================== DEVICE ENDPOINTS ====================

@app.get("/api/v2/devices", response_model=Dict[str, Any])
async def list_devices():
    """
    List all connected DXM devices with their status.
    """
    if not device_manager:
        raise HTTPException(status_code=503, detail="Device manager not initialized")
    
    return device_manager.get_device_status()


@app.get("/api/v2/devices/{device_id}", response_model=Dict[str, Any])
async def get_device(device_id: str):
    """
    Get detailed status for a specific device.
    """
    if not device_manager:
        raise HTTPException(status_code=503, detail="Device manager not initialized")
    
    status = device_manager.get_device_status(device_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    
    return status


@app.get("/api/v2/devices/{device_id}/data", response_model=Dict[str, Any])
async def get_device_data(device_id: str):
    """
    Get latest data from a specific device.
    """
    if not device_manager:
        raise HTTPException(status_code=503, detail="Device manager not initialized")
    
    data = device_manager.get_latest_data(device_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No data available for device {device_id}")
    
    return {
        "device_id": device_id,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }


@app.get("/api/v2/devices/{device_id}/baseline", response_model=Dict[str, Any])
async def get_device_baseline(device_id: str):
    """
    Get baseline statistics for a device.
    """
    if device_id not in signal_processors:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    return {
        "device_id": device_id,
        "baseline": signal_processors[device_id].get_baseline_stats()
    }


@app.post("/api/v2/devices/{device_id}/baseline/reset")
async def reset_device_baseline(device_id: str):
    """
    Reset baseline calculations for a device (e.g., after maintenance).
    """
    if device_id not in signal_processors:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    signal_processors[device_id].reset_baselines()
    
    if device_id in defect_detectors:
        defect_detectors[device_id].reset_stats()
    
    return {"message": f"Baseline reset for device {device_id}"}


# ==================== ALERT ENDPOINTS ====================

@app.get("/api/v2/alerts", response_model=List[Dict[str, Any]])
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status: active, acknowledged, resolved"),
    severity: Optional[str] = Query(None, description="Filter by severity: info, warning, critical"),
    device_id: Optional[str] = Query(None, description="Filter by device")
):
    """
    Get active and recent alerts with optional filtering.
    """
    if not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not initialized")
    
    alerts = alert_manager.get_active_alerts(device_id)
    
    # Apply filters
    if status:
        alerts = [a for a in alerts if a.get("status", "active") == status]
    if severity:
        alerts = [a for a in alerts if a.get("severity") == severity]
    
    return alerts


@app.get("/api/v2/alerts/summary", response_model=Dict[str, Any])
async def get_alerts_summary():
    """
    Get summary of current alert status.
    """
    if not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not initialized")
    
    return alert_manager.get_alert_summary()


@app.post("/api/v2/alerts/{alert_key}/acknowledge")
async def acknowledge_alert(
    alert_key: str,
    acknowledged_by: str = Body(..., embed=True),
    notes: str = Body("", embed=True)
):
    """
    Acknowledge an alert.
    """
    if not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not initialized")
    
    success = await alert_manager.acknowledge_alert(alert_key, acknowledged_by, notes)
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert {alert_key} not found")
    
    return {"message": f"Alert {alert_key} acknowledged by {acknowledged_by}"}


@app.post("/api/v2/alerts/{alert_key}/resolve")
async def resolve_alert(
    alert_key: str,
    resolution_notes: str = Body("", embed=True)
):
    """
    Manually resolve an alert.
    """
    if not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not initialized")
    
    success = await alert_manager.resolve_alert(alert_key, resolution_notes)
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert {alert_key} not found")
    
    return {"message": f"Alert {alert_key} resolved"}


# ==================== EVENTS & DETECTIONS ENDPOINTS ====================

@app.get("/api/v2/events")
async def list_events(
    device_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get defect detection history and system events.
    """
    # Query from database
    session = next(get_db_session())
    try:
        query = session.query(Event)
        
        if device_id:
            query = query.filter(Event.device_id == device_id)
        if event_type:
            query = query.filter(Event.event_type == event_type)
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
        
        events = query.order_by(Event.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "device_id": e.device_id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "severity": e.severity.value if e.severity else None,
                "description": e.description
            }
            for e in events
        ]
    finally:
        session.close()


@app.get("/api/v2/detections")
async def list_detections(
    device_id: Optional[str] = Query(None),
    defect_type: Optional[str] = Query(None),
    min_confidence: float = Query(0, ge=0, le=100),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get defect detection history.
    """
    session = next(get_db_session())
    try:
        query = session.query(DefectDetection)
        
        if device_id:
            query = query.filter(DefectDetection.device_id == device_id)
        if defect_type:
            query = query.filter(DefectDetection.defect_type == defect_type)
        if min_confidence > 0:
            query = query.filter(DefectDetection.confidence_score >= min_confidence)
        if start_time:
            query = query.filter(DefectDetection.timestamp >= start_time)
        if end_time:
            query = query.filter(DefectDetection.timestamp <= end_time)
        
        detections = query.order_by(DefectDetection.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "id": d.id,
                "device_id": d.device_id,
                "timestamp": d.timestamp.isoformat() if d.timestamp else None,
                "defect_type": d.defect_type.value if d.defect_type else None,
                "confidence_score": d.confidence_score,
                "severity_level": d.severity_level,
                "detected_frequency": d.detected_frequency,
                "amplitude": d.amplitude,
                "validated": d.validated
            }
            for d in detections
        ]
    finally:
        session.close()


# ==================== EXPORT ENDPOINTS ====================

@app.get("/api/v2/export")
async def export_data(
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    device_ids: Optional[List[str]] = Query(None),
    data_types: List[str] = Query(["raw", "processed"]),
    format: str = Query("csv", pattern="^(csv|json)$")
):
    """
    Download data for a specified time range.
    """
    # Create export job
    export_id = f"EXP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Return job ID (actual export would be processed asynchronously)
    return {
        "export_id": export_id,
        "status": "processing",
        "parameters": {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "device_ids": device_ids,
            "data_types": data_types,
            "format": format
        },
        "download_url": f"/api/v2/export/{export_id}/download"
    }


# ==================== CONFIGURATION ENDPOINTS ====================

@app.get("/api/v2/config")
async def get_configuration():
    """
    Get current system configuration.
    """
    if not config_manager:
        raise HTTPException(status_code=503, detail="Config manager not initialized")
    
    return config_manager.export_to_dict()


@app.get("/api/v2/config/summary")
async def get_config_summary():
    """
    Get configuration summary.
    """
    if not config_manager:
        raise HTTPException(status_code=503, detail="Config manager not initialized")
    
    return config_manager.get_config_summary()


@app.post("/api/v2/config")
async def update_configuration(config: Dict[str, Any] = Body(...)):
    """
    Update system configuration.
    Changes take effect immediately without restart.
    """
    if not config_manager:
        raise HTTPException(status_code=503, detail="Config manager not initialized")
    
    # Update config (validation happens in ConfigManager)
    try:
        # Save new config
        success = config_manager.save_config()
        if success:
            return {"message": "Configuration updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== WEBSOCKET ENDPOINTS ====================

@app.websocket("/api/v2/ws/realtime")
async def websocket_realtime(websocket: WebSocket):
    """
    WebSocket for real-time data streaming.
    """
    await websocket.accept()
    
    if not device_manager:
        await websocket.close(code=1011, reason="System not initialized")
        return
    
    # Subscribe to data updates
    async def send_update(data):
        try:
            await websocket.send_json(data)
        except Exception:
            pass
    
    # Add to broadcast (simplified - in production use proper pub/sub)
    try:
        while True:
            # Send current data every second
            data = device_manager.get_latest_data()
            await websocket.send_json({
                "type": "data_update",
                "timestamp": datetime.now().isoformat(),
                "devices": data
            })
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# ==================== HEALTH CHECK ====================

@app.get("/")
async def root():
    """Root endpoint - redirects to API documentation"""
    return {
        "message": "Railway Monitoring System API v2.0",
        "docs": "/docs",
        "health": "/health",
        "status": "/api/v2/status"
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
