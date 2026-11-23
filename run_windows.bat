@echo off
setlocal
cd /d "%~dp0"
title BATTLE-PY - WRAITH PROTOCOL
if exist ".venv\Scripts\python.exe" (
  set "GAMEPY=.venv\Scripts\python.exe"
) else (
  where py >nul 2>&1
  if not errorlevel 1 (
    set "GAMEPY=py -3"
  ) else (
    set "GAMEPY=python"
  )
)
echo [BATTLE-PY] Launching with %GAMEPY%
%GAMEPY% -u main.py
if errorlevel 1 (
  echo.
  echo [ERROR] The game encountered a problem. The console is staying open.
  echo [ERROR] Look for battle-py-error.log in this directory.
  echo [ERROR] You can also run: %GAMEPY% main.py --self-check
)
echo.
echo Press any key to close this window...
pause >nul
