"""Repair the summary sheet's result formulas on a COPY of a block-per-bidder workbook.

The workbook you name is never changed. A copy is made beside it ("... (Resume repaired - to check).xlsx"),
the copy is repaired in a hidden Excel, every change is listed on a log sheet inside the copy, and the copy
is compared with the original to confirm nothing else differs.

    python repair_summary.py "C:\\path\\Workbook.xlsx" [--items 1,2,3,4,5,8,10,11,12]

--items: for an "all of these rows must be Qualified" formula, which requirement rows to test, counted
         1, 2, 3 ... down the evaluated rows of one bidder block.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

import pythoncom
import win32com.client
import win32process

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blocks      # noqa: E402
import excel_io    # noqa: E402


def fingerprint(ws, rows=1200, cols=60):
    rng = ws.Range(ws.Cells(1, 1), ws.Cells(rows, cols))
    return hashlib.sha1(repr(rng.Formula).encode("utf-8")).hexdigest()


def main():
    source = os.path.abspath(sys.argv[1])
    items = None
    if "--items" in sys.argv:
        items = [int(x) - 1 for x in sys.argv[sys.argv.index("--items") + 1].split(",")]
    stem, ext = os.path.splitext(source)
    copy = f"{stem} (Resume repaired - to check){ext}"
    pythoncom.CoInitialize()

    original = None
    try:
        original = excel_io.connect(source)[1]              # open in Excel: copy its current state, saved or not
        original.SaveCopyAs(copy)
        how = "copied from the workbook as it is open now (including unsaved changes)"
    except excel_io.ExcelError:
        shutil.copyfile(source, copy)
        how = "copied from the file on disk"

    xl = win32com.client.DispatchEx("Excel.Application")    # a separate, hidden Excel just for the copy
    pid = win32process.GetWindowThreadProcessId(xl.Hwnd)[1]
    xl.Visible = False
    xl.DisplayAlerts = False
    wb = xl.Workbooks.Open(copy)
    try:
        summary_name = blocks.survey(wb, need_free_row=False)[1]["sheet"]
        before = {ws.Name: fingerprint(ws) for ws in wb.Worksheets}
        cells_before = wb.Worksheets(summary_name).Range("A1:Z200").Formula
        report = blocks.repair_summary(wb, items)
        after = {ws.Name: fingerprint(ws) for ws in wb.Worksheets}
        cells_after = wb.Worksheets(summary_name).Range("A1:Z200").Formula
        differing = sorted(f"{blocks.excel_col(c + 1)}{r + 1}" for r, row in enumerate(cells_before)
                           for c, v in enumerate(row) if v != cells_after[r][c])
        logged = sorted(c["cell"] for c in report["changed"])
        sheets, summary, count = blocks.survey(wb, need_free_row=False)
        still_broken = [f"{blocks.excel_col(col)}{summary['base'] + r['k']}" for col in range(1, summary["width"] + 1)
                        if col != summary["col"] for r in blocks._study(summary, sheets, count, col) if r and not r["sound"]]
        errors = [f"{blocks.excel_col(c + 1)}{r + 1}" for r, row in enumerate(wb.Worksheets(summary_name).Range("A1:Z200").Value)
                  for c, v in enumerate(row) if isinstance(v, int) and v < -2146000000]
        check = {
            "other sheets identical to before": all(before[n] == after[n] for n in before if n != summary_name),
            "cells that differ on the summary sheet are exactly the logged ones": differing == logged,
            "formulas still not pointing at their own bidder": still_broken,
            "error values left on the summary sheet": errors,
        }
        if original is not None:
            check["other sheets identical to the open original"] = all(
                fingerprint(original.Worksheets(n)) == after[n] for n in before if n != summary_name)
        wb.Save()
    finally:
        wb.Close(False)
        xl.Quit()
        del wb, xl
        time.sleep(3)
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)    # this script's own hidden Excel only
    print(json.dumps({"copy": copy, "made": how, "report": report, "check": check}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
