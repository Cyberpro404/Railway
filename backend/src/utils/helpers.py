"""
Utility functions for the railway monitoring system.
"""
import logging
import psutil
import platform
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_system_stats() -> Dict[str, Any]:
    """Get current system resource statistics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network stats
        net_io = psutil.net_io_counters()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count(),
                "frequency_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else None
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent": memory.percent,
                "used_gb": round(memory.used / (1024**3), 2)
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent
            },
            "network": {
                "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
                "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errors_in": net_io.errin,
                "errors_out": net_io.errout
            },
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            }
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {"error": str(e)}


def format_bytes(bytes_val: int) -> str:
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"


def calculate_health_score(metrics: Dict[str, Any]) -> float:
    """Calculate overall health score from metrics"""
    scores = []
    
    # CPU health (lower is better)
    cpu_percent = metrics.get("cpu", {}).get("percent", 0)
    scores.append(max(0, 100 - cpu_percent))
    
    # Memory health
    mem_percent = metrics.get("memory", {}).get("percent", 0)
    scores.append(max(0, 100 - mem_percent))
    
    # Disk health
    disk_percent = metrics.get("disk", {}).get("percent", 0)
    scores.append(max(0, 100 - disk_percent))
    
    return round(sum(scores) / len(scores), 1) if scores else 100.0


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division handling zero denominator"""
    if denominator == 0:
        return default
    return numerator / denominator


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range"""
    return max(min_val, min(max_val, value))
