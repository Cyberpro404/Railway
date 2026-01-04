from __future__ import annotations

import asyncio
import csv
import io
import os
import random
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
import uuid

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

import logging

from utils.iso10816 import ISO10816Classifier
from utils.bearing_diagnostics import BearingDiagnosticsSuite
from utils import formatters

from pydantic import BaseModel

from models import Alert, ConnectionConfig, PortInfo, Thresholds
from core import sensor_reader
from api import prediction_api
from api.dataset_api import setup_dataset_routes
from database.operational_db import get_db, init_db

try:
    import winsound  # type: ignore
except Exception:  # pragma: no cover
    winsound = None

try:
    from serial.tools import list_ports
except Exception:  # pragma: no cover
    list_ports = None


app = FastAPI(title="Gandiva Rail Safety Monitor")

# Include ML prediction router
app.include_router(prediction_api.router)

# Setup dataset management routes
setup_dataset_routes(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


HISTORY_MAXLEN = 3600
logger = logging.getLogger(__name__)
_history: deque[dict] = deque(maxlen=HISTORY_MAXLEN)
_latest: dict | None = None
_poll_task: asyncio.Task | None = None

_connection: ConnectionConfig = ConnectionConfig()
_thresholds: Thresholds = Thresholds()

_alerts: dict[str, Alert] = {}
_parameter_level: dict[str, Literal["normal", "warning", "alarm"]] = {}
_sound_enabled: bool = False

# Sensor status tracking
_sensor_status: Literal["ok", "error"] = "ok"
_sensor_error_message: str | None = None

# Track last observed train state so we can create/clear idle alerts on transitions
_last_train_state: str | None = None

# Simple heuristic for train idle detection (mm/s)
# Adjusted for real sensor noise - sensors never reach true 0, always have baseline vibration
IDLE_RMS_THRESHOLD = 0.5  # 0.5 mm/s accounts for sensor noise and ambient vibrations

_sensor_error_count = 0  # Track consecutive sensor errors
_max_sensor_errors = 1

# ISO 10816 classifier and bearing diagnostics suite
_machine_class: str = "class_II"
_iso_classifier = ISO10816Classifier(machine_class=_machine_class)
_bearing_suite = BearingDiagnosticsSuite()


class _SoundSetting(BaseModel):
    enabled: bool


class _EmptyBody(BaseModel):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _threshold_level(value: float, warn: float, alarm: float) -> Literal["normal", "warning", "alarm"]:
    if value >= alarm:
        return "alarm"
    if value >= warn:
        return "warning"
    return "normal"


def _clear_alerts_for_parameter(parameter: str) -> None:
    for a in _alerts.values():
        if a.parameter == parameter and a.status != "cleared":
            a.status = "cleared"


def _maybe_create_alert(
    timestamp: str,
    severity: Literal["warning", "alarm"],
    parameter: str,
    value: float,
    threshold: float,
    message: str,
) -> None:
    alert_id = str(uuid.uuid4())
    _alerts[alert_id] = Alert(
        id=alert_id,
        timestamp=timestamp,
        severity=severity,
        parameter=parameter,
        value=value,
        threshold=threshold,
        message=message,
        status="active",
    )

    # Persist alert to operational database
    try:
        get_db().insert_alert(_alerts[alert_id].model_dump())
    except Exception:
        pass

    if _sound_enabled and winsound is not None:
        try:
            if severity == "alarm":
                # Two short beeps for alarm conditions
                for _ in range(2):
                    winsound.Beep(1500, 140)
                    time.sleep(0.06)
            else:
                # Single beep for warning conditions
                winsound.Beep(1100, 120)
        except Exception:
            pass


def _evaluate_parameter(
    timestamp: str,
    parameter: str,
    value: float,
    warn: float,
    alarm: float,
    unit: str,
) -> None:
    new_level = _threshold_level(value, warn=warn, alarm=alarm)
    prev_level = _parameter_level.get(parameter, "normal")

    if new_level == "normal":
        if prev_level != "normal":
            _clear_alerts_for_parameter(parameter)
        _parameter_level[parameter] = "normal"
        return

    if prev_level == new_level:
        _parameter_level[parameter] = new_level
        return

    if prev_level == "alarm" and new_level == "warning":
        _clear_alerts_for_parameter(parameter)

    _parameter_level[parameter] = new_level

    if prev_level == "normal" and new_level == "warning":
        _maybe_create_alert(
            timestamp=timestamp,
            severity="warning",
            parameter=parameter,
            value=value,
            threshold=warn,
            message=f"{parameter} warning: {value:.3f}{unit} >= {warn:.3f}{unit}",
        )
    elif prev_level in ("normal", "warning") and new_level == "alarm":
        _maybe_create_alert(
            timestamp=timestamp,
            severity="alarm",
            parameter=parameter,
            value=value,
            threshold=alarm,
            message=f"{parameter} alarm: {value:.3f}{unit} >= {alarm:.3f}{unit}",
        )


def _check_thresholds(reading: dict) -> None:
    ts = reading["timestamp"]

    _evaluate_parameter(ts, "z_rms_mm_s", float(reading.get("z_rms_mm_s", 0.0)), _thresholds.z_rms_mm_s_warning, _thresholds.z_rms_mm_s_alarm, "")
    _evaluate_parameter(ts, "x_rms_mm_s", float(reading.get("x_rms_mm_s", 0.0)), _thresholds.x_rms_mm_s_warning, _thresholds.x_rms_mm_s_alarm, "")
    _evaluate_parameter(ts, "temp_c", float(reading.get("temp_c", 0.0)), _thresholds.temp_c_warning, _thresholds.temp_c_alarm, "")

    bt_map = {(bt.axis, bt.band_number): bt for bt in _thresholds.band_thresholds}

    for b in reading.get("bands_z", []):
        bt = bt_map.get(("z", int(b.get("band_number", 0))))
        if not bt:
            continue
        n = int(b["band_number"])
        _evaluate_parameter(ts, f"band_z_{n}_total_rms", float(b.get("total_rms", 0.0)), bt.total_rms_warning, bt.total_rms_alarm, "")
        _evaluate_parameter(ts, f"band_z_{n}_peak_rms", float(b.get("peak_rms", 0.0)), bt.peak_rms_warning, bt.peak_rms_alarm, "")

    for b in reading.get("bands_x", []):
        bt = bt_map.get(("x", int(b.get("band_number", 0))))
        if not bt:
            continue
        n = int(b["band_number"])
        _evaluate_parameter(ts, f"band_x_{n}_total_rms", float(b.get("total_rms", 0.0)), bt.total_rms_warning, bt.total_rms_alarm, "")
        _evaluate_parameter(ts, f"band_x_{n}_peak_rms", float(b.get("peak_rms", 0.0)), bt.peak_rms_warning, bt.peak_rms_alarm, "")


def _compute_data_quality(prev: Optional[dict], current: dict) -> dict:
    """Assess frozen/step-change and band availability for confidence scoring."""
    frozen = False
    step_change = False
    keys = ("z_rms_mm_s", "x_rms_mm_s", "temp_c")
    if prev:
        deltas = []
        for k in keys:
            try:
                pv = float(prev.get(k, 0.0) or 0.0)
                cv = float(current.get(k, 0.0) or 0.0)
                tol = max(0.0005, abs(pv) * 0.005)
                deltas.append(abs(cv - pv) <= tol)
                # Step-change: large jump relative to previous magnitude
                baseline = max(abs(pv), 0.01)
                if abs(cv - pv) > max(0.5, baseline * 0.5):
                    step_change = True
            except Exception:
                continue
        if deltas and all(deltas):
            frozen = True
    missing_bands = not current.get("bands_z") and not current.get("bands_x")
    return {
        "frozen": frozen,
        "step_change": step_change,
        "missing_bands": missing_bands,
    }


def _compute_confidence(data_quality: dict, health: dict, reading: dict) -> float:
    """Compute per-sample confidence based on comms and signal quality."""
    success_rate = float(health.get("success_rate", 1.0) or 0.0)
    score = 0.5 + 0.5 * success_rate  # anchor to comms quality
    if data_quality.get("missing_bands"):
        score -= 0.15
    if data_quality.get("frozen"):
        score -= 0.25
    if data_quality.get("step_change"):
        score -= 0.25
    iso = reading.get("iso10816", {}) or {}
    if iso.get("z_axis") == "D" or iso.get("x_axis") == "D":
        score -= 0.1
    return round(max(0.0, min(1.0, score)), 3)


def _infer_fault_label(reading: dict, data_quality: dict) -> str:
    """Derive an interpretable fault label using RPM harmonics and diagnostics."""
    iso = reading.get("iso10816", {}) or {}
    bearing = reading.get("bearing_diagnostics", {}) or {}
    rpm = float(reading.get("rpm", 0.0) or 0.0)
    fundamental = rpm / 60.0 if rpm > 0 else None

    peak_freq = None
    bands = reading.get("bands_z") or reading.get("bands_x") or []
    if bands:
        try:
            dominant = max(bands, key=lambda b: float(b.get("peak_rms", 0.0) or 0.0))
            peak_freq = float(dominant.get("peak_freq_hz", 0.0) or 0.0)
        except Exception:
            peak_freq = None

    if iso.get("z_axis") == "D" or iso.get("x_axis") == "D":
        return "iso_zone_d_high_vibration"
    if bearing.get("overall_status") in {"warning", "alert", "alarm"}:
        return "bearing_impulse_energy"

    if fundamental and peak_freq:
        if abs(peak_freq - fundamental) <= 0.2 * fundamental:
            return "imbalance_suspected"
        if abs(peak_freq - 2 * fundamental) <= 0.2 * fundamental:
            return "misalignment_possible"
        if abs(peak_freq - 3 * fundamental) <= 0.25 * fundamental:
            return "mechanical_looseness_possible"

    if data_quality.get("step_change"):
        return "sudden_change_check_mounts"
    if data_quality.get("frozen"):
        return "signal_frozen_check_sensor"

    return "normal"


async def _poll_sensor_loop() -> None:
    global _latest, _sensor_status, _sensor_error_message, _sensor_error_count
    loop = asyncio.get_running_loop()
    # Sensor polling interval (seconds). Lower values give faster ML updates
    # but increase Modbus traffic and CPU usage.
    interval_s = 5.0
    next_tick = loop.time()
    while True:
        try:
            prev_reading = _latest
            status, reading = await asyncio.to_thread(sensor_reader.read_sensor_once)
            if status == sensor_reader.SensorStatus.OK and reading is not None:
                # Reset error count on successful read
                _sensor_error_count = 0
                
                # Check the new 'ok' field from sensor_reader
                if reading.get("ok", True):
                    # Derive simple train state (idle vs moving) based on RMS
                    try:
                        z_rms = float(reading.get("z_rms_mm_s", 0.0))
                        x_rms = float(reading.get("x_rms_mm_s", 0.0))
                    except Exception:
                        z_rms = x_rms = 0.0

                    # ISO 10816 classification per axis
                    try:
                        reading["iso10816"] = {
                            "z_axis": _iso_classifier.classify(z_rms),
                            "x_axis": _iso_classifier.classify(x_rms),
                            "machine_class": _machine_class,
                            "limits": _iso_classifier.get_limits(),
                        }
                    except Exception:
                        reading["iso10816"] = {"z_axis": "unknown", "x_axis": "unknown", "machine_class": _machine_class}

                    # Bearing diagnostics (crest factor, kurtosis, HF RMS if available)
                    try:
                        reading["bearing_diagnostics"] = _bearing_suite.analyze_full(
                            cf_z=float(reading.get("z_crest_factor", 0.0) or 0.0),
                            cf_x=float(reading.get("x_crest_factor", 0.0) or 0.0),
                            kurt_z=float(reading.get("z_kurtosis", 0.0) or 0.0),
                            kurt_x=float(reading.get("x_kurtosis", 0.0) or 0.0),
                            hf_z=float(reading.get("z_hf_rms_g", 0.0) or 0.0),
                            hf_x=float(reading.get("x_hf_rms_g", 0.0) or 0.0),
                        )
                    except Exception:
                        reading["bearing_diagnostics"] = {
                            "overall_status": "unknown",
                            "alerts": [],
                            "alert_count": 0,
                        }

                    # Data quality and confidence scoring
                    health_stats = sensor_reader.get_health_stats()
                    dq = _compute_data_quality(prev_reading, reading)
                    reading["data_quality"] = dq
                    reading["confidence"] = _compute_confidence(dq, health_stats, reading)
                    reading["fault_label"] = _infer_fault_label(reading, dq)

                    if z_rms < IDLE_RMS_THRESHOLD and x_rms < IDLE_RMS_THRESHOLD:
                        reading["train_state"] = "idle"
                    else:
                        reading["train_state"] = "moving"

                    _latest = reading
                    _history.append(reading)
                    _check_thresholds(reading)
                    _sensor_status = "ok"
                    _sensor_error_message = None
                    try:
                        # Persist to operational database
                        get_db().upsert_latest(reading)
                    except Exception as db_err:
                        logger.debug(f"DB upsert error: {db_err}")
                    
                    # Run ML prediction if reading is valid
                    try:
                        ml_result = prediction_api.safe_predict_from_reading(reading)
                        if ml_result.get("ok"):
                            reading["ml_prediction"] = {
                                "label": ml_result["prediction"],
                                "class_index": ml_result["class_index"],
                                "confidence": ml_result["confidence"],
                                "probabilities": ml_result["probabilities"]
                            }
                        else:
                            reading["ml_prediction"] = None
                            reading["ml_error"] = ml_result.get("error", "Prediction failed")
                    except Exception as ml_err:
                        logger.debug(f"ML prediction error: {ml_err}")
                        reading["ml_prediction"] = None
                else:
                    # Reading returned but ok=False (sensor communication issue)
                    _sensor_status = "error"
                    _sensor_error_message = reading.get("error", "Sensor read returned ok=False")

                    # Create/clear idle alert on train_state transitions
                    try:
                        global _last_train_state
                        observed_state = str(reading.get("train_state", "")).lower()
                        # If transitioned into idle, create a persistent alert entry (info via warning severity)
                        if observed_state == "idle" and _last_train_state != "idle":
                            # Use the z_rms value and IDLE_RMS_THRESHOLD for numeric fields
                            _maybe_create_alert(
                                timestamp=reading.get("timestamp", _now_iso()),
                                severity="warning",
                                parameter="train_state",
                                value=float(reading.get("z_rms_mm_s", 0.0)),
                                threshold=float(IDLE_RMS_THRESHOLD),
                                message="Train idle — baseline readings",
                            )
                        # If transitioned away from idle, clear any idle alerts
                        if observed_state != "idle" and _last_train_state == "idle":
                            _clear_alerts_for_parameter("train_state")
                        _last_train_state = observed_state
                    except Exception:
                        pass
                    # Don't update _latest with bad data, keep previous good reading
                    logger.debug(f"Sensor read ok=False: {_sensor_error_message}")
            elif status == sensor_reader.SensorStatus.NOT_INITIALIZED:
                # Silently skip until user connects via UI
                _sensor_status = "error"
                _sensor_error_message = "Sensor not initialized. Set connection via /api/connection or /api/ports/connect."
                
                _sensor_error_count += 1
            else:
                # Keep previous good reading but update status and error message
                err, t = sensor_reader.get_last_error()
                _sensor_status = "error"
                _sensor_error_message = err
                
                _sensor_error_count += 1
                if _sensor_error_count <= _max_sensor_errors:
                    logger.debug("Sensor read returned error status: %s (%s)", err, t)
        except Exception as e:
            # Log unexpected errors and keep polling
            _sensor_status = "error"
            _sensor_error_message = str(e)
            logger.exception("Unexpected error in sensor poll loop")

        next_tick += interval_s
        now = loop.time()
        sleep_s = next_tick - now
        if sleep_s < 0:
            next_tick = now
            sleep_s = 0
        await asyncio.sleep(sleep_s)


@app.on_event("startup")
async def _startup() -> None:
    print("[STARTUP] Gandiva backend starting...")
    
    # Load ML model for prediction endpoint
    print("[STARTUP] Loading ML model...")
    model_loaded = prediction_api.load_model()
    print(f"[STARTUP] ML model loaded: {model_loaded}")
    
    # Initialize operational database
    try:
        init_db()
        print("[STARTUP] Operational database initialized")
    except Exception as e:
        logger.warning(f"Failed to init database: {e}")
        print(f"[STARTUP] Database initialization failed: {e}")
    # Auto-initialize sensor reader: scan ports and connect to first available
    print("[STARTUP] Attempting auto sensor connection...")
    global _poll_task
    async def auto_connect_sensor():
        from models import ConnectionConfig
        import time
        max_attempts = 5
        attempt = 0
        while attempt < max_attempts:
            try:
                if list_ports is None:
                    print("[STARTUP] Serial port scanning not available.")
                    break
                ports = list(list_ports.comports())
                if not ports:
                    print("[STARTUP] No serial ports found. Retrying in 5s...")
                    await asyncio.sleep(5)
                    attempt += 1
                    continue
                port = ports[0].device
                print(f"[STARTUP] Auto-connecting to {port}")
                cfg = ConnectionConfig(
                    port=port,
                    baudrate=19200,
                    bytesize=8,
                    parity="N",
                    stopbits=1,
                    timeout_s=3.0,
                    slave_id=1
                )
                from core import sensor_reader
                sensor_reader.init_reader(cfg)
                # Try a test read
                try:
                    sample = sensor_reader.read_scalar_values()
                    print(f"[STARTUP] Sensor connected and read OK: {sample}")
                except Exception as e:
                    print(f"[STARTUP] Sensor connected but read failed: {e}")
                global _connection
                _connection = cfg
                break
            except Exception as e:
                print(f"[STARTUP] Auto sensor connect failed: {e}. Retrying in 5s...")
                await asyncio.sleep(5)
                attempt += 1
    await auto_connect_sensor()
    if _poll_task is None or _poll_task.done():
        _poll_task = asyncio.create_task(_poll_sensor_loop())
    print("[STARTUP] Backend ready!")


@app.get("/api/latest", response_model=None)
def api_latest(envelope: bool = False) -> dict | Response:
    """Return the latest reading with ML prediction if available.

    - By default returns the raw reading dict (preserves backward compatibility).
    - If ?envelope=true is provided, return a status envelope with {status, error_message, reading}.
    
    Reading now includes:
      - ok: bool (True if sensor read succeeded)
      - ml_prediction: {label, class_index, confidence, probabilities} or None
      - ml_error: string if prediction failed
    """
    latest = None
    try:
        latest = get_db().get_latest()
    except Exception:
        latest = _latest

    if envelope:
        return {"status": _sensor_status, "error_message": _sensor_error_message, "reading": latest}

    if latest is None:
        return Response(status_code=204)
    return latest


@app.get("/api/latest/status")
def api_latest_status() -> dict:
    """Always return a status envelope for the latest reading."""
    db_latest = None
    try:
        db_latest = get_db().get_latest()
    except Exception:
        db_latest = _latest
    return {"status": _sensor_status, "error_message": _sensor_error_message, "reading": db_latest}


@app.get("/api/diagnostics")
def api_diagnostics() -> dict:
    """Return diagnostics: connection health, ISO10816, bearing health."""
    health = sensor_reader.get_health_stats()
    latest = _latest
    iso = latest.get("iso10816") if latest else None
    bearing = latest.get("bearing_diagnostics") if latest else None
    return {
        "connection_health": health,
        "iso10816": iso,
        "bearing": bearing,
        "sensor_status": _sensor_status,
        "error_message": _sensor_error_message,
    }


@app.get("/api/industrial/latest")
def api_industrial_latest() -> dict:
    """Return formatted industrial JSON with diagnostics."""
    latest = _latest
    if latest is None:
        raise HTTPException(status_code=404, detail="No readings available")
    health = sensor_reader.get_health_stats()
    iso = latest.get("iso10816") or {}
    bearing = latest.get("bearing_diagnostics") or {}
    cfg = {
        "port": _connection.port,
        "slave_id": _connection.slave_id,
        "baudrate": _connection.baudrate,
    }
    return formatters.format_industrial_json(
        latest,
        iso_zones={"z_axis": iso.get("z_axis", "unknown"), "x_axis": iso.get("x_axis", "unknown")},
        bearing_diagnostics=bearing,
        connection_health=health,
        config=cfg,
    )





@app.post("/api/sensor/test")
def api_test_sensor_connection() -> dict:
    """Test if the sensor can be connected on current config."""
    try:
        # Try to read from sensor
        status, reading = sensor_reader.read_sensor_once()
        if status == sensor_reader.SensorStatus.OK and reading is not None:
            return {
                "ok": True,
                "message": "Sensor connection successful",
                "port": _connection.port,
                "sample_data": {
                    "z_rms": reading.get("z_rms_mm_s"),
                    "x_rms": reading.get("x_rms_mm_s"),
                    "temp": reading.get("temp_c")
                }
            }
        else:
            err, _ = sensor_reader.get_last_error()
            return {
                "ok": False,
                "message": err or "Sensor read failed",
                "port": _connection.port
            }
    except Exception as e:
        return {
            "ok": False,
            "message": str(e),
            "port": _connection.port
        }


@app.get("/api/ml/test")
def api_ml_test() -> dict:
    """Return the latest ML prediction payload for frontend demo/testing."""
    if _latest is None:
        raise HTTPException(status_code=404, detail="No readings available yet")
    pred = _latest.get("ml_prediction")
    if pred is None:
        err = _latest.get("ml_error") or "ML prediction not available"
        raise HTTPException(status_code=503, detail=err)
    return {
        "timestamp": _latest.get("timestamp"),
        "train_state": _latest.get("train_state"),
        "prediction": pred,
    }


@app.get("/api/ml/realtime-stats")
def api_ml_realtime_stats(limit: int = 50) -> dict:
    """Aggregate recent ML predictions for the ML Insights tab.

    Returns class distribution, confidence buckets, and recent prediction rows.
    """
    try:
        source = get_db().get_history(seconds=3600)
    except Exception:
        source = list(_history)

    recent_predictions: list[dict] = []
    for row in reversed(list(source)):
        pred = row.get("ml_prediction")
        if not pred:
            continue
        recent_predictions.append({
            "timestamp": row.get("timestamp"),
            "label": pred.get("label"),
            "confidence": float(pred.get("confidence", 0.0) or 0.0),
            "z_rms": float(row.get("z_rms_mm_s", 0.0) or 0.0),
            "x_rms": float(row.get("x_rms_mm_s", 0.0) or 0.0),
            "temp": float(row.get("temp_c", 0.0) or 0.0),
        })
        if len(recent_predictions) >= max(1, limit):
            break

    class_distribution: dict[str, int] = {"normal": 0, "expansion_gap": 0, "crack": 0}
    confidence_distribution: dict[str, int] = {"high": 0, "medium": 0, "low": 0}

    total_conf = 0.0
    for p in recent_predictions:
        conf = float(p.get("confidence", 0.0) or 0.0)
        total_conf += conf

        label_key = str(p.get("label") or "").lower()
        class_distribution[label_key] = class_distribution.get(label_key, 0) + 1

        if conf >= 0.8:
            confidence_distribution["high"] += 1
        elif conf >= 0.5:
            confidence_distribution["medium"] += 1
        else:
            confidence_distribution["low"] += 1

    average_confidence = total_conf / len(recent_predictions) if recent_predictions else 0.0

    payload = {
        "class_distribution": class_distribution,
        "confidence_distribution": confidence_distribution,
        "average_confidence": average_confidence,
        "recent_predictions": recent_predictions,
        "total_predictions": len(recent_predictions),
    }

    # Provide both nested and flat payload for compatibility with existing frontend logic
    return {"data": payload, **payload}


@app.get("/api/history")
def api_history(seconds: int = 600) -> list[dict]:
    try:
        return get_db().get_history(seconds=seconds)
    except Exception:
        # Fallback to in-memory history
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        out: list[dict] = []
        for r in list(_history):
            try:
                if _parse_iso(r["timestamp"]) >= cutoff:
                    out.append(r)
            except Exception:
                continue
        return out


@app.get("/api/connection")
def api_get_connection() -> ConnectionConfig:
    return _connection


@app.post("/api/config/iso10816")
def api_set_iso_class(machine_class: Literal["class_I", "class_II", "class_III", "class_IV"]) -> dict:
    """Set ISO10816 machine class used for severity classification."""
    global _machine_class, _iso_classifier
    _machine_class = machine_class
    _iso_classifier = ISO10816Classifier(machine_class=machine_class)
    return {"status": "ok", "machine_class": machine_class, "limits": _iso_classifier.get_limits()}


@app.post("/api/config/hex-logging")
def api_set_hex_logging(enabled: bool = True) -> dict:
    """Enable/disable hex frame logging for Modbus diagnostics."""
    from core import sensor_reader as sr
    sr.enable_hex_logging(bool(enabled))
    return {"enabled": bool(enabled)}


@app.post("/api/connection")
def api_set_connection(cfg: ConnectionConfig) -> dict:
    global _connection
    _connection = cfg
    try:
        sensor_reader.init_reader(_connection)
        _ = sensor_reader.read_scalar_values()
    except Exception as e:
        logger.exception("Failed to set connection")
        msg = str(e)
        if "Access is denied" in msg or "PermissionError" in msg:
            raise HTTPException(
                status_code=409,
                detail=f"Failed to open serial port {cfg.port}. The port is busy or access is denied. Close any other application using {cfg.port} and try again.",
            )
        if isinstance(e, sensor_reader.SensorReaderError):
            raise HTTPException(status_code=400, detail=msg)
        raise HTTPException(status_code=500, detail=f"Failed to connect: {msg}")
    return {"status": "connected", "connection": _connection}


@app.get("/api/ports/scan")
def api_ports_scan() -> list[PortInfo]:
    if list_ports is None:
        return []
    out: list[PortInfo] = []
    for p in list_ports.comports():
        out.append(PortInfo(port=p.device, description=getattr(p, "description", None), hwid=getattr(p, "hwid", None)))
    return out


@app.post("/api/ports/connect")
def api_ports_connect(cfg: ConnectionConfig) -> dict:
    global _connection
    _connection = cfg
    try:
        sensor_reader.init_reader(_connection)
        # Try a test read, but don't fail connection if the device doesn't answer
        try:
            sample = sensor_reader.read_scalar_values()
            return {
                "status": "connected",
                "connection": _connection,
                "read_ok": True,
                "sample_data": {
                    "z_rms": sample.get("z_rms_mm_s"),
                    "x_rms": sample.get("x_rms_mm_s"),
                    "temp": sample.get("temp_c"),
                }
            }
        except Exception as e:
            msg = str(e)
            # Permission or port busy should still be hard errors
            if "Access is denied" in msg or "PermissionError" in msg:
                raise HTTPException(
                    status_code=409,
                    detail=f"Failed to open serial port {cfg.port}. The port is busy or access is denied. Close any other application using {cfg.port} and try again.",
                )
            # Sensor didn't answer — keep connection and report warning to client
            return {
                "status": "connected_with_errors",
                "connection": _connection,
                "read_ok": False,
                "error": msg
            }
    except Exception as e:
        logger.exception("Failed to connect via /api/ports/connect")
        msg = str(e)
        if "Access is denied" in msg or "PermissionError" in msg:
            raise HTTPException(
                status_code=409,
                detail=f"Failed to open serial port {cfg.port}. The port is busy or access is denied. Close any other application using {cfg.port} and try again.",
            )
        # Other errors — bubble up as server errors
        raise HTTPException(status_code=500, detail=f"Failed to connect: {msg}")
    


@app.post("/api/read-now")
def api_read_now() -> dict:
    """Perform a single sensor read on demand (useful for testing connections)."""
    try:
        status, reading = sensor_reader.read_sensor_once()
    except Exception as e:
        logger.exception("Read-now failed")
        raise HTTPException(status_code=500, detail=str(e))

    if status != sensor_reader.SensorStatus.OK or reading is None:
        err, t = sensor_reader.get_last_error()
        raise HTTPException(status_code=400, detail=err or "Sensor read failed")

    global _latest, _sensor_status, _sensor_error_message
    _latest = reading
    _history.append(reading)
    _check_thresholds(reading)
    _sensor_status = "ok"
    _sensor_error_message = None
    return reading


@app.get("/api/thresholds")
def api_get_thresholds() -> Thresholds:
    return _thresholds


@app.post("/api/thresholds")
def api_set_thresholds(t: Thresholds) -> dict:
    global _thresholds
    if t.z_rms_mm_s_alarm < t.z_rms_mm_s_warning:
        raise HTTPException(status_code=400, detail="z_rms_mm_s_alarm must be >= z_rms_mm_s_warning")
    if t.x_rms_mm_s_alarm < t.x_rms_mm_s_warning:
        raise HTTPException(status_code=400, detail="x_rms_mm_s_alarm must be >= x_rms_mm_s_warning")
    if t.temp_c_alarm < t.temp_c_warning:
        raise HTTPException(status_code=400, detail="temp_c_alarm must be >= temp_c_warning")
    for bt in t.band_thresholds:
        if bt.total_rms_alarm < bt.total_rms_warning:
            raise HTTPException(status_code=400, detail=f"Band {bt.axis}{bt.band_number} total_rms_alarm must be >= total_rms_warning")
        if bt.peak_rms_alarm < bt.peak_rms_warning:
            raise HTTPException(status_code=400, detail=f"Band {bt.axis}{bt.band_number} peak_rms_alarm must be >= peak_rms_warning")
    _thresholds = t
    return {"status": "ok"}


@app.get("/api/alerts")
def api_alerts() -> list[Alert]:
    try:
        rows = get_db().get_alerts()
        return rows  # return dicts for compatibility
    except Exception:
        return sorted(_alerts.values(), key=lambda a: a.timestamp, reverse=True)


@app.post("/api/alerts/{alert_id}/ack")
def api_alert_ack(alert_id: str) -> dict:
    a = _alerts.get(alert_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if a.status == "active":
        a.status = "acknowledged"
        try:
            # Persist status change
            get_db().update_alert_status(alert_id, "acknowledged")
        except Exception:
            pass
    return {"status": "ok"}


@app.get("/api/alerts/csv")
def api_alerts_csv(since_seconds: int = 86400) -> PlainTextResponse:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "timestamp", "severity", "parameter", "value", "threshold", "message", "status"])

    try:
        rows = get_db().get_alerts(since_seconds=since_seconds)
        for a in sorted(rows, key=lambda x: x["timestamp"]):
            w.writerow([a["id"], a["timestamp"], a["severity"], a["parameter"], a["value"], a["threshold"], a["message"], a["status"]])
    except Exception:
        # Fallback to in-memory
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=since_seconds)
        for a in sorted(_alerts.values(), key=lambda x: x.timestamp):
            try:
                if _parse_iso(a.timestamp) < cutoff:
                    continue
            except Exception:
                continue
            w.writerow([a.id, a.timestamp, a.severity, a.parameter, a.value, a.threshold, a.message, a.status])

    return PlainTextResponse(buf.getvalue(), media_type="text/csv")


@app.get("/api/sound")
def api_get_sound() -> dict:
    return {"enabled": _sound_enabled}


@app.post("/api/sound")
def api_set_sound(setting: _SoundSetting) -> dict:
    global _sound_enabled
    _sound_enabled = bool(setting.enabled)
    return {"enabled": _sound_enabled}


@app.post("/api/test-beep")
def api_test_beep(_: _EmptyBody | None = None) -> dict:
    if winsound is not None:
        winsound.Beep(1200, 150)
    return {"status": "ok"}


# =============================================================================
# LIVE SAMPLE ENDPOINT - combines sensor reading + ML prediction for UI
# =============================================================================

@app.get("/api/live_sample")
def api_live_sample() -> dict:
    """
    Get current sensor sample with ML prediction for real-time UI updates.
    
    Returns:
        {
            "ok": true/false,
            "error": "message if not ok",
            "timestamp": "ISO timestamp",
            "sensor": {rms, peak, temperature, band_1x, ...},
            "prediction": {label, class_index, confidence, probabilities} or null,
            "status": "ok" | "error"
        }
    
    Use this endpoint for the 60-second sliding window graph.
    Poll every 1 second.
    """
    if _latest is None:
        return {
            "ok": False,
            "error": "No sensor data yet",
            "timestamp": _now_iso(),
            "sensor": None,
            "prediction": None,
            "status": _sensor_status
        }
    
    # Check sensor ok status
    if not _latest.get("ok", True):
        return {
            "ok": False,
            "error": _latest.get("error", _sensor_error_message or "Sensor read failed"),
            "timestamp": _latest.get("timestamp", _now_iso()),
            "sensor": None,
            "prediction": None,
            "status": "error"
        }
    
    # Build sensor values for UI
    sensor_data = {
        "rms": _latest.get("z_rms_mm_s", 0.0),
        "peak": _latest.get("z_peak_mm_s", 0.0),
        "temperature": _latest.get("temp_c", 0.0),
        "band_1x": _latest.get("band_1x", 0.0),
        "band_2x": _latest.get("band_2x", 0.0),
        "band_3x": _latest.get("band_3x", 0.0),
        "band_5x": _latest.get("band_5x", 0.0),
        "band_7x": _latest.get("band_7x", 0.0),
    }
    
    # Include ML prediction if available
    prediction = _latest.get("ml_prediction", None)
    
    return {
        "ok": True,
        "error": None,
        "timestamp": _latest.get("timestamp", _now_iso()),
        "sensor": sensor_data,
        "prediction": prediction,
        "status": _sensor_status
    }


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
