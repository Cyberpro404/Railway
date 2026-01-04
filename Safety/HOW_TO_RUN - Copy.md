# 🚂 Gandiva - How to Run

## 🚦 NEW: Automatic Sensor Connection (Dec 2025)

- The backend now automatically scans and connects to the first available Modbus sensor port on startup.
- If the sensor is not connected at launch, the backend will retry in the background until a sensor is found.
- No manual connection is required for most users—just plug in the sensor and start the backend.
- Connection status and errors are logged to the console and available via `/api/latest/status`.

### Manual Connection (Advanced/Override)
- You can still POST to `/api/ports/connect` to override the auto-connect (see below for curl example).
- If you POST a new config, the backend will disconnect and reconnect using your parameters.

---

## Quick Start (3 Steps)

1. **Install Backend Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Start Backend Server**
   ```bash
   cd "c:\Users\athar\Desktop\VS Code\Rail 2 - Copy (2)"
   uvicorn main:app --reload --port 8000
   ```
   - The backend will auto-connect to the sensor (see logs for status).
3. **Open Frontend**
   - Open `frontend/index.html` in your browser.

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
Open in browser: http://localhost:8000/api/live_sample

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
                            │ GET /api/live_sample
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                              │
│                       (main.py)                             │
│                                                             │
│   • Runs on http://localhost:8000                          │
│   • Loads ML model at startup                              │
│   • Reads real sensor via Modbus                           │
│   • Persists realtime readings to SQLite (database/rail.db)│
│   • Runs predictions                                       │
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

## Troubleshooting Auto-Connect

- If the sensor is not detected, check:
  - Sensor is powered and connected to the PC
  - COM port is visible in Device Manager
  - Sensor DIP switches (Slave ID, baud, parity) match backend defaults
  - Backend logs for connection errors
- The backend will keep retrying in the background until a sensor is found.
- For advanced troubleshooting, use `/api/ports/scan` and `/api/latest/status` endpoints.

---

## Sensor Setup (Realtime)

- Scan available ports: GET http://localhost:8000/api/ports/scan
- Connect sensor:

```bash
curl -X POST http://localhost:8000/api/ports/connect \
  -H "Content-Type: application/json" \
  -d '{
        "port": "COM5",
        "baudrate": 19200,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
        "timeout_s": 3.0,
        "slave_id": 1
      }'
```

Data is stored in `database/rail.db`:
- Latest reading: `latest`
- History: `history` (auto-trimmed)
- Alerts: `alerts`
