@echo off
setlocal
title TCF Transcriber Updated Launcher

echo ========================================================
echo        TCF Transcriber Updated (PyTorch-Free Edition)
echo ========================================================
echo.

REM 1. Check Python installation
where python >nul 2>nul
if errorlevel 1 goto no_python
goto check_ffmpeg

:no_python
echo [ERROR] Python is not found in your PATH!
echo Please install Python 3.10+ from https://www.python.org/
echo Make sure to check Add Python to PATH during installation.
pause
exit /b 1

:check_ffmpeg
REM 2. Check FFmpeg
where ffmpeg >nul 2>nul
if errorlevel 1 goto no_ffmpeg
goto check_venv

:no_ffmpeg
echo [WARNING] FFmpeg was not found in your system PATH.
echo Whisper requires FFmpeg to process audio files.
echo You can install it on Windows by opening PowerShell and running:
echo     winget install ffmpeg
echo.
echo Press any key to continue anyway, or close this window to install FFmpeg first.
pause

:check_venv
REM 3. Setup Virtual Environment
if exist ".venv\Scripts\activate.bat" goto activate_venv

echo [INFO] Creating Python virtual environment in .venv...
python -m venv .venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
echo [INFO] Virtual environment created successfully.

:activate_venv
REM 4. Activate Venv and Check Dependencies
call .venv\Scripts\activate.bat

python -c "import faster_whisper, openai, ttkbootstrap, pandas, openpyxl" >nul 2>nul
if errorlevel 1 goto install_deps
goto launch_app

:install_deps
echo [INFO] Installing lightweight dependencies (NO PyTorch needed)... Please wait.
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies. Check your internet connection.
    pause
    exit /b 1
)
echo [INFO] Dependencies installed successfully.

:launch_app
REM 5. Launch the Application
echo [INFO] Starting TCF Transcriber Updated UI...
python app.py

if errorlevel 1 (
    echo.
    echo [INFO] Application closed with an error code.
    pause
)

