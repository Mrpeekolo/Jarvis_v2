@echo off
title JARVIS // Discrete Local AI Core
echo ========================================================
echo  Starting JARVIS Discrete Assistant (Pure Local Core)
echo ========================================================
echo Host: http://127.0.0.1:8765
echo Sandbox: AST Guarded Python 3 Subprocess
echo.

cd /d "%~dp0"

:: Start Ollama automatically if it is not already listening on port 11434.
curl.exe --silent --fail http://127.0.0.1:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo Ollama is not running. Starting Ollama...

    set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
    if exist "%OLLAMA_EXE%" (
        start "Ollama" /MIN "%OLLAMA_EXE%" serve
    ) else (
        start "Ollama" /MIN ollama.exe serve
    )

    set "OLLAMA_READY="
    for /l %%i in (1,1,15) do (
        if not defined OLLAMA_READY (
            curl.exe --silent --fail http://127.0.0.1:11434/api/tags >nul 2>&1
            if not errorlevel 1 set "OLLAMA_READY=1"
            if not defined OLLAMA_READY timeout /t 1 /nobreak >nul
        )
    )

    if not defined OLLAMA_READY (
        echo.
        echo WARNING: Ollama did not respond on http://127.0.0.1:11434.
        echo Install Ollama or start it manually, then rerun JARVIS.
        echo.
    )
)

python -m pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python dependencies are missing.
    echo Install them with: python -m pip install fastapi uvicorn httpx pydantic mss Pillow pywin32
    pause
    exit /b 1
)

:: Open default browser to JARVIS UI
start http://127.0.0.1:8765

:: Run the FastAPI Uvicorn Server
python main.py

pause
