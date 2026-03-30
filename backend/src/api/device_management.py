"""
Realistic Device Management API
Handles device discovery, connection management, and real-time monitoring
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import socket
import struct

from ..core.network_scanner import NetworkScanner, ModbusDeviceScanner, get_local_network_ranges
from ..acquisition.dual_modbus_client import DualModbusClient, ConnectionConfig, ConnectionType, ConnectionState
from ..acquisition.multi_device_manager import MultiDXMManager, DeviceInfo

logger = logging.getLogger(__name__)

# API Models
class NetworkScanRequest(BaseModel):
    network_range: str
    scan_type: str = "full"  # quick, full, modbus_only
    timeout: float = 2.0

class NetworkScanResult(BaseModel):
    scan_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    network_devices: List[Dict[str, Any]]
    modbus_devices: List[Dict[str, Any]]
    scan_duration: Optional[float]

class DeviceConnectionRequest(BaseModel):
    ip: str
    port: int = 502
    slave_id: int = 1
    connection_type: str = "tcp"
    timeout: float = 5.0

class DeviceConnectionResult(BaseModel):
    device_id: str
    status: str
    connection_type: str
    ip: str
    port: int
    slave_id: int
    response_time_ms: float
    device_info: Dict[str, Any]
    registers: Dict[int, Any]
    error_message: Optional[str]

class DeviceTestRequest(BaseModel):
    device_id: str
    test_type: str = "connectivity"  # connectivity, registers, performance

class DeviceTestResult(BaseModel):
    device_id: str
    test_type: str
    status: str
    results: Dict[str, Any]
    error_message: Optional[str]
    timestamp: datetime

# Router
router = APIRouter(prefix="/api/v1/devices", tags=["devices"])

# Global state
active_scans: Dict[str, Dict[str, Any]] = {}
connected_devices: Dict[str, DualModbusClient] = {}
device_managers: Dict[str, MultiDXMManager] = {}

@router.post("/scan/network")
async def start_network_scan(request: NetworkScanRequest, background_tasks: BackgroundTasks):
    """Start network scan for devices"""
    scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Initialize scan
    active_scans[scan_id] = {
        "status": "running",
        "started_at": datetime.now(),
        "completed_at": None,
        "network_devices": [],
        "modbus_devices": [],
        "scan_duration": None
    }
    
    # Start background scan
    background_tasks.add_task(
        perform_network_scan,
        scan_id,
        request.network_range,
        request.scan_type,
        request.timeout
    )
    
    return {"scan_id": scan_id, "status": "started"}

@router.get("/scan/{scan_id}")
async def get_scan_status(scan_id: str):
    """Get scan status and results"""
    if scan_id not in active_scans:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    return active_scans[scan_id]

@router.get("/scan/active")
async def get_active_scans():
    """Get all active scans"""
    return {
        "active_scans": [
            {"scan_id": scan_id, **scan_data}
            for scan_id, scan_data in active_scans.items()
            if scan_data["status"] == "running"
        ]
    }

@router.post("/connect")
async def connect_device(request: DeviceConnectionRequest):
    """Connect to a specific device"""
    device_id = f"device_{request.ip}_{request.slave_id}"
    
    try:
        # Create connection config
        config = ConnectionConfig(
            tcp_host=request.ip,
            tcp_port=request.port,
            serial_port=None,
            serial_baud=19200,
            slave_id=request.slave_id,
            primary_connection=ConnectionType.TCP,
            failover_enabled=False
        )
        
        # Create and connect client
        client = DualModbusClient(config)
        await client.start()
        
        # Test connection and read registers
        start_time = datetime.now()
        registers = await client.read_registers()
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Get device info
        device_info = await get_device_info(client, request.slave_id)
        
        # Store connected device
        connected_devices[device_id] = client
        
        result = DeviceConnectionResult(
            device_id=device_id,
            status="connected",
            connection_type=request.connection_type,
            ip=request.ip,
            port=request.port,
            slave_id=request.slave_id,
            response_time_ms=response_time,
            device_info=device_info,
            registers=registers or {},
            error_message=None
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to connect to device {request.ip}:{request.port}:{request.slave_id} - {e}")
        return DeviceConnectionResult(
            device_id=device_id,
            status="failed",
            connection_type=request.connection_type,
            ip=request.ip,
            port=request.port,
            slave_id=request.slave_id,
            response_time_ms=0.0,
            device_info={},
            registers={},
            error_message=str(e)
        )

@router.delete("/disconnect/{device_id}")
async def disconnect_device(device_id: str):
    """Disconnect a device"""
    if device_id not in connected_devices:
        raise HTTPException(status_code=404, detail="Device not connected")
    
    try:
        client = connected_devices[device_id]
        await client.stop()
        del connected_devices[device_id]
        
        return {"message": f"Device {device_id} disconnected successfully"}
        
    except Exception as e:
        logger.error(f"Failed to disconnect device {device_id} - {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/connected")
async def get_connected_devices():
    """Get list of connected devices"""
    devices = []
    
    for device_id, client in connected_devices.items():
        try:
            status = client.get_status()
            registers = await client.read_registers()
            
            devices.append({
                "device_id": device_id,
                "status": status,
                "registers": registers or {},
                "last_updated": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting status for device {device_id} - {e}")
            devices.append({
                "device_id": device_id,
                "status": {"state": "error", "error": str(e)},
                "registers": {},
                "last_updated": datetime.now().isoformat()
            })
    
    return {"connected_devices": devices}

@router.post("/test/{device_id}")
async def test_device(device_id: str, request: DeviceTestRequest):
    """Test a connected device"""
    if device_id not in connected_devices:
        raise HTTPException(status_code=404, detail="Device not connected")
    
    client = connected_devices[device_id]
    
    try:
        results = {}
        
        if request.test_type == "connectivity":
            results = await test_connectivity(client)
        elif request.test_type == "registers":
            results = await test_registers(client)
        elif request.test_type == "performance":
            results = await test_performance(client)
        else:
            raise HTTPException(status_code=400, detail="Invalid test type")
        
        return DeviceTestResult(
            device_id=device_id,
            test_type=request.test_type,
            status="completed",
            results=results,
            error_message=None,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Test failed for device {device_id} - {e}")
        return DeviceTestResult(
            device_id=device_id,
            test_type=request.test_type,
            status="failed",
            results={},
            error_message=str(e),
            timestamp=datetime.now()
        )

@router.get("/network/ranges")
async def get_network_ranges():
    """Get available network ranges for scanning"""
    try:
        ranges = await get_local_network_ranges()
        return {"network_ranges": ranges}
    except Exception as e:
        logger.error(f"Error getting network ranges: {e}")
        return {"network_ranges": ["192.168.1.0/24", "192.168.0.0/24", "10.0.0.0/24"]}

@router.get("/interfaces")
async def get_network_interfaces():
    """Get network interface information"""
    try:
        import psutil
        
        interfaces = []
        for interface, addrs in psutil.net_if_addrs().items():
            interface_info = {
                "name": interface,
                "addresses": []
            }
            
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    interface_info["addresses"].append({
                        "family": "IPv4",
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast
                    })
                elif addr.family == socket.AF_INET6:
                    interface_info["addresses"].append({
                        "family": "IPv6",
                        "address": addr.address,
                        "netmask": addr.netmask
                    })
            
            # Add interface stats
            try:
                stats = psutil.net_if_stats().get(interface)
                if stats:
                    interface_info["stats"] = {
                        "isup": stats.isup,
                        "duplex": stats.duplex,
                        "speed": stats.speed,
                        "mtu": stats.mtu
                    }
            except:
                pass
            
            interfaces.append(interface_info)
        
        return {"interfaces": interfaces}
        
    except Exception as e:
        logger.error(f"Error getting network interfaces: {e}")
        return {"interfaces": []}

# Background tasks
async def perform_network_scan(scan_id: str, network_range: str, scan_type: str, timeout: float):
    """Perform network scan in background"""
    try:
        scanner = NetworkScanner()
        modbus_scanner = ModbusDeviceScanner()
        
        # Update scan status
        active_scans[scan_id]["status"] = "scanning"
        
        # Scan network devices
        network_devices = []
        modbus_devices = []
        
        if scan_type in ["full", "quick"]:
            network_devices = await scanner.scan_network_range(network_range)
            
            # Filter for Modbus devices
            modbus_ips = [d.ip for d in network_devices if 502 in d.open_ports]
            
            if scan_type == "full" and modbus_ips:
                modbus_devices = await modbus_scanner.scan_modbus_devices(modbus_ips)
        
        elif scan_type == "modbus_only":
            # Scan only Modbus ports in the range
            import ipaddress
            network = ipaddress.ip_network(network_range, strict=False)
            ips = [str(ip) for ip in list(network.hosts())[:100]]  # Limit to 100 IPs
            
            modbus_devices = await modbus_scanner.scan_modbus_devices(ips)
        
        # Update scan results
        active_scans[scan_id].update({
            "status": "completed",
            "completed_at": datetime.now(),
            "network_devices": [device.__dict__ for device in network_devices],
            "modbus_devices": [device.__dict__ for device in modbus_devices],
            "scan_duration": (datetime.now() - active_scans[scan_id]["started_at"]).total_seconds()
        })
        
        logger.info(f"Scan {scan_id} completed: {len(network_devices)} network devices, {len(modbus_devices)} Modbus devices")
        
    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {e}")
        active_scans[scan_id].update({
            "status": "failed",
            "completed_at": datetime.now(),
            "error": str(e)
        })

# Helper functions
async def get_device_info(client: DualModbusClient, slave_id: int) -> Dict[str, Any]:
    """Get device information from registers"""
    try:
        registers = await client.read_registers()
        if not registers:
            return {}
        
        device_info = {}
        
        # Try to extract device information from common registers
        if 40001 in registers:
            device_info["device_id_raw"] = registers[40001]
            device_info["device_id"] = f"DEV-{slave_id:03d}"
        
        if 40002 in registers:
            firmware = registers[40002]
            device_info["firmware_version"] = f"{firmware >> 8}.{firmware & 0xFF}"
        
        if 40003 in registers:
            device_info["serial_number"] = f"{registers[40003]:08d}"
        
        if 40004 in registers:
            device_info["model_number"] = f"MDL-{registers[40004]:04d}"
        
        return device_info
        
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        return {}

async def test_connectivity(client: DualModbusClient) -> Dict[str, Any]:
    """Test device connectivity"""
    results = {}
    
    # Test connection status
    status = client.get_status()
    results["connection_status"] = status
    
    # Test response time
    start_time = datetime.now()
    try:
        await client.read_registers()
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        results["response_time_ms"] = response_time
        results["connectivity_test"] = "passed"
    except Exception as e:
        results["response_time_ms"] = 0
        results["connectivity_test"] = "failed"
        results["error"] = str(e)
    
    return results

async def test_registers(client: DualModbusClient) -> Dict[str, Any]:
    """Test register reading"""
    results = {}
    
    try:
        registers = await client.read_registers()
        results["register_count"] = len(registers) if registers else 0
        results["registers"] = registers or {}
        results["register_test"] = "passed"
        
        # Test specific registers
        test_registers = [40001, 40002, 40003, 40004, 40005]
        results["specific_registers"] = {}
        
        for reg in test_registers:
            if reg in (registers or {}):
                results["specific_registers"][reg] = registers[reg]
        
    except Exception as e:
        results["register_test"] = "failed"
        results["error"] = str(e)
    
    return results

async def test_performance(client: DualModbusClient) -> Dict[str, Any]:
    """Test device performance"""
    results = {}
    
    try:
        # Test multiple reads
        times = []
        for i in range(10):
            start_time = datetime.now()
            await client.read_registers()
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            times.append(response_time)
        
        if times:
            results["avg_response_time_ms"] = sum(times) / len(times)
            results["min_response_time_ms"] = min(times)
            results["max_response_time_ms"] = max(times)
            results["performance_test"] = "passed"
        else:
            results["performance_test"] = "failed"
            
    except Exception as e:
        results["performance_test"] = "failed"
        results["error"] = str(e)
    
    return results
