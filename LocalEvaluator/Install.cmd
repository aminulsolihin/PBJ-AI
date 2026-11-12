@echo off
title Local Evaluator setup
rem One-click setup: installs what is missing (Python, Ollama, the local model), the add-in's own packages,
rem a localhost certificate, the Excel registration, and starts the engine. No administrator rights needed.
echo Local Evaluator setup
echo =====================
echo This sets up the offline bid-evaluation add-in for Excel on this computer.
echo It needs internet now; afterwards the add-in works offline.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if errorlevel 1 (
  echo.
  echo Setup did not finish. The message above says why. You can run Install.cmd again; finished steps are skipped.
)
echo.
pause
