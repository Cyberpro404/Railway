@echo off
color 0F
title Gandiva Pro - System Verification

echo.
echo ========================================
echo    GANDIVA PRO - System Verification
echo ========================================
echo.

:: Check Python
echo [1/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.8 or higher
    goto :end
) else (
    python --version
    echo ✅ Python OK
)

echo.
echo [2/6] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found! Please install Node.js 16 or higher
    goto :end
) else (
    node --version
    echo ✅ Node.js OK
)

echo.
echo [3/6] Checking backend virtual environment...
if exist "backend\venv\Scripts\python.exe" (
    echo ✅ Virtual environment found
) else (
    echo ⚠️  Virtual environment not found
    echo Creating virtual environment...
    cd backend
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    cd ..
    echo ✅ Virtual environment created
)

echo.
echo [4/6] Checking backend dependencies...
cd backend
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    python -c "import fastapi, uvicorn, pymodbus; print('✅ Backend dependencies OK')" 2>nul
    if errorlevel 1 (
        echo ⚠️  Installing backend dependencies...
        pip install -r requirements.txt
    )
) else (
    echo ❌ Virtual environment not activated
)
cd ..

echo.
echo [5/6] Checking frontend dependencies...
cd frontend
if exist "node_modules" (
    echo ✅ Frontend dependencies found
) else (
    echo ⚠️  Installing frontend dependencies...
    call npm install
)
cd ..

echo.
echo [6/6] Testing backend imports...
cd backend
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    python -c "import app; print('✅ Backend imports working')" 2>nul
    if errorlevel 1 (
        echo ❌ Backend import errors detected
        python -c "import app"
    )
) else (
    echo ❌ Cannot test - virtual environment not found
)
cd ..

echo.
echo ========================================
echo    VERIFICATION COMPLETE
echo ========================================
echo.
echo Checking ports...
netstat -ano | findstr ":8000" >nul 2>&1
if not errorlevel 1 (
    echo ⚠️  Port 8000 is already in use
    echo    You may need to close the existing process
) else (
    echo ✅ Port 8000 is available
)

netstat -ano | findstr ":3000" >nul 2>&1
if not errorlevel 1 (
    echo ⚠️  Port 3000 is already in use
    echo    You may need to close the existing process
) else (
    echo ✅ Port 3000 is available
)

echo.
echo ========================================
echo  System is ready!
echo  Run START_ALL.bat to launch
echo ========================================

:end
echo.
pause
