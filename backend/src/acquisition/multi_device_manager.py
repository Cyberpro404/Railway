"""
Multi-DXM Device Manager - Parallel data acquisition from multiple controllers.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from .dual_modbus_client import DualModbusClient, ConnectionConfig, ConnectionType, ConnectionState

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Device metadata"""
    device_id: str
    name: str
    location: str = ""
    coach_id: str = ""
    sensor_type: str = "QM30VT2"
    config: ConnectionConfig = field(default_factory=ConnectionConfig)


@dataclass
class UnifiedData:
    """Unified data packet from all devices"""
    timestamp: str
    devices: Dict[str, Any]
    aggregated: Dict[str, Any]
    device_count: int
    healthy_count: int


class MultiDXMManager:
    """
    Manages multiple DXM controllers for parallel data acquisition.
    Provides unified data stream with device identification.
    """
    
    def __init__(self, max_workers: int = 10):
        self.devices: Dict[str, DualModbusClient] = {}
        self.device_info: Dict[str, DeviceInfo] = {}
        self._running = False
        self._poll_interval: float = 1.0  # 1 Hz polling
        self._poll_task: Optional[asyncio.Task] = None
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Callbacks
        self._on_unified_data: Optional[Callable[[UnifiedData], None]] = None
        self._on_device_error: Optional[Callable[[str, Exception], None]] = None
        
        # Data buffer
        self._latest_data: Dict[str, Any] = {}
        self._data_lock = asyncio.Lock()
        
        logger.info("MultiDXMManager initialized")
    
    def register_device(self, device_info: DeviceInfo) -> bool:
        """Register a new DXM device"""
        device_id = device_info.device_id
        
        if device_id in self.devices:
            logger.warning(f"Device {device_id} already registered, updating config")
            # Stop existing device
            asyncio.create_task(self.devices[device_id].stop())
        
        # Create new dual client
        client = DualModbusClient(device_id, device_info.config)
        
        # Register callbacks
        client.on_status_change(lambda state: self._handle_status_change(device_id, state))
        client.on_failover(lambda conn_type: self._handle_failover(device_id, conn_type))
        
        self.devices[device_id] = client
        self.device_info[device_id] = device_info
        
        logger.info(f"Device {device_id} registered: {device_info.name} at {device_info.location}")
        return True
    
    def unregister_device(self, device_id: str) -> bool:
        """Unregister a device"""
        if device_id not in self.devices:
            logger.warning(f"Device {device_id} not found")
            return False
        
        # Stop the client
        asyncio.create_task(self.devices[device_id].stop())
        
        # Remove from tracking
        del self.devices[device_id]
        del self.device_info[device_id]
        if device_id in self._latest_data:
            del self._latest_data[device_id]
        
        logger.info(f"Device {device_id} unregistered")
        return True
    
    def on_unified_data(self, callback: Callable[[UnifiedData], None]):
        """Register callback for unified data stream"""
        self._on_unified_data = callback
    
    def on_device_error(self, callback: Callable[[str, Exception], None]):
        """Register callback for device errors"""
        self._on_device_error = callback
    
    async def start(self) -> bool:
        """Start all devices and begin polling"""
        self._running = True
        
        # Start all registered devices
        start_results = await asyncio.gather(
            *[device.start() for device in self.devices.values()],
            return_exceptions=True
        )
        
        success_count = sum(1 for r in start_results if r is True)
        logger.info(f"Started {success_count}/{len(self.devices)} devices")
        
        # Start polling loop
        self._poll_task = asyncio.create_task(self._poll_loop())
        
        return success_count > 0
    
    async def stop(self):
        """Stop all devices and polling"""
        self._running = False
        
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        
        # Stop all devices
        await asyncio.gather(
            *[device.stop() for device in self.devices.values()],
            return_exceptions=True
        )
        
        self._executor.shutdown(wait=False)
        logger.info("MultiDXMManager stopped")
    
    async def _poll_loop(self):
        """Main polling loop - reads from all devices concurrently"""
        while self._running:
            try:
                start_time = asyncio.get_event_loop().time()
                
                # Read from all devices concurrently
                read_tasks = []
                for device_id, device in self.devices.items():
                    task = self._read_device_with_timeout(device_id, device)
                    read_tasks.append(task)
                
                # Gather results
                results = await asyncio.gather(*read_tasks, return_exceptions=True)
                
                # Process results
                device_data = {}
                healthy_count = 0
                
                for device_id, result in zip(self.devices.keys(), results):
                    if isinstance(result, Exception):
                        logger.error(f"[{device_id}] Read error: {result}")
                        if self._on_device_error:
                            await asyncio.to_thread(self._on_device_error, device_id, result)
                    elif result is not None:
                        device_data[device_id] = result
                        healthy_count += 1
                
                # Update latest data
                async with self._data_lock:
                    self._latest_data.update(device_data)
                
                # Create unified data packet
                unified = self._create_unified_data(device_data, healthy_count)
                
                # Broadcast
                if self._on_unified_data:
                    try:
                        self._on_unified_data(unified)
                    except Exception as e:
                        logger.error(f"Error in data callback: {e}")
                
                # Calculate sleep time to maintain polling rate
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, self._poll_interval - elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    logger.warning(f"Polling loop running behind by {-sleep_time:.2f}s")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Polling loop error: {e}")
                await asyncio.sleep(1.0)
    
    async def _read_device_with_timeout(
        self, 
        device_id: str, 
        device: DualModbusClient,
        timeout: float = 2.0
    ) -> Optional[Dict[str, Any]]:
        """Read from a single device with timeout"""
        try:
            return await asyncio.wait_for(device.read_registers(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"[{device_id}] Read timeout")
            return None
    
    def _create_unified_data(self, device_data: Dict[str, Any], healthy_count: int) -> UnifiedData:
        """Create unified data packet from all device data"""
        # Calculate aggregated metrics
        aggregated = self._calculate_aggregates(device_data)
        
        return UnifiedData(
            timestamp=datetime.now().isoformat(),
            devices=device_data,
            aggregated=aggregated,
            device_count=len(self.devices),
            healthy_count=healthy_count
        )
    
    def _calculate_aggregates(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate aggregated metrics across all devices"""
        if not device_data:
            return {}
        
        aggregates = {}
        
        # Fields to aggregate
        fields = [
            "z_rms_mm", "x_rms_mm", "temperature",
            "z_peak_accel", "x_peak_accel",
            "z_kurtosis", "x_kurtosis",
            "z_crest_factor", "x_crest_factor",
            "z_hf_rms_accel", "x_hf_rms_accel"
        ]
        
        for field in fields:
            values = [d[field] for d in device_data.values() if field in d and isinstance(d[field], (int, float))]
            if values:
                aggregates[f"{field}_avg"] = round(sum(values) / len(values), 3)
                aggregates[f"{field}_max"] = round(max(values), 3)
                aggregates[f"{field}_min"] = round(min(values), 3)
        
        # Overall health score
        aggregates["health_percentage"] = round(
            (healthy_count / len(self.devices)) * 100, 1
        ) if self.devices else 0
        
        return aggregates
    
    def _handle_status_change(self, device_id: str, state: ConnectionState):
        """Handle device connection status change"""
        logger.info(f"[{device_id}] Connection state changed to {state.value}")
    
    def _handle_failover(self, device_id: str, conn_type: ConnectionType):
        """Handle device failover"""
        logger.warning(f"[{device_id}] Failover to {conn_type.value}")
    
    def get_device_status(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status for one or all devices"""
        if device_id:
            if device_id in self.devices:
                info = self.device_info.get(device_id)
                status = self.devices[device_id].get_status()
                return {
                    "info": {
                        "device_id": info.device_id if info else device_id,
                        "name": info.name if info else "Unknown",
                        "location": info.location if info else "",
                        "coach_id": info.coach_id if info else ""
                    },
                    "status": status
                }
            return {"error": f"Device {device_id} not found"}
        
        # Return all devices
        return {
            device_id: {
                "info": {
                    "device_id": info.device_id,
                    "name": info.name,
                    "location": info.location,
                    "coach_id": info.coach_id
                },
                "status": self.devices[device_id].get_status()
            }
            for device_id, info in self.device_info.items()
        }
    
    def get_latest_data(self, device_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get latest data for one or all devices"""
        if device_id:
            return self._latest_data.get(device_id)
        return dict(self._latest_data)
    
    def set_poll_interval(self, interval: float):
        """Set polling interval in seconds"""
        self._poll_interval = max(0.1, interval)
        logger.info(f"Poll interval set to {self._poll_interval}s")
