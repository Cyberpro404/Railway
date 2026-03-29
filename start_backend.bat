@echo off
title Gandiva Pro - Backend Server
echo =====================================
echo  Gandiva Pro - Backend Server
echo =====================================
echo.

cd /d "%~dp0backend"

set "PY_EXE="

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PY_EXE=%CD%\venv\Scripts\python.exe"
) else (
    where py >nul 2>&1
    if %ERRORLEVEL%==0 (
        set "PY_EXE=py -3"
    ) else (
        where python >nul 2>&1
        if %ERRORLEVEL%==0 (
            set "PY_EXE=python"
        )
    )
)

if "%PY_EXE%"=="" (
    echo ERROR: No Python interpreter found.
    echo Create an environment with:
    echo   python -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    pause
    exit /b 1
)

echo Using Python: %PY_EXE%

echo.
echo Starting FastAPI backend server on http://localhost:8000
echo WebSocket endpoint: ws://localhost:8000/ws
echo.
echo Press Ctrl+C to stop the server
echo.

%PY_EXE% -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

pause
