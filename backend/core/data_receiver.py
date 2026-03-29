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
        registers = await self.cm.client.read_holding_registers(address=5200, count=22, slave_id=slave_id)
        if not registers:
            return None

        def get_reg(index: int, divisor: float = 1.0) -> float:
            if index >= len(registers):
                return 0.0
            return registers[index] / divisor

        def signed(value: float) -> float:
            return value - 655.36 if value > 327.67 else value

        z_rms_mm = get_reg(1, 1000.0)
        x_rms_mm = get_reg(5, 1000.0)
        z_peak_vel_mm = get_reg(17, 1000.0)
        x_peak_vel_mm = get_reg(19, 1000.0)
        z_peak_accel = get_reg(6, 1000.0)
        x_peak_accel = get_reg(7, 1000.0)
        temperature = signed(get_reg(3, 100.0))
        z_peak_freq = get_reg(8, 10.0)
        z_kurtosis = get_reg(12, 1000.0)
        z_crest = get_reg(14, 1000.0)

        return {
            "z_rms": round(z_rms_mm, 3),
            "x_rms": round(x_rms_mm, 3),
            "z_peak": round(z_peak_vel_mm, 3),
            "x_peak": round(x_peak_vel_mm, 3),
            "z_accel": round(z_peak_accel, 3),
            "x_accel": round(x_peak_accel, 3),
            "temperature": round(temperature, 1),
            "frequency": round(z_peak_freq, 1),
            "kurtosis": round(z_kurtosis, 3),
            "crest_factor": round(z_crest, 3),
            "rms_overall": round(math.sqrt(z_rms_mm ** 2 + x_rms_mm ** 2), 3),
            "bearing_health": round(max(0.0, min(100.0, 100.0 - (z_rms_mm * 10.0))), 1),
            "raw_registers": registers,
        }
