"""Hold a test workbook open in a hidden test Excel for a while, then close it without saving.

    venv\\Scripts\\python.exe test\\hold_open.py "<workbook>" <seconds>
"""
import subprocess
import sys
import time

import pythoncom
import win32com.client
import win32process

path, seconds = sys.argv[1], int(sys.argv[2])
pythoncom.CoInitialize()
xl = win32com.client.DispatchEx("Excel.Application")
pid = win32process.GetWindowThreadProcessId(xl.Hwnd)[1]
xl.Visible = False
xl.DisplayAlerts = False
wb = xl.Workbooks.Open(path)
try:
    time.sleep(seconds)
finally:
    wb.Close(False)
    xl.Quit()
    del wb, xl
    time.sleep(3)
    subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)   # this script's own hidden Excel only
