<#
.SYNOPSIS
    Standalone PowerShell launcher for TCF Transcriber Updated (PyTorch-Free Edition)
#>

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "    TCF Transcriber Updated (PyTorch-Free Edition)      " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python was not found in PATH." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/ (ensure 'Add to PATH' is checked)." -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

# 2. Check FFmpeg
$ffmpegCmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpegCmd) {
    Write-Host "[WARNING] FFmpeg not found in PATH." -ForegroundColor Yellow
    Write-Host "Whisper requires FFmpeg to decode audio. To install, run:" -ForegroundColor Yellow
    Write-Host "    winget install ffmpeg" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "[OK] FFmpeg found: $($ffmpegCmd.Source)" -ForegroundColor Green
}

# 3. Virtual Environment
$venvPath = Join-Path $PSScriptRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $venvPath)) {
    Write-Host "[INFO] Creating virtual environment at .venv..." -ForegroundColor Gray
    & python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Could not create virtual environment." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
}

# 4. Install dependencies if missing (No PyTorch)
$checkScript = "import faster_whisper, openai, ttkbootstrap, pandas, openpyxl; print('OK')"
$installed = & $venvPython -c $checkScript 2>$null
if ($installed -ne "OK") {
    Write-Host "[INFO] Installing lightweight dependencies (NO PyTorch)..." -ForegroundColor Gray
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install dependencies." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
}

# 5. Launch Application
Write-Host "[INFO] Launching TCF Transcriber Updated GUI..." -ForegroundColor Green
& $venvPython (Join-Path $PSScriptRoot "app.py")

