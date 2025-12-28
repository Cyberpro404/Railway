"""
Database module for operational sensor data and alerts.
Handles SQLite operations for monitoring history and alerts.
"""

import sqlite3
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional
from pathlib import Path

from utils.logger import setup_logger
from utils.errors import DatabaseError
from config.settings import Config

logger = setup_logger(__name__)


class OperationalDatabase:
    """Manages operational database operations."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database.
        
        Args:
            db_path: Path to database file (default: from config)
        """
        self.db_path = db_path or Config.MAIN_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        try:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise DatabaseError(f"Database connection failed: {e}")
    
    def _init_database(self) -> None:
        """Initialize database tables."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Latest reading table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS latest (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    timestamp TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            """)
            
            # History table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp)
            """)
            
            # Alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    severity TEXT NOT NULL CHECK (severity IN ('warning', 'alarm')),
                    parameter TEXT NOT NULL,
                    value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('active', 'acknowledged', 'cleared'))
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)
            """)
            
            # Initialize latest record if not exists
            cursor.execute("""
                INSERT OR IGNORE INTO latest (id, timestamp, data)
                VALUES (1, ?, ?)
            """, (datetime.now(timezone.utc).isoformat(), "{}"))
            
            conn.commit()
            conn.close()
            logger.info("Operational database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise DatabaseError(f"Failed to initialize database: {e}")
    
    def upsert_latest(self, reading: dict) -> None:
        """
        Update or insert latest reading.
        
        Args:
            reading: Reading dictionary
            
        Raises:
            DatabaseError: If operation fails
        """
        if not reading or not isinstance(reading, dict) or "timestamp" not in reading:
            logger.warning("Skipping invalid reading update")
            return
        
        try:
            ts = reading["timestamp"]
            data = json.dumps(reading)
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Update latest
            cursor.execute(
                "UPDATE latest SET timestamp = ?, data = ? WHERE id = 1",
                (ts, data)
            )
            
            # Insert into history
            cursor.execute(
                "INSERT INTO history (timestamp, data) VALUES (?, ?)",
                (ts, data)
            )
            
            # Trim history to max entries
            cursor.execute(f"""
                DELETE FROM history WHERE id NOT IN (
                    SELECT id FROM history ORDER BY timestamp DESC LIMIT {Config.HISTORY_MAX_ENTRIES}
                )
            """)
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to upsert latest reading: {e}")
            raise DatabaseError(f"Upsert failed: {e}")
    
    def get_latest(self) -> Optional[dict]:
        """
        Get the latest reading.
        
        Returns:
            Latest reading dictionary or None
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM latest WHERE id = 1")
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            return json.loads(row["data"])
        except Exception as e:
            logger.error(f"Failed to get latest reading: {e}")
            raise DatabaseError(f"Failed to get latest: {e}")
    
    def get_history(self, seconds: int = 600) -> list[dict]:
        """
        Get historical readings.
        
        Args:
            seconds: Number of seconds of history to retrieve
            
        Returns:
            List of reading dictionaries
        """
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data FROM history WHERE timestamp >= ? ORDER BY timestamp",
                (cutoff,)
            )
            rows = cursor.fetchall()
            conn.close()
            
            return [json.loads(r["data"]) for r in rows]
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            raise DatabaseError(f"Failed to get history: {e}")
    
    def insert_alert(self, alert: dict) -> None:
        """
        Insert or update an alert.
        
        Args:
            alert: Alert dictionary
            
        Raises:
            DatabaseError: If operation fails
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO alerts
                (id, timestamp, severity, parameter, value, threshold, message, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert["id"], alert["timestamp"], alert["severity"], alert["parameter"],
                alert["value"], alert["threshold"], alert["message"], alert["status"]
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to insert alert: {e}")
            raise DatabaseError(f"Failed to insert alert: {e}")
    
    def get_alerts(self, since_seconds: int = 86400) -> list[dict]:
        """
        Get alerts within a time range.
        
        Args:
            since_seconds: Number of seconds back to query
            
        Returns:
            List of alert dictionaries
        """
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(seconds=since_seconds)).isoformat()
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM alerts WHERE timestamp >= ? ORDER BY timestamp DESC",
                (cutoff,)
            )
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            raise DatabaseError(f"Failed to get alerts: {e}")
    
    def update_alert_status(self, alert_id: str, status: Literal["acknowledged", "cleared"]) -> None:
        """
        Update alert status.
        
        Args:
            alert_id: Alert ID
            status: New status
            
        Raises:
            DatabaseError: If operation fails
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE alerts SET status = ? WHERE id = ?",
                (status, alert_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update alert status: {e}")
            raise DatabaseError(f"Failed to update alert: {e}")


# Global database instance
_db: Optional[OperationalDatabase] = None


def get_db() -> OperationalDatabase:
    """Get or create global database instance."""
    global _db
    if _db is None:
        _db = OperationalDatabase()
    return _db


def init_db() -> None:
    """Initialize database (backward compatibility)."""
    get_db()
