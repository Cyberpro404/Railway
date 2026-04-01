"""
ML Engine - RandomForest classifier with feature engineering
Predicts railway condition anomalies (e.g., expansion gap detection)
"""
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Any
import pickle
import json
from datetime import datetime, timezone
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import asyncio

logger = logging.getLogger(__name__)

class MLEngine:
    """Machine Learning engine for anomaly detection"""
    
    def __init__(self, model_path: str = "models/rf_model.pkl"):
        # Ensure models directory exists
        model_dir = Path("models")
        model_dir.mkdir(exist_ok=True)
        self.model_path = Path(model_path)
        self.model: Optional[RandomForestClassifier] = None
        self.scaler: Optional[StandardScaler] = None
        # 21 features matching data_receiver.py output keys exactly
        self.feature_names = [
            "z_axis_rms",       # R0
            "z_rms",            # R1
            "iso_peak_peak",    # R2
            "temperature",      # R3
            "z_true_peak",      # R4
            "x_rms",            # R5
            "z_accel",          # R6
            "x_accel",          # R7
            "frequency",        # R8
            "x_frequency",      # R9
            "z_band_rms",       # R10
            "x_band_rms",       # R11
            "kurtosis",         # R12
            "x_kurtosis",       # R13
            "crest_factor",     # R14
            "x_crest_factor",   # R15
            "z_hf_rms_accel",   # R16
            "z_peak",           # R17
            "x_hf_rms_accel",   # R18
            "x_peak",           # R19
            "z_x_ratio",        # derived
        ]
        self.label_names = {
            0: "Normal",
            1: "Warning",
            2: "Critical",
            3: "BearingFault",
            4: "Imbalance",
        }
        self.is_loaded = False
        
    async def load_model(self):
        """Load pre-trained model and scaler"""
        try:
            if self.model_path.exists():
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data.get('model')
                    self.scaler = model_data.get('scaler')
                    self.is_loaded = True
                    logger.info(f"ML model loaded from {self.model_path}")
            else:
                # Create default model if none exists
                logger.warning("No model found, creating default model")
                await self._create_default_model()
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            await self._create_default_model()
    
    async def _create_default_model(self):
        """Create a default trained model using synthetic 5-class data"""
        np.random.seed(42)
        rng = np.random.default_rng(42)

        def bounded(mean, std, lo, hi, n):
            return np.clip(rng.normal(mean, std, n), lo, hi)

        n = 300   # samples per class
        class_cfgs = [
            # Normal
            dict(z_rms=(0.8,0.4,0.1,2.7), x_rms=(0.6,0.3,0.1,2.0),
                 kurtosis=(2.5,0.3,1.0,2.95), crest=(2.4,0.3,1.5,3.4),
                 temp=(35,5,20,54), z_a=(0.4,0.15,0.05,1.2), x_a=(0.3,0.12,0.05,1.0), freq=(50,5,38,65)),
            # Warning
            dict(z_rms=(4.0,1.0,2.8,7.0), x_rms=(2.8,0.7,1.5,5.5),
                 kurtosis=(3.8,0.5,3.0,4.9), crest=(3.6,0.5,2.5,4.9),
                 temp=(52,8,35,69), z_a=(1.8,0.5,0.6,3.5), x_a=(1.2,0.4,0.4,2.8), freq=(55,8,38,72)),
            # Critical
            dict(z_rms=(10.0,2.5,7.1,18.0), x_rms=(5.5,1.8,2.0,13.0),
                 kurtosis=(3.0,1.0,1.5,4.9), crest=(3.0,0.8,2.0,4.9),
                 temp=(76,8,70,95), z_a=(5.0,1.5,2.0,10.0), x_a=(3.0,1.0,1.0,7.0), freq=(60,10,38,85)),
            # BearingFault
            dict(z_rms=(4.5,1.2,1.5,9.0), x_rms=(3.2,0.9,1.0,7.0),
                 kurtosis=(7.5,1.5,5.0,14.0), crest=(6.5,1.5,4.0,12.0),
                 temp=(57,8,35,73), z_a=(3.2,0.9,1.0,7.0), x_a=(2.2,0.7,0.7,5.0), freq=(53,7,35,72)),
            # Imbalance
            dict(z_rms=(5.5,1.2,2.0,9.0), x_rms=(1.5,0.3,0.3,2.4),
                 kurtosis=(2.8,0.4,1.5,3.9), crest=(3.2,0.5,2.0,4.5),
                 temp=(46,6,28,62), z_a=(2.8,0.7,1.0,5.0), x_a=(0.9,0.2,0.2,1.7), freq=(48,5,36,62)),
        ]

        rows, labels = [], []
        for label, c in enumerate(class_cfgs):
            z_rms  = bounded(*c["z_rms"], n)
            x_rms  = bounded(*c["x_rms"], n)
            kurtosis = bounded(*c["kurtosis"], n)
            crest  = bounded(*c["crest"], n)
            temp   = bounded(*c["temp"], n)
            z_a    = bounded(*c["z_a"], n)
            x_a    = bounded(*c["x_a"], n)
            freq   = bounded(*c["freq"], n)

            z_peak = z_rms * rng.uniform(1.2, 2.5, n)
            x_peak = x_rms * rng.uniform(1.2, 2.5, n)
            x_freq = freq * rng.uniform(0.88, 1.12, n)

            feat = np.column_stack([
                z_rms * rng.uniform(0.93, 1.07, n),   # z_axis_rms
                z_rms,                                  # z_rms
                z_peak * rng.uniform(1.7, 2.3, n),     # iso_peak_peak
                temp,                                   # temperature
                z_peak * rng.uniform(0.88, 1.12, n),   # z_true_peak
                x_rms,                                  # x_rms
                z_a,                                    # z_accel
                x_a,                                    # x_accel
                freq,                                   # frequency
                x_freq,                                 # x_frequency
                z_rms * rng.uniform(0.55, 0.90, n),    # z_band_rms
                x_rms * rng.uniform(0.55, 0.90, n),    # x_band_rms
                kurtosis,                               # kurtosis
                kurtosis * rng.uniform(0.65, 1.35, n), # x_kurtosis
                crest,                                  # crest_factor
                crest * rng.uniform(0.65, 1.35, n),    # x_crest_factor
                z_a * rng.uniform(0.35, 0.70, n),      # z_hf_rms_accel
                z_peak,                                 # z_peak
                x_a * rng.uniform(0.35, 0.70, n),      # x_hf_rms_accel
                x_peak,                                 # x_peak
                np.where(x_rms > 0, z_rms / x_rms, 0),# z_x_ratio
            ])
            rows.append(feat)
            labels.extend([label] * n)

        X = np.vstack(rows)
        y = np.array(labels)

        self.scaler = StandardScaler()
        X_s = self.scaler.fit_transform(X)
        self.model = RandomForestClassifier(
            n_estimators=100, max_depth=10, class_weight="balanced",
            random_state=42, n_jobs=-1
        )
        self.model.fit(X_s, y)
        
        # Save model
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump({'model': self.model, 'scaler': self.scaler}, f)
        
        self.is_loaded = True
        logger.info("Default ML model created and saved")
    
    def _calculate_features_batch(self, data: Dict[str, np.ndarray]) -> np.ndarray:
        """Calculate features for batch data"""
        features = []
        for i in range(len(data['z_rms'])):
            sample = {k: v[i] for k, v in data.items()}
            feat = self._calculate_single_features(sample)
            features.append([feat.get(name, 0.0) for name in self.feature_names])
        return np.array(features)
    
    def calculate_features(self, sensor_data: Dict[str, float]) -> Dict[str, float]:
        """Calculate ML features from sensor data"""
        return self._calculate_single_features(sensor_data)
    
    def _calculate_single_features(self, data: Dict[str, float]) -> Dict[str, float]:
        """Return a feature dict from sensor_data using all 21 feature keys."""
        z_rms = data.get("z_rms", 0.0)
        x_rms = data.get("x_rms", 0.0)
        return {
            "z_axis_rms":     data.get("z_axis_rms",     0.0),
            "z_rms":          z_rms,
            "iso_peak_peak":  data.get("iso_peak_peak",  0.0),
            "temperature":    data.get("temperature",    0.0),
            "z_true_peak":    data.get("z_true_peak",    0.0),
            "x_rms":          x_rms,
            "z_accel":        data.get("z_accel",        0.0),
            "x_accel":        data.get("x_accel",        0.0),
            "frequency":      data.get("frequency",      0.0),
            "x_frequency":    data.get("x_frequency",   0.0),
            "z_band_rms":     data.get("z_band_rms",     0.0),
            "x_band_rms":     data.get("x_band_rms",     0.0),
            "kurtosis":       data.get("kurtosis",       0.0),
            "x_kurtosis":     data.get("x_kurtosis",     0.0),
            "crest_factor":   data.get("crest_factor",   0.0),
            "x_crest_factor": data.get("x_crest_factor", 0.0),
            "z_hf_rms_accel": data.get("z_hf_rms_accel", 0.0),
            "z_peak":         data.get("z_peak",         0.0),
            "x_hf_rms_accel": data.get("x_hf_rms_accel", 0.0),
            "x_peak":         data.get("x_peak",         0.0),
            "z_x_ratio":      round(z_rms / x_rms, 4) if x_rms > 0 else 0.0,
        }
    
    def predict(self, features: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """Make prediction on features"""
        if not self.is_loaded or not self.model or not self.scaler:
            return None
        
        try:
            # Convert features to array
            feature_array = np.array([[features.get(name, 0.0) for name in self.feature_names]])
            
            # Scale features
            feature_scaled = self.scaler.transform(feature_array)
            
            # Predict
            prediction = int(self.model.predict(feature_scaled)[0])
            probabilities = self.model.predict_proba(feature_scaled)[0]

            # Map class index to class name (handle models with fewer classes)
            classes = self.model.classes_
            prob_dict = {self.label_names.get(int(c), str(c)): float(p)
                         for c, p in zip(classes, probabilities)}

            class_name = self.label_names.get(prediction, str(prediction))
            
            # Get feature importance
            importances = dict(zip(self.feature_names, self.model.feature_importances_))
            
            return {
                "class":              prediction,
                "class_name":         class_name,
                "confidence":         float(max(probabilities)),
                "probabilities":      prob_dict,
                "feature_importance": importances,
                "timestamp":          datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return None
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.is_loaded and self.model is not None
    
    async def reload_model(self):
        """Reload model from disk"""
        self.is_loaded = False
        await self.load_model()
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get model statistics"""
        if not self.is_loaded:
            return {"status": "not_loaded"}
        
        return {
            "status": "loaded",
            "model_type": "RandomForestClassifier",
            "n_features": len(self.feature_names),
            "feature_names": self.feature_names,
            "model_path": str(self.model_path)
        }

