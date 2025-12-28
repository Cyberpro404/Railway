"""
Shared data models for Gandiva Rail Safety Monitor.
Provides pydantic models used across API, sensor reader, and ingest tasks.
"""
from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from config.settings import Config


class PortInfo(BaseModel):
    """Serial port information returned by scans."""

    port: str
    description: str | None = None
    hwid: str | None = None


class ConnectionConfig(BaseModel):
    """Connection configuration for Modbus sensor."""

    port: str = Field(default=Config.DEFAULT_PORT)
    baudrate: int = Field(default=Config.DEFAULT_BAUDRATE)
    bytesize: int = Field(default=Config.DEFAULT_BYTESIZE)
    parity: str = Field(default=Config.DEFAULT_PARITY, pattern="^[NEO]$")
    stopbits: int = Field(default=Config.DEFAULT_STOPBITS)
    timeout_s: float = Field(default=Config.DEFAULT_TIMEOUT_S, gt=0)
    slave_id: int = Field(default=Config.DEFAULT_SLAVE_ID, ge=1, le=247)


class BandThreshold(BaseModel):
    """Thresholds for a specific frequency band and axis."""

    axis: Literal["z", "x"]
    band_number: int = Field(ge=1)
    total_rms_warning: float = Field(default=0.0, ge=0)
    total_rms_alarm: float = Field(default=0.0, ge=0)
    peak_rms_warning: float = Field(default=0.0, ge=0)
    peak_rms_alarm: float = Field(default=0.0, ge=0)


class Thresholds(BaseModel):
    """Warning and alarm thresholds for monitored parameters."""

    z_rms_mm_s_warning: float = Field(default=Config.DEFAULT_Z_RMS_WARNING_MM_S, ge=0)
    z_rms_mm_s_alarm: float = Field(default=Config.DEFAULT_Z_RMS_ALARM_MM_S, ge=0)
    x_rms_mm_s_warning: float = Field(default=Config.DEFAULT_X_RMS_WARNING_MM_S, ge=0)
    x_rms_mm_s_alarm: float = Field(default=Config.DEFAULT_X_RMS_ALARM_MM_S, ge=0)
    temp_c_warning: float = Field(default=Config.DEFAULT_TEMP_WARNING_C, ge=0)
    temp_c_alarm: float = Field(default=Config.DEFAULT_TEMP_ALARM_C, ge=0)
    band_thresholds: list[BandThreshold] = Field(default_factory=list)


class Alert(BaseModel):
    """Alert generated when thresholds are crossed."""

    id: str
    timestamp: str
    severity: Literal["warning", "alarm"]
    parameter: str
    value: float
    threshold: float
    message: str
    status: Literal["active", "acknowledged", "cleared"]


class BandMeasurement(TypedDict):
    """Typed structure for band measurement entries."""

    band_number: int
    axis: Literal["z", "x"]
    multiple: int
    total_rms: float
    peak_rms: float
    peak_freq_hz: float
    peak_rpm: float
    bin_index: int


class SensorReading(TypedDict, total=False):
    """Complete sensor reading payload."""

    timestamp: str
    temp_c: float
    z_rms_mm_s: float
    x_rms_mm_s: float
    z_peak_mm_s: float
    x_peak_mm_s: float
    z_rms_g: float
    x_rms_g: float
    z_hf_rms_g: float
    x_hf_rms_g: float
    z_kurtosis: float
    x_kurtosis: float
    z_crest_factor: float
    x_crest_factor: float
    frequency_hz: float
    bands_z: list[BandMeasurement]
    bands_x: list[BandMeasurement]


__all__ = [
    "Alert",
    "BandMeasurement",
    "BandThreshold",
    "ConnectionConfig",
    "PortInfo",
    "SensorReading",
    "Thresholds",
]
