@echo off
setlocal
echo ===================================================
echo   FitPath AI Coach - Phone APK Installer
echo ===================================================
set ADB="D:\Android\Sdk\platform-tools\adb.exe"

echo Checking connected devices...
%ADB% devices

echo.
echo Installing FitPath_AI_Coach_v1.0.apk to your phone...
%ADB% install -r "%~dp0FitPath_AI_Coach_v1.0.apk"
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Launching FitPath on phone...
    %ADB% shell am start -n com.fitpath.app.fitpath_frontend/.MainActivity
    echo.
    echo ===================================================
    echo  [SUCCESS] FitPath is now running on your phone!
    echo ===================================================
) else (
    echo.
    echo [NOTICE] If no device was listed above:
    echo 1. Plug in your Android phone via USB.
    echo 2. Enable Developer Options -^> USB Debugging.
    echo 3. Unlock your phone screen and tap "Always allow from this computer".
    echo 4. Run this script again!
)
pause
