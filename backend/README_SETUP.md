# Gandiva Pro Backend - Setup Guide

## Quick Setup

### 1. Install Dependencies

```bash
# Windows
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Linux/Mac
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Verify Installation

```bash
python check_dependencies.py
```

### 3. Run Setup Script

```bash
python setup.py
```

### 4. Start Server

```bash
python app.py
```

The server will start on `http://localhost:8000`

## Troubleshooting

### ModuleNotFoundError: No module named 'serial'

**Solution:**
```bash
pip install pyserial
```

Or reinstall all dependencies:
```bash
pip install -r requirements.txt
```

### ModuleNotFoundError: No module named 'pymodbus'

**Solution:**
```bash
pip install pymodbus
```

### Database Issues

The SQLite database will be created automatically on first run. If you encounter database errors:

1. Delete `gandiva_pro.db` if it exists
2. Restart the server - it will recreate the database

### Port Already in Use

If port 8000 is already in use:

1. Change the port in `app.py`:
   ```python
   uvicorn.run(app, host="0.0.0.0", port=8001)
   ```

2. Or kill the process using port 8000:
   ```bash
   # Windows
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   
   # Linux/Mac
   lsof -ti:8000 | xargs kill
   ```

## Required Python Version

- Python 3.8 or higher
- Check version: `python --version`

## Dependencies

All dependencies are listed in `requirements.txt`:

- fastapi - Web framework
- uvicorn - ASGI server
- pymodbus - Modbus communication
- pyserial - Serial port access
- sqlalchemy - Database ORM
- scikit-learn - Machine learning
- numpy, pandas - Data processing

## Development

For development with auto-reload:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

