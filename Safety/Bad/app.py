"""
Gandiva Rail Safety Monitor - Main Application
FastAPI server for real-time sensor monitoring and ML-based diagnostics.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.settings import Config
from utils.logger import setup_logger
import core.sensor_reader as sensor_reader
from database.operational_db import get_db, init_db
from database.training_db import get_training_db, init_training_db
from api.sensor_api import setup_sensor_routes
from api.monitoring_api import setup_monitoring_routes
from api.training_api import setup_training_routes

# Setup logging
logger = setup_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=Config.API_TITLE,
    description=Config.API_DESCRIPTION,
    version=Config.API_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=Config.CORS_ALLOW_CREDENTIALS,
    allow_methods=Config.CORS_ALLOW_METHODS,
    allow_headers=Config.CORS_ALLOW_HEADERS,
)

# Global state
_poll_task: asyncio.Task | None = None
_sensor_status: str = "ok"
_sensor_error_message: str | None = None


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    try:
        logger.info(f"Starting {Config.API_TITLE} v{Config.API_VERSION}")
        
        # Initialize databases
        try:
            init_db()
            init_training_db()
            logger.info("Databases initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
        
        # Setup monitoring background tasks
        global _poll_task
        if _poll_task is None or _poll_task.done():
            _poll_task = asyncio.create_task(_sensor_poll_loop())
            logger.info("Sensor monitoring started")
        
        logger.info("Startup complete")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        logger.info("Shutting down application")
        if _poll_task and not _poll_task.done():
            _poll_task.cancel()
            try:
                await _poll_task
            except asyncio.CancelledError:
                pass
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


async def _sensor_poll_loop():
    """Background task for continuous sensor polling."""
    global _sensor_status, _sensor_error_message
    
    loop = asyncio.get_running_loop()
    interval_s = Config.SENSOR_POLL_INTERVAL_S
    next_tick = loop.time()
    
    while True:
        try:
            # Read sensor
            status, reading = await asyncio.to_thread(sensor_reader.read_sensor_once)
            
            if status == sensor_reader.SensorStatus.OK and reading is not None:
                # Store reading in database
                try:
                    get_db().upsert_latest(reading)
                    _sensor_status = "ok"
                    _sensor_error_message = None
                except Exception as e:
                    logger.error(f"Failed to store reading: {e}")
                    _sensor_status = "error"
                    _sensor_error_message = f"Database error: {e}"
            elif status == sensor_reader.SensorStatus.NOT_INITIALIZED:
                _sensor_status = "not_initialized"
                _sensor_error_message = "Sensor not initialized. Configure connection via /api/sensor/connect"
            else:
                err, t = sensor_reader.get_last_error()
                _sensor_status = "error"
                _sensor_error_message = err or "Unknown sensor error"
                logger.debug(f"Sensor read error: {_sensor_error_message}")
        
        except asyncio.CancelledError:
            logger.info("Sensor poll loop cancelled")
            break
        except Exception as e:
            _sensor_status = "error"
            _sensor_error_message = str(e)
            logger.error(f"Unexpected error in sensor poll loop: {e}")
        
        # Sleep until next poll
        next_tick += interval_s
        now = loop.time()
        sleep_s = next_tick - now
        if sleep_s < 0:
            next_tick = now
            sleep_s = 0
        
        try:
            await asyncio.sleep(sleep_s)
        except asyncio.CancelledError:
            break


# Setup all API routes
setup_sensor_routes(app)
setup_monitoring_routes(app)
setup_training_routes(app)


@app.get("/api/health", tags=["System"])
def api_health() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": Config.API_VERSION,
        "sensor_status": _sensor_status,
        "sensor_error": _sensor_error_message
    }


@app.get("/api/config", tags=["System"])
def api_get_config() -> dict:
    """Get application configuration (non-sensitive)."""
    return {
        "title": Config.API_TITLE,
        "version": Config.API_VERSION,
        "poll_interval_s": Config.SENSOR_POLL_INTERVAL_S,
        "frequency_range": {
            "min_hz": Config.FREQUENCY_MIN,
            "max_hz": Config.FREQUENCY_MAX
        },
        "default_thresholds": {
            "z_rms_mm_s_warning": Config.DEFAULT_Z_RMS_WARNING_MM_S,
            "z_rms_mm_s_alarm": Config.DEFAULT_Z_RMS_ALARM_MM_S,
            "x_rms_mm_s_warning": Config.DEFAULT_X_RMS_WARNING_MM_S,
            "x_rms_mm_s_alarm": Config.DEFAULT_X_RMS_ALARM_MM_S,
            "temp_c_warning": Config.DEFAULT_TEMP_WARNING_C,
            "temp_c_alarm": Config.DEFAULT_TEMP_ALARM_C
        }
    }


# Mount static files (frontend)
frontend_dir = Path(__file__).parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
else:
    logger.warning(f"Frontend directory not found at {frontend_dir}")


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
