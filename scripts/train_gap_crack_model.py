#!/usr/bin/env python3
"""
train_gap_crack_model.py - Train ML model from collected samples
================================================================

Standalone script to train a RandomForest classifier for vibration fault detection.
Uses CSV files created by collect_good_bad_track.py.

Usage:
    python scripts/train_gap_crack_model.py
    python scripts/train_gap_crack_model.py data/gandiva_samples_*.csv

Labels:
    good   -> 0 (normal)
    gap    -> 1 (expansion_gap)
    defect -> 2 (crack_or_defect)

Output:
    gandiva_vib_model.joblib (model file, same name used by web backend)
    gandiva_scaler.joblib (optional scaler for feature normalization)
"""

import os
import sys
import glob
import argparse
from datetime import datetime

import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler

# =============================================================================
# CONFIGURATION
# =============================================================================

# Feature columns (must match what collector saves)
# If sensor doesn't support band registers, these map to:
#   band_1x -> z_kurtosis
#   band_2x -> z_crest_factor  
#   band_3x -> z_rms_g
#   band_5x -> z_hf_rms_g
#   band_7x -> peak/rms ratio
FEATURE_COLUMNS = [
    "rms", "peak", "band_1x", "band_2x", 
    "band_3x", "band_5x", "band_7x", "temperature"
]

# Label mapping
LABEL_MAP = {
    "good": 0,
    "gap": 1,
    "defect": 2
}

LABEL_NAMES = {
    0: "normal",
    1: "expansion_gap",
    2: "crack_or_defect"
}

# Output files
MODEL_FILE = "gandiva_vib_model.joblib"
SCALER_FILE = "gandiva_scaler.joblib"


# =============================================================================
# TRAINING FUNCTIONS
# =============================================================================

def load_csv_files(file_patterns: list) -> pd.DataFrame:
    """Load and concatenate CSV files."""
    all_files = []
    for pattern in file_patterns:
        matched = glob.glob(pattern)
        all_files.extend(matched)
    
    if not all_files:
        raise ValueError(f"No CSV files found matching: {file_patterns}")
    
    print(f"\nLoading {len(all_files)} CSV file(s):")
    
    dfs = []
    for f in all_files:
        print(f"  - {f}")
        df = pd.read_csv(f)
        dfs.append(df)
    
    combined = pd.concat(dfs, ignore_index=True)
    print(f"\nTotal samples: {len(combined)}")
    
    return combined


def prepare_data(df: pd.DataFrame) -> tuple:
    """Prepare features and labels for training.

    If a 'train_state' column is present, we will:
        - Log how many samples are IDLE vs MOVING
        - Train the gap/crack classifier only on MOVING samples
            (idle data is kept in the CSV for future analysis / baseline models)
    """
    # Ensure required columns exist
    missing = [c for c in FEATURE_COLUMNS + ["label"] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in CSV: {missing}")
    
    # If train_state is present, drop idle samples for this classifier
    if "train_state" in df.columns:
        idle_mask = df["train_state"].astype(str).str.lower() == "idle"
        n_idle = int(idle_mask.sum())
        n_total = int(len(df))
        n_moving = n_total - n_idle
        print(f"\nTrain state breakdown: {n_idle} idle, {n_moving} moving, {n_total} total")
        if n_moving > 0:
            df = df.loc[~idle_mask].copy()
        else:
            print("⚠️ All samples are idle. Training on all samples anyway.")

    # Extract features
    X = df[FEATURE_COLUMNS].values
    
    # Map labels to integers
    y = df["label"].map(LABEL_MAP).values
    
    # Check for unmapped labels
    if np.any(np.isnan(y)):
        unknown = df.loc[pd.isna(df["label"].map(LABEL_MAP)), "label"].unique()
        raise ValueError(f"Unknown labels in data: {unknown}")
    
    y = y.astype(int)
    
    return X, y


def train_model(X: np.ndarray, y: np.ndarray, test_size: float = 0.2) -> dict:
    """Train a RandomForest classifier."""
    print(f"\n{'='*60}")
    print("  TRAINING MODEL")
    print(f"{'='*60}")
    
    # Print class distribution
    unique, counts = np.unique(y, return_counts=True)
    print("\nClass distribution:")
    for u, c in zip(unique, counts):
        name = LABEL_NAMES.get(u, f"class_{u}")
        print(f"  {name}: {c} samples ({100*c/len(y):.1f}%)")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    print(f"\nTrain set: {len(X_train)} samples")
    print(f"Test set:  {len(X_test)} samples")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train RandomForest
    print("\nTraining RandomForestClassifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test_scaled)
    accuracy = np.mean(y_pred == y_test)
    
    print(f"\n{'='*60}")
    print("  EVALUATION RESULTS")
    print(f"{'='*60}")
    print(f"\nAccuracy: {accuracy:.2%}")
    
    # Classification report
    target_names = [LABEL_NAMES[i] for i in sorted(LABEL_NAMES.keys()) if i in unique]
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=target_names))
    
    # Confusion matrix
    print("Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(cm)
    
    # Feature importance
    print("\nFeature Importance:")
    importance = dict(zip(FEATURE_COLUMNS, model.feature_importances_))
    for name, imp in sorted(importance.items(), key=lambda x: -x[1]):
        print(f"  {name}: {imp:.4f}")
    
    return {
        "model": model,
        "scaler": scaler,
        "accuracy": accuracy,
        "feature_importance": importance
    }


def save_model(model, scaler, output_dir: str = "."):
    """Save model and scaler to disk."""
    model_path = os.path.join(output_dir, MODEL_FILE)
    scaler_path = os.path.join(output_dir, SCALER_FILE)
    
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    
    print(f"\n{'='*60}")
    print("  MODEL SAVED")
    print(f"{'='*60}")
    print(f"\n  Model:  {model_path}")
    print(f"  Scaler: {scaler_path}")
    print(f"\n  The web backend will automatically load these files.")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Train vibration fault detection model from CSV samples"
    )
    parser.add_argument(
        "csv_files",
        nargs="*",
        default=["data/gandiva_samples_*.csv"],
        help="CSV file(s) or glob patterns (default: data/gandiva_samples_*.csv)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=".",
        help="Directory to save model files (default: current directory)"
    )
    parser.add_argument(
        "--test-size", "-t",
        type=float,
        default=0.2,
        help="Fraction of data for testing (default: 0.2)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("  GANDIVA - Model Training Script")
    print("=" * 60)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Load data
        df = load_csv_files(args.csv_files)
        
        # Prepare features and labels
        X, y = prepare_data(df)
        
        # Train model
        result = train_model(X, y, test_size=args.test_size)
        
        # Save model
        save_model(result["model"], result["scaler"], args.output_dir)
        
        print("\n  ✓ Training complete!")
        print("\n  Next steps:")
        print("    1. Restart the web backend to load the new model")
        print("    2. Or run: python -m uvicorn main:app --reload")
        print()
        
    except Exception as e:
        print(f"\n  ✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
