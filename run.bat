@echo off
title Someone Call Me - Thai Keyword Listener
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    echo Installing dependencies...
    .venv\Scripts\pip.exe install -r requirements.txt
)

echo Starting Someone Call Me...
.venv\Scripts\python.exe main.py
if errorlevel 1 (
    echo.
    echo Application exited with error.
    pause
)
