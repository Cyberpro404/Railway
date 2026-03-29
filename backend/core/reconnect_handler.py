"""Reconnect policy with exponential backoff and jitter."""

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ReconnectHandler:
    """Manages reconnect attempts with bounded exponential backoff."""

    def __init__(self, initial_delay: float = 1.0, max_delay: float = 30.0, backoff_factor: float = 2.0):
        self.initial_delay = max(0.1, initial_delay)
        self.max_delay = max(self.initial_delay, max_delay)
        self.backoff_factor = max(1.1, backoff_factor)

        self.current_delay = self.initial_delay
        self.attempts = 0
        self.last_attempt: Optional[datetime] = None
        self.is_reconnecting = False

    def reset(self) -> None:
        self.current_delay = self.initial_delay
        self.attempts = 0
        self.last_attempt = None
        self.is_reconnecting = False

    async def sleep(self) -> float:
        """Sleep using current delay + jitter and prepare next delay."""
        self.is_reconnecting = True
        self.attempts += 1

        jitter = self.current_delay * random.uniform(-0.15, 0.15)
        wait_time = max(0.1, self.current_delay + jitter)
        self.last_attempt = datetime.now(timezone.utc)

        logger.warning("Reconnect attempt %s in %.2fs", self.attempts, wait_time)
        await asyncio.sleep(wait_time)

        self.current_delay = min(self.max_delay, self.current_delay * self.backoff_factor)
        return wait_time

    def get_status(self) -> Dict[str, Any]:
        return {
            "attempts": self.attempts,
            "next_delay": round(self.current_delay, 2),
            "is_reconnecting": self.is_reconnecting,
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
        }
