@echo off
setlocal
cd /d "%~dp0"
echo ========================================================
echo   FitPath AI Backend Launcher ^& Cloud Tunnel
echo ========================================================
echo.

set NGROK="C:\Users\ATeF\AppData\Local\Microsoft\WindowsApps\ngrok.exe"

echo 1. Launch Local Backend + Live Public Cloud Tunnel (Recommended)
echo 2. Run Local Backend only
echo 3. Start Public Cloud Tunnel only (Port 8000)
echo 4. Cloud Deployment Instructions (Render.com / Railway)
echo.
set /p choice="Select an option (1-4): "

if "%choice%"=="1" goto run_both
if "%choice%"=="2" goto run_backend
if "%choice%"=="3" goto run_tunnel
if "%choice%"=="4" goto cloud_instructions
goto end

:run_both
echo Starting backend server in background...
start "FitPath Backend Server" run_backend.bat
timeout /t 3 /nobreak >nul
echo Starting live public tunnel...
%NGROK% http 8000
goto end

:run_backend
call run_backend.bat
goto end

:run_tunnel
echo Starting public HTTPS/WSS tunnel on port 8000...
%NGROK% http 8000
goto end

:cloud_instructions
cls
echo ========================================================
echo   How to Deploy FitPath AI Backend on Render.com (24/7 Free)
echo ========================================================
echo 1. Go to https://render.com and log in with your GitHub account.
echo 2. Click "New" -^> "Web Service".
echo 3. Select your repository: Brainwave06/gym_coach.
echo 4. Render will automatically detect the Dockerfile and render.yaml!
echo 5. Click "Deploy Web Service".
echo.
echo Once deployed, you will get a permanent URL like:
echo   https://fitpath-ai-backend.onrender.com
echo.
echo You can enter this URL directly into the FitPath mobile app!
pause
goto end

:end
