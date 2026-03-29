@echo off
title Gandiva Pro - Frontend
echo =====================================
echo  Gandiva Pro - Frontend
echo =====================================
echo.

cd /d "%~dp0frontend"

echo Checking for node_modules...
if not exist node_modules (
    echo Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo Starting Vite development server on http://localhost:3000
echo.
echo Press Ctrl+C to stop the server
echo.

call npm run dev

pause
