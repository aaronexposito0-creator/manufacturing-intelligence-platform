@echo off
setlocal
cd /d "%~dp0"

echo =======================================================
echo  Manufacturing Intelligence Platform v2.0
echo =======================================================

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo Python was not found.
    echo Install Python 3.11 or newer from https://www.python.org/downloads/
    echo During installation, enable "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating isolated Python environment...
    python -m venv .venv
    if errorlevel 1 goto :error
)

if not exist ".venv\.mip_setup_complete" (
    echo [2/3] Installing project dependencies ^(first run only^)...
    call .venv\Scripts\python.exe -m pip install --upgrade pip
    if errorlevel 1 goto :error
    call .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 goto :error
    echo setup-complete> ".venv\.mip_setup_complete"
) else (
    echo [2/3] Dependencies already installed - skipping setup.
)

echo [3/3] Starting dashboard...
echo.
echo Open http://localhost:8501 if the browser does not open automatically.
echo Keep this window open while using the application.
echo Press Ctrl+C to stop the server.
echo.
call .venv\Scripts\python.exe -m streamlit run app.py
exit /b 0

:error
echo.
echo Setup failed. Copy the error shown above before closing this window.
pause
exit /b 1
