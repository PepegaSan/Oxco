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

if not exist "%~dp0assets\oxco_icon.ico" (
  echo assets\oxco_icon.ico fehlt. Bitte zuerst: python scripts\make_oxco_icon.py
  goto :err
)

echo Building one-dir bundle...
pyinstaller --noconfirm --clean --windowed --onedir --name Oxco --icon "%~dp0assets\oxco_icon.ico" --add-data "%~dp0assets;assets" --hidden-import oxco_icon_embed --hidden-import oxco_winicon --collect-all cv2 "%~dp0oxco_gui.py"
if errorlevel 1 goto :err

rem Compare subprocess expects compare.py and settings.example.ini next to Oxco.exe (not only under _internal).
copy /Y "%~dp0compare.py" "%~dp0dist\Oxco\compare.py" >nul
copy /Y "%~dp0settings.example.ini" "%~dp0dist\Oxco\settings.example.ini" >nul
if exist "%~dp0assets" xcopy /E /I /Y /Q "%~dp0assets" "%~dp0dist\Oxco\assets\" >nul

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
