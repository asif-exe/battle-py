@echo off
setlocal
cd /d "%~dp0"
title BATTLE-PY - SETUP AND PLAY
echo.
echo  BATTLE-PY // WRAITH PROTOCOL
 echo ---------------------------------
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
)
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Could not create a Python virtual environment.
  echo Install Python 3.10+ and ensure the PATH option is selected.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [ERROR] Installing Panda3D failed. Check the internet and Python version.
  echo Using a 64-bit Python 3.11 or 3.12 installation is recommended.
  pause
  exit /b 1
)
echo.
echo Running tests before launching...
".venv\Scripts\python.exe" main.py --self-check
if errorlevel 1 (
  echo [ERROR] Project check failed. Please share the output.
  pause
  exit /b 1
)
call run_windows.bat
