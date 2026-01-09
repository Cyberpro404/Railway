@echo off
echo Installing Gandiva Pro Backend Dependencies...
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

echo Installing from requirements.txt...
pip install -r requirements.txt

echo.
echo Verifying installation...
python check_dependencies.py

echo.
echo Installation complete!
pause

