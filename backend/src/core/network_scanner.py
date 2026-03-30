"""
Realistic Network Scanner for DXM Device Discovery
Scans network for Banner DXM controllers and other Modbus devices
"""
import asyncio
import socket
import struct
import ipaddress
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import subprocess
import platform

logger = logging.getLogger(__name__)

@dataclass
class NetworkDevice:
    """Discovered network device"""
    ip: str
    mac: str
    hostname: Optional[str]
    vendor: Optional[str]
    open_ports: List[int]
    device_type: str
    confidence: float
    response_time_ms: float
    last_seen: datetime

@dataclass
class ModbusDevice:
    """Modbus-enabled device (DXM or similar)"""
    ip: str
    port: int
    slave_id: int
    device_id: Optional[str]
    firmware_version: Optional[str]
    serial_number: Optional[str]
    model: Optional[str]
    vendor: Optional[str]
    is_dxm: bool
    confidence: float
    registers: Dict[int, Any]

class NetworkScanner:
    """Advanced network scanner for industrial devices"""
    
    def __init__(self):
        self.modbus_port = 502
        self.timeout = 2.0
        self.max_concurrent = 50
        self.banner_signatures = {
            'banner': ['banner', 'dxm', 'qm30', 'engineering'],
            'modbus': ['modbus', 'tcp', 'rtu'],
            'industrial': ['siemens', 'schneider', 'rockwell', 'abb']
        }
    
    async def scan_network_range(self, network_range: str) -> List[NetworkDevice]:
        """Scan a network range for devices"""
        logger.info(f"Scanning network range: {network_range}")
        
        try:
            network = ipaddress.ip_network(network_range, strict=False)
            ips = [str(ip) for ip in network.hosts()]
            
            # Limit scan size for performance
            if len(ips) > 254:
                ips = ips[:254]
            
            logger.info(f"Scanning {len(ips)} IP addresses")
            
            # Concurrent ping scan
            alive_ips = await self._concurrent_ping_scan(ips)
            logger.info(f"Found {len(alive_ips)} responsive hosts")
            
            # Port scan alive hosts
            devices = await self._concurrent_port_scan(alive_ips)
            logger.info(f"Found {len(devices)} devices with open ports")
            
            return devices
            
        except Exception as e:
            logger.error(f"Network scan error: {e}")
            return []
    
    async def _concurrent_ping_scan(self, ips: List[str]) -> List[str]:
        """Concurrent ping scan to find alive hosts"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def ping_host(ip: str) -> Optional[str]:
            async with semaphore:
                return await self._ping_host(ip)
        
        tasks = [ping_host(ip) for ip in ips]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        alive_ips = []
        for result in results:
            if isinstance(result, str):
                alive_ips.append(result)
        
        return alive_ips
    
    async def _ping_host(self, ip: str) -> Optional[str]:
        """Ping a single host"""
        try:
            if platform.system().lower() == 'windows':
                cmd = ['ping', '-n', '1', '-w', '1000', ip]
            else:
                cmd = ['ping', '-c', '1', '-W', '1', ip]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                return ip
            
        except Exception as e:
            logger.debug(f"Ping error for {ip}: {e}")
        
        return None
    
    async def _concurrent_port_scan(self, ips: List[str]) -> List[NetworkDevice]:
        """Concurrent port scan on alive hosts"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def scan_host(ip: str) -> Optional[NetworkDevice]:
            async with semaphore:
                return await self._scan_host_ports(ip)
        
        tasks = [scan_host(ip) for ip in ips]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        devices = []
        for result in results:
            if isinstance(result, NetworkDevice):
                devices.append(result)
        
        return devices
    
    async def _scan_host_ports(self, ip: str) -> Optional[NetworkDevice]:
        """Scan common ports on a host"""
        common_ports = [22, 23, 53, 80, 135, 139, 443, 445, 502, 8080, 8000, 9000]
        open_ports = []
        
        for port in common_ports:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=self.timeout
                )
                open_ports.append(port)
                writer.close()
                await writer.wait_closed()
            except:
                continue
        
        if not open_ports:
            return None
        
        # Get additional host info
        hostname, mac, vendor = await self._get_host_info(ip)
        
        # Determine device type
        device_type = self._classify_device(ip, open_ports, hostname, vendor)
        
        return NetworkDevice(
            ip=ip,
            mac=mac,
            hostname=hostname,
            vendor=vendor,
            open_ports=open_ports,
            device_type=device_type,
            confidence=self._calculate_confidence(open_ports, device_type),
            response_time_ms=0.0,
            last_seen=datetime.now()
        )
    
    async def _get_host_info(self, ip: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get hostname, MAC, and vendor information"""
        hostname = None
        mac = None
        vendor = None
        
        try:
            # Get hostname
            hostname = socket.gethostbyaddr(ip)[0]
        except:
            pass
        
        try:
            # Get MAC address (works on local network)
            if platform.system().lower() != 'windows':
                cmd = ['arp', '-n', ip]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                output = stdout.decode()
                
                if 'ether' in output:
                    parts = output.split()
                    for i, part in enumerate(parts):
                        if ':' in part and len(part) == 17:  # MAC format
                            mac = part
                            break
        except:
            pass
        
        return hostname, mac, vendor
    
    def _classify_device(self, ip: str, open_ports: List[int], hostname: Optional[str], vendor: Optional[str]) -> str:
        """Classify device type based on available information"""
        if 502 in open_ports:
            if hostname and any(sig in hostname.lower() for sig in self.banner_signatures['banner']):
                return 'DXM Controller'
            return 'Modbus Device'
        
        if 80 in open_ports or 443 in open_ports:
            return 'Web Device'
        
        if 22 in open_ports:
            return 'SSH Device'
        
        if hostname:
            hostname_lower = hostname.lower()
            if 'router' in hostname_lower or 'gateway' in hostname_lower:
                return 'Network Infrastructure'
            elif 'switch' in hostname_lower:
                return 'Network Switch'
            elif 'server' in hostname_lower:
                return 'Server'
        
        return 'Unknown Device'
    
    def _calculate_confidence(self, open_ports: List[int], device_type: str) -> float:
        """Calculate confidence score for device classification"""
        confidence = 0.5  # Base confidence
        
        if device_type == 'DXM Controller' and 502 in open_ports:
            confidence = 0.9
        elif device_type == 'Modbus Device':
            confidence = 0.8
        elif 80 in open_ports or 443 in open_ports:
            confidence = 0.7
        elif len(open_ports) > 3:
            confidence = 0.6
        
        return confidence

class ModbusDeviceScanner:
    """Specialized scanner for Modbus devices (DXM controllers)"""
    
    def __init__(self):
        self.modbus_port = 502
        self.timeout = 3.0
        self.dxm_register_map = {
            40001: 'device_id',
            40002: 'firmware_version',
            40003: 'serial_number',
            40004: 'model_number',
            40005: 'temperature',
            40006: 'z_rms_velocity',
            40007: 'x_rms_velocity'
        }
    
    async def scan_modbus_devices(self, ips: List[str]) -> List[ModbusDevice]:
        """Scan specific IPs for Modbus devices"""
        semaphore = asyncio.Semaphore(20)
        
        async def scan_device(ip: str) -> Optional[ModbusDevice]:
            async with semaphore:
                return await self._scan_modbus_device(ip)
        
        tasks = [scan_device(ip) for ip in ips]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        devices = []
        for result in results:
            if isinstance(result, ModbusDevice):
                devices.append(result)
        
        return devices
    
    async def _scan_modbus_device(self, ip: str, slave_ids: List[int] = None) -> Optional[ModbusDevice]:
        """Scan a single IP for Modbus devices"""
        if slave_ids is None:
            slave_ids = list(range(1, 247))  # Standard Modbus slave ID range
        
        for slave_id in slave_ids:
            try:
                device = await self._probe_modbus_device(ip, self.modbus_port, slave_id)
                if device:
                    return device
            except Exception as e:
                logger.debug(f"Failed to probe {ip}:{slave_id} - {e}")
                continue
        
        return None
    
    async def _probe_modbus_device(self, ip: str, port: int, slave_id: int) -> Optional[ModbusDevice]:
        """Probe a Modbus device for identification"""
        try:
            start_time = datetime.now()
            
            # Connect to Modbus device
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=self.timeout
            )
            
            # Send Modbus request (Read Holding Registers)
            request = self._build_modbus_request(slave_id, 40001, 10)
            writer.write(request)
            await writer.drain()
            
            # Read response
            response = await asyncio.wait_for(
                reader.read(1024),
                timeout=self.timeout
            )
            
            writer.close()
            await writer.wait_closed()
            
            # Parse response
            if len(response) >= 9:  # Minimum Modbus TCP response size
                device_info = self._parse_modbus_response(response, slave_id)
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return ModbusDevice(
                    ip=ip,
                    port=port,
                    slave_id=slave_id,
                    device_id=device_info.get('device_id'),
                    firmware_version=device_info.get('firmware_version'),
                    serial_number=device_info.get('serial_number'),
                    model=device_info.get('model'),
                    vendor=device_info.get('vendor'),
                    is_dxm=self._is_dxm_device(device_info),
                    confidence=self._calculate_modbus_confidence(device_info),
                    response_time_ms=response_time,
                    registers=device_info.get('registers', {})
                )
            
        except Exception as e:
            logger.debug(f"Modbus probe failed for {ip}:{port}:{slave_id} - {e}")
        
        return None
    
    def _build_modbus_request(self, slave_id: int, start_address: int, quantity: int) -> bytes:
        """Build Modbus TCP read holding registers request"""
        # Modbus TCP header
        transaction_id = 0x0001
        protocol_id = 0x0000
        length = 6
        unit_id = slave_id
        
        # Function code 0x03 (Read Holding Registers)
        function_code = 0x03
        start_register = start_address - 40001  # Convert to 0-based
        register_count = quantity
        
        request = struct.pack('>HHHHHBBHH', 
            transaction_id, protocol_id, length,
            unit_id, function_code, start_register, register_count)
        
        return request
    
    def _parse_modbus_response(self, response: bytes, slave_id: int) -> Dict[str, Any]:
        """Parse Modbus response and extract device information"""
        try:
            if len(response) < 9:
                return {}
            
            # Extract Modbus data
            function_code = response[7]
            byte_count = response[8]
            
            if function_code != 0x03 or len(response) < 9 + byte_count:
                return {}
            
            data = response[9:9 + byte_count]
            registers = {}
            
            # Parse register values
            for i in range(0, min(byte_count, 20), 2):  # Limit to first 10 registers
                if i + 1 < len(data):
                    value = struct.unpack('>H', data[i:i+2])[0]
                    register_addr = 40001 + (i // 2)
                    registers[register_addr] = value
            
            # Try to identify device from register values
            device_info = {'registers': registers}
            
            # Check for DXM-specific patterns
            if 40001 in registers:
                device_id = registers[40001]
                if device_id == 0x4448:  # 'DX' in hex
                    device_info['device_id'] = f'DXM-{slave_id:03d}'
                    device_info['vendor'] = 'Banner Engineering'
                else:
                    device_info['device_id'] = f'MODBUS-{slave_id:03d}'
            
            if 40002 in registers:
                firmware = registers[40002]
                device_info['firmware_version'] = f'{firmware >> 8}.{firmware & 0xFF}'
            
            if 40003 in registers:
                serial = registers[40003]
                device_info['serial_number'] = f'{serial:08d}'
            
            return device_info
            
        except Exception as e:
            logger.debug(f"Failed to parse Modbus response: {e}")
            return {}
    
    def _is_dxm_device(self, device_info: Dict[str, Any]) -> bool:
        """Check if device is a Banner DXM controller"""
        vendor = device_info.get('vendor', '').lower()
        device_id = device_info.get('device_id', '').lower()
        
        return ('banner' in vendor or 
                'dxm' in device_id or
                'qm30' in device_id)
    
    def _calculate_modbus_confidence(self, device_info: Dict[str, Any]) -> float:
        """Calculate confidence score for Modbus device identification"""
        confidence = 0.5
        
        if device_info.get('vendor') == 'Banner Engineering':
            confidence = 0.95
        elif device_info.get('device_id') and 'dxm' in device_info['device_id'].lower():
            confidence = 0.90
        elif device_info.get('firmware_version'):
            confidence = 0.80
        elif len(device_info.get('registers', {})) > 5:
            confidence = 0.70
        
        return confidence

async def get_local_network_ranges() -> List[str]:
    """Get local network ranges for scanning"""
    ranges = []
    
    try:
        # Get local IP and subnet
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Create network range from local IP
        ip_parts = local_ip.split('.')
        network_range = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
        ranges.append(network_range)
        
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
                
    except Exception as e:
        logger.error(f"Error getting network ranges: {e}")
        # Fallback to common ranges
        ranges = ["192.168.1.0/24", "192.168.0.0/24", "10.0.0.0/24"]
    
    return ranges

async def main():
    """Main scanning function"""
    scanner = NetworkScanner()
    modbus_scanner = ModbusDeviceScanner()
    
    # Get network ranges
    ranges = await get_local_network_ranges()
    logger.info(f"Scanning network ranges: {ranges}")
    
    # Scan for network devices
    all_devices = []
    for range_str in ranges:
        devices = await scanner.scan_network_range(range_str)
        all_devices.extend(devices)
    
    # Filter for Modbus devices
    modbus_ips = [d.ip for d in all_devices if 502 in d.open_ports]
    logger.info(f"Found {len(modbus_ips)} potential Modbus devices")
    
    # Scan Modbus devices in detail
    modbus_devices = await modbus_scanner.scan_modbus_devices(modbus_ips)
    logger.info(f"Found {len(modbus_devices)} Modbus devices")
    
    return all_devices, modbus_devices

if __name__ == "__main__":
    asyncio.run(main())
