# Builds a slim zip your friends can extract and double-click run.bat
# Excludes venv, pose models, personal history, and cache.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Stamp = Get-Date -Format "yyyyMMdd"
$OutDir = Join-Path $Root "dist"
$Stage = Join-Path $OutDir "coach_try"
$Zip = Join-Path $OutDir "AI_Exercise_Coach_$Stamp.zip"

New-Item -ItemType Directory -Force -Path $Stage | Out-Null
Get-ChildItem $Stage -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

$IncludeDirs = @(
    "common",
    "docs",
    "squat",
    "plank",
    "pushup",
    "lunge",
    "glute_bridge",
    "wall_sit",
    "bird_dog",
    "dead_bug",
    "biceps_curl",
    "ml",
    "videos"
)
$IncludeFiles = @(
    "main.py",
    "requirements.txt",
    "run.bat",
    "README.md"
)

foreach ($dir in $IncludeDirs) {
    $src = Join-Path $Root $dir
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $Stage $dir) -Recurse -Force
    }
}
foreach ($file in $IncludeFiles) {
    Copy-Item (Join-Path $Root $file) (Join-Path $Stage $file) -Force
}

New-Item -ItemType Directory -Force -Path (Join-Path $Stage "models") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Stage "data") | Out-Null

$formSrc = Join-Path $Root "models\form"
if (Test-Path $formSrc) {
    Copy-Item $formSrc (Join-Path $Stage "models\form") -Recurse -Force
}

Get-ChildItem $Stage -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

$readme = @"
AI Exercise Coach — try build

1. Install Python 3.11 from python.org (tick Add to PATH).
2. Double-click run.bat
3. First launch downloads packages + the pose model (needs internet).
4. Allow the webcam. Press q in the camera window to quit an exercise.

Read docs/getting-started.md for the full guide.

Do not copy a venv from someone else's PC.
Your own profile is created on first run (onboarding questions).
"@
Set-Content -Path (Join-Path $Stage "START_HERE.txt") -Value $readme -Encoding UTF8

if (Test-Path $Zip) { Remove-Item $Zip -Force }
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $Zip -Force

Write-Host ""
Write-Host "Send this zip to your friends:"
Write-Host "  $Zip"
Write-Host ""
Write-Host "They unzip, then double-click run.bat"
Write-Host ""
