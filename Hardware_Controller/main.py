#!/usr/bin/env python3
"""
Hardware Controller Backend
Sends control commands to ESP32/Arduino via serial communication.
"""

import serial
import time
import logging
import asyncio
from typing import Optional, Dict
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import serial.tools.list_ports

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
COM_PORT = "COM15"  # Changed to COM15
BAUD_RATE = 115200  # Adjust if your device uses different baud rate
SERIAL_TIMEOUT = 1.0
STARTUP_DELAY = 2.0  # 2-second delay after opening serial port

# Global state
class SerialState:
    def __init__(self):
        self.serial_port: Optional[serial.Serial] = None
        self.last_value: Optional[float] = None
        self.last_command_sent: Optional[str] = None  # "ON" or "OFF"
        self.is_connected: bool = False

serial_state = SerialState()


def get_available_ports():
    """List all available COM ports."""
    ports = serial.tools.list_ports.comports()
    available = [port.device for port in ports]
    return available


def open_serial_connection(port: str, baud: int) -> bool:
    """
    Open serial connection to the device.
    Returns True if successful, False otherwise.
    """
    try:
        if serial_state.serial_port and serial_state.serial_port.is_open:
            logger.info("Serial port already open, closing first...")
            serial_state.serial_port.close()
        
        logger.info(f"Attempting to open serial connection: {port} @ {baud} baud")
        serial_state.serial_port = serial.Serial(
            port=port,
            baudrate=baud,
            timeout=SERIAL_TIMEOUT,
            write_timeout=SERIAL_TIMEOUT
        )
        
        # Mandatory 2-second delay after opening
        logger.info(f"Serial port opened. Waiting {STARTUP_DELAY} seconds for device initialization...")
        time.sleep(STARTUP_DELAY)
        
        serial_state.is_connected = True
        logger.info(f"✅ Successfully connected to {port}")
        return True
        
    except serial.SerialException as e:
        logger.error(f"❌ Failed to open serial port: {e}")
        serial_state.is_connected = False
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error opening serial: {e}")
        serial_state.is_connected = False
        return False


def send_command(command: str) -> bool:
    """
    Send a command to the device via serial.
    Commands should be "1\n" (ON) or "0\n" (OFF).
    Returns True if successful, False otherwise.
    """
    if not serial_state.serial_port or not serial_state.serial_port.is_open:
        logger.error("Serial port not open")
        serial_state.is_connected = False
        return False
    
    try:
        serial_state.serial_port.write(command.encode())
        serial_state.serial_port.flush()
        logger.info(f"📤 Sent command: {repr(command)}")
        return True
        
    except serial.SerialException as e:
        logger.error(f"❌ Serial error sending command: {e}")
        serial_state.is_connected = False
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error sending command: {e}")
        serial_state.is_connected = False
        return False


def close_serial_connection():
    """Close the serial connection gracefully."""
    try:
        if serial_state.serial_port and serial_state.serial_port.is_open:
            serial_state.serial_port.close()
            logger.info("Serial port closed")
    except Exception as e:
        logger.warning(f"Warning closing serial: {e}")
    finally:
        serial_state.is_connected = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting Hardware Controller Backend...")
    available_ports = get_available_ports()
    logger.info(f"Available COM ports: {available_ports}")
    
    if open_serial_connection(COM_PORT, BAUD_RATE):
        logger.info("✅ Backend ready to receive control commands")
    else:
        logger.warning(f"⚠️ Could not connect to {COM_PORT}. Backend running but device not available.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Hardware Controller Backend...")
    close_serial_connection()


# FastAPI App
app = FastAPI(
    title="Hardware Controller Backend",
    description="Controls ESP32/Arduino outputs via serial communication",
    lifespan=lifespan
)


# Request/Response Models
class ControlCommand(BaseModel):
    value: float
    threshold: float


class ControlResponse(BaseModel):
    success: bool
    command_sent: str
    last_value: float
    message: str


class StatusResponse(BaseModel):
    connected: bool
    port: str
    baud_rate: int
    last_value: Optional[float]
    last_command: Optional[str]


class PortsResponse(BaseModel):
    available_ports: list


class AlertPayload(BaseModel):
    parameter: str
    current_value: float
    threshold: float
    severity: str


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "service": "Hardware Controller Backend",
        "status": "running",
        "device_connected": serial_state.is_connected
    }


@app.get("/ports", response_model=PortsResponse, tags=["Configuration"])
async def list_ports():
    """List all available COM ports."""
    available = get_available_ports()
    return {"available_ports": available}


@app.post("/connect", tags=["Configuration"])
async def connect_device(port: str = COM_PORT, baud: int = BAUD_RATE):
    """
    Connect to a specific COM port.
    Default: COM5 @ 115200 baud
    """
    success = open_serial_connection(port, baud)
    if success:
        return {
            "success": True,
            "message": f"Connected to {port} @ {baud} baud",
            "port": port,
            "baud_rate": baud
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to {port}"
        )


@app.post("/disconnect", tags=["Configuration"])
async def disconnect_device():
    """Disconnect from the device."""
    close_serial_connection()
    return {"success": True, "message": "Device disconnected"}


@app.get("/status", response_model=StatusResponse, tags=["Status"])
async def get_status():
    """Get current connection status and last command."""
    return {
        "connected": serial_state.is_connected,
        "port": COM_PORT,
        "baud_rate": BAUD_RATE,
        "last_value": serial_state.last_value,
        "last_command": serial_state.last_command_sent
    }


@app.post("/send", response_model=ControlResponse, tags=["Control"])
async def send_control_command(command: ControlCommand):
    """
    Send control command to device based on comparison.
    
    Logic:
    - If value > threshold → send "1\\n" (ON)
    - Else → send "0\\n" (OFF)
    """
    if not serial_state.is_connected:
        raise HTTPException(
            status_code=503,
            detail="Device not connected. Use /connect to establish connection."
        )
    
    # Determine command
    should_turn_on = command.value > command.threshold
    new_command = "1\n" if should_turn_on else "0\n"
    command_name = "ON" if should_turn_on else "OFF"
    
    # Avoid unnecessary repeated writes
    if serial_state.last_command_sent == command_name:
        logger.info(f"⏭️  Command unchanged ({command_name}), skipping send")
        return {
            "success": True,
            "command_sent": command_name,
            "last_value": command.value,
            "message": f"Command unchanged: {command_name} (value: {command.value}, threshold: {command.threshold})"
        }
    
    # Send command
    serial_state.last_value = command.value
    success = send_command(new_command)
    
    if success:
        serial_state.last_command_sent = command_name
        return {
            "success": True,
            "command_sent": command_name,
            "last_value": command.value,
            "message": f"Command sent: {command_name} (value: {command.value} > threshold: {command.threshold})"
        }
    else:
        raise HTTPException(
            status_code=503,
            detail="Failed to send command to device"
        )


@app.post("/send-raw", tags=["Control"])
async def send_raw_command(command: str):
    """
    Send raw command directly to device (advanced use).
    Example: "1\n" or "0\n"
    """
    if not serial_state.is_connected:
        raise HTTPException(
            status_code=503,
            detail="Device not connected"
        )
    
    success = send_command(command)
    if success:
        return {"success": True, "command_sent": command}
    else:
        raise HTTPException(
            status_code=503,
            detail="Failed to send command"
        )


@app.post("/alert", tags=["Alerts"])
async def handle_alert(payload: AlertPayload):
    """Receive alert from backend and trigger ESP32 LED blink."""
    severity = payload.severity.lower()

    if not serial_state.is_connected:
        logger.warning(
            f"Alert received but device not connected: {payload.parameter} = {payload.current_value}"
        )
        return {
            "success": False,
            "message": "Device not connected",
            "alert": payload.parameter
        }
    
    # Log the alert
    alert_msg = (
        f"🚨 ALERT: {payload.parameter} = {payload.current_value} "
        f"(limit: {payload.threshold}) - Severity: {severity}"
    )
    logger.warning(alert_msg)
    
    # Send LED blink command to ESP32
    # For critical severity: rapid blinks (500ms on/off, 5 times)
    # For warning severity: slow blinks (1000ms on/off, 3 times)
    
    if severity in {"critical", "alert"}:
        blink_count = 2
        blink_duration = 500
    else:
        blink_count = 1
        blink_duration = 1000
    
    for i in range(blink_count):
        # Send ON command
        success = send_command("1\n")
        if not success:
            logger.error(f"Failed to send LED ON command during alert")
            return {"success": False, "message": "Failed to send command"}
        
        await asyncio.sleep(blink_duration / 1000.0)
        
        # Send OFF command
        success = send_command("0\n")
        if not success:
            logger.error(f"Failed to send LED OFF command during alert")
            return {"success": False, "message": "Failed to send command"}
        
        await asyncio.sleep(blink_duration / 1000.0)
    
    return {
        "success": True,
        "alert": payload.parameter,
        "blinks": blink_count,
        "severity": severity,
        "message": f"LED blink command sent - {blink_count} blinks at {blink_duration}ms"
    }


@app.get("/alerts/log", tags=["Alerts"])
async def get_alert_log():
    """Get log of recent alerts"""
    # This will be populated as alerts come in
    return {
        "status": "monitoring",
        "last_alert": None,
        "total_alerts": 0
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Hardware Controller Backend starting...")
    logger.info(f"Configure COM port and baud rate by editing COM_PORT and BAUD_RATE in main.py")
    logger.info(f"Current config: {COM_PORT} @ {BAUD_RATE} baud")
    logger.info(f"Connecting at {BAUD_RATE} baud to {COM_PORT}...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
