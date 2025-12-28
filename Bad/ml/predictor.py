"""
Model prediction module for inference using trained models.
"""

import logging
import pandas as pd
from typing import Dict, Optional

from utils.logger import setup_logger
from utils.errors import PredictionError
from ml.model_trainer import load_trained_model

logger = setup_logger(__name__)


class ModelPredictor:
    """Handles predictions using trained models."""
    
    @staticmethod
    def predict(sample: Dict) -> Dict:
        """
        Make prediction on a single sample using trained model.
        
        Args:
            sample: Sample dictionary with sensor data
            
        Returns:
            Dictionary with prediction results
            
        Raises:
            PredictionError: If prediction fails
        """
        try:
            # Load model
            model_data = load_trained_model()
            if model_data is None:
                raise PredictionError("No trained model available")
            
            model = model_data['model']
            scaler = model_data['scaler']
            feature_columns = model_data['feature_columns']
            model_type = model_data['model_type']
            
            # Prepare features
            df = pd.DataFrame([sample])
            X = df[feature_columns].fillna(0)
            X_scaled = scaler.transform(X)
            
            # Make prediction
            prediction = model.predict(X_scaled)[0]
            
            # Get prediction probabilities for classification
            probabilities = None
            if model_type == "classification" and hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(X_scaled)[0].tolist()
                if 'label_encoder' in model_data and model_data['label_encoder']:
                    classes = model_data['label_encoder'].classes_.tolist()
                    probabilities = dict(zip(classes, probabilities))
            
            logger.info(f"Prediction made: {prediction}")
            
            return {
                "status": "ok",
                "prediction": str(prediction) if model_type == "classification" else float(prediction),
                "probabilities": probabilities,
                "model_type": model_type,
                "confidence": float(max(probabilities.values())) if probabilities else None
            }
        except PredictionError:
            raise
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise PredictionError(f"Prediction failed: {e}")
    
    @staticmethod
    def batch_predict(samples: list) -> Dict:
        """
        Make predictions on multiple samples.
        
        Args:
            samples: List of sample dictionaries
            
        Returns:
            Dictionary with prediction results for all samples
            
        Raises:
            PredictionError: If prediction fails
        """
        try:
            if not samples:
                raise PredictionError("No samples provided for batch prediction")
            
            # Load model
            model_data = load_trained_model()
            if model_data is None:
                raise PredictionError("No trained model available")
            
            model = model_data['model']
            scaler = model_data['scaler']
            feature_columns = model_data['feature_columns']
            model_type = model_data['model_type']
            
            # Prepare features for all samples
            df = pd.DataFrame(samples)
            X = df[feature_columns].fillna(0)
            X_scaled = scaler.transform(X)
            
            # Make predictions
            predictions = model.predict(X_scaled)
            
            # Get probabilities for classification
            probabilities_list = None
            if model_type == "classification" and hasattr(model, 'predict_proba'):
                proba = model.predict_proba(X_scaled)
                if 'label_encoder' in model_data and model_data['label_encoder']:
                    classes = model_data['label_encoder'].classes_.tolist()
                    probabilities_list = [
                        dict(zip(classes, proba_row.tolist()))
                        for proba_row in proba
                    ]
            
            logger.info(f"Batch prediction made for {len(samples)} samples")
            
            return {
                "status": "ok",
                "predictions": [str(p) if model_type == "classification" else float(p) for p in predictions],
                "probabilities": probabilities_list,
                "model_type": model_type,
                "n_samples": len(samples)
            }
        except PredictionError:
            raise
        except Exception as e:
            logger.error(f"Batch prediction error: {e}")
            raise PredictionError(f"Batch prediction failed: {e}")
