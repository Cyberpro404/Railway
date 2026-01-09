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
from datetime import datetime
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
        self.feature_names = [
            'z_rms', 'x_rms', 'z_peak', 'x_peak', 'z_accel', 'x_accel',
            'z_kurtosis', 'x_kurtosis', 'z_crest_factor', 'x_crest_factor',
            'temperature', 'z_x_ratio'
        ]
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
        """Create a default trained model"""
        # Generate synthetic training data
        np.random.seed(42)
        n_samples = 1000
        
        # Normal operation data
        normal_data = {
            'z_rms': np.random.normal(0.4, 0.1, n_samples),
            'x_rms': np.random.normal(0.5, 0.1, n_samples),
            'z_peak': np.random.normal(0.6, 0.15, n_samples),
            'x_peak': np.random.normal(0.7, 0.15, n_samples),
            'z_accel': np.random.normal(0.3, 0.1, n_samples),
            'x_accel': np.random.normal(0.4, 0.1, n_samples),
            'temperature': np.random.normal(30, 5, n_samples),
        }
        
        # Anomaly data (expansion gap)
        anomaly_data = {
            'z_rms': np.random.normal(0.8, 0.2, n_samples // 4),
            'x_rms': np.random.normal(0.6, 0.15, n_samples // 4),
            'z_peak': np.random.normal(1.5, 0.3, n_samples // 4),
            'x_peak': np.random.normal(1.2, 0.25, n_samples // 4),
            'z_accel': np.random.normal(0.8, 0.2, n_samples // 4),
            'x_accel': np.random.normal(0.6, 0.15, n_samples // 4),
            'temperature': np.random.normal(32, 6, n_samples // 4),
        }
        
        # Calculate features
        normal_features = self._calculate_features_batch(normal_data)
        anomaly_features = self._calculate_features_batch(anomaly_data)
        
        # Combine and create labels
        X = np.vstack([normal_features, anomaly_features])
        y = np.hstack([np.zeros(len(normal_features)), np.ones(len(anomaly_features))])
        
        # Train model
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_scaled, y)
        
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
        """Calculate features for a single sample"""
        z_rms = data.get('z_rms', 0.0)
        x_rms = data.get('x_rms', 0.0)
        z_peak = data.get('z_peak', 0.0)
        x_peak = data.get('x_peak', 0.0)
        z_accel = data.get('z_accel', 0.0)
        x_accel = data.get('x_accel', 0.0)
        temp = data.get('temperature', 0.0)
        
        # Statistical features (simplified - in production, use rolling window)
        z_kurtosis = self._estimate_kurtosis(z_rms, z_peak)
        x_kurtosis = self._estimate_kurtosis(x_rms, x_peak)
        z_crest_factor = z_peak / z_rms if z_rms > 0 else 0.0
        x_crest_factor = x_peak / x_rms if x_rms > 0 else 0.0
        z_x_ratio = z_rms / x_rms if x_rms > 0 else 0.0
        
        return {
            'z_rms': z_rms,
            'x_rms': x_rms,
            'z_peak': z_peak,
            'x_peak': x_peak,
            'z_accel': z_accel,
            'x_accel': x_accel,
            'z_kurtosis': z_kurtosis,
            'x_kurtosis': x_kurtosis,
            'z_crest_factor': z_crest_factor,
            'x_crest_factor': x_crest_factor,
            'temperature': temp,
            'z_x_ratio': z_x_ratio
        }
    
    def _estimate_kurtosis(self, rms: float, peak: float) -> float:
        """Estimate kurtosis from RMS and peak values"""
        # Simplified kurtosis estimation
        if rms > 0:
            ratio = peak / rms
            # Higher ratio indicates higher kurtosis (more peaked distribution)
            return max(0.0, (ratio - 1.0) * 2.0)
        return 0.0
    
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
            prediction = self.model.predict(feature_scaled)[0]
            probabilities = self.model.predict_proba(feature_scaled)[0]
            
            # Get feature importance
            importances = dict(zip(self.feature_names, self.model.feature_importances_))
            
            return {
                "class": int(prediction),
                "class_name": "ANOMALY" if prediction == 1 else "NORMAL",
                "confidence": float(max(probabilities)),
                "probabilities": {
                    "normal": float(probabilities[0]),
                    "anomaly": float(probabilities[1])
                },
                "feature_importance": importances,
                "timestamp": datetime.utcnow().isoformat()
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

