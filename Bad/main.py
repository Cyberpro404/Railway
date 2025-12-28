from __future__ import annotations

import asyncio
import csv
import io
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Literal
import uuid

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

import logging

from pydantic import BaseModel

from models import Alert, ConnectionConfig, PortInfo, Thresholds
from core import sensor_reader
from api import prediction_api
from api.dataset_api import setup_dataset_routes

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

# Simple heuristic for train idle detection (mm/s)
# Adjusted for real sensor noise - sensors never reach true 0, always have baseline vibration
IDLE_RMS_THRESHOLD = 0.5  # 0.5 mm/s accounts for sensor noise and ambient vibrations


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

    if _sound_enabled and winsound is not None:
        try:
            if severity == "alarm":
                winsound.Beep(1500, 180)
            else:
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


async def _poll_sensor_loop() -> None:
    global _latest, _sensor_status, _sensor_error_message
    loop = asyncio.get_running_loop()
    # Sensor polling interval (seconds). Lower values give faster ML updates
    # but increase Modbus traffic and CPU usage.
    interval_s = 0.5
    next_tick = loop.time()
    while True:
        try:
            status, reading = await asyncio.to_thread(sensor_reader.read_sensor_once)
            if status == sensor_reader.SensorStatus.OK and reading is not None:
                # Check the new 'ok' field from sensor_reader
                if reading.get("ok", True):
                    # Derive simple train state (idle vs moving) based on RMS
                    try:
                        z_rms = float(reading.get("z_rms_mm_s", 0.0))
                        x_rms = float(reading.get("x_rms_mm_s", 0.0))
                    except Exception:
                        z_rms = x_rms = 0.0

                    if z_rms < IDLE_RMS_THRESHOLD and x_rms < IDLE_RMS_THRESHOLD:
                        reading["train_state"] = "idle"
                    else:
                        reading["train_state"] = "moving"

                    _latest = reading
                    _history.append(reading)
                    _check_thresholds(reading)
                    _sensor_status = "ok"
                    _sensor_error_message = None
                    
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
                    # Don't update _latest with bad data, keep previous good reading
                    logger.debug(f"Sensor read ok=False: {_sensor_error_message}")
            elif status == sensor_reader.SensorStatus.NOT_INITIALIZED:
                # Silently skip until user connects via UI
                _sensor_status = "error"
                _sensor_error_message = "Sensor not initialized. Set connection via /api/connection or /api/ports/connect."
            else:
                # Keep previous good reading but update status and error message
                err, t = sensor_reader.get_last_error()
                _sensor_status = "error"
                _sensor_error_message = err
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
    
    # Initialize sensor reader only if a port is configured to avoid startup errors
    try:
        if getattr(_connection, "port", ""):
            sensor_reader.init_reader(_connection)
    except Exception:
        logger.exception("Failed to initialize sensor reader at startup")
    global _poll_task
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
    if envelope:
        return {"status": _sensor_status, "error_message": _sensor_error_message, "reading": _latest}

    if _latest is None:
        return Response(status_code=204)
    return _latest


@app.get("/api/latest/status")
def api_latest_status() -> dict:
    """Always return a status envelope for the latest reading."""
    return {"status": _sensor_status, "error_message": _sensor_error_message, "reading": _latest}


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


@app.get("/api/history")
def api_history(seconds: int = 600) -> list[dict]:
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
        _ = sensor_reader.read_scalar_values()
    except Exception as e:
        logger.exception("Failed to connect via /api/ports/connect")
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
    return sorted(_alerts.values(), key=lambda a: a.timestamp, reverse=True)


@app.post("/api/alerts/{alert_id}/ack")
def api_alert_ack(alert_id: str) -> dict:
    a = _alerts.get(alert_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if a.status == "active":
        a.status = "acknowledged"
    return {"status": "ok"}


@app.get("/api/alerts/csv")
def api_alerts_csv(since_seconds: int = 86400) -> PlainTextResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=since_seconds)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "timestamp", "severity", "parameter", "value", "threshold", "message", "status"])

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
