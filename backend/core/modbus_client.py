"""Unified Modbus transport abstraction for TCP and RTU."""

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional, Union

from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

logger = logging.getLogger(__name__)


@dataclass
class ModbusConnectionProfile:
    protocol: str
    slave_id: int = 1
    host: Optional[str] = None
    tcp_port: int = 502
    serial_port: Optional[str] = None
    baudrate: int = 19200
    timeout: float = 2.5


class UnifiedModbusClient:
    """Thread-safe async modbus client with protocol-agnostic operations."""

    def __init__(self):
        self.client: Optional[Union[AsyncModbusTcpClient, AsyncModbusSerialClient]] = None
        self.connection_type: str = "NONE"
        self.connected: bool = False
        self.profile: Optional[ModbusConnectionProfile] = None
        self._lock = asyncio.Lock()

    async def connect(self, profile: ModbusConnectionProfile) -> bool:
        if profile.protocol.upper() == "TCP":
            return await self.connect_tcp(
                host=profile.host or "",
                port=profile.tcp_port,
                slave_id=profile.slave_id,
                timeout=profile.timeout,
            )
        return await self.connect_rtu(
            port=profile.serial_port or "",
            baudrate=profile.baudrate,
            slave_id=profile.slave_id,
            timeout=profile.timeout,
        )

    async def connect_tcp(self, host: str, port: int = 502, slave_id: int = 1, timeout: float = 2.5) -> bool:
        async with self._lock:
            await self.disconnect()
            self.profile = ModbusConnectionProfile(
                protocol="TCP",
                host=host,
                tcp_port=port,
                slave_id=slave_id,
                timeout=timeout,
            )
            self.client = AsyncModbusTcpClient(host=host, port=port, timeout=timeout)
            try:
                # Force timeout on connect since pymodbus connect() can hang indefinitely
                self.connected = await asyncio.wait_for(self.client.connect(), timeout=timeout)
            except (asyncio.TimeoutError, Exception) as exc:
                logger.error("TCP connect error/timeout: %s", exc)
                self.connected = False
            self.connection_type = "TCP" if self.connected else "NONE"
            return self.connected

    async def connect_rtu(self, port: str, baudrate: int = 19200, slave_id: int = 1, timeout: float = 2.5) -> bool:
        async with self._lock:
            await self.disconnect()
            self.profile = ModbusConnectionProfile(
                protocol="RTU",
                serial_port=port,
                baudrate=baudrate,
                slave_id=slave_id,
                timeout=timeout,
            )
            self.client = AsyncModbusSerialClient(
                port=port,
                baudrate=baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=timeout,
            )
            try:
                # Force timeout on connect to prevent deadlocks/hanging
                self.connected = await asyncio.wait_for(self.client.connect(), timeout=timeout)
            except (asyncio.TimeoutError, Exception) as exc:
                logger.error("RTU connect error/timeout: %s", exc)
                self.connected = False
            self.connection_type = "RTU" if self.connected else "NONE"
            return self.connected

    async def disconnect(self) -> None:
        if self.client is not None:
            try:
                self.client.close()
            except Exception as exc:
                logger.debug("Error while closing Modbus client: %s", exc)
        self.client = None
        self.connected = False
        self.connection_type = "NONE"

    async def read_holding_registers(self, address: int, count: int, slave_id: int = 1) -> Optional[List[int]]:
        if not self.client or not self.client.connected:
            self.connected = False
            return None
        try:
            response = await self.client.read_holding_registers(address, count=count, slave=slave_id)
            if response.isError():
                return None
            return response.registers
        except (ModbusException, asyncio.TimeoutError) as exc:
            logger.warning("Modbus read failed: %s", exc)
            return None
        except Exception as exc:
            logger.error("Unexpected Modbus read error: %s", exc)
            return None

    async def heartbeat(self) -> bool:
        """Small read to validate session liveness."""
        profile = self.profile
        if not profile:
            return False
        registers = await self.read_holding_registers(address=0, count=1, slave_id=profile.slave_id)
        return registers is not None

    def is_connected(self) -> bool:
        # Reflect actual pymodbus socket state, not just our flag
        if self.client is not None:
            self.connected = bool(self.client.connected)
        return self.connected
