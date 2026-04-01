"""Low-latency Modbus polling worker with queue buffering."""

import asyncio
import logging
import math
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class DataReceiver:
    """Continuously polls DXM registers and emits normalized packets."""

    def __init__(self, connection_manager: ConnectionManager, poll_interval: float = 0.25):
        self.cm = connection_manager
        self.poll_interval = max(0.1, poll_interval)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.data_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=256)
        self.error_count = 0
        self.max_errors_before_reconnect = 3

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _emit_packet(self, packet: Dict[str, Any]) -> None:
        if self.data_queue.full():
            try:
                self.data_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        await self.data_queue.put(packet)

    async def _poll_loop(self) -> None:
        while self._running:
            cycle_start = time.perf_counter()
            try:
                if not self.cm.is_connected():
                    await asyncio.sleep(0.2)
                    continue

                data = await self._read_data_block()
                read_latency_ms = round((time.perf_counter() - cycle_start) * 1000.0, 2)

                if data is not None:
                    self.error_count = 0
                    self.cm.note_read_result(success=True)
                    await self._emit_packet(
                        {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "sensor_data": data,
                            "latency_ms": read_latency_ms,
                            "valid": True,
                            "source": "LIVE_FEED",
                        }
                    )
                else:
                    self.error_count += 1
                    self.cm.note_read_result(success=False)
                    if self.error_count >= self.max_errors_before_reconnect:
                        await self.cm.trigger_reconnect(reason="data_timeout")
                        self.error_count = 0

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Data receiver loop error: %s", exc)
                await asyncio.sleep(0.2)

            elapsed = time.perf_counter() - cycle_start
            await asyncio.sleep(max(0.01, self.poll_interval - elapsed))

    async def _read_data_block(self) -> Optional[Dict[str, Any]]:
        if not self.cm.profile:
            return None

        slave_id = self.cm.profile.slave_id
        
        # Try primary register range (5200 = Modbus 45201-45222) first
        registers = await self.cm.client.read_holding_registers(address=5200, count=22, slave_id=slave_id)
        read_source = "5200"
        
        # Fallback: try registers 0-21 if primary range fails or returns all zeros
        if not registers or all(r == 0 for r in registers):
            logger.debug("Primary registers (5200) empty, trying fallback registers (0-21)")
            registers = await self.cm.client.read_holding_registers(address=0, count=22, slave_id=slave_id)
            read_source = "0"
        
        if not registers:
            return None

        def get_reg(index: int, divisor: float = 1.0) -> float:
            if index >= len(registers):
                return 0.0
            return registers[index] / divisor

        def signed(value: float) -> float:
            return value - 655.36 if value > 327.67 else value

        # Try to decode register pair 20-21 as IEEE 754 float32 (big-endian)
        float32_val = 0.0
        if len(registers) >= 22 and (registers[20] != 0 or registers[21] != 0):
            import struct
            try:
                float32_val = struct.unpack('>f', struct.pack('>HH', registers[20], registers[21]))[0]
            except Exception:
                float32_val = 0.0

        # R0-R20: decode all 21 physical parameters
        z_axis_rms     = get_reg(0,  100.0)          # R0  Z-Axis RMS (g)
        z_rms_mm       = get_reg(1,  1000.0)          # R1  Z-RMS velocity mm/s
        iso_peak_peak  = get_reg(2,  1000.0)          # R2  ISO Peak-Peak mm/s
        temperature    = signed(get_reg(3, 100.0))    # R3  Temperature °C
        z_true_peak    = get_reg(4,  1000.0)          # R4  Z-True Peak mm/s
        x_rms_mm       = get_reg(5,  1000.0)          # R5  X-RMS velocity mm/s
        z_peak_accel   = get_reg(6,  1000.0)          # R6  Z-Peak Acceleration g
        x_peak_accel   = get_reg(7,  1000.0)          # R7  X-Peak Acceleration g
        z_peak_freq    = get_reg(8,  10.0)            # R8  Z-Peak Frequency Hz
        x_peak_freq    = get_reg(9,  10.0)            # R9  X-Peak Frequency Hz
        z_band_rms     = get_reg(10, 1000.0)          # R10 Z-Band RMS mm/s
        x_band_rms     = get_reg(11, 1000.0)          # R11 X-Band RMS mm/s
        z_kurtosis     = get_reg(12, 1000.0)          # R12 Z-Kurtosis
        x_kurtosis     = get_reg(13, 1000.0)          # R13 X-Kurtosis
        z_crest        = get_reg(14, 1000.0)          # R14 Z-Crest Factor
        x_crest        = get_reg(15, 1000.0)          # R15 X-Crest Factor
        z_hf_rms_accel = get_reg(16, 1000.0)          # R16 Z-Envelope/HF RMS g
        z_peak_vel_mm  = get_reg(17, 1000.0)          # R17 Z-Peak velocity mm/s
        x_hf_rms_accel = get_reg(18, 1000.0)          # R18 X-Envelope/HF RMS g
        x_peak_vel_mm  = get_reg(19, 1000.0)          # R19 X-Peak velocity mm/s
        device_status  = get_reg(20, 1.0)             # R20 Device Status code

        non_zero_count = sum(1 for r in registers if r != 0)

        return {
            # Primary velocity (mm/s)
            "z_rms":           round(z_rms_mm, 3),
            "x_rms":           round(x_rms_mm, 3),
            "z_peak":          round(z_peak_vel_mm, 3),
            "x_peak":          round(x_peak_vel_mm, 3),
            # Acceleration (g)
            "z_accel":         round(z_peak_accel, 3),
            "x_accel":         round(x_peak_accel, 3),
            # Temperature / environmental
            "temperature":     round(temperature, 1),
            # Frequency (Hz)
            "frequency":       round(z_peak_freq, 1),
            "x_frequency":     round(x_peak_freq, 1),
            # Statistical
            "kurtosis":        round(z_kurtosis, 3),
            "x_kurtosis":      round(x_kurtosis, 3),
            "crest_factor":    round(z_crest, 3),
            "x_crest_factor":  round(x_crest, 3),
            # Additional hardware registers (previously missing)
            "z_axis_rms":      round(z_axis_rms, 4),
            "iso_peak_peak":   round(iso_peak_peak, 3),
            "z_true_peak":     round(z_true_peak, 3),
            "z_band_rms":      round(z_band_rms, 3),
            "x_band_rms":      round(x_band_rms, 3),
            "z_hf_rms_accel":  round(z_hf_rms_accel, 4),
            "x_hf_rms_accel":  round(x_hf_rms_accel, 4),
            "device_status":   int(device_status),
            # Derived
            "rms_overall":     round(math.sqrt(z_rms_mm ** 2 + x_rms_mm ** 2), 3),
            "bearing_health":  round(max(0.0, min(100.0, 100.0 - (z_rms_mm * 10.0))), 1),
            # Raw
            "raw_registers":      registers,
            "register_source":    read_source,
            "non_zero_registers": non_zero_count,
            "float32_reg20_21":   round(float32_val, 4),
        }
