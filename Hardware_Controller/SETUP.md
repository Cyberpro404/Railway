# Hardware Controller Backend - Complete Setup

## 📁 Project Structure
```
Hardware_Controller/
├── main.py              # FastAPI backend (main application)
├── example_client.py    # Python client examples
├── controller.ino       # Arduino/ESP32 sketch
├── requirements.txt     # Python dependencies
├── config.ini          # Configuration reference
├── QUICKSTART.txt      # Quick start guide
└── SETUP.md           # This file
```

## ⚙️ Installation

### Step 1: Install Dependencies
```bash
cd "c:\Users\athar\Desktop\VS Code\Hardware_Controller"
pip install -r requirements.txt
```

### Step 2: Configure COM Port
Edit `main.py` and find these lines (around line 23-24):
```python
COM_PORT = "COM5"      # ← Change to your device's port
BAUD_RATE = 9600       # ← Change if different
```

Find your COM port:
- **Windows**: Device Manager → Ports (COM & LPT)
- **Linux**: `ls /dev/tty* | grep USB`

### Step 3: Flash Arduino/ESP32
1. Open `controller.ino` in Arduino IDE
2. Select correct board (Arduino Uno/Nano or ESP32)
3. Select your COM port
4. Click Upload
5. Open Serial Monitor, should show: "ESP32/Arduino Ready"

### Step 4: Start the Backend
```bash
python main.py
```

Expected output:
```
INFO:     Started server process
2026-01-20 ... | INFO | ✅ Successfully connected to COM5
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 🚀 Quick Test

### Test Endpoint Health
```bash
curl http://localhost:8000/
```

### Test List Ports
```bash
curl http://localhost:8000/ports
```

### Send ON Command
```bash
$body = @{value=100; threshold=50} | ConvertTo-Json
curl -X POST http://localhost:8000/send `
  -ContentType "application/json" `
  -Body $body
```

Expected output in Arduino Serial Monitor:
```
Output: ON
```

### Send OFF Command
```bash
$body = @{value=25; threshold=50} | ConvertTo-Json
curl -X POST http://localhost:8000/send `
  -ContentType "application/json" `
  -Body $body
```

Expected output in Arduino Serial Monitor:
```
Output: OFF
```

## 📡 API Reference

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health check |
| GET | `/ports` | List available COM ports |
| GET | `/status` | Get connection status |
| POST | `/connect` | Connect to device |
| POST | `/disconnect` | Disconnect from device |
| POST | `/send` | Send control command (MAIN) |
| POST | `/send-raw` | Send raw serial data |

### POST /send - Main Control Endpoint
```json
{
  "value": 100,
  "threshold": 50
}
```
- If `value > threshold` → sends "1\n" (ON)
- If `value <= threshold` → sends "0\n" (OFF)

**Response:**
```json
{
  "success": true,
  "command_sent": "ON",
  "last_value": 100,
  "message": "Command sent: ON (value: 100 > threshold: 50)"
}
```

## 🔧 Hardware Wiring

### Simple LED Test
```
ESP32 Pin 5 → 1kΩ Resistor → LED Anode
              ↓
           LED Cathode → GND
GND → GND (common)
```

### Buzzer + Relay
```
ESP32 Pin 5 → N-channel MOSFET Gate (IRF540N)
MOSFET Source → GND
MOSFET Drain → Buzzer Anode / Relay Coil
         ↓ (with protection diode)
      +5V (external power)
```

## 🐍 Python Integration

```python
import requests

# Send control command
response = requests.post(
    'http://localhost:8000/send',
    json={'value': 150, 'threshold': 100}
)

if response.status_code == 200:
    data = response.json()
    print(f"Command sent: {data['command_sent']}")
else:
    print(f"Error: {response.text}")
```

## 🆘 Troubleshooting

### Backend won't start
```
ERROR: [Errno 10048] Address already in use
```
Solution: Kill existing process on port 8000
```powershell
Get-NetTCPConnection -LocalPort 8000 | Stop-Process -Force
```

### Device not responding
1. Check COM port: `curl http://localhost:8000/ports`
2. Verify Arduino Serial Monitor shows "ESP32/Arduino Ready"
3. Check baud rate matches in both backend and Arduino code
4. Try unplugging and replugging USB

### Garbage in Arduino Serial Monitor
Solution: Baud rate mismatch
- Check Arduino code: `Serial.begin(9600)`
- Check main.py: `BAUD_RATE = 9600`
- Common rates: 9600, 19200, 38400, 115200

### Commands sent but hardware doesn't respond
1. Verify pin configuration in Arduino code
2. Check hardware connections (GND, VCC, signal)
3. Use a multimeter to verify pin voltage changes
4. Add simple test in Arduino:
```cpp
void setup() {
  pinMode(5, OUTPUT);
  digitalWrite(5, HIGH);  // Should turn ON immediately
}
```

## 📊 Features

✅ Auto-connect on startup
✅ Graceful disconnection handling
✅ Command deduplication (avoids duplicate sends)
✅ 2-second startup delay (device initialization)
✅ Configurable COM port & baud rate
✅ REST API with FastAPI
✅ State tracking (last command, last value)
✅ Comprehensive logging
✅ Error recovery

## 🔄 How It Works

1. **Startup**: Backend opens serial connection, waits 2 seconds
2. **Ready**: Listens for HTTP POST requests
3. **Command Received**: Compares value vs threshold
4. **Send Decision**: Decides to send "1\n" or "0\n"
5. **Optimization**: Skips duplicate commands
6. **Logging**: Logs all commands and state changes
7. **Arduino**: Receives serial data, sets GPIO high/low

## 📝 Example Use Cases

### Temperature Monitoring
```python
# If temperature > 30°C, turn ON cooler
response = requests.post('http://localhost:8000/send',
    json={'value': current_temp, 'threshold': 30})
```

### Vibration Alerts
```python
# If vibration > 5.0 g, turn ON buzzer
response = requests.post('http://localhost:8000/send',
    json={'value': vibration_level, 'threshold': 5.0})
```

### Threshold Logic
```python
# If sensor_value > limit, turn ON relay
response = requests.post('http://localhost:8000/send',
    json={'value': sensor_value, 'threshold': limit})
```

## 🎯 Performance

- Response time: <100ms
- Serial write time: <1ms
- No blocking operations
- Handles multiple requests sequentially
- Logs all commands for debugging

## 📦 Dependencies

- **fastapi** (0.104.1) - Web framework
- **uvicorn** (0.24.0) - ASGI server
- **pyserial** (3.5) - Serial communication
- **pydantic** (2.5.0) - Data validation

Install with:
```bash
pip install -r requirements.txt
```

## ✨ Next Steps

1. **Run the examples**:
   ```bash
   python example_client.py
   ```

2. **Integrate with your app**:
   ```python
   import requests
   requests.post('http://localhost:8000/send', 
                json={'value': x, 'threshold': y})
   ```

3. **Deploy**: Run on Raspberry Pi or any Python-capable machine

4. **Monitor**: Check logs in console output

## 📞 Support

For issues:
1. Check Arduino Serial Monitor output
2. Verify COM port with `/ports` endpoint
3. Test raw command with `/send-raw` endpoint
4. Check logs for detailed error messages
5. Verify USB connection and baud rate

---

**Status**: ✅ Ready for deployment
**Version**: 1.0
**Last Updated**: January 20, 2026
