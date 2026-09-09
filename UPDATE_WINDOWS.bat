@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run START_WINDOWS.bat once before updating dependencies.
  pause
  exit /b 1
)
call .venv\Scripts\python.exe -m pip install --upgrade pip
call .venv\Scripts\python.exe -m pip install -r requirements.txt --upgrade
if errorlevel 1 (
  echo Update failed.
  pause
  exit /b 1
)
echo setup-complete> ".venv\.mip_setup_complete"
echo Dependencies updated successfully.
pause
