"""
Custom exception classes for Gandiva Rail Safety Monitor.
Provides consistent error handling and reporting.
"""

from typing import Optional


class GandivaError(Exception):
    """Base exception for all Gandiva errors."""
    def __init__(self, message: str, code: str = "GANDIVA_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert error to dictionary format for API responses."""
        return {
            "status": "error",
            "code": self.code,
            "message": self.message
        }


class SensorError(GandivaError):
    """Raised when sensor communication fails."""
    def __init__(self, message: str):
        super().__init__(message, "SENSOR_ERROR")


class ConnectionError(GandivaError):
    """Raised when serial port connection fails."""
    def __init__(self, message: str, port: Optional[str] = None):
        if port:
            message = f"Connection failed on {port}: {message}"
        super().__init__(message, "CONNECTION_ERROR")


class ConfigError(GandivaError):
    """Raised when configuration is invalid."""
    def __init__(self, message: str):
        super().__init__(message, "CONFIG_ERROR")


class DatabaseError(GandivaError):
    """Raised when database operations fail."""
    def __init__(self, message: str):
        super().__init__(message, "DATABASE_ERROR")


class TrainingError(GandivaError):
    """Raised when model training fails."""
    def __init__(self, message: str):
        super().__init__(message, "TRAINING_ERROR")


class PredictionError(GandivaError):
    """Raised when model prediction fails."""
    def __init__(self, message: str):
        super().__init__(message, "PREDICTION_ERROR")


class ValidationError(GandivaError):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: Optional[str] = None):
        if field:
            message = f"Validation error in {field}: {message}"
        super().__init__(message, "VALIDATION_ERROR")
