@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on PATH.
  pause
  exit /b 1
)

echo Installing runtime + PyInstaller...
python -m pip install --upgrade pip
if errorlevel 1 goto :err
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto :err
python -m pip install "pyinstaller>=6.0"
if errorlevel 1 goto :err

if exist "dist\Oxco" rmdir /s /q "dist\Oxco"
if exist "build\Oxco" rmdir /s /q "build\Oxco"

echo Building one-dir bundle...
pyinstaller --noconfirm --clean --windowed --onedir --name Oxco --collect-all cv2 "%~dp0oxco_gui.py"
if errorlevel 1 goto :err

rem Compare subprocess expects compare.py and settings.example.ini next to Oxco.exe (not only under _internal).
copy /Y "%~dp0compare.py" "%~dp0dist\Oxco\compare.py" >nul
copy /Y "%~dp0settings.example.ini" "%~dp0dist\Oxco\settings.example.ini" >nul

echo.
echo Build output:  dist\Oxco\Oxco.exe
echo Copy optional: ffmpeg.exe ffprobe.exe into dist\Oxco\ for bundled tool support.
pause
exit /b 0

:err
echo.
echo Build failed.
pause
exit /b 1
