@echo off
title JARVIS // Desktop
cd /d "%~dp0"

python -c "import webview" >nul 2>&1
if errorlevel 1 (
    echo pywebview is not installed.
    echo Install project dependencies with: python -m pip install -r requirements.txt
    pause
    exit /b 1
)

python desktop.py
if errorlevel 1 (
    echo.
    echo JARVIS desktop window failed to start.
    pause
)
