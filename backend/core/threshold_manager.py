"""
Threshold and Alert Management API
Handles threshold configuration and alert triggering
"""

import json
import os
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel
import asyncio
try:
    import httpx  # type: ignore
except ImportError:
    httpx = None

# Paths
THRESHOLDS_FILE = "config/thresholds.json"
CONTROLLER_THRESHOLDS_FILE = "config/controller_thresholds.json"

DEFAULT_CONTROLLER_THRESHOLDS = [
    {
        "id": "ctrl-1",
        "parameter": "z_rms",
        "parameterLabel": "Z-Axis RMS",
        "unit": "mm/s",
        "warningLimit": 2.0,
        "alertLimit": 4.0,
    },
    {
        "id": "ctrl-2",
        "parameter": "x_rms",
        "parameterLabel": "X-Axis RMS",
        "unit": "mm/s",
        "warningLimit": 2.0,
        "alertLimit": 4.0,
    },
    {
        "id": "ctrl-3",
        "parameter": "temperature",
        "parameterLabel": "Temperature",
        "unit": "°C",
        "warningLimit": 2.0,
        "alertLimit": 4.0,
    },
    {
        "id": "ctrl-4",
        "parameter": "z_accel",
        "parameterLabel": "Z-Peak Accel",
        "unit": "G",
        "warningLimit": 2.0,
        "alertLimit": 4.0,
    },
    {
        "id": "ctrl-5",
        "parameter": "x_accel",
        "parameterLabel": "X-Peak Accel",
        "unit": "G",
        "warningLimit": 2.0,
        "alertLimit": 4.0,
    },
    {
        "id": "ctrl-6",
        "parameter": "kurtosis",
        "parameterLabel": "Kurtosis",
        "unit": "",
        "warningLimit": 2.0,
        "alertLimit": 4.0,
    },
]


def _ensure_z_rms_default(thresholds: List[dict]) -> List[dict]:
    """Guarantee Z-axis RMS defaults (2/4) are present for controller thresholds."""
    has_z_rms = any(t.get("parameter") == "z_rms" for t in thresholds)
    if not has_z_rms:
        thresholds = [DEFAULT_CONTROLLER_THRESHOLDS[0]] + thresholds
    return thresholds

# Data Models
class ThresholdConfig(BaseModel):
    id: str
    parameter: str
    parameterLabel: str
    unit: str
    minLimit: float
    maxLimit: float

class AlertData(BaseModel):
    timestamp: str
    parameter: str
    parameterLabel: str
    current_value: float
    threshold_limit: float
    alert_type: str  # "min_exceeded" or "max_exceeded"
    severity: str  # "warning" or "critical"


class ControllerThreshold(BaseModel):
    id: str
    parameter: str
    parameterLabel: str
    unit: str
    warningLimit: float
    alertLimit: float

# Global state
active_thresholds: List[ThresholdConfig] = []
active_alerts: List[AlertData] = []
controller_thresholds: List[ControllerThreshold] = []

# Alert deduplication and stability
_last_alert_time: Dict[str, datetime] = {}  # key: "param_alerttype"
_current_alert_states: Dict[str, bool] = {} # key: "param_alerttype", value: True if currently in alert
ALERT_COOLDOWN_SECONDS = 30  # Reduced cooldown as we now use hysteresis
HYSTERESIS_FACTOR = 0.05      # 5% hysteresis for industrial stability


def _get_sensor_value(parameter: str, sensor_data: dict) -> Optional[float]:
    """Map a parameter key to its current sensor value."""
    if parameter == 'z_rms':
        return sensor_data.get('z_rms', 0)
    if parameter == 'x_rms':
        return sensor_data.get('x_rms', 0)
    if parameter == 'temperature':
        return sensor_data.get('temperature', 0)
    if parameter == 'z_accel':
        return sensor_data.get('z_accel', 0)
    if parameter == 'x_accel':
        return sensor_data.get('x_accel', 0)
    if parameter == 'kurtosis':
        return sensor_data.get('kurtosis', 0)
    return None

def load_thresholds() -> List[ThresholdConfig]:
    """Load thresholds from file"""
    global active_thresholds
    try:
        if os.path.exists(THRESHOLDS_FILE):
            with open(THRESHOLDS_FILE, 'r') as f:
                data = json.load(f)
                active_thresholds = [ThresholdConfig(**t) for t in data]
                return active_thresholds
    except Exception as e:
        print(f"Error loading thresholds: {e}")
    return []

def save_thresholds(thresholds: List[ThresholdConfig]) -> bool:
    """Save thresholds to file"""
    global active_thresholds
    try:
        os.makedirs(os.path.dirname(THRESHOLDS_FILE), exist_ok=True)
        with open(THRESHOLDS_FILE, 'w') as f:
            json.dump([t.model_dump() for t in thresholds], f, indent=2)
        active_thresholds = thresholds
        return True
    except Exception as e:
        print(f"Error saving thresholds: {e}")
        return False

async def check_thresholds(sensor_data: dict) -> List[AlertData]:
    """
    Check if any sensor values exceed thresholds with hysteresis for stability.
    Returns list of new alerts.
    """
    new_alerts = []
    
    if not active_thresholds:
        return new_alerts
    
    current_time = datetime.now()
    
    for threshold in active_thresholds:
        param_value = _get_sensor_value(threshold.parameter, sensor_data)
        if param_value is None:
            continue
        
        # --- MAX LIMIT CHECK WITH HYSTERESIS ---
        max_key = f"{threshold.parameter}_max"
        is_in_max_alert = _current_alert_states.get(max_key, False)
        
        # Hysteresis: If in alert, must drop below (limit * (1 - factor)) to clear
        # If not in alert, must exceed (limit) to trigger
        trigger_threshold = threshold.maxLimit
        clear_threshold = threshold.maxLimit * (1.0 - HYSTERESIS_FACTOR)
        
        if not is_in_max_alert and param_value > trigger_threshold:
            # TRIGGER NEW MAX ALERT
            _current_alert_states[max_key] = True
            
            # Check cooldown for logging/frontend push
            if max_key not in _last_alert_time or (current_time - _last_alert_time[max_key]).total_seconds() > ALERT_COOLDOWN_SECONDS:
                _last_alert_time[max_key] = current_time
                alert = AlertData(
                    timestamp=current_time.isoformat(),
                    parameter=threshold.parameter,
                    parameterLabel=threshold.parameterLabel,
                    current_value=param_value,
                    threshold_limit=threshold.maxLimit,
                    alert_type="max_exceeded",
                    severity="critical"
                )
                new_alerts.append(alert)
                active_alerts.append(alert)
        
        elif is_in_max_alert and param_value < clear_threshold:
            # CLEAR MAX ALERT
            _current_alert_states[max_key] = False
            # Optional: Log recovery
        
        # --- MIN LIMIT CHECK WITH HYSTERESIS ---
        if threshold.minLimit > -999: # -999 means disabled
            min_key = f"{threshold.parameter}_min"
            is_in_min_alert = _current_alert_states.get(min_key, False)
            
            trigger_min = threshold.minLimit
            clear_min = threshold.minLimit * (1.0 + HYSTERESIS_FACTOR)
            
            if not is_in_min_alert and param_value < trigger_min:
                # TRIGGER NEW MIN ALERT
                _current_alert_states[min_key] = True
                
                if min_key not in _last_alert_time or (current_time - _last_alert_time[min_key]).total_seconds() > ALERT_COOLDOWN_SECONDS:
                    _last_alert_time[min_key] = current_time
                    alert = AlertData(
                        timestamp=current_time.isoformat(),
                        parameter=threshold.parameter,
                        parameterLabel=threshold.parameterLabel,
                        current_value=param_value,
                        threshold_limit=threshold.minLimit,
                        alert_type="min_exceeded",
                        severity="warning"
                    )
                    new_alerts.append(alert)
                    active_alerts.append(alert)
            
            elif is_in_min_alert and param_value > clear_min:
                # CLEAR MIN ALERT
                _current_alert_states[min_key] = False

    return new_alerts


def load_controller_thresholds() -> List[ControllerThreshold]:
    """Load ESP32 controller thresholds, creating defaults if missing."""
    global controller_thresholds

    try:
        if not os.path.exists(CONTROLLER_THRESHOLDS_FILE):
            os.makedirs(os.path.dirname(CONTROLLER_THRESHOLDS_FILE), exist_ok=True)
            with open(CONTROLLER_THRESHOLDS_FILE, 'w') as f:
                json.dump(DEFAULT_CONTROLLER_THRESHOLDS, f, indent=2)
            controller_thresholds = [ControllerThreshold(**t) for t in DEFAULT_CONTROLLER_THRESHOLDS]
            return controller_thresholds

        with open(CONTROLLER_THRESHOLDS_FILE, 'r') as f:
            data = json.load(f)
            data = _ensure_z_rms_default(data)
            controller_thresholds = [ControllerThreshold(**t) for t in data]
            return controller_thresholds
    except Exception as e:
        print(f"Error loading controller thresholds: {e}")
        controller_thresholds = [ControllerThreshold(**t) for t in DEFAULT_CONTROLLER_THRESHOLDS]
        return controller_thresholds


def save_controller_thresholds(thresholds: List[ControllerThreshold]) -> bool:
    """Persist ESP32 controller thresholds to disk."""
    global controller_thresholds
    try:
        os.makedirs(os.path.dirname(CONTROLLER_THRESHOLDS_FILE), exist_ok=True)
        with open(CONTROLLER_THRESHOLDS_FILE, 'w') as f:
            json.dump([t.model_dump() for t in thresholds], f, indent=2)
        controller_thresholds = thresholds
        return True
    except Exception as e:
        print(f"Error saving controller thresholds: {e}")
        return False


async def check_controller_thresholds(sensor_data: dict) -> List[AlertData]:
    """Evaluate ESP32-specific thresholds without affecting web alerts."""
    if not controller_thresholds:
        load_controller_thresholds()

    new_alerts: List[AlertData] = []

    for threshold in controller_thresholds:
        current_value = _get_sensor_value(threshold.parameter, sensor_data)
        if current_value is None:
            continue

        severity: Optional[str] = None
        limit_value: Optional[float] = None
        alert_type: Optional[str] = None

        if current_value >= threshold.alertLimit:
            severity = "alert"
            limit_value = threshold.alertLimit
            alert_type = "controller_alert"
        elif current_value >= threshold.warningLimit:
            severity = "warning"
            limit_value = threshold.warningLimit
            alert_type = "controller_warning"

        if severity and limit_value is not None and alert_type:
            new_alerts.append(AlertData(
                timestamp=datetime.now().isoformat(),
                parameter=threshold.parameter,
                parameterLabel=threshold.parameterLabel,
                current_value=current_value,
                threshold_limit=limit_value,
                alert_type=alert_type,
                severity=severity,
            ))

    return new_alerts

async def send_alert_to_hardware_controller(alert: AlertData):
    """Send alert to Hardware Controller to trigger ESP32 LED"""
    if not httpx:
        print("httpx not installed, skipping alert to hardware controller")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            # Send alert to hardware controller
            await client.post(
                "http://localhost:8001/alert",
                json={
                    "parameter": alert.parameterLabel,
                    "current_value": alert.current_value,
                    "threshold": alert.threshold_limit,
                    "severity": alert.severity
                },
                timeout=2.0
            )
    except Exception as e:
        print(f"Error sending alert to hardware controller: {e}")

async def send_led_blink_command(duration: int = 500, blinks: int = 1):
    """Send LED blink command to Hardware Controller/ESP32"""
    if not httpx:
        print("httpx not installed, skipping LED blink command")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8001/send",
                json={
                    "value": 1.0,
                    "threshold": 0.5
                },
                timeout=2.0
            )
    except Exception as e:
        print(f"Error sending LED blink command: {e}")


# Initialize on import
if not active_thresholds:
    load_thresholds()

if not controller_thresholds:
    load_controller_thresholds()
