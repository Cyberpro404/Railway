"""
Thresholds API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from database import get_db, Threshold
from datetime import datetime, timezone

router = APIRouter()

class ThresholdCreate(BaseModel):
    parameter: str
    warn_value: float
    alarm_value: float
    threshold_type: str = "scalar"
    axis: Optional[str] = None
    band_number: Optional[int] = None

class ThresholdUpdate(BaseModel):
    warn_value: Optional[float] = None
    alarm_value: Optional[float] = None
    threshold_type: Optional[str] = None
    axis: Optional[str] = None
    band_number: Optional[int] = None

class ThresholdResponse(BaseModel):
    id: int
    parameter: str
    warn_value: float
    alarm_value: float
    threshold_type: str
    axis: Optional[str]
    band_number: Optional[int]
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[ThresholdResponse])
async def get_thresholds(db: Session = Depends(get_db)):
    """Get all thresholds"""
    thresholds = db.query(Threshold).all()
    return thresholds

@router.get("/{parameter}", response_model=ThresholdResponse)
async def get_threshold(parameter: str, db: Session = Depends(get_db)):
    """Get threshold by parameter"""
    threshold = db.query(Threshold).filter(Threshold.parameter == parameter).first()
    if not threshold:
        raise HTTPException(status_code=404, detail="Threshold not found")
    return threshold

@router.post("/", response_model=ThresholdResponse)
async def create_threshold(threshold: ThresholdCreate, db: Session = Depends(get_db)):
    """Create or update threshold"""
    existing = db.query(Threshold).filter(Threshold.parameter == threshold.parameter).first()
    
    if existing:
        # Update existing
        if threshold.warn_value is not None:
            existing.warn_value = threshold.warn_value
        if threshold.alarm_value is not None:
            existing.alarm_value = threshold.alarm_value
        if threshold.threshold_type:
            existing.threshold_type = threshold.threshold_type
        if threshold.axis:
            existing.axis = threshold.axis
        if threshold.band_number is not None:
            existing.band_number = threshold.band_number
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        new_threshold = Threshold(**threshold.model_dump())
        db.add(new_threshold)
        db.commit()
        db.refresh(new_threshold)
        return new_threshold

@router.put("/{parameter}", response_model=ThresholdResponse)
async def update_threshold(
    parameter: str,
    threshold: ThresholdUpdate,
    db: Session = Depends(get_db)
):
    """Update threshold"""
    existing = db.query(Threshold).filter(Threshold.parameter == parameter).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Threshold not found")
    
    if threshold.warn_value is not None:
        existing.warn_value = threshold.warn_value
    if threshold.alarm_value is not None:
        existing.alarm_value = threshold.alarm_value
    if threshold.threshold_type:
        existing.threshold_type = threshold.threshold_type
    if threshold.axis:
        existing.axis = threshold.axis
    if threshold.band_number is not None:
        existing.band_number = threshold.band_number
    
    existing.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(existing)
    return existing

@router.delete("/{parameter}")
async def delete_threshold(parameter: str, db: Session = Depends(get_db)):
    """Delete threshold"""
    threshold = db.query(Threshold).filter(Threshold.parameter == parameter).first()
    if not threshold:
        raise HTTPException(status_code=404, detail="Threshold not found")
    
    db.delete(threshold)
    db.commit()
    return {"message": "Threshold deleted"}

@router.post("/reset-defaults")
async def reset_defaults(db: Session = Depends(get_db)):
    """Reset all thresholds to defaults"""
    defaults = [
        {"parameter": "z_rms", "warn_value": 2.0, "alarm_value": 4.0},
        {"parameter": "x_rms", "warn_value": 2.0, "alarm_value": 4.0},
        {"parameter": "temperature", "warn_value": 50.0, "alarm_value": 70.0},
    ]
    
    for default in defaults:
        existing = db.query(Threshold).filter(Threshold.parameter == default["parameter"]).first()
        if existing:
            existing.warn_value = default["warn_value"]
            existing.alarm_value = default["alarm_value"]
            existing.updated_at = datetime.now(timezone.utc)
        else:
            new_threshold = Threshold(**default)
            db.add(new_threshold)
    
    db.commit()
    return {"message": "Defaults reset"}

