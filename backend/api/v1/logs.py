"""
Logs API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from database import get_db, LogEntry

router = APIRouter()


class LogResponse(BaseModel):
    id: int
    level: str
    message: str
    source: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[LogResponse])
async def get_logs(
    limit: int = 100,
    level: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Fetch recent logs with optional level/source filters."""
    safe_limit = min(max(limit, 1), 1000)
    query = db.query(LogEntry)

    if level:
        query = query.filter(LogEntry.level == level.upper())
    if source:
        query = query.filter(LogEntry.source == source)

    return query.order_by(desc(LogEntry.created_at)).limit(safe_limit).all()
