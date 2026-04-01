"""
Gandiva Pro - Main FastAPI Backend Application
Serves all /api/v1/* endpoints consumed by the React frontend.
"""

import asyncio
import ipaddress
import json
import logging
import math
import os
import random
import re
import socket
import struct
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from core.modbus_client import ModbusConnectionProfile, UnifiedModbusClient
    _MODBUS_AVAILABLE = True
except ImportError:
    _MODBUS_AVAILABLE = False
    logger_boot = logging.getLogger(__name__)
    logger_boot.warning("pymodbus not available — Modbus polling disabled")

from fastapi import Body, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

THRESHOLDS_FILE = CONFIG_DIR / "thresholds.json"
CTRL_THRESHOLDS_FILE = CONFIG_DIR / "controller_thresholds.json"
SENSOR_STATE_FILE = DATA_DIR / "sensor_state.json"
CHART_DATA_FILE = DATA_DIR / "chart_data.json"

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── In-memory state ──────────────────────────────────────────────────────────
_state: Dict[str, Any] = {
    "demo_mode": False,   # demo is a fallback — not the default
    "connected": False,
    "port": None,
    "baud": 19200,
    "slave_id": 1,
    "connect_time": None,
    "last_poll": None,
    "packet_loss": 0.0,
    "auto_reconnect": True,
    "uptime_seconds": 0,
}

_alerts: List[Dict[str, Any]] = []
_alert_id_counter: int = 1

# ─── Modbus live polling state ─────────────────────────────────────────────────
_modbus_client: Optional[Any] = None   # UnifiedModbusClient instance
_poll_task: Optional[asyncio.Task] = None  # background asyncio Task


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_json(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read %s: %s", path, exc)
    return default if default is not None else []


def _save_json(path: Path, data: Any) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception as exc:
        logger.error("Could not write %s: %s", path, exc)
        return False


def _idle_sensor() -> Dict[str, Any]:
    """Return a zeroed sensor payload used when no device is connected.

    All 21 register-mapped fields are present so the frontend never reads
    undefined — every value is 0 / empty-string / 'disconnected'.
    """
    ts = datetime.now(timezone.utc).isoformat()
    return {
        "z_rms": 0.0, "x_rms": 0.0,
        "z_peak": 0.0, "x_peak": 0.0,
        "z_peak_vel_mm": 0.0, "x_peak_vel_mm": 0.0,
        "z_rms_in": 0.0, "x_rms_in": 0.0,
        "z_peak_vel_in": 0.0, "x_peak_vel_in": 0.0,
        "z_accel": 0.0, "x_accel": 0.0,
        "z_rms_accel": 0.0, "x_rms_accel": 0.0,
        "z_peak_accel": 0.0, "x_peak_accel": 0.0,
        "z_hf_rms_accel": 0.0,
        "temperature": 0.0, "temp_f": 0.0,
        "z_peak_freq": 0.0, "x_peak_freq": 0.0,
        "kurtosis": 0.0, "z_kurtosis": 0.0, "x_kurtosis": 0.0,
        "crest_factor": 0.0, "z_crest_factor": 0.0, "x_crest_factor": 0.0,
        "rms_overall": 0.0, "energy": 0.0,
        "bearing_health": 0.0,
        "iso_class": "—", "alarm_status": "disconnected",
        "humidity": 0.0, "frequency": 0.0,
        "vibration_trend": 0.0, "temp_trend": 0.0,
        "uptime": 0,
        "sensor_status": "disconnected", "data_quality": 0,
        "peak_accel": 0.0, "peak_velocity": 0.0,
        "timestamp": ts,
    }


def _enrich_sensor(sensor: Dict[str, Any]) -> Dict[str, Any]:
    """Fill in any missing derived fields from already-parsed sensor values.

    Called when serving data from sensor_state.json (the live-polled file).
    Since _registers_to_sensor() already fills all fields, this is mostly
    a safety net for any missing keys in older saved data.

    DXM register map (for raw_registers fallback, addr 5200 or 0):
      R1 z_rms/1000  R3 temperature/100(signed)  R5 x_rms/1000
      R6 z_peak_accel/1000  R7 x_peak_accel/1000
      R8 z_peak_freq/10  R9 x_peak_freq/10
      R10 z_band_rms/1000  R11 x_band_rms/1000
      R12 z_kurtosis/1000  R13 x_kurtosis/1000
      R14 z_crest/1000  R15 x_crest/1000
      R16 z_hf_rms/1000  R17 z_peak_vel_mm/1000
      R18 x_hf_rms/1000  R19 x_peak_vel_mm/1000
    """
    raw: list = sensor.get("raw_registers") or []

    def _r(idx: int, scale: float, fallback: float = 0.0) -> float:
        try:
            v = raw[idx] / scale if idx < len(raw) else fallback
            return round(v, 4)
        except (TypeError, ZeroDivisionError, IndexError):
            return fallback

    z_rms = float(sensor.get("z_rms", 0.0))
    x_rms = float(sensor.get("x_rms", 0.0))
    z_peak = float(sensor.get("z_peak", 0.0))
    x_peak = float(sensor.get("x_peak", 0.0))
    z_accel = float(sensor.get("z_accel", 0.0))
    x_accel = float(sensor.get("x_accel", 0.0))
    temperature = float(sensor.get("temperature", 0.0))
    freq = float(sensor.get("frequency", 0.0))
    kurtosis = float(sensor.get("kurtosis", sensor.get("z_kurtosis", 0.0)))
    crest = float(sensor.get("crest_factor", sensor.get("z_crest_factor", 0.0)))

    def _set(key: str, value: float) -> None:
        if key not in sensor or sensor[key] is None:
            sensor[key] = round(value, 4)

    # Velocity in/sec (DXM does not send these directly — derive from mm/s)
    _set("z_rms_in",      _r(1, 1000 * 25.4) or round(z_rms / 25.4, 4))
    _set("x_rms_in",      _r(5, 1000 * 25.4) or round(x_rms / 25.4, 4))
    _set("z_peak_vel_in", _r(17, 1000 * 25.4) or round(z_peak / 25.4, 4))
    _set("x_peak_vel_in", _r(19, 1000 * 25.4) or round(x_peak / 25.4, 4))

    # Velocity mm/s aliases
    _set("z_peak_vel_mm", _r(17, 1000) or z_peak)
    _set("x_peak_vel_mm", _r(19, 1000) or x_peak)

    # Temperature °F
    _set("temp_f", round(temperature * 9 / 5 + 32, 1))

    # Acceleration  (R6=z_peak_accel, R7=x_peak_accel, R10=z_band_rms, R11=x_band_rms)
    _set("z_rms_accel",  _r(10, 1000) or z_accel)
    _set("x_rms_accel",  _r(11, 1000) or x_accel)
    _set("z_peak_accel", _r(6, 1000) or round(z_accel * 1.45, 3))
    _set("x_peak_accel", _r(7, 1000) or round(x_accel * 1.45, 3))
    _set("z_hf_rms_accel", _r(16, 1000) or round(z_accel * 0.35, 3))

    # Frequency
    _set("z_peak_freq", _r(8, 10) or freq)
    _set("x_peak_freq", _r(9, 10) or float(sensor.get("x_frequency", freq)))

    # Statistical
    _set("z_kurtosis",     _r(12, 1000) or kurtosis)
    _set("x_kurtosis",     _r(13, 1000) or round(kurtosis * 0.9, 3))
    _set("z_crest_factor", _r(14, 1000) or crest)
    _set("x_crest_factor", _r(15, 1000) or round(crest * 0.9, 3))

    # Aggregate / status
    _set("rms_overall",   round(math.sqrt(z_rms**2 + x_rms**2), 3))
    _set("energy",        round((z_rms**2 + x_rms**2) * 100, 1))
    _set("bearing_health", float(sensor.get("bearing_health", 0.0)))
    _set("humidity",      0.0)
    _set("vibration_trend", 0.0)
    _set("temp_trend",    0.0)
    _set("peak_accel",    round(max(z_accel, x_accel) * 1.2, 3))
    _set("peak_velocity", round(max(z_rms, x_rms) * 1.05, 3))

    if "iso_class" not in sensor:
        sensor["iso_class"] = "B" if z_rms < 2.3 else ("C" if z_rms < 4.5 else "D")
    if "alarm_status" not in sensor:
        sensor["alarm_status"] = "normal" if z_rms < 2.8 else ("warning" if z_rms < 4.0 else "alarm")

    return sensor


def _generate_demo_sensor() -> Dict[str, Any]:
    """Synthetic oscillating data — ONLY used when demo mode is explicitly on.

    All 21 register-mapped fields are present (addresses 45201-45221).
    in/sec values are derived from mm/s using 1 in = 25.4 mm.
    """
    t = time.time()
    base_z = 1.8 + 0.8 * math.sin(t * 0.3) + random.uniform(-0.1, 0.1)
    base_x = 1.4 + 0.6 * math.sin(t * 0.4 + 1.0) + random.uniform(-0.1, 0.1)
    temp_c = 38.5 + 2.0 * math.sin(t * 0.05) + random.uniform(-0.2, 0.2)
    kurtosis_val = 3.2 + 1.5 * abs(math.sin(t * 0.15)) + random.uniform(-0.1, 0.1)

    z_rms = round(max(0.1, base_z), 3)
    x_rms = round(max(0.1, base_x), 3)
    z_peak = round(z_rms * 1.42 + random.uniform(-0.05, 0.05), 3)
    x_peak = round(x_rms * 1.42 + random.uniform(-0.05, 0.05), 3)
    z_accel = round(z_rms * 0.65 + random.uniform(-0.05, 0.05), 3)
    x_accel = round(x_rms * 0.55 + random.uniform(-0.05, 0.05), 3)
    z_kurtosis = round(kurtosis_val + random.uniform(-0.05, 0.05), 3)
    x_kurtosis = round(kurtosis_val * 0.9 + random.uniform(-0.05, 0.05), 3)
    z_crest = round(z_kurtosis * 0.85 + random.uniform(-0.05, 0.05), 3)
    x_crest = round(x_kurtosis * 0.85 + random.uniform(-0.05, 0.05), 3)
    freq_z = round(9.5 + random.uniform(-0.5, 0.5), 1)
    freq_x = round(11.2 + random.uniform(-0.5, 0.5), 1)
    temperature = round(temp_c, 1)

    return {
        "z_rms": z_rms, "x_rms": x_rms,
        "z_peak": z_peak, "x_peak": x_peak,
        "z_peak_vel_mm": z_peak, "x_peak_vel_mm": x_peak,
        "z_rms_in": round(z_rms / 25.4, 4), "x_rms_in": round(x_rms / 25.4, 4),
        "z_peak_vel_in": round(z_peak / 25.4, 4), "x_peak_vel_in": round(x_peak / 25.4, 4),
        "z_accel": z_accel, "x_accel": x_accel,
        "z_rms_accel": z_accel, "x_rms_accel": x_accel,
        "z_peak_accel": round(z_accel * 1.45 + random.uniform(-0.03, 0.03), 3),
        "x_peak_accel": round(x_accel * 1.45 + random.uniform(-0.03, 0.03), 3),
        "z_hf_rms_accel": round(z_accel * 0.35 + random.uniform(-0.01, 0.01), 3),
        "temperature": temperature, "temp_f": round(temperature * 9 / 5 + 32, 1),
        "z_peak_freq": freq_z, "x_peak_freq": freq_x,
        "kurtosis": round(kurtosis_val, 3),
        "z_kurtosis": z_kurtosis, "x_kurtosis": x_kurtosis,
        "crest_factor": z_crest, "z_crest_factor": z_crest, "x_crest_factor": x_crest,
        "rms_overall": round(math.sqrt(z_rms**2 + x_rms**2), 3),
        "energy": round((z_rms**2 + x_rms**2) * 100, 1),
        "bearing_health": round(max(50, min(100, 95 - kurtosis_val * 2 + random.uniform(-1, 1))), 1),
        "iso_class": "B" if z_rms < 2.3 else ("C" if z_rms < 4.5 else "D"),
        "alarm_status": "normal" if z_rms < 2.8 else ("warning" if z_rms < 4.0 else "alarm"),
        "humidity": round(45 + random.uniform(-3, 3), 1),
        "frequency": freq_z,
        "vibration_trend": round(random.uniform(-0.02, 0.02), 4),
        "temp_trend": round(random.uniform(-0.01, 0.01), 4),
        "uptime": int(time.time() - _state["connect_time"]) if _state.get("connect_time") else 0,
        "sensor_status": "demo", "data_quality": 98,
        "peak_accel": round(max(z_accel, x_accel) * 1.2, 3),
        "peak_velocity": round(max(z_rms, x_rms) * 1.05, 3),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _rule_based_ml(sensor: Dict[str, Any]) -> Dict[str, Any]:
    """Simple rule-based ML prediction derived from sensor values."""
    z_rms = sensor.get("z_rms", 0.0)
    kurtosis = sensor.get("kurtosis", 0.0)
    crest = sensor.get("crest_factor", 0.0)
    temp = sensor.get("temperature", 0.0)

    # Score severity based on multiple thresholds
    score = 0.0
    if z_rms > 7.1:   score += 0.5   # ISO class D+
    elif z_rms > 4.5: score += 0.3   # ISO class C
    elif z_rms > 1.8: score += 0.1   # ISO class B
    if kurtosis > 10: score += 0.3
    elif kurtosis > 6: score += 0.1
    if crest > 8:     score += 0.2
    elif crest > 5:   score += 0.05
    if temp > 70:     score += 0.2
    elif temp > 55:   score += 0.1

    score = min(score, 1.0)
    is_anomaly = score >= 0.4

    normal_prob   = round(1.0 - score, 4)
    anomaly_prob  = round(score, 4)
    confidence    = round(max(normal_prob, anomaly_prob), 4)
    cls           = 1 if is_anomaly else 0
    cls_name      = "anomaly" if is_anomaly else "normal"

    # ISO severity
    if z_rms <= 1.8:
        iso_lvl, iso_cls, iso_color, iso_desc = "A", "A", "green", "Very good — new machinery"
    elif z_rms <= 4.5:
        iso_lvl, iso_cls, iso_color, iso_desc = "B", "B", "green", "Good — new machines in this zone"
    elif z_rms <= 7.1:
        iso_lvl, iso_cls, iso_color, iso_desc = "C", "C", "yellow", "Acceptable — damaged machines in this zone"
    elif z_rms <= 11.2:
        iso_lvl, iso_cls, iso_color, iso_desc = "D", "D", "orange", "Warning — check bearings & alignment"
    else:
        iso_lvl, iso_cls, iso_color, iso_desc = "E", "E", "red",    "Danger — immediate maintenance required"

    return {
        "ml": {
            "class": cls,
            "class_name": cls_name,
            "confidence": confidence,
            "probabilities": {"normal": normal_prob, "anomaly": anomaly_prob},
            "feature_importance": {
                "z_rms": 0.35, "kurtosis": 0.25, "crest_factor": 0.20,
                "temperature": 0.12, "x_rms": 0.08,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "iso": {
            "level": iso_lvl, "class": iso_cls, "color": iso_color,
            "description": iso_desc, "rms_velocity": z_rms,
        },
    }


def _build_ws_payload() -> Dict[str, Any]:
    """Build the WebSocket broadcast payload.

    Priority (strict):
      1. Connected to real Modbus device   → live sensor data from saved state.
      2. Demo mode explicitly toggled ON   → synthetic oscillating data.
      3. Disconnected but has saved data   → stale data (keep connected=True so
                                             all pages stay ONLINE while we auto-reconnect).
      4. Idle / no data at all            → all-zero idle payload.
    """
    if _state["connected"]:
        saved = _load_json(SENSOR_STATE_FILE, {})
        if saved.get("sensor_data"):
            sensor = saved["sensor_data"]
            sensor = _enrich_sensor(sensor)
            # If we are missing polls, mark it as stale
            if _state.get("packet_loss", 0.0) >= 3.3:
                sensor["sensor_status"] = "stale"
                sensor["data_quality"] = max(0, 95 - int(_state["packet_loss"]))
                source = "stale"
            else:
                sensor["sensor_status"] = "live"
                sensor["data_quality"] = 95
                source = "live"
            sensor["timestamp"] = saved.get("last_updated", sensor.get("timestamp"))
        else:
            sensor = _idle_sensor()
            sensor["sensor_status"] = "connecting"
            source = "live"
        device_connected = True
    elif _state["demo_mode"]:
        sensor = _generate_demo_sensor()
        source = "demo"
        device_connected = True
    else:
        # Not connected — show last known data as stale so pages don't go OFFLINE
        # while auto-reconnect is in progress.  Only show idle (zeros) if there
        # is truly no prior data at all.
        saved = _load_json(SENSOR_STATE_FILE, {})
        if saved.get("sensor_data"):
            sensor = saved["sensor_data"]
            sensor = _enrich_sensor(sensor)
            sensor["sensor_status"] = "stale"
            sensor["data_quality"] = 50
            source = "stale"
            device_connected = False   # actually disconnected!
        else:
            sensor = _idle_sensor()
            source = "idle"
            device_connected = False

    z_rms = sensor.get("z_rms", 0.0)
    has_real_data = _state["connected"] or _state["demo_mode"] or (z_rms > 0.0 or sensor.get("temperature", 0.0) > 0.0)

    # Rule-based ML prediction (replaces None so ML tab always renders)
    if has_real_data:
        analysis = _rule_based_ml(sensor)
        ml_pred  = analysis["ml"]
        iso_sev  = analysis["iso"]
    else:
        ml_pred = None
        iso_sev = {
            "level": "—", "class": "—", "color": "gray",
            "description": "No device connected",
            "rms_velocity": 0.0,
        }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sensor_data": sensor,
        "features": {
            "z_rms": z_rms,
            "x_rms": sensor.get("x_rms", 0.0),
            "temperature": sensor.get("temperature", 0.0),
            "kurtosis": sensor.get("kurtosis", 0.0),
        },
        "ml_prediction": ml_pred,
        "iso_severity": iso_sev,
        "connection_status": {
            "connected": device_connected,
            "stale": source == "stale",
            "port": _state["port"],
            "baud": _state["baud"],
            "slave_id": _state["slave_id"],
            "uptime_seconds": _state["uptime_seconds"],
            "last_poll": _state.get("last_poll") or (
                datetime.now(timezone.utc).isoformat() if device_connected else None
            ),
            "packet_loss": _state["packet_loss"],
            "auto_reconnect": _state["auto_reconnect"],
        },
        "source": source,
    }


# ─── Lifespan ─────────────────────────────────────────────────────────────────

# ─── Register → field conversion ─────────────────────────────────────────────
# DXM actual register map (22 holding registers, starting at address 5200 primary, 0 fallback)
# Matches backend/core/data_receiver.py exactly:
#  R0  Z-Axis RMS (g)          ÷100    R1  Z-RMS vel (mm/s)       ÷1000
#  R2  ISO Peak-Peak (mm/s)    ÷1000   R3  Temperature (°C signed) ÷100
#  R4  Z-True Peak (mm/s)      ÷1000   R5  X-RMS vel (mm/s)        ÷1000
#  R6  Z-Peak Accel (g)        ÷1000   R7  X-Peak Accel (g)        ÷1000
#  R8  Z-Peak Freq (Hz)        ÷10     R9  X-Peak Freq (Hz)         ÷10
#  R10 Z-Band RMS (mm/s)       ÷1000   R11 X-Band RMS (mm/s)       ÷1000
#  R12 Z-Kurtosis              ÷1000   R13 X-Kurtosis              ÷1000
#  R14 Z-Crest Factor          ÷1000   R15 X-Crest Factor          ÷1000
#  R16 Z-HF RMS Accel (g)      ÷1000   R17 Z-Peak vel (mm/s)       ÷1000
#  R18 X-HF RMS Accel (g)      ÷1000   R19 X-Peak vel (mm/s)       ÷1000
#  R20 Device Status (raw int)          R21 reserved
_REG_ADDR_PRIMARY = 5200    # DXM primary Modbus address block
_REG_ADDR_FALLBACK = 0      # Fallback address block (some DXM firmware)
_REG_COUNT = 22


def _registers_to_sensor(regs: List[int], read_source: str = "unknown") -> Dict[str, Any]:
    """Convert raw DXM register array → full sensor dict.

    Register map matches data_receiver.py exactly.
    """
    def _g(idx: int, div: float = 1.0) -> float:
        try:
            return round(regs[idx] / div, 4) if idx < len(regs) else 0.0
        except Exception:
            return 0.0

    def _signed(val: float) -> float:
        """Convert unsigned 16-bit encoded signed value (÷100)."""
        return val - 655.36 if val > 327.67 else val

    z_axis_rms    = _g(0,  100.0)
    z_rms         = _g(1,  1000.0)
    iso_peak_peak = _g(2,  1000.0)
    temperature   = _signed(_g(3, 100.0))
    z_true_peak   = _g(4,  1000.0)
    x_rms         = _g(5,  1000.0)
    z_peak_accel  = _g(6,  1000.0)
    x_peak_accel  = _g(7,  1000.0)
    z_peak_freq   = _g(8,  10.0)
    x_peak_freq   = _g(9,  10.0)
    z_band_rms    = _g(10, 1000.0)
    x_band_rms    = _g(11, 1000.0)
    z_kurtosis    = _g(12, 1000.0)
    x_kurtosis    = _g(13, 1000.0)
    z_crest       = _g(14, 1000.0)
    x_crest       = _g(15, 1000.0)
    z_hf_rms      = _g(16, 1000.0)
    z_peak_vel    = _g(17, 1000.0)
    x_hf_rms      = _g(18, 1000.0)
    x_peak_vel    = _g(19, 1000.0)
    device_status = int(regs[20]) if len(regs) > 20 else 0

    temp_f      = round(temperature * 9 / 5 + 32, 1)
    rms_overall = round(math.sqrt(z_rms**2 + x_rms**2), 3)
    connect_t   = _state.get("connect_time") or time.time()

    return {
        # Velocity mm/s
        "z_rms":           round(z_rms, 3),
        "x_rms":           round(x_rms, 3),
        "z_peak":          round(z_true_peak, 3),
        "x_peak":          round(x_peak_vel, 3),
        "z_peak_vel_mm":   round(z_peak_vel, 3),
        "x_peak_vel_mm":   round(x_peak_vel, 3),
        # Velocity in/sec (derived)
        "z_rms_in":        round(z_rms / 25.4, 4),
        "x_rms_in":        round(x_rms / 25.4, 4),
        "z_peak_vel_in":   round(z_peak_vel / 25.4, 4),
        "x_peak_vel_in":   round(x_peak_vel / 25.4, 4),
        # Acceleration g
        "z_accel":         round(z_peak_accel, 3),
        "x_accel":         round(x_peak_accel, 3),
        "z_peak_accel":    round(z_peak_accel, 3),
        "x_peak_accel":    round(x_peak_accel, 3),
        "z_rms_accel":     round(z_band_rms, 3),
        "x_rms_accel":     round(x_band_rms, 3),
        "z_hf_rms_accel":  round(z_hf_rms, 4),
        "x_hf_rms_accel":  round(x_hf_rms, 4),
        # Temperature
        "temperature":     round(temperature, 1),
        "temp_f":          temp_f,
        # Frequency
        "z_peak_freq":     round(z_peak_freq, 1),
        "x_peak_freq":     round(x_peak_freq, 1),
        "frequency":       round(z_peak_freq, 1),
        # Statistical
        "z_kurtosis":      round(z_kurtosis, 3),
        "x_kurtosis":      round(x_kurtosis, 3),
        "kurtosis":        round(z_kurtosis, 3),
        "z_crest_factor":  round(z_crest, 3),
        "x_crest_factor":  round(x_crest, 3),
        "crest_factor":    round(z_crest, 3),
        # Additional DXM fields
        "z_axis_rms":      round(z_axis_rms, 4),
        "iso_peak_peak":   round(iso_peak_peak, 3),
        "z_true_peak":     round(z_true_peak, 3),
        "z_band_rms":      round(z_band_rms, 3),
        "x_band_rms":      round(x_band_rms, 3),
        "device_status":   device_status,
        # Derived / aggregate
        "rms_overall":     rms_overall,
        "energy":          round((z_rms**2 + x_rms**2) * 100, 1),
        "bearing_health":  round(max(0.0, min(100.0, 100.0 - (z_rms * 10.0))), 1),
        "iso_class":       "B" if z_rms < 2.3 else ("C" if z_rms < 4.5 else "D"),
        "alarm_status":    "normal" if z_rms < 2.8 else ("warning" if z_rms < 4.0 else "alarm"),
        "peak_accel":      round(max(z_peak_accel, x_peak_accel) * 1.2, 3),
        "peak_velocity":   round(max(z_rms, x_rms) * 1.05, 3),
        # Constants / metadata
        "humidity":        0.0,
        "vibration_trend": 0.0,
        "temp_trend":      0.0,
        "raw_registers":   list(regs),
        "non_zero_registers": sum(1 for r in regs if r != 0),
        "register_source": read_source,
        "sensor_status":   "live",
        "data_quality":    95,
        "uptime":          int(time.time() - connect_t),
        "timestamp":       datetime.now(timezone.utc).isoformat(),
    }


async def _modbus_poll_loop() -> None:
    """Background task: poll DXM Modbus registers at 1 Hz and save to sensor_state.json.

    Tries address 5200 first (DXM primary block), falls back to address 0.
    Auto-reconnects when the DXM drops the TCP connection (which it does periodically).
    Only marks connected=False after 30 consecutive failures with no successful reconnect.
    """
    global _modbus_client
    consecutive_failures = 0
    reconnect_attempts = 0
    read_source = "5200"
    logger.info("Modbus poll loop started (will try addr=5200 then addr=0)")

    while _state["connected"] and _modbus_client:
        try:
            slave_id = _state.get("slave_id", 1)

            # Auto-reconnect if client reports not connected
            if not _modbus_client.is_connected() and consecutive_failures >= 1:
                port_label = _state.get("port", "")
                if port_label.startswith("TCP:"):
                    parts = port_label.split(":")  # TCP:192.168.0.1:502
                    host = parts[1]
                    tcp_port = int(parts[2]) if len(parts) > 2 else 502
                    logger.info(
                        "TCP connection lost — reconnecting to %s:%d (attempt #%d)…",
                        host, tcp_port, reconnect_attempts + 1,
                    )
                    ok = await _modbus_client.connect_tcp(host, tcp_port, slave_id)
                    if ok:
                        consecutive_failures = 0
                        reconnect_attempts += 1
                        logger.info("Reconnected to %s:%d successfully", host, tcp_port)
                    else:
                        logger.warning("Reconnect failed (attempt #%d)", reconnect_attempts + 1)
                        reconnect_attempts += 1
                        await asyncio.sleep(2.0)
                        continue

            # Try primary address (DXM Modbus block)
            regs = await _modbus_client.read_holding_registers(
                address=_REG_ADDR_PRIMARY, count=_REG_COUNT, slave_id=slave_id
            )
            read_source = "5200"

            # Fallback to address 0 if primary returns nothing or all zeros
            if regs is None or all(r == 0 for r in regs):
                regs = await _modbus_client.read_holding_registers(
                    address=_REG_ADDR_FALLBACK, count=_REG_COUNT, slave_id=slave_id
                )
                read_source = "0"

            if regs is not None:
                sensor = _registers_to_sensor(regs, read_source)
                _state["last_poll"] = sensor["timestamp"]
                _state["uptime_seconds"] = sensor["uptime"]
                _state["packet_loss"] = 0.0
                consecutive_failures = 0
                reconnect_attempts = 0

                _save_json(SENSOR_STATE_FILE, {
                    "last_updated": sensor["timestamp"],
                    "sensor_data": sensor,
                })
                logger.info(
                    "Poll OK [addr=%s]: z_rms=%.3f x_rms=%.3f temp=%.1f°C nz=%d",
                    read_source, sensor["z_rms"], sensor["x_rms"],
                    sensor["temperature"], sensor["non_zero_registers"],
                )
            else:
                consecutive_failures += 1
                _state["packet_loss"] = min(100.0, consecutive_failures * 3.3)
                logger.warning(
                    "Modbus poll: no data at addr 5200 or 0 (failure #%d)", consecutive_failures
                )

                if consecutive_failures >= 30:
                    logger.error("30 consecutive poll failures — marking disconnected")
                    _state["connected"] = False
                    break

        except asyncio.CancelledError:
            break
        except Exception as exc:
            consecutive_failures += 1
            logger.error("Poll loop error: %s", exc)
            if consecutive_failures >= 30:
                logger.error("30 consecutive errors — marking disconnected")
                _state["connected"] = False
                break

        await asyncio.sleep(1.0)

    logger.info("Modbus poll loop stopped")


async def _start_modbus_connection(req_data: Dict[str, Any]) -> Dict[str, Any]:
    """Actually connect to the Modbus device and start the poll loop."""
    global _modbus_client, _poll_task

    # Cancel any existing poll task
    if _poll_task and not _poll_task.done():
        _poll_task.cancel()
        try:
            await _poll_task
        except asyncio.CancelledError:
            pass
    _poll_task = None

    if not _MODBUS_AVAILABLE:
        return {"success": False, "message": "pymodbus not installed"}

    proto = (req_data.get("protocol") or "RTU").upper()
    slave_id = req_data.get("slave_id", 1)

    if _modbus_client is None:
        _modbus_client = UnifiedModbusClient()

    if proto == "TCP":
        host = req_data.get("host") or str(req_data.get("port", "127.0.0.1"))
        tcp_port = int(req_data.get("tcp_port", 502))
        # Provide a top-level timeout to prevent UI from hanging indefinitely
        try:
            ok = await asyncio.wait_for(
                _modbus_client.connect_tcp(host=host, port=tcp_port, slave_id=slave_id),
                timeout=req_data.get("timeout", 5.0)
            )
        except asyncio.TimeoutError:
            logger.error("Connect TCP timed out")
            ok = False
        except Exception as exc:
            logger.error("Connect TCP failed: %s", exc)
            ok = False
        port_label = f"TCP:{host}:{tcp_port}"
    else:
        serial_port = str(req_data.get("port") or "COM1")
        baud = int(req_data.get("baud") or req_data.get("baudrate") or 19200)
        try:
            ok = await asyncio.wait_for(
                _modbus_client.connect_rtu(port=serial_port, baudrate=baud, slave_id=slave_id),
                timeout=req_data.get("timeout", 5.0)
            )
        except asyncio.TimeoutError:
            logger.error("Connect RTU timed out")
            ok = False
        except Exception as exc:
            logger.error("Connect RTU failed: %s", exc)
            ok = False
        port_label = serial_port


    if ok:
        _state["connected"] = True
        _state["demo_mode"] = False
        _state["port"] = port_label
        _state["baud"] = req_data.get("baud") or req_data.get("baudrate") or 19200
        _state["slave_id"] = slave_id
        _state["connect_time"] = time.time()
        _state["uptime_seconds"] = 0
        _state["packet_loss"] = 0.0
        # Clear stale sensor state so WS shows "connecting" until first real poll
        _save_json(SENSOR_STATE_FILE, {})
        _poll_task = asyncio.create_task(_modbus_poll_loop())
        logger.info("Connected to %s — poll loop started", port_label)
        return {"success": True, "message": f"Connected to {port_label} and polling started"}
    else:
        logger.warning("Failed to connect to %s", port_label)
        return {"success": False, "message": f"Could not connect to {port_label}"}


async def _stop_modbus_connection() -> None:
    """Stop the poll loop and disconnect the Modbus client."""
    global _modbus_client, _poll_task
    _state["connected"] = False
    _state["connect_time"] = None

    if _poll_task and not _poll_task.done():
        _poll_task.cancel()
        try:
            await _poll_task
        except asyncio.CancelledError:
            pass
    _poll_task = None

    if _modbus_client:
        await _modbus_client.disconnect()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("✅ Gandiva Pro backend started (port 8000)")
    yield
    await _stop_modbus_connection()
    logger.info("🛑 Gandiva Pro backend stopped")


# ─── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Gandiva Pro API",
    description="Railway Rolling Stock Monitoring System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic models ──────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    # Serial-style (from lib/api.ts)
    port: Optional[Any] = None      # str for COM ports, int (502) for TCP port
    baud: Optional[int] = None
    slave_id: int = 1
    # TCP-style (from DeviceManagementTab.tsx)
    protocol: Optional[str] = None  # "TCP" | "RTU"
    host: Optional[str] = None
    baudrate: Optional[int] = None  # alternative to baud
    timeout: Optional[float] = None


class DeviceConnectRequest(BaseModel):
    """Used by /api/v1/connect (Connection.tsx)"""
    ip: str
    port: int = 502
    slave_id: int = 1
    connection_type: str = "tcp"
    timeout: float = 5.0


class ThresholdConfig(BaseModel):
    id: str
    parameter: str
    parameterLabel: Optional[str] = None
    unit: Optional[str] = None
    minLimit: float
    maxLimit: float


class ControllerThresholdConfig(BaseModel):
    id: str
    parameter: str
    parameterLabel: Optional[str] = None
    unit: Optional[str] = None
    warningLimit: float
    alertLimit: float


class AlertCreate(BaseModel):
    alert_type: str = "manual"
    severity: str = "warning"
    message: str
    parameter: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None


# ─────────────────────────────────────────────────────────────────────────────
# ROOT / HEALTH
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Gandiva Pro API v1.0", "docs": "/docs", "health": "/health"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/v1/health")
async def health_v1():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# ─────────────────────────────────────────────────────────────────────────────
# DEMO MODE
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/demo/status")
async def demo_status():
    return {
        "demo_mode": _state["demo_mode"],
        "modbus_connected": _state["connected"],
        "active_connections": 1 if (_state["connected"] or _state["demo_mode"]) else 0,
        "message": "Demo mode active — synthetic data" if _state["demo_mode"] else "Live Modbus connection",
    }


@app.post("/api/v1/demo/toggle")
async def demo_toggle():
    _state["demo_mode"] = not _state["demo_mode"]
    return {
        "demo_mode": _state["demo_mode"],
        "message": "Demo mode enabled" if _state["demo_mode"] else "Demo mode disabled — connect a device",
    }


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTION
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/connection/status")
async def connection_status():
    return {
        "connected": _state["connected"],
        "demo_mode": _state["demo_mode"],
        "port": _state["port"],
        "baud": _state["baud"],
        "slave_id": _state["slave_id"],
        "uptime_seconds": _state["uptime_seconds"],
        "last_poll": _state["last_poll"],
        "packet_loss": _state["packet_loss"],
        "auto_reconnect": _state["auto_reconnect"],
    }


@app.post("/api/v1/connection/scan")
async def scan_ports():
    """Detect available serial ports."""
    ports = []
    try:
        import serial.tools.list_ports  # type: ignore
        ports = [
            {"device": p.device, "description": p.description or "Unknown", "hwid": p.hwid or "Unknown"}
            for p in serial.tools.list_ports.comports()
        ]
    except Exception:
        pass
    return {"ports": ports}


@app.post("/api/v1/connection/connect")
async def connect(req: ConnectRequest):
    result = await _start_modbus_connection({
        "protocol": req.protocol,
        "port": req.port,
        "host": req.host,
        "baud": req.baud,
        "baudrate": req.baudrate,
        "slave_id": req.slave_id,
        "tcp_port": req.port if isinstance(req.port, int) else 502,
    })
    return result


@app.post("/api/v1/connection/disconnect")
async def disconnect():
    await _stop_modbus_connection()
    _state["port"] = None
    return {"success": True, "message": "Disconnected"}


# ─────────────────────────────────────────────────────────────────────────────
# NETWORK SCAN  (Connection.tsx and DeviceManagementTab.tsx)
# ─────────────────────────────────────────────────────────────────────────────

_scans: Dict[str, Any] = {}
_connected_devices: Dict[str, Any] = {}


def _quick_tcp_ping(ip: str, port: int = 502, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


async def _run_network_scan(scan_id: str, network_range: str, timeout: float = 0.5):
    """Background scan for Modbus TCP devices — fully async, all hosts probed in parallel."""
    found_ips: List[str] = []

    async def _probe(ip_str: str) -> None:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip_str, 502),
                timeout=min(float(timeout), 2.0),
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            found_ips.append(ip_str)
        except Exception:
            pass

    try:
        net = ipaddress.IPv4Network(network_range, strict=False)
        hosts = [str(h) for h in list(net.hosts())[:254]]
        await asyncio.gather(*[_probe(ip) for ip in hosts])
        _scans[scan_id].update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "network_devices": sorted(found_ips),
            "modbus_devices": [
                {"ip": ip, "port": 502, "slave_id": 1, "status": "reachable"}
                for ip in sorted(found_ips)
            ],
            "scan_duration": None,
        })
    except Exception as exc:
        _scans[scan_id].update({"status": "failed", "error": str(exc)})


@app.post("/api/v1/connection/scan-network")
async def scan_network_get(subnet: str = Query("192.168.0"), background_tasks=None):
    """DeviceManagementTab: POST /api/v1/connection/scan-network?subnet=192.168.0"""
    network_range = f"{subnet}.0/24"
    scan_id = f"scan_{int(time.time())}"
    _scans[scan_id] = {
        "scan_id": scan_id, "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None, "network_devices": [], "modbus_devices": [],
    }
    asyncio.create_task(_run_network_scan(scan_id, network_range, 0.5))
    # Wait up to 4 seconds then return whatever we have (parallel scan is fast)
    for _ in range(8):
        await asyncio.sleep(0.5)
        if _scans[scan_id]["status"] != "running":
            break
    return {"scan_id": scan_id, "devices": _scans[scan_id]["network_devices"], **_scans[scan_id]}


class NetworkScanBody(BaseModel):
    network_range: str
    scan_type: str = "quick"
    timeout: float = 2.0


@app.post("/api/v1/scan/network")
async def start_network_scan(body: NetworkScanBody):
    """Connection.tsx: POST /api/v1/scan/network"""
    scan_id = f"scan_{int(time.time())}"
    _scans[scan_id] = {
        "scan_id": scan_id, "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None, "network_devices": [], "modbus_devices": [],
    }
    asyncio.create_task(_run_network_scan(scan_id, body.network_range, body.timeout))
    return {"scan_id": scan_id, "status": "started"}


@app.get("/api/v1/scan/{scan_id}")
async def get_scan_status(scan_id: str):
    if scan_id not in _scans:
        raise HTTPException(status_code=404, detail="Scan not found")
    return _scans[scan_id]


@app.get("/api/v1/interfaces")
async def get_interfaces():
    """Return network interfaces for the Connection page."""
    interfaces: List[Dict[str, Any]] = []
    try:
        import socket
        hostname = socket.gethostname()
        ips = socket.gethostbyname_ex(hostname)[2]
        for ip in ips:
            interfaces.append({"name": "eth0", "ip": ip, "status": "up"})
    except Exception:
        interfaces = [{"name": "eth0", "ip": "127.0.0.1", "status": "up"}]
    return {"interfaces": interfaces}


@app.get("/api/v1/network/ranges")
async def get_network_ranges():
    """Return detected network ranges."""
    ranges: List[str] = ["192.168.0.0/24", "192.168.1.0/24"]
    return {"network_ranges": ranges}


@app.get("/api/v1/connected")
async def get_connected_devices():
    return {"connected_devices": list(_connected_devices.values())}


@app.post("/api/v1/connect")
async def connect_device(req: DeviceConnectRequest):
    """Connection.tsx: POST /api/v1/connect"""
    device_id = f"device_{req.ip}_{req.slave_id}"
    _connected_devices[device_id] = {
        "device_id": device_id,
        "ip": req.ip,
        "port": req.port,
        "slave_id": req.slave_id,
        "connection_type": req.connection_type,
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "status": "connected",
    }
    _state["connected"] = True
    _state["demo_mode"] = False
    _state["port"] = f"TCP:{req.ip}:{req.port}"
    return {
        "device_id": device_id,
        "status": "connected",
        "ip": req.ip,
        "port": req.port,
        "slave_id": req.slave_id,
    }


@app.delete("/api/v1/disconnect/{device_id}")
async def disconnect_device(device_id: str):
    """Connection.tsx: DELETE /api/v1/disconnect/{device_id}"""
    _connected_devices.pop(device_id, None)
    if not _connected_devices:
        _state["connected"] = False
    return {"success": True, "message": f"Device {device_id} disconnected"}


# ─────────────────────────────────────────────────────────────────────────────
# THRESHOLDS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/thresholds/get")
async def get_thresholds():
    thresholds = _load_json(THRESHOLDS_FILE, [])
    return {"thresholds": thresholds}


@app.post("/api/v1/thresholds/save")
async def save_thresholds(body: Any = Body(...)):
    # Accept both a JSON array and a single object
    items = body if isinstance(body, list) else [body]
    try:
        data = [ThresholdConfig(**i).model_dump() for i in items]
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if _save_json(THRESHOLDS_FILE, data):
        return {"success": True, "message": "Thresholds saved"}
    raise HTTPException(status_code=500, detail="Failed to save thresholds")


@app.get("/api/v1/controller-thresholds/get")
async def get_controller_thresholds():
    thresholds = _load_json(CTRL_THRESHOLDS_FILE, [])
    return {"thresholds": thresholds}


@app.post("/api/v1/controller-thresholds/save")
async def save_controller_thresholds(body: Any = Body(...)):
    items = body if isinstance(body, list) else [body]
    try:
        data = [ControllerThresholdConfig(**i).model_dump() for i in items]
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if _save_json(CTRL_THRESHOLDS_FILE, data):
        return {"success": True, "message": "Controller thresholds saved"}
    raise HTTPException(status_code=500, detail="Failed to save controller thresholds")


# ─────────────────────────────────────────────────────────────────────────────
# ALERTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/alerts")
async def get_alerts(
    limit: int = Query(100, ge=1, le=1000),
    acknowledged: Optional[bool] = Query(None),
    severity: Optional[str] = Query(None),
):
    result = list(_alerts)
    if acknowledged is not None:
        result = [a for a in result if a["acknowledged"] == acknowledged]
    if severity:
        result = [a for a in result if a["severity"] == severity]
    return result[-limit:]


@app.get("/api/v1/alerts/active")
async def get_active_alerts():
    active = [a for a in _alerts if not a["acknowledged"]]
    # Return {alerts: [...]} for AlertsEnhanced.tsx; lib/api.ts uses response.data directly
    return {"alerts": active}


@app.post("/api/v1/alerts/clear")
async def clear_alerts():
    global _alerts
    _alerts = []
    return {"success": True, "message": "All alerts cleared"}


@app.post("/api/v1/alerts")
async def create_alert(alert: AlertCreate):
    global _alert_id_counter
    new_alert = {
        "id": _alert_id_counter,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "message": alert.message,
        "parameter": alert.parameter,
        "value": alert.value,
        "threshold": alert.threshold,
        "ml_confidence": None,
        "acknowledged": False,
        "acknowledged_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _alerts.append(new_alert)
    _alert_id_counter += 1
    return new_alert


@app.post("/api/v1/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    for alert in _alerts:
        if alert["id"] == alert_id:
            alert["acknowledged"] = True
            alert["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
            return {"success": True, "alert": alert}
    raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")


@app.delete("/api/v1/alerts/{alert_id}")
async def delete_alert(alert_id: int):
    global _alerts
    before = len(_alerts)
    _alerts = [a for a in _alerts if a["id"] != alert_id]
    if len(_alerts) == before:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────────────────────

def _get_chart_points() -> List[Any]:
    """Extract the list of data points from chart_data.json regardless of format."""
    raw = _load_json(CHART_DATA_FILE, [])
    if isinstance(raw, dict):
        return raw.get("data_points", raw.get("data", []))
    return raw if isinstance(raw, list) else []


@app.get("/api/v1/data/chart")
async def get_chart_data():
    return _get_chart_points()


@app.get("/api/v1/data/batch")
async def get_data_batch(limit: int = Query(100, ge=1, le=10000)):
    points = _get_chart_points()
    return points[-limit:]


@app.get("/api/v1/metrics")
async def get_metrics():
    saved = _load_json(SENSOR_STATE_FILE, {})
    sensor = saved.get("sensor_data", {})
    return {
        "uptime": _state["uptime_seconds"],
        "connected": _state["connected"],
        "demo_mode": _state["demo_mode"],
        "z_rms": sensor.get("z_rms", 0),
        "x_rms": sensor.get("x_rms", 0),
        "temperature": sensor.get("temperature", 0),
        "bearing_health": sensor.get("bearing_health", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# LOGS
# ─────────────────────────────────────────────────────────────────────────────

LOG_FILES = {
    "app": LOGS_DIR / "app.log",
    "errors": LOGS_DIR / "errors.log",
    "modbus": LOGS_DIR / "modbus.log",
    "readings": LOGS_DIR / "readings.log",
}

LOG_LEVEL_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[^\s]*)?\s*"
    r"(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)?",
    re.IGNORECASE,
)


def _parse_log_line(line: str) -> Dict[str, Any]:
    m = LOG_LEVEL_PATTERN.match(line)
    timestamp = None
    level = "INFO"
    if m:
        timestamp = m.group("timestamp")
        level = (m.group("level") or "INFO").upper()
    return {"timestamp": timestamp, "level": level, "message": line.strip(), "raw": line.rstrip()}


@app.get("/api/v1/logs/offline")
async def get_offline_logs(
    file: str = Query("app"),
    limit: int = Query(200, ge=1, le=5000),
    search: Optional[str] = Query(None),
):
    # Sanitize file parameter to prevent path traversal
    if file not in LOG_FILES:
        raise HTTPException(status_code=400, detail=f"Unknown log file: {file}. Valid: {list(LOG_FILES)}")

    log_path = LOG_FILES[file]
    if not log_path.exists():
        return {"file": file, "count": 0, "entries": []}

    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if search:
        lines = [l for l in lines if search.lower() in l.lower()]

    lines = lines[-limit:]
    entries = [_parse_log_line(l) for l in lines]
    return {"file": file, "count": len(entries), "entries": entries}


@app.get("/api/v1/logs/offline/stats")
async def get_log_stats(file: str = Query("app")):
    if file not in LOG_FILES:
        raise HTTPException(status_code=400, detail=f"Unknown log file: {file}")

    log_path = LOG_FILES[file]
    if not log_path.exists():
        return {
            "file": file, "exists": False, "size_bytes": 0, "size_mb": 0.0,
            "line_count": 0, "level_counts": {}, "last_updated": None,
        }

    stat = log_path.stat()
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        lines = []

    level_counts: Dict[str, int] = {}
    for l in lines:
        entry = _parse_log_line(l)
        level_counts[entry["level"]] = level_counts.get(entry["level"], 0) + 1

    return {
        "file": file,
        "exists": True,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 3),
        "line_count": len(lines),
        "level_counts": level_counts,
        "last_updated": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# WEBSOCKET — real-time streaming
# ─────────────────────────────────────────────────────────────────────────────

async def _ws_client_handler(websocket: WebSocket, label: str = "") -> None:
    """Accept a WebSocket, send 1 Hz payloads, and keep alive until disconnect."""
    await websocket.accept()
    if label:
        logger.info("WebSocket client connected [%s]", label)

    async def _send_loop() -> None:
        while True:
            try:
                payload = _build_ws_payload()
                _state["uptime_seconds"] = (
                    int(time.time() - _state["connect_time"])
                    if _state.get("connect_time")
                    else _state.get("uptime_seconds", 0)
                )
                await websocket.send_json(payload)
            except Exception:
                break
            await asyncio.sleep(1.0)

    send_task = asyncio.create_task(_send_loop())
    try:
        while True:
            try:
                await websocket.receive_text()  # wait for client pings / close
            except WebSocketDisconnect:
                break
            except Exception:
                break
    finally:
        send_task.cancel()
        if label:
            logger.info("WebSocket client disconnected [%s]", label)


@app.websocket("/ws")
async def websocket_ws(websocket: WebSocket):
    """Legacy /ws endpoint (keep for compatibility)."""
    await _ws_client_handler(websocket)


@app.websocket("/api/v2/ws/realtime")
async def websocket_realtime(websocket: WebSocket):
    """Primary WebSocket endpoint consumed by the frontend."""
    await _ws_client_handler(websocket, label="realtime")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
