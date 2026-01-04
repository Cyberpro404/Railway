@echo off
REM Project Gandiva - Train ML Model
REM This script generates sample data and trains the fault detection model

echo ============================================================
echo Project Gandiva - ML Training Pipeline
echo ============================================================
echo.

cd /d "%~dp0.."

echo Step 1: Generating sample training data...
python generate_sample_data.py --samples 200
if errorlevel 1 (
    echo ERROR: Failed to generate sample data
    pause
    exit /b 1
)

echo.
echo Step 2: Training RandomForest model...
python train_model.py
if errorlevel 1 (
    echo ERROR: Failed to train model
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Training complete! You can now start the API server.
echo Run: uvicorn main:app --reload
echo ============================================================
pause
