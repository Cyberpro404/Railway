"""Asynchronous discovery for Modbus TCP and serial endpoints."""

import asyncio
import ipaddress
import logging
from typing import List

import serial.tools.list_ports

logger = logging.getLogger(__name__)


class NetworkScanner:
    """Scans subnet and serial interfaces without blocking the event loop."""

    CONCURRENCY_LIMIT = 64
    SCAN_TIMEOUT = 0.45
    RETRIES = 2

    @staticmethod
    def _normalize_subnet(subnet_base: str) -> str:
        base = (subnet_base or "192.168.0").strip().rstrip(".")
        if "/" in base:
            network = ipaddress.ip_network(base, strict=False)
            if network.prefixlen <= 24:
                return str(list(network.hosts())[0]).rsplit(".", 1)[0]
            return str(network.network_address).rsplit(".", 1)[0]
        parts = base.split(".")
        if len(parts) != 3:
            return "192.168.0"
        return base

    @classmethod
    async def _probe_ip(cls, ip: str, timeout: float) -> bool:
        for attempt in range(1, cls.RETRIES + 1):
            writer = None
            try:
                _, writer = await asyncio.wait_for(asyncio.open_connection(ip, 502), timeout=timeout)
                return True
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                if attempt >= cls.RETRIES:
                    return False
            finally:
                if writer is not None:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass
        return False

    @classmethod
    async def scan_subnet(cls, subnet_base: str = "192.168.0") -> List[str]:
        base = cls._normalize_subnet(subnet_base)
        semaphore = asyncio.Semaphore(cls.CONCURRENCY_LIMIT)
        discovered: List[str] = []

        logger.info("Starting DXM TCP subnet scan on %s.*", base)

        async def bounded_probe(ip: str) -> None:
            async with semaphore:
                if await cls._probe_ip(ip, cls.SCAN_TIMEOUT):
                    discovered.append(ip)

        tasks = [bounded_probe(f"{base}.{host}") for host in range(1, 255)]
        await asyncio.gather(*tasks, return_exceptions=False)
        discovered.sort(key=lambda item: tuple(int(part) for part in item.split(".")))
        logger.info("Completed subnet scan on %s.*; found %s device(s)", base, len(discovered))
        return discovered

    @staticmethod
    async def scan_serial_ports() -> list:
        try:
            ports = await asyncio.to_thread(serial.tools.list_ports.comports)
            return sorted([{"device": p.device, "description": p.description, "hwid": p.hwid or "Unknown"} for p in ports], key=lambda x: x["device"])
        except Exception as exc:
            logger.error("Serial port scan failed: %s", exc)
            return []
