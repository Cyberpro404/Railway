"""Connection lifecycle manager with state machine and watchdog."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .modbus_client import ModbusConnectionProfile, UnifiedModbusClient
from .network_discovery import NetworkScanner
from .reconnect_handler import ReconnectHandler

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    IDLE = "IDLE"
    SCANNING = "SCANNING"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    RECONNECTING = "RECONNECTING"
    DISCONNECTED = "DISCONNECTED"
    STOPPED = "STOPPED"


class ConnectionManager:
    """Manages connection state, reconnect policy, and watchdog heartbeat."""

    HEARTBEAT_INTERVAL = 5.0
    WATCHDOG_FAILURE_THRESHOLD = 2

    def __init__(self):
        self.client = UnifiedModbusClient()
        self.reconnect_handler = ReconnectHandler(initial_delay=1.0, max_delay=30.0, backoff_factor=2.0)
        self.scanner = NetworkScanner()

        self.target_type: str = "NONE"
        self.target_params: Dict[str, Any] = {}
        self.profile: Optional[ModbusConnectionProfile] = None

        self.state: ConnectionState = ConnectionState.IDLE
        self.status_message = "Ready"
        self.last_successful_read: Optional[datetime] = None
        self.last_heartbeat: Optional[datetime] = None
        self.connected_at: Optional[datetime] = None
        self.packet_loss = 0.0
        self.total_reads = 0
        self.failed_reads = 0
        self._last_reconnect_reason: Optional[str] = None

        self._lock = asyncio.Lock()
        self._watchdog_task: Optional[asyncio.Task] = None
        self._shutdown = False

    async def start(self) -> None:
        self._shutdown = False
        if self._watchdog_task is None or self._watchdog_task.done():
            self._watchdog_task = asyncio.create_task(self._watchdog_loop())

    async def stop(self) -> None:
        self._shutdown = True
        if self._watchdog_task:
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass
        await self.disconnect(manual=True)
        self.state = ConnectionState.STOPPED

    def _transition(self, state: ConnectionState, message: str) -> None:
        self.state = state
        self.status_message = message

    async def connect_device(self, protocol: str, **kwargs: Any) -> bool:
        async with self._lock:
            protocol = (protocol or "").upper()
            self._transition(ConnectionState.CONNECTING, "Connecting")
            self.reconnect_handler.reset()

            if protocol == "TCP":
                profile = ModbusConnectionProfile(
                    protocol="TCP",
                    host=kwargs.get("host"),
                    tcp_port=int(kwargs.get("port", 502)),
                    slave_id=int(kwargs.get("slave_id", 1)),
                    timeout=float(kwargs.get("timeout", 2.5)),
                )
            else:
                profile = ModbusConnectionProfile(
                    protocol="RTU",
                    serial_port=kwargs.get("port"),
                    baudrate=int(kwargs.get("baud", kwargs.get("baudrate", 19200))),
                    slave_id=int(kwargs.get("slave_id", 1)),
                    timeout=float(kwargs.get("timeout", 2.5)),
                )

            success = await self.client.connect(profile)
            if success:
                self.profile = profile
                self.target_type = profile.protocol
                self.target_params = {
                    "host": profile.host,
                    "port": profile.tcp_port if profile.protocol == "TCP" else profile.serial_port,
                    "baud": profile.baudrate,
                    "slave_id": profile.slave_id,
                }
                now = datetime.now(timezone.utc)
                self.connected_at = now
                self.last_successful_read = now
                self.last_heartbeat = now
                self._transition(ConnectionState.CONNECTED, "Connected")
                return True

            self._transition(ConnectionState.DISCONNECTED, "Connection failed")
            return False

    async def disconnect(self, manual: bool = True) -> None:
        await self.client.disconnect()
        if manual:
            self.profile = None
            self.target_type = "NONE"
            self.target_params = {}
            self._transition(ConnectionState.DISCONNECTED, "Disconnected")

    async def trigger_reconnect(self, reason: str = "read_failure") -> bool:
        if self.profile is None:
            return False
        self._last_reconnect_reason = reason
        self._transition(ConnectionState.RECONNECTING, f"Reconnecting ({reason})")
        await self.reconnect_handler.sleep()

        try:
            success = await self.client.connect(self.profile)
        except Exception as exc:
            logger.error("Reconnect failed: %s", exc)
            success = False

        if success:
            self.reconnect_handler.reset()
            now = datetime.now(timezone.utc)
            self.last_heartbeat = now
            self.last_successful_read = now
            self._transition(ConnectionState.CONNECTED, "Connected")
            return True

        self._transition(ConnectionState.DEGRADED, "Reconnect failed")
        return False

    async def _watchdog_loop(self) -> None:
        failures = 0
        while not self._shutdown:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                if self.profile is None or not self.client.is_connected():
                    continue

                healthy = await self.client.heartbeat()
                if healthy:
                    failures = 0
                    self.last_heartbeat = datetime.now(timezone.utc)
                    if self.state in (ConnectionState.DEGRADED, ConnectionState.RECONNECTING):
                        self._transition(ConnectionState.CONNECTED, "Connected")
                    continue

                failures += 1
                if failures >= self.WATCHDOG_FAILURE_THRESHOLD:
                    await self.trigger_reconnect(reason="heartbeat_failure")
                    failures = 0
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Watchdog error: %s", exc)

    def note_read_result(self, success: bool) -> None:
        self.total_reads += 1
        if success:
            self.last_successful_read = datetime.now(timezone.utc)
        else:
            self.failed_reads += 1
        if self.total_reads > 0:
            self.packet_loss = round((self.failed_reads / self.total_reads) * 100.0, 2)

    def is_connected(self) -> bool:
        return self.client.is_connected()

    def get_status(self) -> Dict[str, Any]:
        uptime_seconds = 0
        if self.connected_at and self.is_connected():
            uptime_seconds = int((datetime.now(timezone.utc) - self.connected_at).total_seconds())

        port_value = None
        baud = 19200
        slave_id = 1
        if self.profile:
            if self.profile.protocol == "TCP":
                port_value = self.profile.host
            else:
                port_value = self.profile.serial_port
            baud = self.profile.baudrate
            slave_id = self.profile.slave_id

        return {
            "connected": self.is_connected(),
            "port": port_value,
            "baud": baud,
            "slave_id": slave_id,
            "uptime_seconds": uptime_seconds,
            "last_poll": self.last_successful_read.isoformat() if self.last_successful_read else None,
            "packet_loss": self.packet_loss,
            "auto_reconnect": True,
            "state": self.state.value,
            "message": self.status_message,
            "type": self.target_type,
            "reconnect_status": self.reconnect_handler.get_status(),
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "last_reconnect_reason": self._last_reconnect_reason,
        }

    async def scan_network(self, subnet: str = "192.168.0") -> List[str]:
        self._transition(ConnectionState.SCANNING, f"Scanning {subnet}.*")
        devices = await self.scanner.scan_subnet(subnet)
        if self.is_connected():
            self._transition(ConnectionState.CONNECTED, "Connected")
        elif self.profile:
            self._transition(ConnectionState.DEGRADED, "Idle (configured)")
        else:
            self._transition(ConnectionState.IDLE, "Ready")
        return devices

    async def scan_ports(self) -> list:
        self._transition(ConnectionState.SCANNING, "Scanning serial ports")
        ports = await self.scanner.scan_serial_ports()
        if self.is_connected():
            self._transition(ConnectionState.CONNECTED, "Connected")
        elif self.profile:
            self._transition(ConnectionState.DEGRADED, "Idle (configured)")
        else:
            self._transition(ConnectionState.IDLE, "Ready")
        return ports
