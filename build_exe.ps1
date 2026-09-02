$ErrorActionPreference = "Stop"
Write-Host "Installing PyInstaller..."
pip install pyinstaller

Write-Host "Building executable..."
python -m PyInstaller --noconfirm --onefile `
  --exclude-module torch `
  --exclude-module pandas `
  --exclude-module IPython `
  --exclude-module notebook `
  --exclude-module tkinter `
  --exclude-module PyQt5 `
  --exclude-module PySide6 `
  --collect-all mediapipe `
  --add-data "models;models/" `
  --add-data "videos;videos/" `
  --name "AI_Exercise_Coach" `
  main.py

Write-Host "Build complete! Executable is located in dist/AI_Exercise_Coach.exe"
