@echo off
echo Installing Gandiva Pro Backend Dependencies...
echo.

set "PY_EXE="

if exist "%~dp0..\.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0..\.venv\Scripts\python.exe"
) else if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0venv\Scripts\python.exe"
) else (
    where py >nul 2>&1
    if %ERRORLEVEL%==0 (
        set "PY_EXE=py -3"
    ) else (
        set "PY_EXE=python"
    )
)

echo Using Python: %PY_EXE%

echo Installing from requirements.txt...
%PY_EXE% -m pip install -r requirements.txt

echo.
echo Verifying installation...
%PY_EXE% check_dependencies.py

echo.
echo Installation complete!
pause

