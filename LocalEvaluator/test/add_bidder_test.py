"""Test adding bidders on a fresh copy of the real-layout workbook, through the running engine.

    venv\\Scripts\\python.exe test\\add_bidder_test.py
"""
import hashlib
import json
import os
import shutil
import ssl
import sys
import urllib.request

import pythoncom
import win32com.client
import win32process

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "app"))
import excel_io  # noqa: E402

SRC = r"C:\Users\User\Downloads\Form 11 A _Lot 2_Automatic Extractor.xlsx"
WB = os.path.join(HERE, "Add bidder test.xlsx")
CTX = ssl.create_default_context()


def call(path, body):
    body = dict(body, workbook=WB)
    req = urllib.request.Request("https://localhost:47821" + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json", "X-Local-Evaluator": "1"})
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{path} -> {e.code}: {e.read().decode('utf-8', 'replace')}")


def fp(ws, rows, cols=60):
    rng = ws.Range(ws.Cells(1, 1), ws.Cells(rows, cols))
    return hashlib.sha1(repr(rng.Formula).encode("utf-8")).hexdigest()[:12]


def last_row(ws):
    ur = ws.UsedRange
    return ur.Row + ur.Rows.Count - 1


def main():
    shutil.copyfile(SRC, WB)
    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    pid = win32process.GetWindowThreadProcessId(xl.Hwnd)[1]
    xl.Visible = False
    xl.DisplayAlerts = False
    wb = xl.Workbooks.Open(WB)
    try:
        adm, f11, res = wb.Worksheets("Administrasi"), wb.Worksheets("Form 11a_Lot 1"), wb.Worksheets("Resume")
        others = [ws for ws in wb.Worksheets if ws.Name not in ("Administrasi", "Form 11a_Lot 1", "Resume")]
        before = {"adm": fp(adm, 643), "f11": fp(f11, 506), "res": fp(res, 19),
                  "others": [fp(ws, min(last_row(ws), 1000)) for ws in others]}

        print("PLAN:", json.dumps(call("/api/bidder/plan-block", {}), ensure_ascii=False)[:900])
        out = call("/api/bidder/add-block", {"name": "PT Uji Tambahan Satu", "sheet": "Administrasi"})
        rep = out["report"]
        print("\nREPORT:", json.dumps({k: v for k, v in rep.items() if k != "backup"}, ensure_ascii=False))
        print("backup saved:", os.path.exists(rep["backup"]), os.path.basename(rep["backup"]))

        print("\nUNCHANGED old areas -> Administrasi:", before["adm"] == fp(adm, 643), "| Form 11a:", before["f11"] == fp(f11, 506),
              "| Resume rows 1-19:", before["res"] == fp(res, 19),
              "| other sheets:", before["others"] == [fp(ws, min(last_row(ws), 1000)) for ws in others])

        for ws, sheet in ((adm, "Administrasi"), (f11, "Form 11a_Lot 1")):
            info = next(s for s in rep["sheets"] if s["sheet"] == sheet)
            top, bottom = (int(x) for x in info["rows"].split("-"))
            n = info["nameRow"]
            lay = call("/api/layout", {"sheet": sheet})["profile"]
            t_new, t_first = lay["targets"][-1], lay["targets"][0]
            formulas = []
            grid = ws.Range(ws.Cells(top, 1), ws.Cells(bottom, 30)).Formula
            for r, row in enumerate(grid, top):
                for c, v in enumerate(row, 1):
                    if isinstance(v, str) and v.startswith("="):
                        formulas.append(f"{ws.Cells(r, c).Address.replace('$', '')}{v}")
            print(f"\n[{sheet}] blocks now: {len(lay['targets'])} | new block rows {top}-{bottom} | name row {n}: "
                  f"value={ws.Cells(n, 3).Value!r}")
            print("   formulas in the new block:", " ; ".join(formulas))
            print("   requirement numbers match block 1:",
                  [r["no"] for r in t_new["rows"] if r["kind"] == "item"] == [r["no"] for r in t_first["rows"] if r["kind"] == "item"],
                  "| requirement texts match:",
                  [r.get("requirement") for r in t_new["rows"]] == [r.get("requirement") for r in t_first["rows"]])
            first_item = min(r["row"] for r in t_new["rows"] if r["kind"] == "item")
            last_item = max(r["row"] for r in t_new["rows"] if r["kind"] == "item")
            start = (min(t_new["human"]) if t_new["human"] else t_new["cols"]["req"] + 1)
            typed = 0
            vals = ws.Range(ws.Cells(first_item, start), ws.Cells(last_item, 30)).Formula
            for row in vals:
                typed += sum(1 for v in row if v not in (None, "") and not str(v).startswith("="))
            print(f"   typed evaluator cells left in the new block (verdict columns onward): {typed}")
            b1_first = min(r["row"] for r in t_first["rows"] if r["kind"] == "item")
            thresholds_same = [ws.Cells(first_item + i, c).Formula == ws.Cells(b1_first + i, c).Formula
                               for i in range(last_item - first_item + 1) for c in range(t_new["cols"]["req"], t_new["cols"]["req"] + 2)]
            print("   requirement + next column identical to block 1:", all(thresholds_same),
                  "| merged header cells:", ws.Cells(t_new["headerRow"], t_new["cols"]["req"]).MergeArea.Rows.Count,
                  "| dropdown on verdict cell:", _has_list(ws.Cells(first_item, max(t_new["human"]))) if t_new["human"] else "n/a")

        row = rep["summary"]["row"]
        print(f"\n[Resume] new row {row}:")
        for c in range(1, 8):
            cell = res.Cells(row, c)
            f = str(cell.Formula2)
            print(f"   {cell.Address.replace('$', '')}: {f[:230]}  ->  {str(cell.Text)[:60]!r}")

        # second bidder, after AI columns exist and block 1 holds an AI result
        call("/api/prepare", {"sheet": "Administrasi"})
        call("/api/prepare", {"sheet": "Form 11a_Lot 1"})
        lay = call("/api/layout", {"sheet": "Administrasi"})["profile"]
        t1 = lay["targets"][0]
        row1 = next(r["row"] for r in t1["rows"] if r["kind"] == "item")
        excel_io.write_result(adm, row1, t1["col"], {"label": "Not Meet", "note": "Deviation – test.\n\nID: Penyimpangan – uji.",
                                                     "en_len": len("Deviation – test."), "refs": "1. x.pdf (p. 1)", "link": None},
                              lay["font"], lay["labels"])
        out = call("/api/bidder/add-block", {"name": "PT Uji Tambahan Dua", "sheet": "Administrasi"})
        lay = out["profile"]
        t_new = lay["targets"][-1]
        new_first = next(r["row"] for r in t_new["rows"] if r["kind"] == "item")
        cell = adm.Cells(new_first, t_new["col"])
        print(f"\n[second bidder] blocks: {len(lay['targets'])} | names of the last two: {[t['bidder'] for t in lay['targets'][-2:]]}")
        print(f"   AI columns on the new block: {bool(t_new['col'])} | new AI verdict cell empty: {cell.Value is None} | no fill: {cell.Interior.ColorIndex == -4142}"
              f" | block 1 AI result kept: {adm.Cells(row1, t1['col']).Value!r}")
        print("   Resume rows:", [(str(res.Cells(r, 1).Text), str(res.Cells(r, 2).Text)) for r in (19, 20, 21)])
        print("   second report summary:", out["report"]["summary"], "| not extended:", out["report"]["notExtended"])
        wb.Save()
    finally:
        wb.Close(False)
        xl.Quit()
        del wb, xl
        import subprocess
        import time
        time.sleep(3)
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)     # my own hidden test Excel only
    import openpyxl
    check = openpyxl.load_workbook(WB)
    print("\nsaved file reopens cleanly:", [ws.title for ws in check.worksheets] == ["Resume", "Administrasi", "Form 11a_Lot 1", "Form 15", "Form 8 A", "Form 13"],
          "| Administrasi rows:", check["Administrasi"].max_row)


def _has_list(cell):
    try:
        return cell.Validation.Type == 3
    except Exception:
        return False


if __name__ == "__main__":
    main()
