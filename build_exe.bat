@echo off
setlocal
title Build Standalone Executable (PyTorch-Free)

echo ========================================================
echo   Building TCF Transcriber Updated (PyTorch-Free .exe)
echo ========================================================
echo.

REM 1. Check Python installation
where python >nul 2>nul
if errorlevel 1 goto no_python
goto check_venv

:no_python
echo [ERROR] Python is not found in your PATH!
pause
exit /b 1

:check_venv
REM 2. Create or verify virtual environment
if exist ".venv\Scripts\activate.bat" goto activate_venv

echo [INFO] Creating Python virtual environment in .venv...
python -m venv .venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

:activate_venv
call .venv\Scripts\activate.bat

REM 3. Ensure dependencies and PyInstaller are installed
echo [INFO] Checking lightweight dependencies and PyInstaller...
pip install -r requirements.txt
pip install pyinstaller

REM 4. Build executable with PyInstaller (Excluding PyTorch)
echo [INFO] Packaging app.py with PyInstaller (excluding torch for compact footprint)...
pyinstaller --noconfirm --onedir --windowed ^
    --name "TCF Transcriber Updated" ^
    --icon "app_icon.ico" ^
    --add-data "config.json;." ^
    --add-data "app_icon.ico;." ^
    --add-data "app_icon.png;." ^
    --collect-all "faster_whisper" ^
    --collect-all "ctranslate2" ^
    --collect-all "ttkbootstrap" ^
    --exclude-module "torch" ^
    --exclude-module "torchaudio" ^
    --exclude-module "torchvision" ^
    --hidden-import "tiktoken_ext.openai_public" ^
    --hidden-import "tiktoken_ext" ^
    --hidden-import "pandas" ^
    --hidden-import "openpyxl" ^
    app.py

if errorlevel 1 goto build_failed
goto build_success

:build_failed
echo.
echo [ERROR] Build failed! Check the log messages above.
pause
exit /b 1

:build_success
echo.
echo ========================================================
echo [SUCCESS] Build finished!
echo Executable is located in: dist\TCF Transcriber Updated\TCF Transcriber Updated.exe
echo ========================================================
pause

