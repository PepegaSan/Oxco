@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0dist\Oxco\Oxco.exe" (
  start "" "%~dp0dist\Oxco\Oxco.exe"
  exit /b 0
)

where pythonw >nul 2>nul
if not errorlevel 1 (
  start "" pythonw "%~dp0oxco_gui.py"
  exit /b 0
)

where python >nul 2>nul
if errorlevel 1 (
  echo Python nicht gefunden.
  pause
  exit /b 1
)

start "" python "%~dp0oxco_gui.py"
exit /b 0
