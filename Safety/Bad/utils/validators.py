"""
Input validation utilities for Gandiva Rail Safety Monitor.
"""

from typing import Any, Optional
from utils.errors import ValidationError


def validate_frequency(frequency: float) -> float:
    """
    Validate frequency parameter.
    
    Args:
        frequency: Frequency value in Hz
        
    Returns:
        Validated frequency value
        
    Raises:
        ValidationError: If frequency is invalid
    """
    try:
        freq = float(frequency)
        if freq <= 0:
            raise ValidationError("Frequency must be positive", "frequency")
        if freq > 10000:
            raise ValidationError("Frequency must be <= 10000 Hz", "frequency")
        return freq
    except (TypeError, ValueError):
        raise ValidationError("Frequency must be a number", "frequency")


def validate_port(port: str) -> str:
    """
    Validate serial port name.
    
    Args:
        port: Port name (e.g., 'COM1', '/dev/ttyUSB0')
        
    Returns:
        Validated port name
        
    Raises:
        ValidationError: If port is invalid
    """
    if not port or not isinstance(port, str):
        raise ValidationError("Port must be a non-empty string", "port")
    
    port = port.strip()
    if len(port) > 50:
        raise ValidationError("Port name is too long", "port")
    
    return port


def validate_slave_id(slave_id: int) -> int:
    """
    Validate Modbus slave ID.
    
    Args:
        slave_id: Slave ID (1-247)
        
    Returns:
        Validated slave ID
        
    Raises:
        ValidationError: If slave ID is invalid
    """
    try:
        sid = int(slave_id)
        if sid < 1 or sid > 247:
            raise ValidationError("Slave ID must be between 1 and 247", "slave_id")
        return sid
    except (TypeError, ValueError):
        raise ValidationError("Slave ID must be an integer", "slave_id")


def validate_threshold_pair(warning: float, alarm: float, name: str) -> tuple:
    """
    Validate that alarm threshold >= warning threshold.
    
    Args:
        warning: Warning threshold value
        alarm: Alarm threshold value
        name: Parameter name for error messages
        
    Returns:
        Tuple of (warning, alarm)
        
    Raises:
        ValidationError: If thresholds are invalid
    """
    try:
        warn = float(warning)
        alrm = float(alarm)
        
        if warn < 0 or alrm < 0:
            raise ValidationError(f"{name} thresholds must be non-negative", name)
        
        if alrm < warn:
            raise ValidationError(
                f"{name} alarm ({alrm}) must be >= warning ({warn})",
                name
            )
        
        return warn, alrm
    except (TypeError, ValueError):
        raise ValidationError(f"{name} thresholds must be numbers", name)


def validate_label(label: Optional[str]) -> Optional[str]:
    """
    Validate training label.
    
    Args:
        label: Label string or None
        
    Returns:
        Validated label
        
    Raises:
        ValidationError: If label is invalid
    """
    if label is None:
        return None
    
    if not isinstance(label, str):
        raise ValidationError("Label must be a string", "label")
    
    label = label.strip()
    if len(label) == 0:
        return None
    
    if len(label) > 100:
        raise ValidationError("Label is too long (max 100 characters)", "label")
    
    # Only allow alphanumeric, underscore, hyphen, and space
    if not all(c.isalnum() or c in '_- ' for c in label):
        raise ValidationError(
            "Label can only contain letters, numbers, spaces, hyphens, and underscores",
            "label"
        )
    
    return label
