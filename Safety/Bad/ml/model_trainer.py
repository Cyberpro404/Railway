"""
ML model training module with comprehensive error handling.
Handles model training, saving, and loading using scikit-learn.
"""

import logging
import pickle
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, mean_squared_error, r2_score

from utils.logger import setup_logger
from utils.errors import TrainingError
from config.settings import Config

logger = setup_logger(__name__)


class ModelTrainer:
    """Handles ML model training and evaluation."""
    
    FEATURE_COLUMNS = [
        'z_rms_mm_s', 'x_rms_mm_s', 'z_peak_mm_s', 'x_peak_mm_s',
        'z_rms_g', 'x_rms_g', 'z_hf_rms_g', 'x_hf_rms_g',
        'z_kurtosis', 'x_kurtosis', 'z_crest_factor', 'x_crest_factor',
        'temp_c', 'frequency_hz',
        'band_total_rms', 'band_peak_rms', 'band_peak_freq_hz', 'band_peak_rpm'
    ]
    
    @staticmethod
    def prepare_features(samples: List[Dict]) -> tuple[pd.DataFrame, Optional[pd.Series]]:
        """
        Prepare feature matrix and labels from training samples.
        
        Args:
            samples: List of training sample dictionaries
            
        Returns:
            Tuple of (X_features, y_labels)
            
        Raises:
            TrainingError: If data preparation fails
        """
        try:
            if not samples:
                raise TrainingError("No training samples provided")
            
            # Convert to DataFrame
            df = pd.DataFrame(samples)
            
            # Select available features
            available_features = [col for col in ModelTrainer.FEATURE_COLUMNS if col in df.columns]
            
            if not available_features:
                raise TrainingError("No feature columns found in training data")
            
            # Extract features, filling missing values with 0
            X = df[available_features].fillna(0)
            
            # Handle labels if present
            y = None
            if 'label' in df.columns:
                y = df['label'].fillna('unknown')
                # Filter out unknown labels
                valid_mask = y != 'unknown'
                X = X[valid_mask]
                y = y[valid_mask]
            
            return X, y
        except TrainingError:
            raise
        except Exception as e:
            logger.error(f"Feature preparation error: {e}")
            raise TrainingError(f"Failed to prepare features: {e}")
    
    @staticmethod
    def train(
        samples: List[Dict],
        target_label_field: str = "label",
        algorithm: str = "baseline"
    ) -> Dict:
        """
        Train ML model on training samples.
        
        Args:
            samples: List of training samples
            target_label_field: Field to use as target
            algorithm: Algorithm to use ('baseline' for Random Forest)
            
        Returns:
            Dictionary with training results
            
        Raises:
            TrainingError: If training fails
        """
        try:
            # Validate inputs
            if len(samples) < Config.MIN_TRAINING_SAMPLES:
                raise TrainingError(
                    f"Need at least {Config.MIN_TRAINING_SAMPLES} samples, only have {len(samples)}"
                )
            
            # Prepare features and labels
            X, y = ModelTrainer.prepare_features(samples)
            
            if X.empty:
                raise TrainingError("No features available for training")
            
            if y is None:
                raise TrainingError("No labels found in training data for supervised learning")
            
            if len(y) < Config.MIN_TRAINING_SAMPLES:
                raise TrainingError(
                    f"Need at least {Config.MIN_TRAINING_SAMPLES} labeled samples, only have {len(y)}"
                )
            
            n_classes = len(y.unique())
            if n_classes < 2:
                raise TrainingError(f"Need at least 2 different classes, found {n_classes}")
            
            logger.info(f"Training on {len(X)} samples with {n_classes} classes")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=Config.TRAIN_TEST_SPLIT_RATIO,
                random_state=Config.MODEL_RANDOM_STATE,
                stratify=y
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Choose model based on algorithm
            if algorithm == "baseline":
                if n_classes < 10:
                    # Classification
                    model = RandomForestClassifier(
                        n_estimators=100,
                        random_state=Config.MODEL_RANDOM_STATE,
                        max_depth=10,
                        min_samples_split=5,
                        min_samples_leaf=2
                    )
                    model_type = "classification"
                else:
                    # Regression for continuous labels
                    model = RandomForestRegressor(
                        n_estimators=100,
                        random_state=Config.MODEL_RANDOM_STATE,
                        max_depth=10,
                        min_samples_split=5,
                        min_samples_leaf=2
                    )
                    model_type = "regression"
            else:
                raise TrainingError(f"Unsupported algorithm: {algorithm}")
            
            # Train model
            logger.info(f"Training {model_type} model...")
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            if model_type == "classification":
                y_pred = model.predict(X_test_scaled)
                metrics = {
                    "train_accuracy": float(accuracy_score(y_train, model.predict(X_train_scaled))),
                    "test_accuracy": float(accuracy_score(y_test, y_pred)),
                    "classification_report": classification_report(y_test, y_pred, output_dict=True)
                }
            else:
                y_pred = model.predict(X_test_scaled)
                metrics = {
                    "train_mse": float(mean_squared_error(y_train, model.predict(X_train_scaled))),
                    "test_mse": float(mean_squared_error(y_test, y_pred)),
                    "train_r2": float(r2_score(y_train, model.predict(X_train_scaled))),
                    "test_r2": float(r2_score(y_test, y_pred))
                }
            
            # Create label encoder for classification
            label_encoder = None
            if model_type == "classification":
                label_encoder = LabelEncoder()
                label_encoder.fit(y)
            
            # Save model and metadata
            model_data = {
                'model': model,
                'scaler': scaler,
                'feature_columns': X.columns.tolist(),
                'model_type': model_type,
                'label_encoder': label_encoder,
                'training_date': datetime.now(timezone.utc).isoformat()
            }
            
            # Save model
            Config.MODELS_DIR.mkdir(exist_ok=True)
            with open(Config.MODEL_PATH, 'wb') as f:
                pickle.dump(model_data, f)
            
            # Save model info
            model_info = {
                "algorithm": f"RandomForest{model_type.capitalize()}",
                "model_type": model_type,
                "n_samples": len(samples),
                "n_features": len(X.columns),
                "n_classes": n_classes if model_type == "classification" else None,
                "feature_columns": X.columns.tolist(),
                "metrics": metrics,
                "training_date": model_data['training_date']
            }
            
            with open(Config.MODEL_INFO_PATH, 'w') as f:
                json.dump(model_info, f, indent=2)
            
            logger.info(f"Model trained and saved successfully")
            
            return {
                "status": "ok",
                "algorithm": model_info["algorithm"],
                "model_type": model_type,
                "n_samples": model_info["n_samples"],
                "n_features": model_info["n_features"],
                "n_classes": model_info["n_classes"],
                "metrics": metrics
            }
        except TrainingError:
            raise
        except Exception as e:
            logger.error(f"Model training error: {e}")
            raise TrainingError(f"Training failed: {e}")


def load_model_info() -> Dict:
    """
    Load information about the trained model.
    
    Returns:
        Dictionary with model information
    """
    try:
        if not Config.MODEL_INFO_PATH.exists():
            return {"status": "no_model", "message": "No trained model found"}
        
        with open(Config.MODEL_INFO_PATH, 'r') as f:
            model_info = json.load(f)
        
        model_info["status"] = "loaded"
        return model_info
    except Exception as e:
        logger.error(f"Failed to load model info: {e}")
        return {"status": "error", "message": str(e)}


def load_trained_model() -> Optional[dict]:
    """
    Load the trained model from disk.
    
    Returns:
        Model data dictionary or None if model doesn't exist
    """
    try:
        if not Config.MODEL_PATH.exists():
            logger.warning("Trained model not found")
            return None
        
        with open(Config.MODEL_PATH, 'rb') as f:
            model_data = pickle.load(f)
        
        return model_data
    except Exception as e:
        logger.error(f"Failed to load trained model: {e}")
        return None
