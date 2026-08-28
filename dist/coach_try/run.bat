@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo  AI Exercise Coach
echo  First run installs Python packages and downloads the pose model.
echo  Need: Windows, Python 3.10-3.12, a webcam, internet on first launch.
echo.

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    set "PY=py -3"
) else (
    where python >nul 2>&1
    if %ERRORLEVEL%==0 (
        set "PY=python"
    ) else (
        echo Python was not found. Install Python 3.11 from https://www.python.org/downloads/
        echo Tick "Add python.exe to PATH", then run this file again.
        pause
        exit /b 1
    )
)

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PY% -m venv venv
    if errorlevel 1 (
        echo Could not create venv. Is Python installed with "pip" and "venv"?
        pause
        exit /b 1
    )
)

call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Package install failed. Check your internet connection and Python version.
    pause
    exit /b 1
)

echo.
echo Starting coach...
echo Close the camera window with Q. Use the terminal menu for Start today / Practice.
echo.
python main.py
echo.
pause
