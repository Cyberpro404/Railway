"""
Centralized logging configuration with console, rotating file, and database handlers.
Logs are queued to avoid blocking the event loop and to flush reliably on shutdown.
"""
import logging
import logging.config
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from queue import SimpleQueue
from pathlib import Path
from datetime import datetime
import json

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

_listener = None
_queue = None


class DatabaseLogHandler(logging.Handler):
    """Persist error and warning logs to the database."""

    def emit(self, record: logging.LogRecord) -> None:
        session = None
        try:
            # Local import avoids circular dependency during startup.
            from database import SessionLocal, LogEntry

            session = SessionLocal()
            message = self._build_message(record)
            entry = LogEntry(
                level=record.levelname,
                message=message,
                source=record.name,
            )
            session.add(entry)
            session.commit()
        except Exception:
            # Swallow to avoid recursive logging loops on DB issues.
            pass
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass

    def _build_message(self, record: logging.LogRecord) -> str:
        payload = {
            "message": record.getMessage(),
            "level": record.levelname,
            "name": record.name,
            "time": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
        }
        if record.exc_info:
            formatter = logging.Formatter()
            payload["exception"] = formatter.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = record.stack_info
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root logging with queue + file + console + DB handlers."""
    global _listener, _queue

    if _listener is not None:
        return

    _queue = SimpleQueue()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    db_handler = DatabaseLogHandler()
    db_handler.setLevel(logging.WARNING)

    _listener = QueueListener(
        _queue,
        console_handler,
        file_handler,
        db_handler,
        respect_handler_level=True,
    )
    _listener.start()

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(QueueHandler(_queue))
    root_logger.propagate = False


def shutdown_logging() -> None:
    """Flush and stop the queue listener."""
    global _listener, _queue

    if _listener is not None:
        _listener.stop()
    _listener = None
    _queue = None


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper to fetch a configured logger."""
    return logging.getLogger(name)
