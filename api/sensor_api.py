"""
Sensor API endpoints for connection management and data reading.
Handles sensor connections, frequency configuration, and real-time data retrieval.
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from pydantic import BaseModel, Field

import core.sensor_reader as sensor_reader
from models import ConnectionConfig, PortInfo
from utils.logger import setup_logger
from utils.errors import SensorError, ConnectionError, ValidationError
from utils.validators import (
    validate_frequency, validate_port, validate_slave_id, validate_threshold_pair
)
from config.settings import Config

logger = setup_logger(__name__)

try:
    from serial.tools import list_ports
except Exception:
    list_ports = None


# Request models
class FrequencyRequest(BaseModel):
    """Frequency configuration request."""
    frequency_hz: float = Field(..., gt=0, le=10000, description="Frequency in Hz")


class ConnectionRequest(BaseModel):
    """Connection configuration request."""
    port: str = Field(..., description="Serial port")
    slave_id: int = Field(default=Config.DEFAULT_SLAVE_ID, ge=1, le=247)
    baudrate: int = Field(default=Config.DEFAULT_BAUDRATE)
    bytesize: int = Field(default=Config.DEFAULT_BYTESIZE)
    parity: str = Field(default=Config.DEFAULT_PARITY, pattern="^[NEO]$")
    stopbits: int = Field(default=Config.DEFAULT_STOPBITS)
    timeout_s: float = Field(default=Config.DEFAULT_TIMEOUT_S, gt=0)
    frequency_hz: float = Field(default=sensor_reader.DEFAULT_FREQUENCY_HZ, gt=0, le=10000)


def setup_sensor_routes(app):
    """Setup all sensor-related API routes."""
    
    @app.get("/api/sensor/status", tags=["Sensor"])
    def api_sensor_status() -> Dict:
        """
        Get current sensor status.
        
        Returns the current connection and operational status of the sensor.
        """
        try:
            reader = sensor_reader.get_reader()
            return {
                "status": "ok",
                "data": {
                    "connected": True,
                    "port": reader.config.port,
                    "frequency_hz": reader.frequency_hz,
                    "slave_id": reader.config.slave_id,
                    "baudrate": reader.config.baudrate
                }
            }
        except SensorError:
            return {
                "status": "not_initialized",
                "data": {
                    "connected": False,
                    "message": "Sensor not initialized. Configure connection first."
                }
            }
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return {
                "status": "error",
                "data": {
                    "connected": False,
                    "message": str(e)
                }
            }
    
    @app.get("/api/sensor/ports", tags=["Sensor"])
    def api_scan_ports() -> Dict:
        """
        Scan available serial ports.
        
        Returns a list of detected serial ports that can be used for sensor connection.
        """
        try:
            if list_ports is None:
                return {
                    "status": "ok",
                    "data": {
                        "ports": [],
                        "message": "Serial port scanning not available on this system"
                    }
                }
            
            ports = []
            for p in list_ports.comports():
                ports.append({
                    "port": p.device,
                    "description": getattr(p, "description", None),
                    "hwid": getattr(p, "hwid", None)
                })
            
            return {
                "status": "ok",
                "data": {
                    "ports": ports,
                    "count": len(ports)
                }
            }
        except Exception as e:
            logger.error(f"Port scan error: {e}")
            raise HTTPException(status_code=500, detail="Failed to scan ports: " + str(e))
    
    @app.post("/api/sensor/connect", tags=["Sensor"])
    def api_connect_sensor(request: ConnectionRequest) -> Dict:
        """
        Connect to sensor with specified configuration.
        
        Establishes a connection to the sensor using Modbus RTU protocol.
        """
        try:
            # Validate inputs
            try:
                port = validate_port(request.port)
                slave_id = validate_slave_id(request.slave_id)
                frequency = validate_frequency(request.frequency_hz)
            except ValidationError as e:
                logger.warning(f"Validation error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            
            # Create connection config
            config = ConnectionConfig(
                port=port,
                slave_id=slave_id,
                baudrate=request.baudrate,
                bytesize=request.bytesize,
                parity=request.parity,
                stopbits=request.stopbits,
                timeout_s=request.timeout_s
            )
            
            # Initialize reader
            try:
                sensor_reader.init_reader(config, frequency)
                # Test connection
                _ = sensor_reader.read_scalar_values()
                
                logger.info(f"Sensor connected on {port} at {frequency} Hz")
                
                return {
                    "status": "ok",
                    "message": "Sensor connected successfully",
                    "data": {
                        "port": port,
                        "frequency_hz": frequency,
                        "slave_id": slave_id
                    }
                }
            except SensorError as e:
                logger.warning(f"Connection error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise HTTPException(status_code=500, detail="Connection failed: " + str(e))
    
    @app.post("/api/sensor/frequency", tags=["Sensor"])
    def api_set_frequency(request: FrequencyRequest) -> Dict:
        """
        Set the sensor sampling frequency.
        
        Updates the frequency parameter for the sensor. Valid range: 0.1 - 10000 Hz.
        """
        try:
            try:
                frequency = validate_frequency(request.frequency_hz)
                sensor_reader.set_frequency(frequency)
                
                logger.info(f"Frequency set to {frequency} Hz")
                
                return {
                    "status": "ok",
                    "message": f"Frequency set to {frequency} Hz",
                    "data": {
                        "frequency_hz": frequency
                    }
                }
            except ValidationError as e:
                logger.warning(f"Frequency validation error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except SensorError as e:
            logger.warning(f"Frequency set error: {e}")
            raise HTTPException(status_code=500, detail="Failed to set frequency: " + str(e))
        except Exception as e:
            logger.error(f"Frequency set error: {e}")
            raise HTTPException(status_code=500, detail="Failed to set frequency: " + str(e))
    
    @app.get("/api/sensor/frequency", tags=["Sensor"])
    def api_get_frequency() -> Dict:
        """Get the current sensor sampling frequency."""
        try:
            frequency = sensor_reader.get_frequency()
            return {
                "status": "ok",
                "data": {
                    "frequency_hz": frequency
                }
            }
        except SensorError:
            raise HTTPException(status_code=503, detail="Sensor not initialized")
        except Exception as e:
            logger.error(f"Get frequency error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get frequency: " + str(e))
    
    @app.post("/api/sensor/read", tags=["Sensor"])
    def api_read_now() -> Dict:
        """
        Perform a single on-demand sensor read.
        
        Useful for testing sensor connectivity and getting current readings.
        """
        try:
            status, reading = sensor_reader.read_sensor_once()
            
            if status != sensor_reader.SensorStatus.OK or reading is None:
                err, t = sensor_reader.get_last_error()
                logger.warning(f"Sensor read failed: {err}")
                raise HTTPException(status_code=400, detail=err or "Sensor read failed")
            
            return {
                "status": "ok",
                "data": reading
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Read error: {e}")
            raise HTTPException(status_code=500, detail="Read failed: " + str(e))
    
    @app.get("/api/sensor/last-error", tags=["Sensor"])
    def api_get_last_error() -> Dict:
        """Get the last sensor error message."""
        err, timestamp = sensor_reader.get_last_error()
        return {
            "status": "ok",
            "data": {
                "error": err,
                "timestamp": timestamp
            }
        }
