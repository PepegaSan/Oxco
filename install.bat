@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on PATH. Install Python 3.10+ and try again.
  pause
  exit /b 1
)

echo Installing Oxco dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto :err
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto :err

echo.
echo Done. You can run:  python oxco_gui.py
pause
exit /b 0

:err
echo.
echo pip install failed.
pause
exit /b 1
