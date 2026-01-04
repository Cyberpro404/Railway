"""
Enhanced sensor data formatters for industrial JSON and CSV output.

Provides production-grade output formats including:
- Industrial JSON with ISO 10816 zones
- Bearing diagnostics integration
- Communication health statistics
- CSV format for SCADA integration
"""

from typing import Dict, Any, Optional
from datetime import datetime
import csv
import io


def format_industrial_json(
    reading: Dict[str, Any],
    iso_zones: Optional[Dict[str, str]] = None,
    bearing_diagnostics: Optional[Dict[str, Any]] = None,
    connection_health: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format sensor reading as industrial JSON structure.
    
    Args:
        reading: Raw sensor reading dict
        iso_zones: ISO 10816 classification results
        bearing_diagnostics: Bearing health diagnostics
        connection_health: Connection health statistics
        config: Connection configuration
    
    Returns:
        Formatted industrial JSON
    """
    # Extract basic values with defaults
    temp_c = reading.get("temp_c", reading.get("temperature", 0.0))
    z_rms = reading.get("z_rms_mm_s", reading.get("z_rms", 0.0))
    x_rms = reading.get("x_rms_mm_s", reading.get("x_rms", 0.0))
    z_peak = reading.get("z_peak_mm_s", reading.get("z_peak", 0.0))
    x_peak = reading.get("x_peak_mm_s", reading.get("x_peak", 0.0))
    z_rms_g = reading.get("z_rms_g", 0.0)
    x_rms_g = reading.get("x_rms_g", 0.0)
    z_hf_rms_g = reading.get("z_hf_rms_g", 0.0)
    x_hf_rms_g = reading.get("x_hf_rms_g", 0.0)
    z_cf = reading.get("z_crest_factor", 0.0)
    x_cf = reading.get("x_crest_factor", 0.0)
    z_kurt = reading.get("z_kurtosis", 0.0)
    x_kurt = reading.get("x_kurtosis", 0.0)
    rpm = reading.get("rpm")
    confidence = reading.get("confidence")
    fault_label = reading.get("fault_label")
    data_quality = reading.get("data_quality", {}) or {}
    
    # Build industrial structure
    output = {
        "timestamp": reading.get("timestamp", datetime.utcnow().isoformat()),
        "connection": config or {
            "port": "unknown",
            "slave_id": 1,
            "baudrate": 19200
        },
        "temperature": {
            "celsius": round(temp_c, 2),
            "fahrenheit": round(temp_c * 9/5 + 32, 2),
            "status": "normal" if -40 <= temp_c <= 85 else "warning"
        },
        "vibration": {
            "z_axis": {
                "rms_velocity_mm_s": round(z_rms, 3),
                "peak_velocity_mm_s": round(z_peak, 3),
                "rms_acceleration_g": round(z_rms_g, 3),
                "hf_rms_acceleration_g": round(z_hf_rms_g, 3),
                "crest_factor": round(z_cf, 3),
                "kurtosis": round(z_kurt, 3),
                "iso10816_zone": iso_zones.get("z_axis", "unknown") if iso_zones else "unknown"
            },
            "x_axis": {
                "rms_velocity_mm_s": round(x_rms, 3),
                "peak_velocity_mm_s": round(x_peak, 3),
                "rms_acceleration_g": round(x_rms_g, 3),
                "hf_rms_acceleration_g": round(x_hf_rms_g, 3),
                "crest_factor": round(x_cf, 3),
                "kurtosis": round(x_kurt, 3),
                "iso10816_zone": iso_zones.get("x_axis", "unknown") if iso_zones else "unknown"
            }
        },
        "machine": {
            "rpm": rpm,
            "fault_label": fault_label,
            "confidence": confidence
        },
        "spectral_bands": {
            "z_axis": _format_bands(reading.get("bands_z", [])),
            "x_axis": _format_bands(reading.get("bands_x", []))
        },
        "diagnostics": {
            "bearing_health": bearing_diagnostics or {
                "status": "unknown",
                "crest_factor_alert": False,
                "kurtosis_alert": False,
                "hf_trend_alert": False
            },
            "communication": connection_health or {
                "success_rate": 0.0,
                "consecutive_failures": 0,
                "last_error": None
            },
            "data_quality": data_quality
        }
    }
    
    return output


def _format_bands(bands_list) -> list:
    """Format band measurements for JSON output."""
    if not bands_list:
        return []
    
    formatted = []
    for i, band in enumerate(bands_list, start=1):
        if isinstance(band, dict):
            formatted.append({
                "band_number": i,
                "multiple": f"{i}×",
                "total_rms": round(band.get("total_rms", 0.0), 3),
                "peak_rms": round(band.get("peak_rms", 0.0), 3),
                "peak_frequency_hz": round(band.get("peak_frequency", 0.0), 1),
                "peak_rpm": round(band.get("peak_rpm", 0.0), 0)
            })
    
    return formatted


def format_scada_csv_row(
    reading: Dict[str, Any],
    iso_zones: Optional[Dict[str, str]] = None
) -> str:
    """
    Format sensor reading as SCADA CSV row.
    
    Args:
        reading: Raw sensor reading dict
        iso_zones: ISO 10816 classification results
    
    Returns:
        CSV row string
    """
    timestamp = reading.get("timestamp", datetime.utcnow().isoformat())
    temp_c = reading.get("temperature", 0.0)
    z_rms = reading.get("z_rms", 0.0)
    x_rms = reading.get("x_rms", 0.0)
    z_peak = reading.get("z_peak", 0.0)
    x_peak = reading.get("x_peak", 0.0)
    z_rms_g = reading.get("z_rms_g", 0.0)
    x_rms_g = reading.get("x_rms_g", 0.0)
    z_hf_rms_g = reading.get("z_hf_rms_g", 0.0)
    x_hf_rms_g = reading.get("x_hf_rms_g", 0.0)
    z_cf = reading.get("z_crest_factor", 0.0)
    x_cf = reading.get("x_crest_factor", 0.0)
    z_kurt = reading.get("z_kurtosis", 0.0)
    x_kurt = reading.get("x_kurtosis", 0.0)
    z_iso = iso_zones.get("z_axis", "unknown") if iso_zones else "unknown"
    x_iso = iso_zones.get("x_axis", "unknown") if iso_zones else "unknown"
    
    # Build CSV row
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        timestamp,
        f"{temp_c:.2f}",
        f"{z_rms:.3f}",
        f"{x_rms:.3f}",
        f"{z_peak:.3f}",
        f"{x_peak:.3f}",
        f"{z_rms_g:.3f}",
        f"{x_rms_g:.3f}",
        f"{z_hf_rms_g:.3f}",
        f"{x_hf_rms_g:.3f}",
        f"{z_cf:.3f}",
        f"{x_cf:.3f}",
        f"{z_kurt:.3f}",
        f"{x_kurt:.3f}",
        z_iso,
        x_iso
    ])
    
    return output.getvalue().strip()


def get_csv_header() -> str:
    """Get CSV header for SCADA format."""
    headers = [
        "timestamp",
        "temp_c",
        "z_rms_mm_s",
        "x_rms_mm_s",
        "z_peak_mm_s",
        "x_peak_mm_s",
        "z_rms_g",
        "x_rms_g",
        "z_hf_rms_g",
        "x_hf_rms_g",
        "z_crest_factor",
        "x_crest_factor",
        "z_kurtosis",
        "x_kurtosis",
        "z_iso10816",
        "x_iso10816"
    ]
    return ",".join(headers)


def format_console_report(
    reading: Dict[str, Any],
    iso_zones: Optional[Dict[str, str]] = None,
    bearing_diagnostics: Optional[Dict[str, Any]] = None,
    connection_health: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Format sensor reading as detailed console report.
    
    Args:
        reading: Raw sensor reading dict
        iso_zones: ISO 10816 classification results
        bearing_diagnostics: Bearing health diagnostics
        connection_health: Connection health statistics
        config: Connection configuration
    
    Returns:
        Formatted console report string
    """
    temp_c = reading.get("temperature", 0.0)
    temp_f = temp_c * 9/5 + 32
    
    port = config.get("port", "unknown") if config else "unknown"
    slave_id = config.get("slave_id", 1) if config else 1
    baudrate = config.get("baudrate", 19200) if config else 19200
    success_rate = connection_health.get("success_rate", 0.0) if connection_health else 0.0
    
    z_rms = reading.get("z_rms", 0.0)
    z_peak = reading.get("z_peak", 0.0)
    z_rms_g = reading.get("z_rms_g", 0.0)
    z_hf_rms_g = reading.get("z_hf_rms_g", 0.0)
    z_cf = reading.get("z_crest_factor", 0.0)
    z_kurt = reading.get("z_kurtosis", 0.0)
    z_iso = iso_zones.get("z_axis", "unknown") if iso_zones else "unknown"
    
    x_rms = reading.get("x_rms", 0.0)
    x_peak = reading.get("x_peak", 0.0)
    x_rms_g = reading.get("x_rms_g", 0.0)
    x_hf_rms_g = reading.get("x_hf_rms_g", 0.0)
    x_cf = reading.get("x_crest_factor", 0.0)
    x_kurt = reading.get("x_kurtosis", 0.0)
    x_iso = iso_zones.get("x_axis", "unknown") if iso_zones else "unknown"
    
    timestamp = reading.get("timestamp", datetime.utcnow().isoformat())
    
    # Bearing health status
    bearing_status = "UNKNOWN"
    if bearing_diagnostics:
        bearing_status = bearing_diagnostics.get("overall_status", "unknown").upper()
        alerts = bearing_diagnostics.get("alerts", [])
    else:
        alerts = []
    
    report = f"""
═══════════════════════════════════════════════════════════════
BANNER QM30VT2 READING @ {timestamp}
Port: {port} | Slave: {slave_id} | Baud: {baudrate} | Success Rate: {success_rate*100:.1f}%
═══════════════════════════════════════════════════════════════

TEMPERATURE
───────────────────────────────────────────────────────────────
  Celsius:     {temp_c:6.2f} °C
  Fahrenheit:  {temp_f:6.2f} °F
  Status:      NORMAL

Z-AXIS VIBRATION
───────────────────────────────────────────────────────────────
  RMS Velocity:              {z_rms:6.3f} mm/s
  Peak Velocity:             {z_peak:6.3f} mm/s
  RMS Acceleration:          {z_rms_g:6.3f} g
  HF RMS Acceleration:       {z_hf_rms_g:6.3f} g (1-4 kHz)
  Crest Factor:              {z_cf:6.3f}
  Kurtosis:                  {z_kurt:6.3f}
  ISO 10816 Classification:  {z_iso.upper()}

X-AXIS VIBRATION
───────────────────────────────────────────────────────────────
  RMS Velocity:              {x_rms:6.3f} mm/s
  Peak Velocity:             {x_peak:6.3f} mm/s
  RMS Acceleration:          {x_rms_g:6.3f} g
  HF RMS Acceleration:       {x_hf_rms_g:6.3f} g (1-4 kHz)
  Crest Factor:              {x_cf:6.3f}
  Kurtosis:                  {x_kurt:6.3f}
  ISO 10816 Classification:  {x_iso.upper()}

PREDICTIVE MAINTENANCE DIAGNOSTICS
───────────────────────────────────────────────────────────────
  Bearing Health:     {bearing_status}
  Active Alerts:      {len(alerts)}
"""
    
    if alerts:
        for alert in alerts:
            report += f"  ⚠ {alert}\n"
    else:
        report += "  ✓ NO ACTIONABLE FAULTS\n"
    
    if connection_health:
        report += f"""
COMMUNICATION DIAGNOSTICS
───────────────────────────────────────────────────────────────
  Consecutive Failures:  {connection_health.get('consecutive_failures', 0)}
  Total Reads:           {connection_health.get('total_reads', 0)}
  Failed Reads:          {connection_health.get('failed_reads', 0)}
  Success Rate:          {success_rate*100:.2f}%
  Last Error:            {connection_health.get('last_error', 'None')}
"""
    
    report += "═══════════════════════════════════════════════════════════════\n"
    
    return report
