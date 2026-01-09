# Gandiva Pro - Quick Start Guide

## 🚀 Installation & Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm or yarn

### Backend Setup

1. **Navigate to backend directory:**
```bash
cd backend
```

2. **Create virtual environment:**
```bash
python -m venv venv
```

3. **Activate virtual environment:**
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

4. **Install dependencies:**
```bash
pip install -r requirements.txt
```

5. **Run backend server:**
```bash
python app.py
```

Backend will start on `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory:**
```bash
cd frontend
```

2. **Install dependencies:**
```bash
npm install
```

3. **Start development server:**
```bash
npm run dev
```

Frontend will start on `http://localhost:3000`

## 📡 Modbus Connection

1. **Connect Hardware:**
   - Connect your Modbus RTU device to a COM port
   - Default settings: 19200 baud, Slave ID: 1

2. **In Dashboard:**
   - Go to **CONNECTION STATUS** tab
   - Click **SCAN PORTS** to find available COM ports
   - Click **Connect [PORT]** to establish connection

3. **Safe Register Access:**
   - System only reads registers 45201-45217
   - No access to restricted registers (e.g., 43501)

## 🎯 Key Features

### Real-time Monitoring
- **1Hz Updates**: WebSocket streaming at 1 second intervals
- **Live Gauges**: Visual indicators for critical parameters
- **Sparkline Trends**: Mini charts in metric cards

### ML Intelligence
- **Anomaly Detection**: RandomForest classifier predicts faults
- **Confidence Levels**: Real-time prediction confidence
- **Feature Importance**: Shows which features drive predictions

### ISO10816 Classification
- **Automatic Severity**: Classifies vibration levels
- **Color Coding**: Green/Yellow/Red based on severity
- **Class II Standard**: Optimized for medium-sized machinery

### Alerts & Thresholds
- **Configurable Limits**: Set warn/alarm thresholds
- **Active Alerts**: Priority-sorted alert center
- **Sound Notifications**: Audio alerts for critical events

## 🐳 Docker Deployment

```bash
cd deploy
docker-compose -f docker-compose.prod.yml up -d
```

## 📊 Dashboard Tabs Overview

1. **CONNECTION STATUS** - System health, port management
2. **EXECUTIVE DASHBOARD** - 16 KPI tiles, live gauges
3. **HEALTH ANALYTICS** - 6 live charts, statistics
4. **ML INTELLIGENCE** - Predictions, confidence, features
5. **DATA MANAGEMENT** - Training dataset browser
6. **OPERATION LOGS** - Real-time log stream
7. **ACTIVE ALERTS** - Alert center with priorities
8. **THRESHOLDS** - Configure limits (scalar & band)
9. **SYSTEM CONTROL** - Settings, ML controls, backup

## 🔧 Configuration

### Default Thresholds
- **Z/X RMS**: Warn 2.0 mm/s, Alarm 4.0 mm/s
- **Temperature**: Warn 50°C, Alarm 70°C

### Modbus Scaling
- **Velocity**: `register_value / 65535 * 65.535` mm/s
- **Temperature**: `register_value / 100` °C

## 🆘 Troubleshooting

### Backend Issues
- Check Python version: `python --version` (should be 3.11+)
- Verify dependencies: `pip list`
- Check logs in console for errors

### Frontend Issues
- Clear node_modules: `rm -rf node_modules && npm install`
- Check Node version: `node --version` (should be 18+)
- Verify Vite is running: Check `http://localhost:3000`

### Modbus Connection
- Verify COM port exists: Use Device Manager (Windows)
- Check baud rate matches device settings
- Ensure Slave ID is correct (default: 1)

### WebSocket Issues
- Check backend is running on port 8000
- Verify CORS settings in backend
- Check browser console for connection errors

## 📝 Notes

- Database is SQLite (created automatically)
- ML model is auto-generated on first run
- All data persists in `gandiva_pro.db`
- Logs are stored in database

## 🎨 Theme Customization

Edit `frontend/tailwind.config.js` to customize:
- Colors (Midnight Steel theme)
- Typography
- Border radius
- Animations

