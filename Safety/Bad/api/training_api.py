"""
Training API endpoints for ML model training and data management.
Handles data capture, retrieval, and model training with comprehensive error handling.
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timezone

from fastapi import HTTPException
from pydantic import BaseModel, Field

from database.operational_db import get_db
from database.training_db import get_training_db
from ml.model_trainer import ModelTrainer, load_model_info
from ml.predictor import ModelPredictor
from config import MODEL_FILE, SCALER_FILE
from utils.logger import setup_logger
from utils.errors import (
    GandivaError, TrainingError, PredictionError, DatabaseError, ValidationError
)
from config.settings import Config

logger = setup_logger(__name__)


# Request models
class CaptureRequest(BaseModel):
    """Training sample capture request."""
    axis: str = Field(..., pattern="^(z|x|both)$", description="Measurement axis")
    label: Optional[str] = Field(None, description="Training label")
    selected_band_axis: Optional[str] = Field(None, pattern="^(z|x)$", description="Band axis")
    selected_band_number: Optional[int] = Field(None, ge=1, le=20, description="Band number")


class TrainRequest(BaseModel):
    """Model training request."""
    target_label_field: str = Field("label", description="Target label field")
    algorithm: str = Field("baseline", description="Training algorithm")


class PredictRequest(BaseModel):
    """Model prediction request."""
    sample: Dict = Field(..., description="Sample data for prediction")


class BatchPredictRequest(BaseModel):
    """Batch prediction request."""
    samples: list[Dict] = Field(..., description="List of samples for prediction")


def setup_training_routes(app):
    """Setup all training-related API routes."""
    
    @app.post("/api/training/capture", tags=["Training"])
    def api_capture_training_sample(request: CaptureRequest) -> Dict:
        """
        Capture current sensor reading as training sample.
        
        This endpoint captures the latest sensor reading and stores it
        for later model training with an optional label.
        """
        try:
            # Get latest reading
            latest = get_db().get_latest()
            if not latest or latest == {}:
                raise HTTPException(
                    status_code=404,
                    detail="No sensor reading available. Please connect sensor first."
                )
            
            # Handle API response envelope if present
            reading = latest.get('reading') if isinstance(latest, dict) and 'reading' in latest else latest
            
            if not reading:
                raise HTTPException(status_code=404, detail="Invalid sensor reading")
            
            # Insert training sample
            try:
                inserted_id, timestamp = get_training_db().insert_sample(
                    reading=reading,
                    axis=request.axis,
                    label=request.label,
                    selected_band_axis=request.selected_band_axis,
                    selected_band_number=request.selected_band_number
                )
                
                return {
                    "status": "ok",
                    "message": f"Training sample captured successfully",
                    "inserted_id": inserted_id,
                    "timestamp": timestamp,
                    "axis": request.axis,
                    "label": request.label
                }
            except (ValidationError, DatabaseError) as e:
                logger.warning(f"Capture validation error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Capture error: {e}")
            raise HTTPException(status_code=500, detail="Capture failed: " + str(e))
    
    @app.get("/api/training/samples", tags=["Training"])
    def api_get_training_samples(limit: int = 100, offset: int = 0) -> Dict:
        """
        Get paginated list of training samples.
        
        Retrieve training samples with pagination support.
        """
        try:
            result = get_training_db().get_samples(limit=limit, offset=offset)
            return {
                "status": "ok",
                "data": result
            }
        except DatabaseError as e:
            logger.warning(f"Get samples error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error(f"Get samples error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get samples: " + str(e))
    
    @app.get("/api/training/stats", tags=["Training"])
    def api_get_training_stats() -> Dict:
        """
        Get training data statistics.
        
        Returns statistics about collected training samples.
        """
        try:
            stats = get_training_db().get_stats()
            return {
                "status": "ok",
                "data": stats
            }
        except DatabaseError as e:
            logger.warning(f"Get stats error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error(f"Get stats error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get stats: " + str(e))
    
    @app.post("/api/training/train", tags=["Training"])
    def api_train_model(request: TrainRequest) -> Dict:
        """
        Train ML model on stored training samples.
        
        Trains a model using all labeled training samples in the database.
        Requires at least 20 labeled samples.
        """
        try:
            # Load all training samples
            samples = get_training_db().get_all_samples()
            
            if not samples:
                raise HTTPException(
                    status_code=400,
                    detail="No training samples available"
                )
            
            # Check minimum samples
            if len(samples) < Config.MIN_TRAINING_SAMPLES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Need at least {Config.MIN_TRAINING_SAMPLES} samples, only have {len(samples)}"
                )
            
            # Check for labeled samples
            labeled_samples = [s for s in samples if s.get('label') and s['label'] != '']
            if not labeled_samples:
                raise HTTPException(
                    status_code=400,
                    detail="No labeled samples found. Add labels to training data first."
                )
            
            logger.info(f"Starting model training with {len(labeled_samples)} labeled samples")
            
            # Train the model
            try:
                result = ModelTrainer.train(
                    labeled_samples,
                    request.target_label_field,
                    request.algorithm
                )
                return {
                    "status": "ok",
                    "message": "Model trained successfully",
                    "data": result
                }
            except TrainingError as e:
                logger.warning(f"Training error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Training error: {e}")
            raise HTTPException(status_code=500, detail="Model training failed: " + str(e))
    
    @app.get("/api/training/model-info", tags=["Training"])
    def api_get_model_info() -> Dict:
        """Get information about the trained model."""
        try:
            info = load_model_info()
            return {
                "status": info.get("status", "ok"),
                "data": info
            }
        except Exception as e:
            logger.error(f"Get model info error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get model info: " + str(e))
    
    @app.post("/api/training/predict", tags=["Prediction"])
    def api_predict(request: PredictRequest) -> Dict:
        """
        Make prediction on a single sample.
        
        Uses the trained model to make predictions on new sensor data.
        """
        try:
            try:
                result = ModelPredictor.predict(request.sample)
                return {
                    "status": "ok",
                    "data": result
                }
            except PredictionError as e:
                logger.warning(f"Prediction error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise HTTPException(status_code=500, detail="Prediction failed: " + str(e))
    
    @app.post("/api/training/batch-predict", tags=["Prediction"])
    def api_batch_predict(request: BatchPredictRequest) -> Dict:
        """
        Make predictions on multiple samples.
        
        Uses the trained model to make batch predictions.
        """
        try:
            try:
                result = ModelPredictor.batch_predict(request.samples)
                return {
                    "status": "ok",
                    "data": result
                }
            except PredictionError as e:
                logger.warning(f"Batch prediction error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Batch prediction error: {e}")
            raise HTTPException(status_code=500, detail="Batch prediction failed: " + str(e))
    
    @app.delete("/api/training/samples/{sample_id}", tags=["Training"])
    def api_delete_sample(sample_id: int) -> Dict:
        """Delete a training sample."""
        try:
            get_training_db().delete_sample(sample_id)
            return {"status": "ok", "message": f"Sample {sample_id} deleted"}
        except DatabaseError as e:
            logger.warning(f"Delete sample error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error(f"Delete sample error: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete sample: " + str(e))
    
    @app.delete("/api/training/samples/by-label/{label}", tags=["Training"])
    def api_delete_by_label(label: str) -> Dict:
        """Delete all samples with a specific label."""
        try:
            try:
                deleted_count = get_training_db().delete_by_label(label)
                return {
                    "status": "ok",
                    "message": f"Deleted {deleted_count} samples with label '{label}'",
                    "deleted_count": deleted_count
                }
            except ValidationError as e:
                raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Delete by label error: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete samples: " + str(e))
