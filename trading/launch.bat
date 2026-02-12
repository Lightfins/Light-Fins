@echo off
REM ═══════════════════════════════════════════════════════
REM  TRADING COMMAND CENTER — Windows One-Click Launcher
REM  Double-click this file to launch
REM ═══════════════════════════════════════════════════════

title Trading Command Center
echo.
echo   ╔══════════════════════════════════════════════╗
echo   ║       TRADING COMMAND CENTER v1.1            ║
echo   ║       Launching...                           ║
echo   ╚══════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

REM --- Create venv if needed ---
if not exist .venv (
    echo [SETUP] Creating Python virtual environment...
    python -m venv .venv
)

REM --- Activate venv ---
call .venv\Scripts\activate.bat

REM --- Install dependencies ---
echo [SETUP] Checking dependencies...
pip install -q -r requirements.txt 2>nul

REM --- Create data directory ---
if not exist data mkdir data

REM --- Launch server and open browser ---
echo [BOOT] Starting server on port 8085...
echo.

start "" http://localhost:8085
python server.py

pause
