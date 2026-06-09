@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python wurde nicht gefunden.
  pause
  exit /b 1
)

python -c "import win32com" >nul 2>nul
if errorlevel 1 (
  echo Installiere pywin32 fuer Taskleisten-Icon der Verknuepfung...
  python -m pip install pywin32
)

python "%~dp0oxco_shortcut.py"
if errorlevel 1 (
  echo.
  echo Verknuepfung konnte nicht erstellt werden.
  pause
  exit /b 1
)

echo.
echo Optional: pip install pywin32  (setzt AppUserModelID fuer die Taskleiste)
pause
exit /b 0
