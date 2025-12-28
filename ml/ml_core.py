"""
Project Gandiva - ML Core Module
================================

This module handles machine learning operations:
- Training data collection (sampling mode)
- Model training (RandomForestClassifier)
- Real-time prediction

Labels:
    0: normal        - No fault, normal operation
    1: expansion_gap - Intentional gap (no alarm needed)
    2: crack         - Real fault (raise alert!)
    3: other_fault   - Unknown/other fault type
"""

import os
import json
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from pathlib import Path

import numpy as np
import joblib

# ML imports
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler

# Configure logging
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# File paths
MODEL_FILE = "gandiva_vib_model.joblib"
SCALER_FILE = "gandiva_scaler.joblib"
TRAINING_DATA_FILE = "training_data.json"

# Feature configuration
FEATURE_NAMES = [
    "rms", "peak", "band_1x", "band_2x", 
    "band_3x", "band_5x", "band_7x", "temperature"
]
N_FEATURES = len(FEATURE_NAMES)

# Label mapping
LABEL_MAP = {
    0: "normal",
    1: "expansion_gap",
    2: "crack",
    3: "other_fault"
}

LABEL_REVERSE_MAP = {v: k for k, v in LABEL_MAP.items()}

# Label descriptions for UI
LABEL_INFO = {
    "normal": {
        "display": "NORMAL",
        "message": "No issues detected",
        "severity": "ok",
        "color": "green",
        "action": None
    },
    "expansion_gap": {
        "display": "EXPANSION GAP",
        "message": "Intentional gap - no action needed",
        "severity": "info",
        "color": "blue",
        "action": None
    },
    "crack": {
        "display": "CRACK DETECTED",
        "message": "Potential crack - inspect immediately!",
        "severity": "critical",
        "color": "red",
        "action": "inspect"
    },
    "other_fault": {
        "display": "FAULT DETECTED",
        "message": "Unknown fault type - investigate",
        "severity": "warning",
        "color": "orange",
        "action": "investigate"
    }
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SamplingStatus:
    """Status of data sampling mode."""
    active: bool = False
    label: Optional[str] = None
    label_index: Optional[int] = None
    start_time: Optional[float] = None
    sample_count: int = 0
    

@dataclass
class TrainingData:
    """Container for training samples."""
    samples: Dict[str, List[List[float]]] = field(default_factory=dict)
    timestamps: Dict[str, List[float]] = field(default_factory=dict)
    
    def __post_init__(self):
        # Initialize empty lists for each label
        for label in LABEL_MAP.values():
            if label not in self.samples:
                self.samples[label] = []
            if label not in self.timestamps:
                self.timestamps[label] = []
    
    def add_sample(self, label: str, features: List[float]) -> None:
        """Add a sample with the given label."""
        if label not in self.samples:
            self.samples[label] = []
            self.timestamps[label] = []
        self.samples[label].append(features)
        self.timestamps[label].append(time.time())
    
    def get_counts(self) -> Dict[str, int]:
        """Get sample counts per label."""
        return {label: len(samples) for label, samples in self.samples.items()}
    
    def total_samples(self) -> int:
        """Get total sample count."""
        return sum(len(s) for s in self.samples.values())
    
    def to_arrays(self) -> Tuple[np.ndarray, np.ndarray]:
        """Convert to X, y arrays for training."""
        X_list = []
        y_list = []
        
        for label, samples in self.samples.items():
            label_idx = LABEL_REVERSE_MAP.get(label, 3)
            for sample in samples:
                X_list.append(sample)
                y_list.append(label_idx)
        
        if not X_list:
            return np.array([]).reshape(0, N_FEATURES), np.array([])
        
        return np.array(X_list), np.array(y_list)
    
    def save(self, filepath: str) -> None:
        """Save training data to JSON file."""
        data = {
            "samples": self.samples,
            "timestamps": self.timestamps,
            "saved_at": datetime.now().isoformat()
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Training data saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> 'TrainingData':
        """Load training data from JSON file."""
        if not os.path.exists(filepath):
            return cls()
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            td = cls()
            td.samples = data.get("samples", {})
            td.timestamps = data.get("timestamps", {})
            
            # Ensure all labels exist
            for label in LABEL_MAP.values():
                if label not in td.samples:
                    td.samples[label] = []
                if label not in td.timestamps:
                    td.timestamps[label] = []
            
            logger.info(f"Loaded training data from {filepath}: {td.get_counts()}")
            return td
            
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return cls()


@dataclass
class PredictionResult:
    """Result of a model prediction."""
    label_index: int
    label: str
    probabilities: List[float]
    confidence: float
    info: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON."""
        # Build probabilities dict safely - handle models trained with different class counts
        prob_dict = {}
        for i, p in enumerate(self.probabilities):
            if i in LABEL_MAP:
                prob_dict[LABEL_MAP[i]] = round(p, 4)
            else:
                # Handle unknown class indices (e.g., from old models)
                prob_dict[f"class_{i}"] = round(p, 4)
        
        return {
            "label_index": self.label_index,
            "label": self.label,
            "probabilities": prob_dict,
            "confidence": round(self.confidence, 4),
            "display": self.info["display"],
            "message": self.info["message"],
            "severity": self.info["severity"],
            "color": self.info["color"],
            "action": self.info["action"]
        }


# =============================================================================
# ML CORE CLASS
# =============================================================================

class MLCore:
    """
    Core ML functionality for Project Gandiva.
    
    Handles:
    - Data collection (sampling mode)
    - Model training
    - Real-time prediction
    """
    
    def __init__(self, model_path: str = MODEL_FILE, 
                 scaler_path: str = SCALER_FILE,
                 data_path: str = TRAINING_DATA_FILE):
        """Initialize ML core."""
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.data_path = data_path
        
        # Model and scaler
        self.model: Optional[RandomForestClassifier] = None
        self.scaler: Optional[StandardScaler] = None
        self.model_loaded = False
        
        # Sampling state
        self._sampling = SamplingStatus()
        self._training_data = TrainingData.load(data_path)
        self._lock = threading.Lock()
        
        # Try to load existing model
        self.load_model()
    
    # -------------------------------------------------------------------------
    # SAMPLING MODE
    # -------------------------------------------------------------------------
    
    def start_sampling(self, label: str) -> Dict[str, Any]:
        """
        Start data collection mode for a specific label.
        
        Args:
            label: One of "normal", "expansion_gap", "crack", "other_fault"
            
        Returns:
            Status dictionary
        """
        if label not in LABEL_REVERSE_MAP:
            return {
                "success": False,
                "error": f"Invalid label: {label}. Must be one of: {list(LABEL_REVERSE_MAP.keys())}"
            }
        
        with self._lock:
            self._sampling.active = True
            self._sampling.label = label
            self._sampling.label_index = LABEL_REVERSE_MAP[label]
            self._sampling.start_time = time.time()
            self._sampling.sample_count = 0
        
        logger.info(f"Started sampling for label: {label}")
        
        return {
            "success": True,
            "message": f"Sampling started for '{label}'",
            "label": label,
            "label_index": self._sampling.label_index
        }
    
    def stop_sampling(self) -> Dict[str, Any]:
        """
        Stop data collection mode.
        
        Returns:
            Status dictionary with samples collected
        """
        with self._lock:
            if not self._sampling.active:
                return {
                    "success": False,
                    "error": "Sampling was not active"
                }
            
            label = self._sampling.label
            count = self._sampling.sample_count
            duration = time.time() - self._sampling.start_time if self._sampling.start_time else 0
            
            self._sampling.active = False
            self._sampling.label = None
            self._sampling.label_index = None
            self._sampling.start_time = None
            
            # Save training data
            self._training_data.save(self.data_path)
        
        logger.info(f"Stopped sampling. Collected {count} samples for '{label}'")
        
        return {
            "success": True,
            "message": f"Sampling stopped",
            "label": label,
            "samples_collected": count,
            "duration_seconds": round(duration, 1),
            "total_samples": self._training_data.get_counts()
        }
    
    def add_sample(self, features: List[float]) -> bool:
        """
        Add a sample if sampling is active.
        
        Args:
            features: List of 8 feature values
            
        Returns:
            True if sample was added, False otherwise
        """
        with self._lock:
            if not self._sampling.active or self._sampling.label is None:
                return False
            
            if len(features) != N_FEATURES:
                logger.warning(f"Invalid feature count: {len(features)}, expected {N_FEATURES}")
                return False
            
            self._training_data.add_sample(self._sampling.label, features)
            self._sampling.sample_count += 1
            
            return True
    
    def get_sampling_status(self) -> Dict[str, Any]:
        """
        Get current sampling status.
        
        Returns:
            Dictionary with sampling state information
        """
        with self._lock:
            return {
                "active": self._sampling.active,
                "label": self._sampling.label,
                "label_index": self._sampling.label_index,
                "samples_this_session": self._sampling.sample_count,
                "duration_seconds": round(time.time() - self._sampling.start_time, 1) 
                                   if self._sampling.start_time else 0,
                "total_samples": self._training_data.get_counts(),
                "total_count": self._training_data.total_samples()
            }
    
    def clear_training_data(self, label: Optional[str] = None) -> Dict[str, Any]:
        """
        Clear training data.
        
        Args:
            label: If specified, clear only that label's data. Otherwise clear all.
            
        Returns:
            Status dictionary
        """
        with self._lock:
            if label:
                if label in self._training_data.samples:
                    count = len(self._training_data.samples[label])
                    self._training_data.samples[label] = []
                    self._training_data.timestamps[label] = []
                    self._training_data.save(self.data_path)
                    return {"success": True, "cleared": label, "count": count}
                else:
                    return {"success": False, "error": f"Unknown label: {label}"}
            else:
                self._training_data = TrainingData()
                self._training_data.save(self.data_path)
                return {"success": True, "cleared": "all"}
    
    # -------------------------------------------------------------------------
    # MODEL TRAINING
    # -------------------------------------------------------------------------
    
    def train_model(self, test_size: float = 0.2) -> Dict[str, Any]:
        """
        Train RandomForestClassifier on collected data.
        
        Args:
            test_size: Fraction of data to use for testing
            
        Returns:
            Training results dictionary
        """
        logger.info("Starting model training...")
        
        # Get training data
        X, y = self._training_data.to_arrays()
        
        if len(X) < 10:
            return {
                "success": False,
                "error": f"Insufficient training data. Have {len(X)} samples, need at least 10.",
                "sample_counts": self._training_data.get_counts()
            }
        
        # Check class distribution
        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            return {
                "success": False,
                "error": f"Need at least 2 classes for training. Have classes: {unique_classes.tolist()}",
                "sample_counts": self._training_data.get_counts()
            }
        
        try:
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )
            
            # Scale features
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1,
                class_weight='balanced'
            )
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test_scaled)
            accuracy = (y_pred == y_test).mean()
            
            # Classification report
            target_names = [f"{i}-{LABEL_MAP[i]}" for i in sorted(unique_classes)]
            report = classification_report(y_test, y_pred, target_names=target_names, 
                                          output_dict=True, zero_division=0)
            
            # Feature importance
            importances = dict(zip(FEATURE_NAMES, self.model.feature_importances_.tolist()))
            
            # Save model and scaler
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            
            self.model_loaded = True
            
            logger.info(f"Model trained successfully. Accuracy: {accuracy:.2%}")
            
            return {
                "success": True,
                "message": "Model trained and saved successfully",
                "accuracy": round(accuracy, 4),
                "train_samples": len(X_train),
                "test_samples": len(X_test),
                "classes": [LABEL_MAP[c] for c in sorted(unique_classes)],
                "feature_importance": {k: round(v, 4) for k, v in 
                                      sorted(importances.items(), key=lambda x: -x[1])},
                "classification_report": report,
                "model_file": self.model_path
            }
            
        except Exception as e:
            logger.exception(f"Training failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # -------------------------------------------------------------------------
    # MODEL LOADING
    # -------------------------------------------------------------------------
    
    def load_model(self) -> bool:
        """
        Load trained model from disk.
        
        Returns:
            True if model loaded successfully
        """
        if not os.path.exists(self.model_path):
            logger.warning(f"Model file not found: {self.model_path}")
            self.model_loaded = False
            return False
        
        try:
            self.model = joblib.load(self.model_path)
            
            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
            else:
                self.scaler = None
                logger.warning("Scaler not found, predictions may be less accurate")
            
            self.model_loaded = True
            logger.info(f"Model loaded from {self.model_path}")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to load model: {e}")
            self.model = None
            self.scaler = None
            self.model_loaded = False
            return False
    
    # -------------------------------------------------------------------------
    # PREDICTION
    # -------------------------------------------------------------------------
    
    def predict(self, features: List[float]) -> Optional[PredictionResult]:
        """
        Predict fault type from features.
        
        Args:
            features: List of 8 feature values [rms, peak, band_1x, ...]
            
        Returns:
            PredictionResult or None if model not loaded
        """
        if not self.model_loaded or self.model is None:
            return None
        
        if len(features) != N_FEATURES:
            logger.error(f"Invalid feature count: {len(features)}, expected {N_FEATURES}")
            return None
        
        try:
            # Prepare features
            X = np.array(features).reshape(1, -1)
            
            # Scale if scaler available
            if self.scaler is not None:
                X = self.scaler.transform(X)
            
            # Predict
            label_idx = int(self.model.predict(X)[0])
            probabilities = self.model.predict_proba(X)[0].tolist()
            
            # Get the model's actual classes (in case it was trained with different labels)
            model_classes = list(self.model.classes_)
            
            # Map the predicted class index to our label system
            # The model.predict() returns the actual class label, not the index into probabilities
            # So label_idx is the actual class number (e.g., 0, 1, 2, 3, 4)
            
            # Get the label string - handle models trained with different class sets
            if label_idx in LABEL_MAP:
                label = LABEL_MAP[label_idx]
            elif label_idx == 4:
                # Old model compatibility: class 4 was sometimes "crack" or another fault
                label = "other_fault"
            else:
                label = "other_fault"
            
            confidence = max(probabilities) if probabilities else 0.0
            info = LABEL_INFO.get(label, LABEL_INFO["other_fault"])
            
            return PredictionResult(
                label_index=label_idx,
                label=label,
                probabilities=probabilities,
                confidence=confidence,
                info=info
            )
            
        except Exception as e:
            logger.exception(f"Prediction failed: {e}")
            return None
    
    # -------------------------------------------------------------------------
    # STATUS
    # -------------------------------------------------------------------------
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get overall ML core status.
        
        Returns:
            Status dictionary
        """
        return {
            "model_loaded": self.model_loaded,
            "model_file": self.model_path,
            "model_exists": os.path.exists(self.model_path),
            "sampling": self.get_sampling_status(),
            "labels": LABEL_MAP,
            "label_info": LABEL_INFO,
            "feature_names": FEATURE_NAMES
        }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

# Singleton instance
_ml_core: Optional[MLCore] = None


def get_ml_core() -> MLCore:
    """Get or create the global MLCore instance."""
    global _ml_core
    if _ml_core is None:
        _ml_core = MLCore()
    return _ml_core


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def start_sampling(label: str) -> Dict[str, Any]:
    """Start sampling mode for a label."""
    return get_ml_core().start_sampling(label)


def stop_sampling() -> Dict[str, Any]:
    """Stop sampling mode."""
    return get_ml_core().stop_sampling()


def get_sampling_status() -> Dict[str, Any]:
    """Get sampling status."""
    return get_ml_core().get_sampling_status()


def train_model() -> Dict[str, Any]:
    """Train the model."""
    return get_ml_core().train_model()


def load_model() -> bool:
    """Load the model."""
    return get_ml_core().load_model()


def predict(features: List[float]) -> Optional[PredictionResult]:
    """Make a prediction."""
    return get_ml_core().predict(features)


def get_status() -> Dict[str, Any]:
    """Get ML core status."""
    return get_ml_core().get_status()


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("Testing MLCore...")
    
    ml = MLCore(
        model_path="test_model.joblib",
        scaler_path="test_scaler.joblib",
        data_path="test_training_data.json"
    )
    
    # Test sampling
    print("\n=== Testing Sampling ===")
    print(ml.start_sampling("normal"))
    
    # Add some fake samples
    import numpy as np
    for _ in range(50):
        features = np.random.randn(8).tolist()
        features = [abs(f) for f in features]  # Make positive
        ml.add_sample(features)
    
    print(ml.get_sampling_status())
    print(ml.stop_sampling())
    
    # Add samples for other classes
    for label in ["expansion_gap", "crack"]:
        ml.start_sampling(label)
        for _ in range(50):
            features = np.random.randn(8).tolist()
            features = [abs(f) + (1 if label == "crack" else 0.5) for f in features]
            ml.add_sample(features)
        ml.stop_sampling()
    
    # Train
    print("\n=== Testing Training ===")
    result = ml.train_model()
    print(f"Training result: {result['success']}, Accuracy: {result.get('accuracy', 'N/A')}")
    
    # Predict
    print("\n=== Testing Prediction ===")
    test_features = [1.5, 4.0, 0.8, 0.3, 0.2, 0.1, 0.05, 42.0]
    pred = ml.predict(test_features)
    if pred:
        print(f"Prediction: {pred.label} (confidence: {pred.confidence:.2%})")
        print(f"Info: {pred.info}")
    
    # Cleanup test files
    import os
    for f in ["test_model.joblib", "test_scaler.joblib", "test_training_data.json"]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\nTest complete!")
