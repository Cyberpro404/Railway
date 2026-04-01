"""High-level backend facade used by API layer and GUI-facing flows."""

import asyncio
from typing import Any, Dict, List, Optional

from .connection_manager import ConnectionManager
from .data_receiver import DataReceiver
from .realtime_data_stream import RealtimeStream


class BackendFacade:
    """Frontend-safe API layer: scan/connect/read without protocol leakage."""

    def __init__(self, connection_manager: ConnectionManager, data_receiver: DataReceiver, realtime_stream: RealtimeStream):
        self.connection_manager = connection_manager
        self.data_receiver = data_receiver
        self.realtime_stream = realtime_stream

    async def start(self) -> None:
        await self.connection_manager.start()
        await self.data_receiver.start()
        await self.realtime_stream.start()

    async def stop(self) -> None:
        await self.data_receiver.stop()
        await self.realtime_stream.stop()
        await self.connection_manager.stop()

    async def scan_network(self, subnet: str = "192.168.0") -> List[str]:
        return await self.connection_manager.scan_network(subnet)

    async def scan_ports(self) -> list:
        return await self.connection_manager.scan_ports()

    async def connect_device(
        self,
        protocol: str,
        host: Optional[str] = None,
        port: Optional[str] = None,
        baud: int = 19200,
        slave_id: int = 1,
        tcp_port: int = 502,
    ) -> bool:
        protocol_upper = protocol.upper()
        if protocol_upper == "TCP":
            target_host = host or port
            return await self.connection_manager.connect_device(
                "TCP", host=target_host, port=tcp_port, slave_id=slave_id
            )

        return await self.connection_manager.connect_device(
            "RTU", port=port, baud=baud, slave_id=slave_id
        )

    async def disconnect_device(self) -> None:
        await self.connection_manager.disconnect(manual=True)

    def get_status(self) -> Dict[str, Any]:
        return self.connection_manager.get_status()

    async def get_live_data(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        try:
            return await asyncio.wait_for(self.data_receiver.data_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def notify_connection_success(self) -> None:
        await self.realtime_stream.broadcast(
            {
                "event": "connection_success",
                "timestamp": self.get_status().get("last_poll"),
                "connection_status": self.get_status(),
            }
        )

    async def notify_connection_failure(self, message: str) -> None:
        await self.realtime_stream.broadcast(
            {
                "event": "connection_failure",
                "message": message,
                "connection_status": self.get_status(),
            }
        )
