"""
Logging configuration and utilities for Gandiva Rail Safety Monitor.
Provides centralized logging setup for all modules.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log file with timestamp
LOG_FILE = LOG_DIR / f"gandiva_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Setup and configure logger for a module.
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (default: INFO)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.hasHandlers():
        return logger
    
    # Console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler with more detailed formatting
    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        console_handler.emit(
            logging.LogRecord(
                name, logging.WARNING, "logger.py", 0, f"Failed to setup file logging: {e}",
                (), None
            )
        )
    
    logger.addHandler(console_handler)
    
    return logger


# Module-level logger
logger = setup_logger(__name__)
