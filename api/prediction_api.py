"""
Project Gandiva - Railway Vibration Fault Detection
FastAPI Prediction Endpoint

This module provides the /predict endpoint for real-time fault classification
based on vibration sensor features.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import numpy as np
import joblib
import os
from typing import List
from datetime import datetime, timezone

# Model file locations - use absolute path from project root
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)  # go up from api/ to project root
MODEL_FILE = os.path.join(_PROJECT_ROOT, "gandiva_vib_model.joblib")
SCALER_FILE = os.path.join(_PROJECT_ROOT, "gandiva_scaler.joblib")

# Class label mapping - must match train_gap_crack_model.py
# 3-class model: good track, expansion gap, crack/defect
CLASS_LABELS = {
    0: "normal",        # good track
    1: "expansion_gap", # intentional gap (not a fault)
    2: "crack"          # crack or defect (needs inspection)
}

# Create router
router = APIRouter(tags=["ML Prediction"])

# Global model variable (loaded once at startup)
_model = None
_scaler = None


class VibrationSample(BaseModel):
    """
    Input schema for vibration sensor readings.
    
    All 8 features are required for fault prediction.
    """
    rms: float = Field(..., description="Root Mean Square of vibration signal", ge=0)
    peak: float = Field(..., description="Peak amplitude of vibration", ge=0)
    band_1x: float = Field(..., description="Energy in 1x rotational frequency band", ge=0)
    band_2x: float = Field(..., description="Energy in 2x rotational frequency band", ge=0)
    band_3x: float = Field(..., description="Energy in 3x rotational frequency band", ge=0)
    band_5x: float = Field(..., description="Energy in 5x rotational frequency band", ge=0)
    band_7x: float = Field(..., description="Energy in 7x rotational frequency band", ge=0)
    temperature: float = Field(..., description="Sensor temperature in Celsius")
    
    class Config:
        json_schema_extra = {
            "example": {
                "rms": 2.5,
                "peak": 8.3,
                "band_1x": 1.2,
                "band_2x": 0.8,
                "band_3x": 0.5,
                "band_5x": 0.3,
                "band_7x": 0.1,
                "temperature": 45.2
            }
        }


class PredictionResponse(BaseModel):
    """Output schema for fault prediction results."""
    class_index: int = Field(..., description="Predicted class index (0-4)")
    class_label: str = Field(..., description="Human-readable fault type")
    probabilities: List[float] = Field(
        ..., 
        description="Probability for each class [normal, misalignment, unbalance, looseness, crack]"
    )
    confidence: float = Field(..., description="Confidence score (max probability)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "class_index": 0,
                "class_label": "normal",
                "probabilities": [0.85, 0.05, 0.04, 0.03, 0.03],
                "confidence": 0.85
            }
        }


class ModelStatus(BaseModel):
    """Model status information."""
    loaded: bool
    model_file: str
    n_classes: int
    class_labels: dict


def load_model():
    """
    Load the trained model and scaler from disk.
    Called once at application startup.
    """
    global _model, _scaler
    
    # Diagnostic prints so we can see exactly where it's looking
    print(f"[ML] Looking for model at: {MODEL_FILE}")
    print(f"[ML] File exists: {os.path.exists(MODEL_FILE)}")
    
    if not os.path.exists(MODEL_FILE):
        print(f"[ML] WARNING: Model file NOT FOUND at: {MODEL_FILE}")
        print(f"[ML]    Run 'python scripts/train_gap_crack_model.py' to train the model first.")
        _model = None
        return False
    
    try:
        _model = joblib.load(MODEL_FILE)
        print(f"[ML] SUCCESS: Model loaded successfully from: {MODEL_FILE}")
        print(f"[ML]   Model type: {type(_model).__name__}")
        if hasattr(_model, 'classes_'):
            print(f"[ML]   Classes: {list(_model.classes_)}")
        
        # Load scaler if available (optional)
        print(f"[ML] Looking for scaler at: {SCALER_FILE}")
        if os.path.exists(SCALER_FILE):
            _scaler = joblib.load(SCALER_FILE)
            print(f"[ML] SUCCESS: Scaler loaded successfully from: {SCALER_FILE}")
        else:
            _scaler = None
            print(f"[ML] INFO: No scaler file found - using raw features")
        
        return True
    except Exception as e:
        print(f"[ML] ERROR: Error loading model: {e}")
        import traceback
        traceback.print_exc()
        _model = None
        _scaler = None
        return False


def get_model():
    """Get the loaded model, raising an error if not available."""
    if _model is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Model not loaded",
                "message": f"ML model '{MODEL_FILE}' is not available. "
                           f"Run 'python train_model.py' to train the model first."
            }
        )
    return _model


@router.get("/model/status", response_model=ModelStatus)
async def get_model_status():
    """
    Check if the ML model is loaded and ready for predictions.
    """
    return ModelStatus(
        loaded=_model is not None,
        model_file=MODEL_FILE,
        n_classes=len(CLASS_LABELS),
        class_labels=CLASS_LABELS
    )


@router.get("/ml_status")
async def get_ml_status():
    """Simple status endpoint to debug ML integration.

    Use this from a browser or Postman to confirm the backend can see the
    trained model and which classes it exposes.
    """
    return {
        "model_loaded": _model is not None,
        "scaler_loaded": _scaler is not None,
        "model_path": MODEL_FILE,
        "scaler_path": SCALER_FILE,
        "classes": list(CLASS_LABELS.values())
    }


@router.post("/ml/reload")
async def reload_ml_model():
    """Reload the ML model and scaler from disk.

    This lets you train a new model file and reload it from the web UI
    without having to restart the FastAPI process.
    """
    ok = load_model()
    return {
        "ok": ok,
        "model_loaded": _model is not None,
        "scaler_loaded": _scaler is not None,
        "model_path": MODEL_FILE,
        "scaler_path": SCALER_FILE,
        "classes": list(CLASS_LABELS.values())
    }


@router.get("/debug/features")
async def debug_features():
    """
    Debug endpoint to see what features would be extracted from current sensor reading.
    Use this to verify non-zero feature values before training.
    """
    from core import sensor_reader
    
    try:
        status, reading = sensor_reader.read_sensor_once()
        
        if reading is None:
            return {"error": "No reading available", "status": str(status)}
        
        if not reading.get("ok", False):
            return {"error": reading.get("error", "Sensor read failed")}
        
        # Extract feature values
        rms = reading.get("z_rms_mm_s", 0.0)
        peak = reading.get("z_peak_mm_s", 0.0)
        temp = reading.get("temp_c", 0.0)
        kurtosis = reading.get("z_kurtosis", 0.0)
        crest = reading.get("z_crest_factor", 0.0)
        rms_g = reading.get("z_rms_g", 0.0)
        hf_rms_g = reading.get("z_hf_rms_g", 0.0)
        
        band_1x = reading.get("band_1x", 0.0)
        band_2x = reading.get("band_2x", 0.0)
        band_3x = reading.get("band_3x", 0.0)
        band_5x = reading.get("band_5x", 0.0)
        band_7x = reading.get("band_7x", 0.0)
        
        bands_all_zero = (band_1x == 0 and band_2x == 0 and band_3x == 0)
        
        if bands_all_zero:
            features_used = {
                "rms": rms,
                "peak": peak,
                "kurtosis (alt band_1x)": kurtosis,
                "crest_factor (alt band_2x)": crest,
                "rms_g (alt band_3x)": rms_g,
                "hf_rms_g (alt band_5x)": hf_rms_g,
                "peak/rms ratio (alt band_7x)": peak / (rms + 0.001),
                "temperature": temp
            }
        else:
            features_used = {
                "rms": rms,
                "peak": peak,
                "band_1x": band_1x,
                "band_2x": band_2x,
                "band_3x": band_3x,
                "band_5x": band_5x,
                "band_7x": band_7x,
                "temperature": temp
            }
        
        return {
            "bands_available": not bands_all_zero,
            "using_alternative_features": bands_all_zero,
            "features": features_used,
            "raw_scalars": {
                "z_rms_mm_s": rms,
                "z_peak_mm_s": peak,
                "z_kurtosis": kurtosis,
                "z_crest_factor": crest,
                "z_rms_g": rms_g,
                "z_hf_rms_g": hf_rms_g,
                "temp_c": temp,
                "frequency_hz": reading.get("frequency_hz", 0)
            },
            "raw_bands": {
                "band_1x": band_1x,
                "band_2x": band_2x,
                "band_3x": band_3x,
                "band_5x": band_5x,
                "band_7x": band_7x
            }
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/predict", response_model=PredictionResponse)
async def predict_fault(sample: VibrationSample):
    """
    Predict fault type from vibration sensor features.
    
    Accepts 8 vibration features and returns:
    - Predicted fault class (0-4)
    - Human-readable label
    - Probability distribution across all classes
    - Confidence score
    
    **Fault Types:**
    - 0: normal - No fault detected
    - 1: misalignment - Shaft or coupling misalignment
    - 2: unbalance - Rotating mass imbalance
    - 3: looseness - Mechanical looseness
    - 4: crack - Structural crack detected
    """
    model = get_model()
    
    # Convert input to numpy array of shape (1, 8)
    features = np.array([[
        sample.rms,
        sample.peak,
        sample.band_1x,
        sample.band_2x,
        sample.band_3x,
        sample.band_5x,
        sample.band_7x,
        sample.temperature
    ]])
    
    # Get prediction and probabilities
    class_index = int(model.predict(features)[0])
    probabilities = model.predict_proba(features)[0].tolist()
    
    # Round probabilities for cleaner output
    probabilities = [round(p, 4) for p in probabilities]
    
    return PredictionResponse(
        class_index=class_index,
        class_label=CLASS_LABELS[class_index],
        probabilities=probabilities,
        confidence=round(max(probabilities), 4)
    )


def safe_predict_from_reading(reading: dict) -> dict:
    """
    Safe ML prediction wrapper - checks ok status before predicting.
    
    Use this in the polling loop to avoid feeding bad data to ML.
    
    Args:
        reading: Sensor reading dict with 'ok' field
        
    Returns:
        {
            "ok": True/False,
            "prediction": "crack" / "normal" / etc,
            "class_index": 0-4,
            "probabilities": [...],
            "confidence": 0.0-1.0,
            "features": {...original reading...}
        }
        OR
        {
            "ok": False,
            "error": "reason"
        }
    """
    global _model
    
    # Check if reading is valid
    if reading is None:
        return {"ok": False, "error": "No reading provided"}
    
    if not reading.get("ok", False):
        return {
            "ok": False,
            "error": reading.get("error", "Sensor read failed")
        }
    
    # Check if model is loaded
    if _model is None:
        # Attempt lazy load in case the model file was added after startup
        loaded_now = load_model()
        if not loaded_now or _model is None:
            return {
                "ok": False, 
                "error": "Model not loaded - train or reload the ML model"
            }
    
    # Build feature vector
    try:
        # Map reading keys to ML features
        # Use available scalar values - sensor may not have band registers
        rms = reading.get("z_rms_mm_s", reading.get("rms", 0.0))
        peak = reading.get("z_peak_mm_s", reading.get("peak", 0.0))
        temp = reading.get("temp_c", reading.get("temperature", 25.0))
        
        # Use kurtosis, crest factor, and g values if bands not available
        # These are more likely to be supported by the sensor
        kurtosis = reading.get("z_kurtosis", 0.0)
        crest = reading.get("z_crest_factor", 0.0)
        rms_g = reading.get("z_rms_g", 0.0)
        hf_rms_g = reading.get("z_hf_rms_g", 0.0)
        
        # Band values (may be 0 if sensor doesn't support)
        band_1x = reading.get("band_1x", 0.0)
        band_2x = reading.get("band_2x", 0.0)
        band_3x = reading.get("band_3x", 0.0)
        band_5x = reading.get("band_5x", 0.0)
        band_7x = reading.get("band_7x", 0.0)
        
        # If bands are all zero, use scalar features instead
        if band_1x == 0 and band_2x == 0 and band_3x == 0:
            # Use alternative features when bands unavailable
            features = np.array([[
                rms,
                peak,
                kurtosis,       # instead of band_1x
                crest,          # instead of band_2x
                rms_g,          # instead of band_3x
                hf_rms_g,       # instead of band_5x
                peak / (rms + 0.001),  # peak-to-RMS ratio instead of band_7x
                temp
            ]])
        else:
            # Use band values when available
            features = np.array([[
                rms,
                peak,
                band_1x,
                band_2x,
                band_3x,
                band_5x,
                band_7x,
                temp
            ]])
        
        # Apply scaler if available
        if _scaler is not None:
            features = _scaler.transform(features)
        
        # Predict
        class_index = int(_model.predict(features)[0])
        
        # Handle unknown class index gracefully
        if class_index not in CLASS_LABELS:
            class_index = min(class_index, max(CLASS_LABELS.keys()))
        
        probabilities = _model.predict_proba(features)[0].tolist()
        probabilities = [round(p, 4) for p in probabilities]
        
        return {
            "ok": True,
            "prediction": CLASS_LABELS.get(class_index, "unknown"),
            "class_index": class_index,
            "probabilities": probabilities,
            "confidence": round(max(probabilities), 4),
            "features": {
                "rms": rms,
                "peak": peak,
                "band_1x": reading.get("band_1x", 0.0),
                "band_2x": reading.get("band_2x", 0.0),
                "band_3x": reading.get("band_3x", 0.0),
                "band_5x": reading.get("band_5x", 0.0),
                "band_7x": reading.get("band_7x", 0.0),
                "temperature": temp
            }
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"Prediction failed: {e}"
        }


@router.post("/predict/batch", response_model=List[PredictionResponse])
async def predict_batch(samples: List[VibrationSample]):
    """
    Predict fault types for multiple samples at once.
    
    More efficient than calling /predict multiple times.
    Maximum 100 samples per request.
    """
    if len(samples) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 samples per batch request"
        )
    
    model = get_model()
    
    # Convert all samples to feature matrix
    features = np.array([
        [s.rms, s.peak, s.band_1x, s.band_2x, s.band_3x, s.band_5x, s.band_7x, s.temperature]
        for s in samples
    ])
    
    # Batch prediction
    class_indices = model.predict(features)
    all_probabilities = model.predict_proba(features)
    
    # Build response
    results = []
    for i, (cls_idx, probs) in enumerate(zip(class_indices, all_probabilities)):
        probs_list = [round(p, 4) for p in probs.tolist()]
        results.append(PredictionResponse(
            class_index=int(cls_idx),
            class_label=CLASS_LABELS[int(cls_idx)],
            probabilities=probs_list,
            confidence=round(max(probs_list), 4)
        ))
    
    return results

# -------------------------------------------------
# Debug/testing endpoint to simulate an ML reading
# -------------------------------------------------
@router.post("/ml/simulate")
async def simulate_ml_reading():
    """Simulate a single sensor reading, run ML prediction, and store it.

    Useful for testing the ML Insights tab when hardware isn't responding.
    """
    try:
        # Build a synthetic reading similar to the runtime structure
        now = datetime.now(timezone.utc).isoformat()
        reading = {
            "ok": True,
            "timestamp": now,
            # Scalars commonly present in runtime reads
            "z_rms_mm_s": 1.2,
            "x_rms_mm_s": 0.9,
            "z_peak_mm_s": 3.4,
            "x_peak_mm_s": 2.8,
            "temp_c": 36.5,
            # Alternative scalar features used when bands are missing
            "z_kurtosis": 2.1,
            "z_crest_factor": 3.0,
            "z_rms_g": 0.06,
            "z_hf_rms_g": 0.02,
            # No band values – let safe_predict_from_reading use alternative features
            "band_1x": 0.0,
            "band_2x": 0.0,
            "band_3x": 0.0,
            "band_5x": 0.0,
            "band_7x": 0.0,
            # Train state for UI
            "train_state": "idle",
        }

        # Run ML prediction using the same helper as runtime
        result = safe_predict_from_reading(reading)
        if not result.get("ok"):
            raise HTTPException(status_code=503, detail=result.get("error", "Prediction unavailable"))

        reading["ml_prediction"] = {
            "label": result["prediction"],
            "class_index": result["class_index"],
            "confidence": result["confidence"],
            "probabilities": result["probabilities"],
        }

        # Persist to operational DB so Insights can read it
        try:
            from database.operational_db import get_db
            get_db().upsert_latest(reading)
        except Exception as db_err:
            # Non-fatal for simulation; return the reading anyway
            print(f"[ML simulate] DB upsert failed: {db_err}")

        return {
            "status": "ok",
            "data": {
                "timestamp": reading["timestamp"],
                "prediction": reading["ml_prediction"],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e}")
