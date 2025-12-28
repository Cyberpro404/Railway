#!/usr/bin/env python3
"""
Project Gandiva - Generate Sample Training Data

This script generates synthetic vibration data for testing the ML pipeline.
In production, replace this with real sensor data collection.

Usage:
    python generate_sample_data.py
    python generate_sample_data.py --samples 5000
"""

import numpy as np
import argparse
from pathlib import Path

# Feature names for reference
FEATURE_NAMES = [
    "rms", "peak", "band_1x", "band_2x", 
    "band_3x", "band_5x", "band_7x", "temperature"
]

# Class definitions
CLASS_LABELS = {
    0: "normal",
    1: "misalignment", 
    2: "unbalance",
    3: "looseness",
    4: "crack"
}

# Characteristic patterns for each fault type (mean values)
# These are simplified patterns - real data would have more complex signatures
FAULT_SIGNATURES = {
    0: {  # Normal
        "rms": (1.5, 0.3),      # (mean, std)
        "peak": (4.0, 0.8),
        "band_1x": (0.8, 0.2),
        "band_2x": (0.3, 0.1),
        "band_3x": (0.2, 0.05),
        "band_5x": (0.1, 0.03),
        "band_7x": (0.05, 0.02),
        "temperature": (40.0, 3.0)
    },
    1: {  # Misalignment - high 2x component
        "rms": (3.5, 0.5),
        "peak": (10.0, 1.5),
        "band_1x": (1.5, 0.3),
        "band_2x": (2.5, 0.4),  # High 2x is characteristic
        "band_3x": (0.8, 0.2),
        "band_5x": (0.3, 0.1),
        "band_7x": (0.1, 0.05),
        "temperature": (48.0, 4.0)
    },
    2: {  # Unbalance - high 1x component
        "rms": (4.0, 0.6),
        "peak": (12.0, 2.0),
        "band_1x": (3.5, 0.5),  # High 1x is characteristic
        "band_2x": (0.5, 0.15),
        "band_3x": (0.3, 0.1),
        "band_5x": (0.15, 0.05),
        "band_7x": (0.08, 0.03),
        "temperature": (45.0, 3.5)
    },
    3: {  # Looseness - multiple harmonics, broadband
        "rms": (5.0, 0.8),
        "peak": (15.0, 2.5),
        "band_1x": (2.0, 0.4),
        "band_2x": (1.8, 0.35),
        "band_3x": (1.5, 0.3),  # Multiple harmonics elevated
        "band_5x": (1.0, 0.25),
        "band_7x": (0.6, 0.15),
        "temperature": (52.0, 5.0)
    },
    4: {  # Crack - irregular patterns, high frequency
        "rms": (6.0, 1.0),
        "peak": (18.0, 3.0),
        "band_1x": (2.5, 0.5),
        "band_2x": (1.2, 0.3),
        "band_3x": (1.8, 0.4),
        "band_5x": (1.5, 0.35),  # High frequency elevated
        "band_7x": (1.2, 0.3),   # High frequency elevated
        "temperature": (55.0, 6.0)
    }
}


def generate_samples(n_samples_per_class: int, random_state: int = 42) -> tuple:
    """
    Generate synthetic vibration samples for each fault class.
    
    Args:
        n_samples_per_class: Number of samples to generate per class
        random_state: Random seed for reproducibility
    
    Returns:
        tuple: (X, y) feature matrix and label vector
    """
    np.random.seed(random_state)
    
    X_list = []
    y_list = []
    
    for class_idx, signatures in FAULT_SIGNATURES.items():
        for _ in range(n_samples_per_class):
            sample = []
            for feature in FEATURE_NAMES:
                mean, std = signatures[feature]
                # Generate value with some noise
                value = np.random.normal(mean, std)
                # Ensure non-negative (except temperature)
                if feature != "temperature":
                    value = max(0.01, value)
                sample.append(value)
            
            X_list.append(sample)
            y_list.append(class_idx)
    
    X = np.array(X_list)
    y = np.array(y_list)
    
    # Shuffle data
    indices = np.random.permutation(len(y))
    X = X[indices]
    y = y[indices]
    
    return X, y


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic vibration data for Project Gandiva"
    )
    parser.add_argument(
        "--samples", 
        type=int, 
        default=200,
        help="Number of samples per class (default: 200)"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="vibration_features.npy",
        help="Output file path (default: vibration_features.npy)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)"
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("Project Gandiva - Sample Data Generator")
    print("="*60 + "\n")
    
    # Generate data
    X, y = generate_samples(args.samples, args.seed)
    
    total_samples = len(y)
    print(f"Generated {total_samples} total samples ({args.samples} per class)\n")
    
    # Show class distribution
    print("Class distribution:")
    for cls_idx, cls_name in CLASS_LABELS.items():
        count = np.sum(y == cls_idx)
        print(f"  {cls_idx} ({cls_name}): {count} samples")
    
    # Show feature statistics
    print("\nFeature statistics:")
    for i, name in enumerate(FEATURE_NAMES):
        print(f"  {name}: min={X[:, i].min():.2f}, max={X[:, i].max():.2f}, "
              f"mean={X[:, i].mean():.2f}, std={X[:, i].std():.2f}")
    
    # Save data
    data = {'X': X, 'y': y}
    np.save(args.output, data)
    
    print(f"\n✓ Saved to '{args.output}'")
    print(f"\nNext step: Run 'python train_model.py' to train the model")


if __name__ == "__main__":
    main()
