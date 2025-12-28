@echo off
REM Gandiva Rail Safety Monitor - Startup Script
echo ========================================
echo Gandiva Rail Safety Monitor - Startup
echo ========================================
echo.

cd /d "%~dp0"

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10 or higher.
    pause
    exit /b 1
)

echo.
echo Checking required packages...
python -c "import fastapi, uvicorn, numpy, pandas, sklearn, joblib" 2>nul
if errorlevel 1 (
    echo WARNING: Some packages may be missing.
    echo Run: pip install -r requirements.txt
    echo.
)

echo.
echo Testing imports...
python test_imports.py
if errorlevel 1 (
    echo ERROR: Import test failed!
    pause
    exit /b 1
)

echo.
echo Starting Gandiva Rail Safety Monitor...
echo Server will be available at: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
