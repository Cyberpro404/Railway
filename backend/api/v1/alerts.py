"""
Alerts API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import List, Optional
from database import get_db, Alert
from datetime import datetime, timezone

router = APIRouter()

class AlertCreate(BaseModel):
    alert_type: str
    severity: str
    message: str
    parameter: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None
    ml_confidence: Optional[float] = None

class AlertResponse(BaseModel):
    id: int
    alert_type: str
    severity: str
    message: str
    parameter: Optional[str]
    value: Optional[float]
    threshold: Optional[float]
    ml_confidence: Optional[float]
    acknowledged: bool
    acknowledged_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    limit: int = 100,
    acknowledged: Optional[bool] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get alerts with filters"""
    query = db.query(Alert)
    
    if acknowledged is not None:
        query = query.filter(Alert.acknowledged == acknowledged)
    if severity:
        query = query.filter(Alert.severity == severity)
    
    alerts = query.order_by(desc(Alert.created_at)).limit(limit).all()
    return alerts

@router.get("/active", response_model=List[AlertResponse])
async def get_active_alerts(db: Session = Depends(get_db)):
    """Get unacknowledged alerts"""
    alerts = db.query(Alert).filter(Alert.acknowledged == False).order_by(desc(Alert.created_at)).all()
    return alerts

@router.post("/", response_model=AlertResponse)
async def create_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    """Create new alert"""
    new_alert = Alert(**alert.model_dump())
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)
    return new_alert

@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    """Acknowledge an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.acknowledged = True
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Alert acknowledged"}

@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """Delete an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    db.delete(alert)
    db.commit()
    return {"message": "Alert deleted"}

