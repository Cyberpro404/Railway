# 🚂 Gandiva - How to Run

## Quick Start (3 Steps)

### Step 1: Install Backend Dependencies
```bash
pip install fastapi uvicorn joblib numpy scikit-learn
```

### Step 2: Start Backend Server
```bash
cd "c:\Users\athar\Desktop\VS Code\Rail 2"
uvicorn main:app --reload --port 8000
```

You should see:
```
✅ MODEL LOADED: gandiva_vib_model.joblib
✅ SCALER LOADED: gandiva_scaler.joblib
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 3: Open Frontend
Simply open this file in your browser:
```
c:\Users\athar\Desktop\VS Code\Rail 2\frontend\index.html
```

Or double-click the file in Explorer.

---

## Testing the System

### Check Backend is Running
Open in browser: http://localhost:8000

You should see:
```json
{"message": "Gandiva Backend is running!", "status": "ok"}
```

### Check Model Status
Open in browser: http://localhost:8000/ml_status

You should see:
```json
{
  "model_loaded": true,
  "model_path": "gandiva_vib_model.joblib",
  "scaler_loaded": true,
  "scaler_path": "gandiva_scaler.joblib"
}
```

### Check Live Data
Open in browser: http://localhost:8000/live_sample

You should see sensor data + ML prediction:
```json
{
  "ok": true,
  "features": {
    "rms": 0.351,
    "peak": 0.812,
    "temperature": 32.5,
    ...
  },
  "ml": {
    "ml_ready": true,
    "prediction": "normal",
    "confidence": 0.95,
    ...
  }
}
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│                  (frontend/index.html)                      │
│                                                             │
│   • Opens in browser                                        │
│   • Calls backend every 1 second                           │
│   • Shows graphs and colored alerts                        │
│   • Does NOT touch sensor or model files                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP (fetch)
                            │ GET /live_sample
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                              │
│                       (main.py)                             │
│                                                             │
│   • Runs on http://localhost:8000                          │
│   • Loads ML model at startup                              │
│   • Reads sensor (dummy data for now)                      │
│   • Runs predictions                                        │
│   • Returns JSON to frontend                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ joblib.load()
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      MODEL FILES                            │
│                                                             │
│   • gandiva_vib_model.joblib (trained classifier)          │
│   • gandiva_scaler.joblib (feature scaler)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Files Summary

| File | Purpose |
|------|---------|
| `main.py` | Backend server (FastAPI) |
| `frontend/index.html` | Frontend UI (simple HTML/JS) |
| `gandiva_vib_model.joblib` | Trained ML model |
| `gandiva_scaler.joblib` | Feature scaler |

---

## Troubleshooting

### "Cannot connect to backend"
- Make sure backend is running (`uvicorn main:app --reload`)
- Check port 8000 is not used by another app

### "ML Model Not Found"
- Make sure `gandiva_vib_model.joblib` exists in project root
- Check console for error messages

### Frontend not updating
- Open browser console (F12) for errors
- Make sure backend is running

---

## Next Steps

1. **Replace dummy sensor data** - Edit `read_sensor()` in main.py to use real Modbus
2. **Train better model** - Use real sensor data for training
3. **Add more features** - Graphs, history, alerts
