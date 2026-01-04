#!/usr/bin/env python3
"""
Project Gandiva - Railway Vibration Fault Detection
Model Training Script

This script trains a RandomForestClassifier on vibration feature data
and saves the trained model for use by the FastAPI prediction endpoint.

Features (8 total):
    - rms: Root Mean Square of vibration signal
    - peak: Peak amplitude
    - band_1x, band_2x, band_3x, band_5x, band_7x: Frequency band energies
    - temperature: Sensor temperature

Output Classes:
    0 = normal
    1 = misalignment
    2 = unbalance
    3 = looseness
    4 = crack
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import os
from pathlib import Path

# === Configuration ===
DATA_FILE = "vibration_features.npy"
MODEL_FILE = "gandiva_vib_model.joblib"
TEST_SIZE = 0.2
RANDOM_STATE = 42
N_ESTIMATORS = 100

# Class label mapping
CLASS_LABELS = {
    0: "normal",
    1: "misalignment",
    2: "unbalance",
    3: "looseness",
    4: "crack"
}

FEATURE_NAMES = [
    "rms", "peak", "band_1x", "band_2x", 
    "band_3x", "band_5x", "band_7x", "temperature"
]


def load_data(filepath: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Load vibration feature data from .npy file.
    
    Expected format: Dictionary with keys 'X' and 'y'
    - X: numpy array of shape (n_samples, 8) containing features
    - y: numpy array of shape (n_samples,) containing class labels (0-4)
    
    Returns:
        tuple: (X, y) feature matrix and label vector
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Data file '{filepath}' not found.\n"
            f"Please create it with X (n_samples, 8) and y (n_samples,) arrays.\n"
            f"Example:\n"
            f"  data = {{'X': X_array, 'y': y_array}}\n"
            f"  np.save('{filepath}', data)"
        )
    
    data = np.load(filepath, allow_pickle=True).item()
    
    if not isinstance(data, dict) or 'X' not in data or 'y' not in data:
        raise ValueError(
            "Data file must contain a dictionary with 'X' and 'y' keys.\n"
            f"Got keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
        )
    
    X = np.array(data['X'])
    y = np.array(data['y'])
    
    if X.shape[1] != 8:
        raise ValueError(
            f"Expected 8 features, got {X.shape[1]}.\n"
            f"Features should be: {FEATURE_NAMES}"
        )
    
    print(f"✓ Loaded {X.shape[0]} samples with {X.shape[1]} features")
    print(f"  Class distribution:")
    for cls_idx, cls_name in CLASS_LABELS.items():
        count = np.sum(y == cls_idx)
        print(f"    {cls_idx} ({cls_name}): {count} samples")
    
    return X, y


def train_model(X: np.ndarray, y: np.ndarray) -> RandomForestClassifier:
    """
    Train a RandomForestClassifier on the vibration data.
    
    Args:
        X: Feature matrix of shape (n_samples, 8)
        y: Label vector of shape (n_samples,)
    
    Returns:
        Trained RandomForestClassifier model
    """
    # Split data for evaluation
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, 
        test_size=TEST_SIZE, 
        random_state=RANDOM_STATE,
        stratify=y
    )
    
    print(f"\n✓ Split data: {len(X_train)} train, {len(X_test)} test samples")
    
    # Initialize and train the model
    model = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        random_state=RANDOM_STATE,
        n_jobs=-1,  # Use all CPU cores
        class_weight='balanced'  # Handle imbalanced classes
    )
    
    print(f"\n⏳ Training RandomForestClassifier with {N_ESTIMATORS} trees...")
    model.fit(X_train, y_train)
    print("✓ Training complete!")
    
    # Evaluate on test set
    y_pred = model.predict(X_test)
    
    print("\n" + "="*60)
    print("CLASSIFICATION REPORT")
    print("="*60)
    
    target_names = [f"{i}-{CLASS_LABELS[i]}" for i in range(5)]
    report = classification_report(y_test, y_pred, target_names=target_names)
    print(report)
    
    print("\n" + "="*60)
    print("CONFUSION MATRIX")
    print("="*60)
    cm = confusion_matrix(y_test, y_pred)
    print(cm)
    
    # Feature importance
    print("\n" + "="*60)
    print("FEATURE IMPORTANCE")
    print("="*60)
    importances = model.feature_importances_
    for name, importance in sorted(zip(FEATURE_NAMES, importances), 
                                    key=lambda x: x[1], reverse=True):
        print(f"  {name}: {importance:.4f}")
    
    return model


def save_model(model: RandomForestClassifier, filepath: str) -> None:
    """Save trained model to disk using joblib."""
    joblib.dump(model, filepath)
    file_size = os.path.getsize(filepath) / (1024 * 1024)  # MB
    print(f"\n✓ Model saved to '{filepath}' ({file_size:.2f} MB)")


def main():
    """Main training pipeline."""
    print("="*60)
    print("PROJECT GANDIVA - Railway Vibration Fault Detection")
    print("Model Training Script")
    print("="*60 + "\n")
    
    # Load data
    X, y = load_data(DATA_FILE)
    
    # Train model
    model = train_model(X, y)
    
    # Save model
    save_model(model, MODEL_FILE)
    
    print("\n" + "="*60)
    print("✅ TRAINING COMPLETE")
    print("="*60)
    print(f"\nNext steps:")
    print(f"  1. Start FastAPI server: uvicorn main:app --reload")
    print(f"  2. Send predictions to: POST /predict")
    print(f"  3. To retrain: update {DATA_FILE} and re-run this script")


if __name__ == "__main__":
    main()
