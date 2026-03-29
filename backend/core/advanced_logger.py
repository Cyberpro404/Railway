"""
Advanced Logging System for Railway Monitoring
Captures all processes, errors, and readings for easy error identification
"""
import logging
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path
import threading
from queue import Queue, Empty
import traceback

class AdvancedLogger:
    """Advanced logging system with structured logging and error tracking"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create log files
        self.app_log_file = self.log_dir / "app.log"
        self.error_log_file = self.log_dir / "errors.log"
        self.modbus_log_file = self.log_dir / "modbus.log"
        self.readings_log_file = self.log_dir / "readings.log"
        
        # Queue for thread-safe logging
        self.log_queue = Queue()
        self.running = True
        
        # Start background logging thread
        self.log_thread = threading.Thread(target=self._log_worker, daemon=True)
        self.log_thread.start()
        
        # Setup structured logging
        self._setup_loggers()
        
    def _setup_loggers(self):
        """Setup different loggers for different components"""
        # Main application logger
        self.app_logger = logging.getLogger("railway.app")
        self.app_logger.setLevel(logging.INFO)
        
        # Error logger
        self.error_logger = logging.getLogger("railway.errors")
        self.error_logger.setLevel(logging.ERROR)
        
        # Modbus logger
        self.modbus_logger = logging.getLogger("railway.modbus")
        self.modbus_logger.setLevel(logging.DEBUG)
        
        # Readings logger
        self.readings_logger = logging.getLogger("railway.readings")
        self.readings_logger.setLevel(logging.INFO)
        
        # Create file handlers
        self._create_file_handler(self.app_logger, self.app_log_file)
        self._create_file_handler(self.error_logger, self.error_log_file)
        self._create_file_handler(self.modbus_logger, self.modbus_log_file)
        self._create_file_handler(self.readings_logger, self.readings_log_file)
        
    def _create_file_handler(self, logger: logging.Logger, log_file: Path):
        """Create file handler with rotation"""
        from logging.handlers import RotatingFileHandler
        
        handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    def _log_worker(self):
        """Background thread for processing log entries"""
        while self.running:
            try:
                log_entry = self.log_queue.get(timeout=1)
                self._write_log_entry(log_entry)
            except Empty:
                continue
            except Exception as e:
                print(f"Logging error: {e}")
                
    def _write_log_entry(self, log_entry: Dict[str, Any]):
        """Write log entry to appropriate file"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if log_entry["type"] == "error":
            with open(self.error_log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} | {log_entry['component']} | {log_entry['error']} | {log_entry['traceback']}\n")
        elif log_entry["type"] == "modbus":
            with open(self.modbus_log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} | {log_entry['action']} | {log_entry['details']}\n")
        elif log_entry["type"] == "reading":
            with open(self.readings_log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} | {json.dumps(log_entry['data'])}\n")
                
    def log_error(self, component: str, error: Exception, context: Optional[Dict] = None):
        """Log error with full context"""
        log_entry = {
            "type": "error",
            "component": component,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        self.log_queue.put(log_entry)
        
    def log_modbus_action(self, action: str, details: Dict[str, Any]):
        """Log Modbus actions"""
        log_entry = {
            "type": "modbus",
            "action": action,
            "details": json.dumps(details)
        }
        self.log_queue.put(log_entry)
        
    def log_reading(self, data: Dict[str, Any]):
        """Log sensor readings"""
        log_entry = {
            "type": "reading",
            "data": data
        }
        self.log_queue.put(log_entry)
        
    def get_recent_errors(self, count: int = 10) -> list:
        """Get recent errors for debugging"""
        try:
            with open(self.error_log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return lines[-count:] if len(lines) >= count else lines
        except FileNotFoundError:
            return []
            
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary for dashboard"""
        try:
            with open(self.error_log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            error_count = len(lines)
            recent_errors = lines[-5:] if len(lines) >= 5 else lines
            
            return {
                "total_errors": error_count,
                "recent_errors": recent_errors,
                "last_error": lines[-1] if lines else None
            }
        except FileNotFoundError:
            return {
                "total_errors": 0,
                "recent_errors": [],
                "last_error": None
            }

# Global logger instance
advanced_logger = AdvancedLogger()
