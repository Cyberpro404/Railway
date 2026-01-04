# Manual Training Workflow

## Overview

These scripts let you train the vibration fault detection model without using the web UI.

```
collect_good_bad_track.py  →  CSV files  →  train_gap_crack_model.py  →  .joblib model
```

---

## Step 1: Collect Training Data

Run the collector while the sensor is connected:

```bash
cd "c:\Users\athar\Desktop\VS Code\Rail 2"
python scripts/collect_good_bad_track.py
```

### Interactive Menu

```
========================================
  GANDIVA - Training Data Collector
========================================

Commands:
  [1] Label next sample: GOOD
  [2] Label next sample: GAP (expansion gap)
  [3] Label next sample: DEFECT (crack/damage)
  [4] Pause collection
  [5] Save & exit
  [6] Discard & exit
```

### Workflow

1. Position cart on **good track** → Press `1` repeatedly (collect 50-100 samples)
2. Move to a **known gap** → Press `2` while crossing it (20-50 samples)
3. Move to a **known defect** → Press `3` while over it (20-50 samples)
4. Press `5` to save → Creates `data/gandiva_samples_YYYYMMDD_HHMMSS.csv`

### Tips

- Collect at least **30 samples per class** for reasonable accuracy
- Re-run on different days or track sections for variety
- You can merge multiple CSV files during training

---

## Step 2: Train the Model

After collecting samples:

```bash
python scripts/train_gap_crack_model.py
```

### Options

```bash
# Train from all CSV files in data/
python scripts/train_gap_crack_model.py

# Train from specific files
python scripts/train_gap_crack_model.py data/session1.csv data/session2.csv

# Use glob patterns
python scripts/train_gap_crack_model.py data/gandiva_samples_*.csv

# Specify output directory
python scripts/train_gap_crack_model.py -o models/
```

### Output

```
==================================================
  EVALUATION RESULTS
==================================================

Accuracy: 94.12%

Classification Report:
              precision    recall  f1-score   support

      normal       0.95      0.97      0.96        30
 expansion_gap     0.92      0.88      0.90        17
crack_or_defect   0.93      0.93      0.93        15

Feature Importance:
  rms: 0.2341
  band_1x: 0.1892
  ...

==================================================
  MODEL SAVED
==================================================

  Model:  gandiva_vib_model.joblib
  Scaler: gandiva_scaler.joblib
```

---

## Step 3: Deploy the Model

### A) Copy Model Files

After training, ensure these files are in the **project root** (same folder as `main.py`):

```
Rail 2/
├── main.py
├── gandiva_vib_model.joblib   ← Model file
├── gandiva_scaler.joblib      ← Scaler file (optional)
└── ...
```

### B) Restart FastAPI

```bash
python -m uvicorn main:app --reload
```

Watch for these startup messages:

```
✓ Loaded ML model from 'gandiva_vib_model.joblib'
✓ Loaded feature scaler from 'gandiva_scaler.joblib'
```

### C) Verify via `/ml_status`

Open in browser or Postman:

```
http://localhost:8000/ml_status
```

Expected response:

```json
{
  "model_loaded": true,
  "scaler_loaded": true,
  "model_path": "gandiva_vib_model.joblib",
  "scaler_path": "gandiva_scaler.joblib",
  "classes": ["normal", "expansion_gap", "crack"]
}
```

If `model_loaded` is `false`, check:
- Is `gandiva_vib_model.joblib` in the project root?
- Any error messages in the terminal?

---

## Step 4: Check Dashboard Alerts

1. Open the dashboard: `http://localhost:8000/`
2. Go to the **Overview** tab
3. Look for:
   - **ML Prediction KPI** tile showing "NORMAL", "GAP", or "CRACK"
   - **Alert banner** at the top of the page (green/blue/red)

### Alert Colors

| Prediction | Banner Color | Meaning |
|------------|--------------|---------|
| NORMAL     | 🟢 Green     | Good track - all clear |
| GAP        | 🔵 Blue      | Expansion gap detected - no action needed |
| CRACK      | 🔴 Red       | Crack/defect - inspect immediately! |

---

## Step 5: Debug Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /ml_status` | Check if model is loaded |
| `GET /api/latest` | Latest reading with `ml_prediction` field |
| `GET /api/live_sample` | Combined sensor + ML data for UI polling |
| `GET /model/status` | Detailed model info |

### Example `/api/latest` Response

```json
{
  "ok": true,
  "timestamp": "2025-01-15T10:30:45Z",
  "z_rms_mm_s": 1.23,
  "temp_c": 25.5,
  "ml_prediction": {
    "label": "normal",
    "class_index": 0,
    "confidence": 0.92,
    "probabilities": [0.92, 0.05, 0.03]
  }
}
```

---

## Troubleshooting

### "Model not loaded" in dashboard

1. Check `/ml_status` - is `model_loaded: true`?
2. Ensure `gandiva_vib_model.joblib` is in project root
3. Restart the backend: `python -m uvicorn main:app --reload`

### "No communication with the instrument"

- Check USB/RS-485 cable connection
- Verify correct COM port in Connection tab
- Ensure sensor is powered on

### Alert banner not changing

1. Verify ML is working via `/ml_status`
2. Check browser console (F12) for errors
3. Ensure you're on the Overview tab
4. The banner updates every 1 second when sensor is active

### Low prediction accuracy

- Collect more samples (aim for 100+ per class)
- Ensure labels are accurate (gap readings during actual gaps)
- Try collecting on different track sections for variety
