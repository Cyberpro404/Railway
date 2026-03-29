"""Auto-detect COM port with active Modbus sensor (fast, non-blocking)."""
import asyncio
import logging
from time import sleep
from typing import Any, Dict, List, Optional, Tuple

from pymodbus.client import ModbusSerialClient
from serial.tools import list_ports

logger = logging.getLogger(__name__)


async def _probe_port(
    port: str,
    address_to_read: int,
    baud: int,
    slave_id: int,
    connect_timeout: float,
) -> Tuple[str, Dict[str, Any]]:
    """Run the blocking Modbus probe for a single port in a worker thread."""

    def _run_probe() -> Dict[str, Any]:
        client = ModbusSerialClient(
            port=port,
            baudrate=baud,
            timeout=connect_timeout,
            retries=0,
            bytesize=8,
            parity="N",
            stopbits=1,
            strict=False,
        )

        try:
            if not client.connect():
                return {"success": False, "reason": "connect_failed"}

            # Allow the adapter to stabilize without blocking the main loop
            sleep(0.15)

            result = client.read_holding_registers(
                address=address_to_read,
                count=5,
                slave=slave_id,
            )
            if result.isError() or not getattr(result, "registers", None):
                return {"success": False, "reason": f"no_response:{result}"}

            registers = result.registers[:5]
            if any(r != 0 for r in registers):
                return {
                    "success": True,
                    "test_registers": registers,
                    "signal_strength": 95,
                }

            return {"success": False, "reason": "all_zero_registers"}
        finally:
            try:
                client.close()
            except Exception:
                pass

    try:
        result = await asyncio.wait_for(asyncio.to_thread(_run_probe), timeout=connect_timeout + 1.0)
    except asyncio.TimeoutError:
        return port, {"success": False, "reason": "timeout"}
    except Exception as exc:  # Defensive: serial drivers can throw unexpected errors
        return port, {"success": False, "reason": f"exception:{str(exc)[:80]}"}

    return port, result


async def auto_detect_modbus_port(
    start_register: int = 45201,
    baud: int = 19200,
    slave_id: int = 1,
    test_ports: Optional[List[str]] = None,
    max_concurrency: int = 4,
    connect_timeout: float = 1.2,
) -> Dict[str, Any]:
    """
    Quickly scan available COM ports for an active Modbus sensor without blocking the event loop.

    Args:
        start_register: Starting register address (45201 for railway sensor)
        baud: Baud rate (default 19200)
        slave_id: Modbus slave ID (default 1)
        test_ports: Optional list of ports to test (if None, scans all available)
        max_concurrency: Number of ports probed in parallel
        connect_timeout: Per-port timeout in seconds

    Returns:
        Dict with detection results and metadata.
    """

    logger.info("🔍 Starting auto-detection of Modbus sensor (non-blocking)")

    # Get available ports if not provided
    if test_ports is None:
        detected: List[str] = []
        try:
            for port in list_ports.comports():
                if getattr(port, "device", None):
                    detected.append(port.device)
                elif getattr(port, "name", None):
                    detected.append(port.name)
        except Exception as exc:
            logger.warning(f"Could not scan ports: {exc}")
        test_ports = detected or [f"COM{i}" for i in range(1, 21)]

    # Deduplicate while preserving order
    seen = set()
    test_ports = [p for p in test_ports if not (p in seen or seen.add(p))]

    if not test_ports:
        logger.warning("No COM ports found")
        return {
            "success": False,
            "port": None,
            "message": "No COM ports detected on this system",
            "tested_ports": [],
        }

    logger.info(f"Testing {len(test_ports)} ports: {', '.join(test_ports)}")

    address_to_read = start_register - 40001
    semaphore = asyncio.Semaphore(max(1, max_concurrency))
    tested_results: Dict[str, Dict[str, Any]] = {}

    async def _bounded_probe(port: str) -> Tuple[str, Dict[str, Any]]:
        async with semaphore:
            logger.info(f"⚡ Testing {port}...")
            return await _probe_port(port, address_to_read, baud, slave_id, connect_timeout)

    tasks = [asyncio.create_task(_bounded_probe(port)) for port in test_ports]

    # Process results as they complete to return the first success immediately
    for task in asyncio.as_completed(tasks):
        port, result = await task
        tested_results[port] = result

        if result.get("success"):
            logger.info(f"✅ Found active Modbus sensor on {port}")
            return {
                "success": True,
                "port": port,
                "baud": baud,
                "slave_id": slave_id,
                "message": f"Sensor detected on {port}",
                "test_registers": result.get("test_registers"),
                "signal_strength": result.get("signal_strength", 90),
                "tested_ports": list(tested_results.keys()),
            }
        else:
            reason = result.get("reason", "unknown")
            logger.debug(f"   {port}: probe failed ({reason})")

    # No sensor found
    logger.warning(
        f"⚠️  No active Modbus sensor detected on {len(test_ports)} tested ports"
    )
    return {
        "success": False,
        "port": None,
        "tested_ports": list(tested_results.keys()) or test_ports,
        "message": (
            f"Tested {len(test_ports)} ports in parallel, no sensor found. "
            "Check physical connections."
        ),
        "baud": baud,
        "slave_id": slave_id,
    }
