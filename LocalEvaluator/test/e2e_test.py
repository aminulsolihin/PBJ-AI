"""End-to-end tests against the running engine and real Excel windows.

    venv\\Scripts\\python.exe test\\e2e_test.py real       profile + prepare a COPY of the real-layout workbook
    venv\\Scripts\\python.exe test\\e2e_test.py evaluate   evaluate two rows of bidder 1 in that copy, check the cells
    venv\\Scripts\\python.exe test\\e2e_test.py side       simple one-table sheet: import criteria, add a bidder
    venv\\Scripts\\python.exe test\\e2e_test.py close      close the test workbooks
"""
import hashlib
import json
import os
import shutil
import ssl
import sys
import time
import urllib.request

import pymupdf
import pythoncom
import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "app"))
import excel_io  # noqa: E402

BASE = "https://localhost:47821"
REAL_SRC = r"C:\Users\User\Downloads\Form 11 A _Lot 2_Automatic Extractor.xlsx"
REAL = os.path.join(HERE, "Real layout test.xlsx")
SIDE = os.path.join(HERE, "Side layout test.xlsx")
FOLDER = os.path.join(HERE, "PT Contoh Alkes Nusantara")
CTX = ssl.create_default_context()        # validates against the Windows trust store


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json", "X-Local-Evaluator": "1"})
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=240) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{path} -> {e.code}: {e.read().decode('utf-8', 'replace')}")


def make_pdfs():
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((60, 80), "AKTA PENDIRIAN PERSEROAN TERBATAS\nPT CONTOH ALKES NUSANTARA\nNomor: 45\n"
                     "Pada hari ini, Senin, tanggal 3 Februari 2014, menghadap kepada saya, Hartono, S.H., M.Kn., Notaris di Jakarta.\n"
                     "Para penghadap mendirikan perseroan terbatas bernama PT Contoh Alkes Nusantara, berkedudukan di Jakarta Pusat.\n"
                     "Pengesahan Menteri Hukum dan HAM Nomor AHU-01234.AH.01.01.Tahun 2014 tanggal 20 Februari 2014.\n"
                     "Direktur Utama: Budi Santoso. Komisaris: Agus Wijaya.", fontsize=11)
    doc.save(os.path.join(FOLDER, "06 Akta Pendirian.pdf"))
    doc.close()
    src = pymupdf.open()                  # a "scan": a picture of a page, with no text layer
    p = src.new_page()
    p.insert_text((60, 90), "KARTU TANDA PENDUDUK\nPROVINSI DKI JAKARTA\nNIK : 3171011203750004\nNama : BUDI SANTOSO\n"
                  "Tempat/Tgl Lahir : JAKARTA, 12-03-1975\nPekerjaan : DIREKTUR\nBerlaku Hingga : SEUMUR HIDUP", fontsize=16)
    pix = p.get_pixmap(dpi=200)
    src.close()
    scan = pymupdf.open()
    sp = scan.new_page()
    sp.insert_image(sp.rect, pixmap=pix)
    scan.save(os.path.join(FOLDER, "07 KTP Direktur (scan).pdf"))
    scan.close()


def open_book(path, create=False):
    """The workbook, from whichever Excel window has it; otherwise opened in a separate test window."""
    pythoncom.CoInitialize()
    try:
        return excel_io.connect(path)[1]
    except excel_io.ExcelError:
        xl = win32com.client.DispatchEx("Excel.Application")     # a new Excel, apart from the user's own
        xl.Visible = True
        if create:
            wb = xl.Workbooks.Add()
            wb.SaveAs(path, 51)
            return wb
        return xl.Workbooks.Open(path)


def human_hash(ws, last_col):
    """Fingerprint of everything left of the AI columns (values and formulas)."""
    rng = ws.Range(ws.Cells(1, 1), ws.Cells(ws.UsedRange.Row + ws.UsedRange.Rows.Count - 1, last_col))
    return hashlib.sha1(repr(rng.Formula).encode("utf-8")).hexdigest()[:12]


def real():
    if not os.path.exists(REAL):
        shutil.copyfile(REAL_SRC, REAL)
    wb = open_book(REAL)
    for sheet in ("Administrasi", "Form 11a_Lot 1"):
        ws = wb.Worksheets(sheet)
        lay = call("/api/layout", {"workbook": REAL, "sheet": sheet})
        p = lay["profile"]
        t0 = p["targets"][0]
        named = [t for t in p["targets"] if t["bidder"]]
        print(f"\n[{sheet}] mode={p['mode']} title={p['title']!r} blocks={len(p['targets'])} with a bidder name={len(named)}")
        print(f"  labels={p['labels']}")
        print(f"  block 1: header rows {t0['headerTop']}-{t0['headerBottom']}, cols={t0['cols']}, human cols={t0['human']}, "
              f"last header col={t0['lastHead']}, requirement numbers={[r['no'] for r in t0['rows'] if r['kind'] == 'item' and not r.get('group')]}")
        print(f"  requirements per block: {sorted({t['toEvaluate'] for t in p['targets']})}; AI col now={p['aiCol']}, free col={p['freeCol']}")
        before = human_hash(ws, p["freeCol"] - 1)
        lay = call("/api/prepare", {"workbook": REAL, "sheet": sheet})
        p = lay["profile"]
        after = human_hash(ws, p["aiCol"] - 1)
        ready = sum(1 for t in p["targets"] if t["col"])
        top = ws.Cells(t0["headerTop"], p["aiCol"])
        print(f"  prepared: AI col={p['aiCol']}, blocks with AI headers={ready}/{len(p['targets'])}, header text={top.Value!r}, "
              f"merged rows={top.MergeArea.Rows.Count}, everything left of the AI columns unchanged={before == after}")
        again = call("/api/prepare", {"workbook": REAL, "sheet": sheet})["profile"]
        print(f"  prepare again adds nothing: AI col still {again['aiCol']}, free col {again['freeCol']}")
    wb.Save()
    print("\nREAL LAYOUT OK")


def evaluate():
    make_pdfs()
    wb = open_book(REAL)
    sheet = "Administrasi"
    ws = wb.Worksheets(sheet)
    lay = call("/api/layout", {"workbook": REAL, "sheet": sheet})
    p = lay["profile"]
    t = p["targets"][0]
    lay = call("/api/bidder/folder", {"workbook": REAL, "sheet": sheet, "name": t["bidder"], "folder": FOLDER})
    rows = {}
    for r in t["rows"]:
        if r["kind"] == "item":
            rows.setdefault(r["no"], r["row"])
    targets = [rows["5a"], rows["5d"]]        # deed of establishment (text PDF) and identity card (scanned PDF)
    before = human_hash(ws, p["aiCol"] - 1)
    print("evaluating rows", targets, "of block 1; label words:", p["labels"])
    call("/api/evaluate", {"workbook": REAL, "sheet": sheet, "bidders": [t["bidder"]], "rows": targets})
    while True:
        j = call("/api/job")
        if j["state"] != "running":
            break
        time.sleep(10)
    print("job:", j["state"], j["error"])
    print("\n".join(line.split("  ", 1)[1] if "  " in line else line for line in j["log"]))
    col = p["aiCol"]
    for r in targets:
        label, note, refs = (ws.Cells(r, col + i) for i in range(3))
        text = note.Value or ""
        cut = text.find("\n\nID: ")
        en_colour = note.GetCharacters(1, 5).Font.Color if hasattr(note, "GetCharacters") else note.Characters(1, 5).Font.Color
        id_part = (note.GetCharacters(cut + 3, 5) if hasattr(note, "GetCharacters") else note.Characters(cut + 3, 5)) if cut > 0 else None
        print(f"\nrow {r}: {label.Value} | fill {int(label.Interior.Color):06X} | EN colour {int(en_colour):06X} | ID colour "
              f"{'none' if id_part is None else format(int(id_part.Font.Color), '06X')} | links {refs.Hyperlinks.Count}")
        print(text)
        print("refs:", refs.Value)
    print("\neverything left of the AI columns unchanged:", before == human_hash(ws, col - 1))
    wb.Save()


def side():
    wb = open_book(SIDE, create=True)
    lay = call("/api/criteria/import", {"workbook": SIDE, "path": r"C:\Users\User\Downloads\Kriteria Administrasi.docx"})
    p = lay["profile"]
    print(f"sheet '{p['sheet']}' mode={p['mode']} to evaluate={p['toEvaluate']} labels={p['labels']} position={wb.Worksheets(p['sheet']).Index}/{wb.Worksheets.Count}")
    lay = call("/api/bidder/add", {"workbook": SIDE, "sheet": p["sheet"], "name": "PT Contoh Alkes Nusantara", "folder": FOLDER})
    t = lay["profile"]["targets"][0]
    print(f"bidder '{t['bidder']}' at column {t['col']}, folder remembered={t['folder'] == FOLDER}")
    lay = call("/api/bidder/add", {"workbook": SIDE, "sheet": p["sheet"], "name": "PT Kedua", "folder": ""})
    print("two bidders, columns:", [x["col"] for x in lay["profile"]["targets"]])
    wb.Save()
    print("SIDE LAYOUT OK")


def close():
    for path in (REAL, SIDE, os.path.join(HERE, "Test Package.xlsx")):
        try:
            wb = excel_io.connect(path)[1]
        except excel_io.ExcelError:
            continue
        xl = wb.Application
        wb.Close(True)
        if xl.Workbooks.Count == 0:
            xl.Quit()
        print("closed", os.path.basename(path))


if __name__ == "__main__":
    {"real": real, "evaluate": evaluate, "side": side, "close": close}[sys.argv[1]]()
