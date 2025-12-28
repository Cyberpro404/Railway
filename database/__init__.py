"""Database package exports convenience functions for operational data."""

from .operational_db import get_db


def get_latest() -> dict | None:
	"""Return the latest sensor reading (or None if none recorded)."""
	return get_db().get_latest()


def get_history(seconds: int = 600) -> list[dict]:
	"""Return history of readings within the last ``seconds`` window."""
	return get_db().get_history(seconds)


def get_alerts(since_seconds: int = 86400) -> list[dict]:
	"""Return alerts within the last ``since_seconds`` window."""
	return get_db().get_alerts(since_seconds)


def update_alert_status(alert_id: str, status: str) -> None:
	"""Update the status of an alert by id."""
	return get_db().update_alert_status(alert_id, status)


__all__ = [
	"get_latest",
	"get_history",
	"get_alerts",
	"update_alert_status",
	"get_db",
]
