@echo off
rem Attach the Local Evaluator pane to an evaluation workbook, then open it.
rem Double-click and choose the workbook, or drag a workbook onto this file. The workbook must be closed.
"%~dp0venv\Scripts\python.exe" "%~dp0app\launcher.py" add %1
echo.
pause
