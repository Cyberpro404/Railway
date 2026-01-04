@echo off
REM Project Gandiva - Start Redesigned Backend
REM This starts the FastAPI server with the new architecture

echo ============================================================
echo Project Gandiva - Railway Vibration Monitor (Redesigned)
echo ============================================================
echo.

cd /d "%~dp0.."

echo Starting FastAPI server...
echo.
echo Endpoints:
echo   - API Docs:  http://localhost:8000/docs
echo   - Status:    http://localhost:8000/status
echo   - Live:      http://localhost:8000/live_sample
echo   - Frontend:  Open frontend/gandiva.html in browser
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

python -m uvicorn app_redesigned:app --reload --host 0.0.0.0 --port 8000

pause
