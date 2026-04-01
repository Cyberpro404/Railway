"""
Simplified Device Management API
Basic device discovery and connection management
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import socket
import ipaddress

logger = logging.getLogger(__name__)

# API Models
class NetworkScanRequest(BaseModel):
    network_range: str
    scan_type: str = "quick"
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

# Router
router = APIRouter(tags=["devices"])

# Global state
active_scans: Dict[str, Dict[str, Any]] = {}
connected_devices: Dict[str, Dict[str, Any]] = {}

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
        # Simulate connection
        start_time = datetime.now()
        
        # Simulate Modbus connection and register read
        await asyncio.sleep(0.1)  # Simulate network delay
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Simulate device registers
        registers = {
            40001: 0x4448,  # DX identifier
            40002: 0x0102,  # Firmware version 1.2
            40003: 12345678,  # Serial number
            40004: 5678,  # Model number
            40005: 2500,  # Temperature (0.1°C)
            40006: 1234,  # Z RMS velocity (0.001 mm/s)
            40007: 1567,  # X RMS velocity (0.001 mm/s)
        }
        
        device_info = {
            "device_id": f"DXM-{request.slave_id:03d}",
            "firmware_version": "1.2",
            "serial_number": f"{registers[40003]:08d}",
            "model": f"MDL-{registers[40004]:04d}",
            "vendor": "Banner Engineering"
        }
        
        # Store connected device
        connected_devices[device_id] = {
            "device_id": device_id,
            "ip": request.ip,
            "port": request.port,
            "slave_id": request.slave_id,
            "connected_at": datetime.now(),
            "registers": registers,
            "device_info": device_info
        }
        
        result = DeviceConnectionResult(
            device_id=device_id,
            status="connected",
            connection_type=request.connection_type,
            ip=request.ip,
            port=request.port,
            slave_id=request.slave_id,
            response_time_ms=response_time,
            device_info=device_info,
            registers=registers,
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
        del connected_devices[device_id]
        return {"message": f"Device {device_id} disconnected successfully"}
        
    except Exception as e:
        logger.error(f"Failed to disconnect device {device_id} - {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/connected")
async def get_connected_devices():
    """Get list of connected devices"""
    devices = []
    
    for device_id, device_data in connected_devices.items():
        # Simulate real-time data updates
        registers = device_data["registers"].copy()
        
        # Add some realistic variation to sensor values
        import random
        registers[40005] = 2500 + random.randint(-50, 50)  # Temperature variation
        registers[40006] = 1234 + random.randint(-100, 100)  # Vibration variation
        registers[40007] = 1567 + random.randint(-100, 100)  # Vibration variation
        
        devices.append({
            "device_id": device_id,
            "status": {"state": "connected", "ip": device_data["ip"]},
            "registers": registers,
            "last_updated": datetime.now().isoformat()
        })
    
    return {"connected_devices": devices}

@router.get("/network/ranges")
async def get_network_ranges():
    """Get available network ranges for scanning"""
    try:
        # Get local IP and create network range
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        ip_parts = local_ip.split('.')
        network_range = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
        
        ranges = [network_range]
        
        # Add common private network ranges
        common_ranges = [
            "192.168.1.0/24",
            "192.168.0.0/24", 
            "10.0.0.0/24",
            "172.16.0.0/24"
        ]
        
        for range_str in common_ranges:
            if range_str not in ranges:
                ranges.append(range_str)
        
        return {"network_ranges": ranges}
        
    except Exception as e:
        logger.error(f"Error getting network ranges: {e}")
        return {"network_ranges": ["192.168.1.0/24", "192.168.0.0/24", "10.0.0.0/24"]}

@router.get("/interfaces")
async def get_network_interfaces():
    """Get network interface information"""
    try:
        # Simulate network interface data
        interfaces = [
            {
                "name": "Ethernet",
                "addresses": [
                    {
                        "family": "IPv4",
                        "address": "192.168.1.100",
                        "netmask": "255.255.255.0",
                        "broadcast": "192.168.1.255"
                    }
                ],
                "stats": {
                    "isup": True,
                    "duplex": 2,
                    "speed": 1000,
                    "mtu": 1500
                }
            },
            {
                "name": "Wi-Fi",
                "addresses": [
                    {
                        "family": "IPv4",
                        "address": "192.168.1.101",
                        "netmask": "255.255.255.0"
                    }
                ],
                "stats": {
                    "isup": True,
                    "duplex": 2,
                    "speed": 866,
                    "mtu": 1500
                }
            }
        ]
        
        return {"interfaces": interfaces}
        
    except Exception as e:
        logger.error(f"Error getting network interfaces: {e}")
        return {"interfaces": []}

# Background tasks
async def perform_network_scan(scan_id: str, network_range: str, scan_type: str, timeout: float):
    """Perform network scan in background"""
    try:
        # Update scan status
        active_scans[scan_id]["status"] = "scanning"
        
        # Simulate scanning
        await asyncio.sleep(2)  # Simulate scan time
        
        # Generate mock scan results
        network_devices = []
        modbus_devices = []
        
        if scan_type in ["full", "quick"]:
            # Simulate finding some network devices
            network_devices = [
                {
                    "ip": "192.168.1.1",
                    "mac": "00:11:22:33:44:55",
                    "hostname": "router",
                    "vendor": "Unknown",
                    "open_ports": [22, 80, 443],
                    "device_type": "Network Infrastructure",
                    "confidence": 0.8,
                    "response_time_ms": 5.2,
                    "last_seen": datetime.now().isoformat()
                },
                {
                    "ip": "192.168.1.10",
                    "mac": "AA:BB:CC:DD:EE:FF",
                    "hostname": "server",
                    "vendor": "Dell",
                    "open_ports": [22, 80, 443, 502],
                    "device_type": "Modbus Device",
                    "confidence": 0.7,
                    "response_time_ms": 8.1,
                    "last_seen": datetime.now().isoformat()
                }
            ]
            
            if scan_type == "full":
                # Simulate finding Modbus devices
                modbus_devices = [
                    {
                        "ip": "192.168.1.10",
                        "port": 502,
                        "slave_id": 1,
                        "device_id": "DXM-001",
                        "firmware_version": "1.2",
                        "serial_number": "12345678",
                        "model": "MDL-5678",
                        "vendor": "Banner Engineering",
                        "is_dxm": True,
                        "confidence": 0.95,
                        "response_time_ms": 12.3,
                        "registers": {
                            40001: 0x4448,
                            40002: 0x0102,
                            40003: 12345678,
                            40004: 5678,
                            40005: 2500,
                            40006: 1234,
                            40007: 1567
                        }
                    }
                ]
        
        elif scan_type == "modbus_only":
            # Simulate Modbus-only scan
            modbus_devices = [
                {
                    "ip": "192.168.1.10",
                    "port": 502,
                    "slave_id": 1,
                    "device_id": "DXM-001",
                    "firmware_version": "1.2",
                    "serial_number": "12345678",
                    "model": "MDL-5678",
                    "vendor": "Banner Engineering",
                    "is_dxm": True,
                    "confidence": 0.95,
                    "response_time_ms": 12.3,
                    "registers": {
                        40001: 0x4448,
                        40002: 0x0102,
                        40003: 12345678,
                        40004: 5678,
                        40005: 2500,
                        40006: 1234,
                        40007: 1567
                    }
                }
            ]
        
        # Update scan results
        active_scans[scan_id].update({
            "status": "completed",
            "completed_at": datetime.now(),
            "network_devices": network_devices,
            "modbus_devices": modbus_devices,
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
