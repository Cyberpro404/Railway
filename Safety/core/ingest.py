from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Literal
import uuid

import sensor_reader
from database import upsert_latest, insert_alert, get_latest
from models import Alert, Thresholds

# Configuration (you can move these to a config file later)
HISTORY_MAXLEN = 3600
logger = logging.getLogger(__name__)

# In-memory state (only for threshold evaluation)
_thresholds: Thresholds = Thresholds()
_parameter_level: dict[str, Literal["normal", "warning", "alarm"]] = {}
_sound_enabled: bool = False

try:
    import winsound  # type: ignore
except Exception:  # pragma: no cover
    winsound = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _threshold_level(value: float, warn: float, alarm: float) -> Literal["normal", "warning", "alarm"]:
    if value >= alarm:
        return "alarm"
    if value >= warn:
        return "warning"
    return "normal"


def _clear_alerts_for_parameter(parameter: str) -> None:
    # Mark existing alerts for this parameter as cleared in DB
    from database import get_alerts, update_alert_status
    for a in get_alerts():
        if a["parameter"] == parameter and a["status"] != "cleared":
            update_alert_status(a["id"], "cleared")


def _maybe_create_alert(
    timestamp: str,
    severity: Literal["warning", "alarm"],
    parameter: str,
    value: float,
    threshold: float,
    message: str,
) -> None:
    alert_id = str(uuid.uuid4())
    alert = Alert(
        id=alert_id,
        timestamp=timestamp,
        severity=severity,
        parameter=parameter,
        value=value,
        threshold=threshold,
        message=message,
        status="active",
    )
    insert_alert(alert.model_dump())

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
    loop = asyncio.get_running_loop()
    interval_s = 1.0
    next_tick = loop.time()
    while True:
        try:
            status, reading = await asyncio.to_thread(sensor_reader.read_sensor_once)
            if status == sensor_reader.SensorStatus.OK and reading:
                upsert_latest(reading)
                _check_thresholds(reading)
            else:
                # Sensor read failed, don't update database with empty data
                logger.debug("Sensor read failed, status: %s", status)
        except Exception as e:
            # Log sensor read errors for visibility; keep polling
            logger.debug("Sensor read failed: %s", e)

        next_tick += interval_s
        now = loop.time()
        sleep_s = next_tick - now
        if sleep_s < 0:
            next_tick = now
            sleep_s = 0
        await asyncio.sleep(sleep_s)


def set_connection(cfg):
    sensor_reader.init_reader(cfg)


def set_thresholds(t: Thresholds):
    global _thresholds
    _thresholds = t


def set_sound(enabled: bool):
    global _sound_enabled
    _sound_enabled = enabled


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Rail sensor ingest service")
    parser.add_argument("--port", help="Serial port (e.g., COM3). If omitted, will scan and prompt.")
    parser.add_argument("--baudrate", type=int, default=19200, help="Baud rate")
    parser.add_argument("--slave-id", type=int, default=1, help="Modbus slave ID")
    args = parser.parse_args()

    # Scan for ports if not provided
    if not args.port:
        try:
            from serial.tools import list_ports
            ports = list_ports.comports()
            if not ports:
                print("No serial ports found.")
                return
            print("Available serial ports:")
            for i, p in enumerate(ports, 1):
                print(f"  {i}: {p.device} - {p.description or 'No description'}")
            
            # Prefer USB serial ports over Bluetooth
            usb_ports = [p for p in ports if 'USB' in (p.description or '').upper()]
            if usb_ports:
                args.port = usb_ports[0].device
                print(f"Auto-selecting USB port: {args.port}")
            else:
                # Fallback to first port
                args.port = ports[0].device
                print(f"Auto-selecting: {args.port}")
        except Exception as e:
            print(f"Failed to scan serial ports: {e}")
            return

    from models import ConnectionConfig
    cfg = ConnectionConfig(
        port=args.port,
        baudrate=args.baudrate,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout_s=3.0,
        slave_id=args.slave_id,
    )
    try:
        set_connection(cfg)
    except Exception as e:
        print(f"Failed to connect to {args.port}: {e}")
        print("Check that the device is connected and not in use by another program.")
        return

    # Start polling
    await _poll_sensor_loop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
