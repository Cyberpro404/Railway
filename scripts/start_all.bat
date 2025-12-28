@echo off
echo Starting Rail 2-Backend Ingest + API + Load Balancer setup...
echo.

echo 1. Starting Ingest Service (reads sensor, writes to SQLite)...
start "Ingest" cmd /k run_ingest.bat

timeout /t 2 >nul

echo 2. Starting API Server 1 (port 8001)...
start "API1" cmd /k run_api1.bat

timeout /t 2 >nul

echo 3. Starting API Server 2 (port 8002)...
start "API2" cmd /k run_api2.bat

timeout /t 2 >nul

echo 4. Starting Caddy load balancer (port 8080)...
start "Caddy" cmd /k run_caddy.bat

echo.
echo All services started.
echo Open http://127.0.0.1:8080 in your browser.
echo API servers: http://127.0.0.1:8001 and http://127.0.0.1:8002
echo Caddy admin: http://localhost:2020
pause
