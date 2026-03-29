# Railway Rolling Stock Condition Monitoring System v2.0

Enterprise-grade industrial monitoring system for railway rolling stock with multi-DXM support, dual connectivity, and intelligent defect detection.

## Overview

This upgraded system provides:
- **Dual Connectivity**: Automatic failover between TCP/IP (primary) and Serial RS485 (fallback)
- **Multi-DXM Support**: Parallel data acquisition from multiple controllers across multiple coaches
- **Advanced Signal Processing**: Temperature compensation, speed normalization, and adaptive baselines
- **Defect Detection**: AI-powered algorithms for wheel flats, bearing defects, imbalance, and misalignment
- **Intelligent Alerting**: Multi-level alerts with hysteresis, aggregation, and email/SMS notifications
- **Enhanced Data Logging**: Structured storage with high-resolution event capture

## Quick Start

### Prerequisites

- Python 3.8+
- SQLite (included with Python)
- Modbus TCP or Serial connection to DXM controllers

### Installation

1. **Install dependencies**:
```bash
cd backend/src
pip install -r requirements.txt
```

2. **Copy default configuration**:
```bash
cp config/default_config.yaml config.yaml
```

3. **Edit configuration** to match your setup:
```bash
# Edit config.yaml with your device IP addresses, serial ports, and notification settings
nano config.yaml
```

4. **Run database migration** (if upgrading from v1):
```bash
python -m storage.migrate
```

5. **Start the system**:
```bash
python -m api.main
```

The API will be available at `http://localhost:8000`

## Configuration

### Device Configuration

Configure each DXM controller in `config.yaml`:

```yaml
devices:
  - device_id: "DXM-C001-A1"
    name: "Coach 1 Axle Box 1"
    location: "Coach 1 - Axle 1 (Left)"
    coach_id: "C001"
    primary_connection: "tcp"
    tcp_host: "192.168.1.101"
    tcp_port: 502
    serial_port: "COM3"
    serial_baud: 19200
    slave_id: 1
    failover_enabled: true
```

### Defect Detection Thresholds

Adjust detection sensitivity:

```yaml
defect_detection:
  wheel_flat_kurtosis_threshold: 3.0
  wheel_flat_peak_threshold: 10.0
  bearing_hf_threshold: 2.0
  min_confidence: 60.0  # Minimum 60% confidence to report
```

### Notifications

Configure email (SMTP) and SMS (Twilio):

```yaml
email:
  enabled: true
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  username: "your-email@gmail.com"
  password: "your-app-password"
  from_address: "alerts@railway.com"

sms:
  enabled: true
  account_sid: "your-twilio-sid"
  auth_token: "your-twilio-token"
  from_number: "+1234567890"
```

## API Endpoints

### System Status
- `GET /api/v2/status` - System health summary
- `GET /health` - Health check

### Devices
- `GET /api/v2/devices` - List all devices with status
- `GET /api/v2/devices/{id}` - Get specific device status
- `GET /api/v2/devices/{id}/data` - Get latest device data
- `GET /api/v2/devices/{id}/baseline` - Get baseline statistics
- `POST /api/v2/devices/{id}/baseline/reset` - Reset baselines

### Alerts
- `GET /api/v2/alerts` - List alerts (filter by status, severity, device)
- `GET /api/v2/alerts/summary` - Alert summary
- `POST /api/v2/alerts/{id}/acknowledge` - Acknowledge alert
- `POST /api/v2/alerts/{id}/resolve` - Resolve alert

### Events & Detections
- `GET /api/v2/events` - System events history
- `GET /api/v2/detections` - Defect detection history

### Data Export
- `GET /api/v2/export` - Export data for date range (CSV/JSON)

### Configuration
- `GET /api/v2/config` - Get current configuration
- `POST /api/v2/config` - Update configuration (hot-reload)

### Real-time
- `WS /api/v2/ws/realtime` - WebSocket for real-time data

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Railway Monitoring System                 │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   DXM #1     │  │   DXM #2     │  │   DXM #N     │      │
│  │  TCP/Serial  │  │  TCP/Serial  │  │  TCP/Serial  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │              │
│  ┌──────▼─────────────────▼─────────────────▼──────┐      │
│  │         Dual Connectivity Manager              │      │
│  │    (Auto-failover TCP ↔ Serial RS485)         │      │
│  └──────┬──────────────────────────────────────┬───┘      │
│         │                                      │          │
│  ┌──────▼──────────┐  ┌──────────▼───────────┐ │          │
│  │ Multi-DXM Mgr   │  │   Signal Processor   │ │          │
│  │ (Parallel Poll) │  │ (Normalize/Filter)   │ │          │
│  └──────┬──────────┘  └──────────┬───────────┘ │          │
│         │                        │             │          │
│  ┌──────▼────────────────────────▼──────┐      │          │
│  │         Defect Detector              │      │          │
│  │  (Wheel Flat/Bearing/Imbalance/...)  │      │          │
│  └──────┬───────────────────────────────┘      │          │
│         │                                      │          │
│  ┌──────▼──────────────┐  ┌──────────▼──────┐  │          │
│  │   Alert Manager     │  │   Notifier      │  │          │
│  │ (Hysteresis/Agg.)   │──▶│ (Email/SMS)     │  │          │
│  └──────┬──────────────┘  └─────────────────┘  │          │
│         │                                      │          │
│  ┌──────▼──────────────────────────────────────▼───┐      │
│  │              Enhanced Database                  │      │
│  │  (Raw/Processed/Events/Alerts/Detections)     │      │
│  └─────────────────────────────────────────────────┘      │
│         │                                                  │
│  ┌──────▼──────────────────────────────────────┐          │
│  │           FastAPI REST + WebSocket          │          │
│  │  (Dashboard, Export, Config, Real-time)     │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## Defect Detection Capabilities

### 1. Wheel Flats
- **Detection**: Periodic high-peak events with high kurtosis
- **Signature**: Impulsive vibration at wheel rotation frequency
- **Confidence**: Based on kurtosis, peak amplitude, and periodicity

### 2. Bearing Outer Race Defect
- **Detection**: Elevated HF RMS acceleration with specific spectral patterns
- **Signature**: High-frequency energy increase
- **Threshold**: HF RMS > 2.0G, Kurtosis > 3.5

### 3. Bearing Inner Race Defect
- **Detection**: Modulated high-frequency content
- **Signature**: Higher frequency than outer race, often with sidebands
- **Characteristics**: Varying amplitude with rotation

### 4. Imbalance
- **Detection**: Elevated RMS at rotational frequency (1x)
- **Signature**: Low crest factor (<3.0), smooth sinusoidal vibration
- **Characteristics**: Both axes elevated, similar amplitude

### 5. Misalignment
- **Detection**: Elevated axial vibration (X-axis)
- **Signature**: Axial vibration nearly equal to radial
- **Characteristics**: 1x and 2x frequency components

## Database Schema

The enhanced database includes:

- **devices**: DXM device registry with connection settings
- **raw_data**: High-resolution raw sensor readings
- **processed_data**: Normalized and compensated values
- **defect_detections**: Detected defect records with confidence scores
- **alerts**: Multi-level alert system with lifecycle tracking
- **events**: System events and high-resolution anomaly capture
- **system_status**: Resource monitoring and health tracking
- **threshold_configs**: Per-device configurable thresholds
- **data_exports**: Export job tracking

## Security

The system includes:
- JWT token-based authentication
- Role-based access control (viewer/operator/admin)
- Input validation on all endpoints
- Parameterized database queries (SQL injection prevention)

**Default credentials** (change in production):
- admin/admin123
- operator/operator123
- viewer/viewer123

## Troubleshooting

### Connection Issues
1. Check TCP/IP connectivity: `ping <dxm_ip>`
2. Verify serial port: Check device manager / `ls /dev/tty*`
3. Review logs: Check `backend/logs/` directory
4. Test Modbus: Use `modbuscheck.py` utility

### Database Migration Issues
1. Backup existing database before migration
2. Check database file permissions
3. Run migration with: `python -m storage.migrate --verify`

### Performance Issues
1. Reduce polling interval in config
2. Decrease baseline window size
3. Enable data retention cleanup
4. Check system resources: CPU, memory, disk

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Adding New Defect Detection
1. Implement detection method in `processing/defect_detector.py`
2. Add threshold configuration in `DetectionConfig`
3. Add alert rule in default config
4. Update documentation

## Support

For issues and feature requests, please contact the development team.

## License

Copyright © 2024 Railway Monitoring Systems. All rights reserved.
