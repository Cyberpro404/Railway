"""
Training database module for ML model training data.
Handles SQLite operations for storing and retrieving training samples.
"""

import sqlite3
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, List
from pathlib import Path

from utils.logger import setup_logger
from utils.errors import DatabaseError, ValidationError
from utils.validators import validate_label
from config.settings import Config

logger = setup_logger(__name__)


class TrainingDatabase:
    """Manages training data database operations."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize training database.
        
        Args:
            db_path: Path to database file (default: from config)
        """
        self.db_path = db_path or Config.TRAINING_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        try:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to training database: {e}")
            raise DatabaseError(f"Training database connection failed: {e}")
    
    def _init_database(self) -> None:
        """Initialize training database tables."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Training samples table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    axis TEXT NOT NULL CHECK (axis IN ('z', 'x', 'both')),
                    z_rms_mm_s REAL,
                    x_rms_mm_s REAL,
                    z_peak_mm_s REAL,
                    x_peak_mm_s REAL,
                    z_rms_g REAL,
                    x_rms_g REAL,
                    z_hf_rms_g REAL,
                    x_hf_rms_g REAL,
                    z_kurtosis REAL,
                    x_kurtosis REAL,
                    z_crest_factor REAL,
                    x_crest_factor REAL,
                    temp_c REAL,
                    frequency_hz REAL,
                    label TEXT,
                    selected_band_number INTEGER,
                    selected_band_axis TEXT,
                    band_total_rms REAL,
                    band_peak_rms REAL,
                    band_peak_freq_hz REAL,
                    band_peak_rpm REAL
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_timestamp ON training_samples(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_label ON training_samples(label)
            """)
            
            conn.commit()
            conn.close()
            logger.info("Training database initialized successfully")
        except Exception as e:
            logger.error(f"Training database initialization error: {e}")
            raise DatabaseError(f"Failed to initialize training database: {e}")
    
    def insert_sample(
        self,
        reading: dict,
        axis: str,
        label: Optional[str] = None,
        selected_band_axis: Optional[str] = None,
        selected_band_number: Optional[int] = None
    ) -> Tuple[int, str]:
        """
        Insert a training sample into the database.
        
        Args:
            reading: Sensor reading dictionary
            axis: 'z', 'x', or 'both'
            label: Optional training label
            selected_band_axis: Optional selected band axis
            selected_band_number: Optional selected band number
            
        Returns:
            Tuple of (inserted_id, timestamp)
            
        Raises:
            DatabaseError: If insertion fails
            ValidationError: If data is invalid
        """
        # Validate inputs
        if axis not in ('z', 'x', 'both'):
            raise ValidationError(f"Invalid axis: {axis}", "axis")
        
        label = validate_label(label)
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Extract band info if provided
        band_info = {}
        if selected_band_axis and selected_band_number:
            if selected_band_axis not in ('z', 'x'):
                raise ValidationError(f"Invalid band axis: {selected_band_axis}", "selected_band_axis")
            
            bands_key = f"bands_{selected_band_axis}"
            bands = reading.get(bands_key, [])
            found = False
            for band in bands:
                if band.get('band_number') == selected_band_number:
                    band_info = {
                        'band_total_rms': band.get('total_rms'),
                        'band_peak_rms': band.get('peak_rms'),
                        'band_peak_freq_hz': band.get('peak_freq_hz'),
                        'band_peak_rpm': band.get('peak_rpm')
                    }
                    found = True
                    break
            
            if not found:
                raise ValidationError(
                    f"Band {selected_band_number} not found in {selected_band_axis} axis",
                    "selected_band_number"
                )
            
            band_info['selected_band_axis'] = selected_band_axis
            band_info['selected_band_number'] = selected_band_number
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO training_samples (
                    timestamp, axis,
                    z_rms_mm_s, x_rms_mm_s, z_peak_mm_s, x_peak_mm_s,
                    z_rms_g, x_rms_g, z_hf_rms_g, x_hf_rms_g,
                    z_kurtosis, x_kurtosis, z_crest_factor, x_crest_factor,
                    temp_c, frequency_hz, label,
                    selected_band_number, selected_band_axis,
                    band_total_rms, band_peak_rms, band_peak_freq_hz, band_peak_rpm
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, axis,
                reading.get('z_rms_mm_s'), reading.get('x_rms_mm_s'),
                reading.get('z_peak_mm_s'), reading.get('x_peak_mm_s'),
                reading.get('z_rms_g'), reading.get('x_rms_g'),
                reading.get('z_hf_rms_g'), reading.get('x_hf_rms_g'),
                reading.get('z_kurtosis'), reading.get('x_kurtosis'),
                reading.get('z_crest_factor'), reading.get('x_crest_factor'),
                reading.get('temp_c'), reading.get('frequency_hz', Config.DEFAULT_FREQUENCY_HZ), label,
                band_info.get('selected_band_number'),
                band_info.get('selected_band_axis'),
                band_info.get('band_total_rms'),
                band_info.get('band_peak_rms'),
                band_info.get('band_peak_freq_hz'),
                band_info.get('band_peak_rpm')
            ))
            
            inserted_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Training sample {inserted_id} inserted with axis={axis}, label={label}")
            return inserted_id, timestamp
        except Exception as e:
            logger.error(f"Failed to insert training sample: {e}")
            raise DatabaseError(f"Failed to insert training sample: {e}")
    
    def insert_raw_sample(self, sample_data: dict, label: Optional[str] = None) -> Tuple[int, str]:
        """
        Insert a raw sample from CSV import directly into the database.
        
        Args:
            sample_data: Dictionary with sample columns
            label: Optional label override
            
        Returns:
            Tuple of (inserted_id, timestamp)
            
        Raises:
            DatabaseError: If insertion fails
        """
        timestamp = sample_data.get('timestamp') or datetime.now(timezone.utc).isoformat()
        axis = sample_data.get('axis', 'both')
        if label is None:
            label = sample_data.get('label')
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO training_samples (
                    timestamp, axis,
                    z_rms_mm_s, x_rms_mm_s, z_peak_mm_s, x_peak_mm_s,
                    z_rms_g, x_rms_g, z_hf_rms_g, x_hf_rms_g,
                    z_kurtosis, x_kurtosis, z_crest_factor, x_crest_factor,
                    temp_c, frequency_hz, label,
                    selected_band_number, selected_band_axis,
                    band_total_rms, band_peak_rms, band_peak_freq_hz, band_peak_rpm
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, axis,
                sample_data.get('z_rms_mm_s'), sample_data.get('x_rms_mm_s'),
                sample_data.get('z_peak_mm_s'), sample_data.get('x_peak_mm_s'),
                sample_data.get('z_rms_g'), sample_data.get('x_rms_g'),
                sample_data.get('z_hf_rms_g'), sample_data.get('x_hf_rms_g'),
                sample_data.get('z_kurtosis'), sample_data.get('x_kurtosis'),
                sample_data.get('z_crest_factor'), sample_data.get('x_crest_factor'),
                sample_data.get('temp_c'), sample_data.get('frequency_hz'),
                label,
                sample_data.get('selected_band_number'),
                sample_data.get('selected_band_axis'),
                sample_data.get('band_total_rms'),
                sample_data.get('band_peak_rms'),
                sample_data.get('band_peak_freq_hz'),
                sample_data.get('band_peak_rpm')
            ))
            
            inserted_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return inserted_id, timestamp
        except Exception as e:
            logger.error(f"Failed to insert raw sample: {e}")
            raise DatabaseError(f"Failed to insert raw sample: {e}")

    def get_samples(self, limit: int = 100, offset: int = 0) -> dict:
        """
        Get paginated training samples.
        
        Args:
            limit: Number of samples to return (max 1000)
            offset: Number of samples to skip
            
        Returns:
            Dictionary with samples and metadata
            
        Raises:
            DatabaseError: If query fails
        """
        try:
            # Validate parameters
            limit = min(max(1, int(limit)), 1000)
            offset = max(0, int(offset))
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) as count FROM training_samples")
            total = cursor.fetchone()["count"]
            
            # Get paginated samples
            cursor.execute("""
                SELECT * FROM training_samples
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            rows = cursor.fetchall()
            conn.close()
            
            samples = [dict(r) for r in rows]
            
            return {
                "samples": samples,
                "total": total,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"Failed to get training samples: {e}")
            raise DatabaseError(f"Failed to get training samples: {e}")
    
    def get_all_samples(self) -> List[dict]:
        """
        Get all training samples for model training.
        
        Returns:
            List of all training samples
            
        Raises:
            DatabaseError: If query fails
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM training_samples ORDER BY timestamp")
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to get all training samples: {e}")
            raise DatabaseError(f"Failed to get all training samples: {e}")
    
    def get_stats(self) -> dict:
        """
        Get training data statistics.
        
        Returns:
            Dictionary with statistics
            
        Raises:
            DatabaseError: If query fails
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Total samples
            cursor.execute("SELECT COUNT(*) as count FROM training_samples")
            total = cursor.fetchone()["count"]
            
            # Labeled samples
            cursor.execute("SELECT COUNT(*) as count FROM training_samples WHERE label IS NOT NULL AND label != ''")
            labeled = cursor.fetchone()["count"]
            
            # Unlabeled samples
            unlabeled = total - labeled
            
            # Samples by label
            cursor.execute("""
                SELECT label, COUNT(*) as count FROM training_samples
                WHERE label IS NOT NULL AND label != ''
                GROUP BY label
                ORDER BY count DESC
            """)
            label_distribution = {row["label"]: row["count"] for row in cursor.fetchall()}
            
            # Samples by axis
            cursor.execute("""
                SELECT axis, COUNT(*) as count FROM training_samples
                GROUP BY axis
                ORDER BY count DESC
            """)
            axis_distribution = {row["axis"]: row["count"] for row in cursor.fetchall()}
            
            # Date range
            cursor.execute("SELECT MIN(timestamp) as min_ts, MAX(timestamp) as max_ts FROM training_samples")
            date_range = cursor.fetchone()
            
            conn.close()
            
            return {
                "total_samples": total,
                "labeled_samples": labeled,
                "unlabeled_samples": unlabeled,
                "label_distribution": label_distribution,
                "axis_distribution": axis_distribution,
                "first_sample": date_range["min_ts"],
                "last_sample": date_range["max_ts"]
            }
        except Exception as e:
            logger.error(f"Failed to get training stats: {e}")
            raise DatabaseError(f"Failed to get training stats: {e}")
    
    def delete_sample(self, sample_id: int) -> None:
        """
        Delete a training sample.
        
        Args:
            sample_id: Sample ID to delete
            
        Raises:
            DatabaseError: If deletion fails
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM training_samples WHERE id = ?", (sample_id,))
            conn.commit()
            conn.close()
            logger.info(f"Training sample {sample_id} deleted")
        except Exception as e:
            logger.error(f"Failed to delete training sample: {e}")
            raise DatabaseError(f"Failed to delete training sample: {e}")
    
    def delete_by_label(self, label: str) -> int:
        """
        Delete all samples with a specific label.
        
        Args:
            label: Label to delete
            
        Returns:
            Number of samples deleted
            
        Raises:
            DatabaseError: If deletion fails
        """
        try:
            label = validate_label(label)
            if not label:
                raise ValidationError("Label cannot be empty", "label")
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM training_samples WHERE label = ?", (label,))
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Deleted {deleted_count} training samples with label={label}")
            return deleted_count
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete samples by label: {e}")
            raise DatabaseError(f"Failed to delete samples by label: {e}")


# Global training database instance
_training_db: Optional[TrainingDatabase] = None


def get_training_db() -> TrainingDatabase:
    """Get or create global training database instance."""
    global _training_db
    if _training_db is None:
        _training_db = TrainingDatabase()
    return _training_db


def init_training_db() -> None:
    """Initialize training database (backward compatibility)."""
    get_training_db()
