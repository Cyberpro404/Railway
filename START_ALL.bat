@echo off
title Gandiva Pro - Launcher
color 0A

echo.
echo ========================================
echo    GANDIVA PRO - System Launcher
echo    Railway Condition Monitoring
echo ========================================
echo.
echo Starting backend and frontend servers...
echo.

:: Start backend in new window
start "Gandiva Pro - Backend" cmd /k "%~dp0start_backend.bat"

:: Wait a bit for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend in new window
start "Gandiva Pro - Frontend" cmd /k "%~dp0start_frontend.bat"

:: Wait a bit for frontend to start
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo    SERVERS LAUNCHED
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Both servers are running in separate windows.
echo Close those windows to stop the servers.
echo.

:: Open browser to frontend
timeout /t 2 /nobreak >nul
start http://localhost:3000

echo.
echo Press any key to exit this launcher window...
pause >nul
