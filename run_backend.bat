@echo off
cd /d "%~dp0"
echo ========================================================
echo   Starting FitPath AI Backend Server (FastAPI + Uvicorn)
echo ========================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found in .\venv!
    echo Please create it using: python -m venv venv
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Server running on:
echo   - Local:    http://127.0.0.1:8000
echo   - Network:  http://0.0.0.0:8000
echo   - API Docs: http://127.0.0.1:8000/docs
echo   - WebSocket: ws://127.0.0.1:8000/stream/{exercise_id}
echo.
echo Press CTRL+C to stop the server.
echo.

python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
pause
