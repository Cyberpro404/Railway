"""
Configuration module for Gandiva Rail Safety Monitor.
Manages all configuration settings and defaults.
"""

from pathlib import Path
from typing import Optional


class Config:
    """Main configuration class."""
    
    # Application paths
    BASE_DIR = Path(__file__).parent.parent
    DATABASE_DIR = BASE_DIR / "database"
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    MODELS_DIR = BASE_DIR / "models"
    
    # Create directories if they don't exist
    for directory in [DATABASE_DIR, DATA_DIR, LOGS_DIR, MODELS_DIR]:
        directory.mkdir(exist_ok=True)
    
    # Database configuration
    MAIN_DB_PATH = DATABASE_DIR / "rail.db"
    TRAINING_DB_PATH = DATABASE_DIR / "gandiva_data.db"
    
    # Sensor configuration
    # Set this to your sensor's COM port (COM3, COM4, or COM5)
    # Project default: COM5
    DEFAULT_PORT = "COM5"
    DEFAULT_SLAVE_ID = 1
    DEFAULT_BAUDRATE = 19200
    DEFAULT_BYTESIZE = 8
    DEFAULT_PARITY = "N"
    DEFAULT_STOPBITS = 1
    DEFAULT_TIMEOUT_S = 3.0
    
    # Sensor reading configuration
    SENSOR_POLL_INTERVAL_S = 1.0
    SENSOR_READ_RETRY_COUNT = 2
    SENSOR_RETRY_DELAY_MS = 100
    
    # History configuration
    HISTORY_MAX_ENTRIES = 3600
    HISTORY_DEFAULT_SECONDS = 600
    TRAINING_HISTORY_LIMIT = 10000
    
    # Default thresholds
    DEFAULT_Z_RMS_WARNING_MM_S = 2.0
    DEFAULT_Z_RMS_ALARM_MM_S = 4.0
    DEFAULT_X_RMS_WARNING_MM_S = 2.0
    DEFAULT_X_RMS_ALARM_MM_S = 4.0
    DEFAULT_TEMP_WARNING_C = 50.0
    DEFAULT_TEMP_ALARM_C = 70.0
    
    # Frequency ranges (Hz)
    FREQUENCY_MIN = 0.1
    FREQUENCY_MAX = 10000.0
    FREQUENCY_SAMPLE_RATE = 51200  # Hz, typical for industrial sensors
    
    # Training configuration
    MIN_TRAINING_SAMPLES = 20
    TRAIN_TEST_SPLIT_RATIO = 0.2
    MODEL_RANDOM_STATE = 42
    
    # Model paths
    MODEL_PATH = MODELS_DIR / "model.pkl"
    MODEL_INFO_PATH = MODELS_DIR / "model_info.json"
    
    # API configuration
    API_TITLE = "Gandiva Rail Safety Monitor"
    API_VERSION = "2.0"
    API_DESCRIPTION = "Advanced sensor monitoring and ML-based diagnostics"
    
    # CORS configuration
    CORS_ORIGINS = ["*"]
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOW_METHODS = ["*"]
    CORS_ALLOW_HEADERS = ["*"]
    
    # Logging configuration
    LOG_LEVEL = "INFO"
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def get_config() -> Config:
    """Get configuration instance."""
    return Config()
