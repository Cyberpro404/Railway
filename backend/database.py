"""
SQLite Database Models and Setup
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

class Threshold(Base):
    """Threshold configuration"""
    __tablename__ = "thresholds"
    
    id = Column(Integer, primary_key=True, index=True)
    parameter = Column(String, unique=True, index=True)  # e.g., "z_rms", "temperature"
    warn_value = Column(Float)
    alarm_value = Column(Float)
    threshold_type = Column(String, default="scalar")  # "scalar" or "band"
    axis = Column(String, nullable=True)  # "Z" or "X" for band thresholds
    band_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Alert(Base):
    """Alert history"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String)  # "threshold", "ml_prediction", "iso_severity"
    severity = Column(String)  # "warning", "critical"
    message = Column(String)
    parameter = Column(String, nullable=True)
    value = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    ml_confidence = Column(Float, nullable=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class LogEntry(Base):
    """Operation log entries"""
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String, index=True)  # "DEBUG", "INFO", "WARN", "ERROR", "MODBUS"
    message = Column(Text)
    source = Column(String, nullable=True)  # "backend", "modbus", "ml", etc.
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class TrainingData(Base):
    """ML training dataset"""
    __tablename__ = "training_data"
    
    id = Column(Integer, primary_key=True, index=True)
    z_rms = Column(Float)
    x_rms = Column(Float)
    z_peak = Column(Float)
    x_peak = Column(Float)
    z_accel = Column(Float)
    x_accel = Column(Float)
    temperature = Column(Float)
    z_kurtosis = Column(Float)
    x_kurtosis = Column(Float)
    z_crest_factor = Column(Float)
    x_crest_factor = Column(Float)
    z_x_ratio = Column(Float)
    label = Column(Integer)  # 0 = normal, 1 = anomaly
    created_at = Column(DateTime, default=datetime.utcnow)

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./gandiva_pro.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    
    # Create default thresholds if they don't exist
    db = SessionLocal()
    try:
        default_thresholds = [
            {"parameter": "z_rms", "warn_value": 2.0, "alarm_value": 4.0},
            {"parameter": "x_rms", "warn_value": 2.0, "alarm_value": 4.0},
            {"parameter": "temperature", "warn_value": 50.0, "alarm_value": 70.0},
        ]
        
        for thresh in default_thresholds:
            existing = db.query(Threshold).filter(Threshold.parameter == thresh["parameter"]).first()
            if not existing:
                threshold = Threshold(**thresh)
                db.add(threshold)
        
        db.commit()
        logger.info("Database initialized with default thresholds")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

