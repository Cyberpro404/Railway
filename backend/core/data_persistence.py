"""
Data persistence for maintaining chart data across tab navigation
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any
from pathlib import Path

class DataPersistence:
    """Manages persistent storage for chart data and application state with memory caching"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Data files
        self.chart_data_file = self.data_dir / "chart_data.json"
        self.sensor_state_file = self.data_dir / "sensor_state.json"
        self.app_state_file = self.data_dir / "app_state.json"
        
        # Maximum data points to keep
        self.max_points = 2000 # Increased for better history
        
        # Memory Cache
        self._chart_cache: List[Dict[str, Any]] = self.load_chart_data()
        self._last_save_time = datetime.now()
        self._save_interval = 30 # Seconds
        
    def save_chart_data(self, chart_data_point: Dict[str, Any], immediate: bool = False):
        """Add a data point to memory cache and occasionally flush to disk"""
        try:
            self._chart_cache.append(chart_data_point)
            
            # Keep only the latest data points
            if len(self._chart_cache) > self.max_points:
                self._chart_cache = self._chart_cache[-self.max_points:]
            
            # Flush to disk if interval passed or requested immediate
            now = datetime.now()
            if immediate or (now - self._last_save_time).total_seconds() >= self._save_interval:
                self.flush_to_disk()
                self._last_save_time = now
                
        except Exception as e:
            print(f"Error buffering chart data: {e}")
            
    def flush_to_disk(self):
        """Explicitly write cache to disk"""
        try:
            data = {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "data_points": self._chart_cache
            }
            with open(self.chart_data_file, "w", encoding="utf-8") as f:
                json.dump(data, f) # Removed indent for smaller file size & speed
        except Exception as e:
            print(f"Error flushing to disk: {e}")

    def load_chart_data(self) -> List[Dict[str, Any]]:
        """Load chart data from persistent storage"""
        try:
            if not self.chart_data_file.exists():
                return []
            
            with open(self.chart_data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("data_points", [])
                
        except Exception as e:
            print(f"Error loading chart data: {e}")
            return []
            
    def get_buffered_chart_data(self) -> List[Dict[str, Any]]:
        """Return current in-memory cache"""
        return self._chart_cache
    
    def save_sensor_state(self, sensor_data: Dict[str, Any]):
        """Save current sensor state (lightweight)"""
        try:
            data = {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "sensor_data": sensor_data
            }
            with open(self.sensor_state_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving sensor state: {e}")
    
    def load_sensor_state(self) -> Dict[str, Any]:
        """Load sensor state from persistent storage"""
        try:
            if not self.sensor_state_file.exists():
                return {}
            
            with open(self.sensor_state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("sensor_data", {})
        except Exception as e:
            print(f"Error loading sensor state: {e}")
            return {}
    
    def save_app_state(self, app_state: Dict[str, Any]):
        """Save application state"""
        try:
            data = {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "app_state": app_state
            }
            with open(self.app_state_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving app state: {e}")
    
    def load_app_state(self) -> Dict[str, Any]:
        """Load application state"""
        try:
            if not self.app_state_file.exists():
                return {}
            
            with open(self.app_state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("app_state", {})
        except Exception as e:
            print(f"Error loading app state: {e}")
            return {}
    
    def cleanup_old_data(self):
        """Clean up old data files to prevent disk space issues"""
        try:
            if self.chart_data_file.exists():
                with open(self.chart_data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    last_updated_str = data.get("last_updated", "")
                    if last_updated_str:
                        last_updated = datetime.fromisoformat(last_updated_str)
                        if (datetime.now(timezone.utc) - last_updated).days > 1:
                            self.chart_data_file.unlink()
        except Exception as e:
            print(f"Error cleaning up old data: {e}")

# Global persistence instance
data_persistence = DataPersistence()


# Global persistence instance
data_persistence = DataPersistence()
