"""Read and write the workbook that is open in Excel, through Excel's automation interface (COM).

Two sheet layouts are recognised, both found from the sheet itself (nothing is hard-coded):

  stacked  The criteria table is repeated down the sheet, one block per bidder, each under a
           "Name of Bidder / Proposer" row (World Bank style forms such as Form 11A).
           One set of three AI Evaluation columns, to the right of the table, serves every block.
  side     One criteria table; each bidder gets its own set of three AI Evaluation columns.

Rules carried over from the evaluate-tech-spec skill:
- Only columns whose header contains "(AI Evaluation)" are ever written. Human columns
  (Document Reference, Determination, Remark ...) are never touched.
- The AI set is added once and updated in place.
- Notes are English (black) + "ID: " Indonesian (blue) in one cell.
"""
import os
import re
import time

import pythoncom
import win32com.client

from criteria import _NUM, _SUB
from engine import ID_MARK, LABELS

AI = "(AI Evaluation)"
HEADERS = ("REMARKS (AI Evaluation)",
           "NOTES (AI Evaluation) – English / Bahasa Indonesia",
           "ATTACHED DOCUMENT (AI Evaluation)")
WIDTHS = (17, 62, 38)
LABEL_COLOURS = {"Meet": ("#C6EFCE", "#006100"),
                 "Not Meet": ("#FFC7CE", "#9C0006"),
                 "Clarification Required": ("#FFEB9C", "#9C5700")}
XL_NONE, XL_TOP, XL_CENTER, XL_CONTINUOUS, XL_THIN, XL_LIST = -4142, -4160, -4108, 1, 2, 3
BUSY = {-2147418111, -2146777998, -2147417846}   # Excel is busy / a cell is being edited
NO_WORDS = {"no", "nomor", "#", "item", "item no", "s/n", "sn", "ref", "id"}
REQ_HEADER = re.compile(r"^(requirements?|persyaratan|kriteria|criteria|criterion|uraian|spesifikasi|specifications?)\b", re.I)
DOC_HEADER = re.compile(r"doc|dokumen|evidence|bukti", re.I)
BIDDER_ROW = re.compile(r"^(name of (the )?(bidder|proposer|tenderer)|nama (peserta|penyedia|penawar|perusahaan)|bidder name)", re.I)
EVAL_HEADER = re.compile(r"^(document reference|determination|remarks?|keterangan|catatan|hasil evaluasi|evaluator)", re.I)
ITEM_NO = re.compile(r"^([A-Za-z]|[ivxIVX]{1,4})[.)]?$")     # "A", "b)", "iv." besides the digit forms in _NUM


class ExcelError(Exception):
    pass


def rgb(hex_colour):
    h = hex_colour.lstrip("#")
    return int(h[0:2], 16) | int(h[2:4], 16) << 8 | int(h[4:6], 16) << 16


def with_retry(fn, seconds=90):
    """Run fn, waiting patiently while Excel is busy (for example while the user types in a cell)."""
    end = time.time() + seconds
    while True:
        try:
            return fn()
        except pythoncom.com_error as exc:
            inner = exc.excepinfo[5] if exc.excepinfo else None
            if (exc.hresult in BUSY or inner in BUSY) and time.time() < end:
                time.sleep(1.5)
                continue
            raise


def txt(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def safe(text):
    """Stop Excel from reading text as a formula."""
    text = str(text or "")
    return "'" + text if text[:1] in "=+-@" else text


# ------------------------------------------------------------------ connecting
def _open_workbooks():
    """Every workbook open in any Excel window on this computer, as (display name, moniker)."""
    rot = pythoncom.GetRunningObjectTable()
    ctx = pythoncom.CreateBindCtx(0)
    found = []
    for moniker in rot.EnumRunning():
        try:
            name = moniker.GetDisplayName(ctx, None)
        except pythoncom.com_error:
            continue
        if name.startswith("!") or name.startswith("clsid:"):
            continue
        found.append((name, moniker))
    return rot, found


def connect(hint=None):
    """Find the workbook the pane belongs to, in whichever Excel window has it open.

    With a hint (the workbook's full path, or its name while unsaved) the exact workbook is
    returned or an error is raised: the engine never falls back to some other open workbook.
    """
    pythoncom.CoInitialize()
    if hint:
        target = hint.lower().replace("/", "\\")
        rot, books = _open_workbooks()
        exact = [m for n, m in books if n.lower().replace("/", "\\") == target]
        if not exact and "\\" not in target and ":" not in target:        # unsaved workbook: match by name
            exact = [m for n, m in books if os.path.basename(n).lower() == target]
        for moniker in exact:
            try:
                obj = rot.GetObject(moniker).QueryInterface(pythoncom.IID_IDispatch)
                wb = win32com.client.Dispatch(obj)
                return wb.Application, wb
            except (pythoncom.com_error, AttributeError):
                continue
        raise ExcelError(f"The workbook \"{os.path.basename(hint)}\" was not found among the open Excel files. "
                         f"Save it, then reopen this pane.")
    try:
        xl = win32com.client.GetActiveObject("Excel.Application")
    except pythoncom.com_error:
        raise ExcelError("Excel is not running, or no workbook is open.")
    wb = xl.ActiveWorkbook
    if wb is None:
        raise ExcelError("No workbook is open in Excel.")
    return xl, wb


# ------------------------------------------------------------------- profiling
def _grid(ws, max_rows=5000, max_cols=120):
    ur = ws.UsedRange
    last_row = min(ur.Row + ur.Rows.Count - 1, max_rows)
    last_col = min(ur.Column + ur.Columns.Count - 1, max_cols)
    vals = ws.Range(ws.Cells(1, 1), ws.Cells(last_row, last_col)).Value
    if not isinstance(vals, tuple):
        vals = ((vals,),)
    return [[txt(v) for v in row] for row in vals]


def _is_no(text):
    return bool(_NUM.match(text) or ITEM_NO.match(text))


def _parse_rows(grid, first, end, c_no, c_req, c_doc):
    """Requirement rows between two 0-based grid rows. Trailing non-requirement rows are dropped."""
    rows, section, parent = [], "", None
    for r in range(first, min(end, len(grid))):
        no, req = grid[r][c_no], grid[r][c_req]
        doc = grid[r][c_doc] if c_doc is not None else ""
        if not req:
            continue
        if no and _is_no(no):
            item = {"row": r + 1, "no": no, "requirement": req, "doc": doc, "kind": "item", "section": section}
            rows.append(item)
            parent = item
            continue
        if no:
            continue                                   # a label such as "Project" in the number column
        sub = _SUB.match(req)
        if sub and parent:
            parent["group"] = True
            rows.append({"row": r + 1, "no": parent["no"] + sub.group(1).lower(), "requirement": sub.group(2).strip(),
                         "doc": doc, "kind": "item", "child": True, "parent": parent["requirement"], "section": section})
        else:
            section, parent = req, None
            rows.append({"row": r + 1, "kind": "section", "text": req})
    while rows and rows[-1]["kind"] != "item":          # signatures, dates, the next block's title ...
        rows.pop()
    # "5" ending with ":" followed by "5a", "5b" ... is a heading for its children
    items = [x for x in rows if x["kind"] == "item"]
    for i, it in enumerate(items[:-1]):
        nxt = items[i + 1]
        if it["requirement"].rstrip().endswith(":") and nxt["no"].startswith(it["no"]) and len(nxt["no"]) > len(it["no"]):
            it["group"] = True
            for later in items[i + 1:]:
                if later["no"].startswith(it["no"]) and len(later["no"]) > len(it["no"]):
                    later["parent"] = it["requirement"]
                else:
                    break
    return rows


def _labels(ws, row, cols):
    """The sheet's own verdict words, read from the dropdown of a human verdict column.

    Returns canonical -> text shown, e.g. {"Meet": "Qualified", "Not Meet": "Not Qualified", ...}.
    """
    for c in cols:
        try:
            v = ws.Cells(row, c).Validation
            if v.Type != XL_LIST:
                continue
            formula = str(v.Formula1 or "")
        except pythoncom.com_error:
            continue
        if formula.startswith("="):
            try:
                vals = ws.Range(formula[1:]).Value
                opts = [txt(x) for r in (vals if isinstance(vals, tuple) else ((vals,),)) for x in r]
            except pythoncom.com_error:
                continue
        else:
            opts = [o.strip() for o in re.split(r"[,;]", formula)]
        opts = [o for o in opts if o]
        neg = next((o for o in opts if re.search(r"\b(not|non|tidak|fail|gagal)\b", o, re.I)), None)
        ask = next((o for o in opts if re.search(r"clarif|klarif", o, re.I)), None)
        pos = next((o for o in opts if o not in (neg, ask)), None)
        if pos and neg:
            return {"Meet": pos, "Not Meet": neg, "Clarification Required": ask or "Clarification Required"}
    return {k: k for k in LABELS}


def _status(grid, items, col0, shown):
    """What one bidder's AI cells already hold. col0 is the 0-based REMARKS column."""
    back = {v: k for k, v in shown.items()}
    counts = {k: 0 for k in LABELS}
    filled, edited = [], []
    for it in items:
        row = grid[it["row"] - 1]
        label = row[col0] if col0 < len(row) else ""
        note = row[col0 + 1] if col0 + 1 < len(row) else ""
        if not label and not note:
            continue
        filled.append(it["row"])
        if label in back:
            counts[back[label]] += 1
        if label not in back or ID_MARK not in note:
            edited.append(it["row"])
    return counts, filled, edited


def profile(ws):
    """Describe the criteria table(s) on a sheet. Returns None when there is none."""
    grid = _grid(ws)
    width = max((len(r) for r in grid), default=0)
    heads = []
    for r, row in enumerate(grid):
        c_req = next((c for c, v in enumerate(row) if REQ_HEADER.match(v) and AI not in v and len(v) < 60), None)
        if c_req is None:
            continue
        c_no = next((c for c, v in enumerate(row[:c_req]) if v.lower().rstrip(".") in NO_WORDS), None)
        if c_no is not None:
            heads.append((r, c_no, c_req))
    if not heads:
        return None

    blocks = []
    for i, (hr, c_no, c_req) in enumerate(heads):
        floor = heads[i - 1][0] + 1 if i else 0
        name, name_row = None, None
        for r in range(hr - 1, max(floor, hr - 10) - 1, -1):
            hit = next((c for c, v in enumerate(grid[r][:8]) if BIDDER_ROW.match(v)), None)
            if hit is not None:
                name = next((v for v in grid[r][hit + 1:] if v and v != "0"), "")
                name_row = r
                break
        header = grid[hr]
        span = int(ws.Cells(hr + 1, c_req + 1).MergeArea.Rows.Count)
        above = grid[hr - 1] if hr > 0 and (name_row is None or hr - 1 > name_row) else []
        grouped = sum(1 for v in above if v) >= 2 or any(EVAL_HEADER.match(v) for v in above)
        top = hr - 1 if grouped else hr
        c_doc = next((c for c in range(c_req + 1, len(header)) if DOC_HEADER.search(header[c]) and AI not in header[c]), None)
        head_rows = range(top, hr + span)
        human = sorted({c for r in head_rows for c, v in enumerate(grid[r]) if c > c_req and EVAL_HEADER.match(v) and AI not in v})
        ai_cols = sorted({c for r in head_rows for c, v in enumerate(grid[r]) if v.startswith(HEADERS[0])})
        last_head = max((c for r in head_rows for c, v in enumerate(grid[r]) if v and AI not in v), default=c_req)
        end = heads[i + 1][0] if i + 1 < len(heads) else len(grid)
        rows = _parse_rows(grid, hr + span, end, c_no, c_req, c_doc)
        title = next((v for v in (grid[top] if grouped else []) if v), "")
        blocks.append({"bidder": name, "headerRow": hr + 1, "headerTop": top + 1, "headerBottom": hr + span,
                       "cols": {"no": c_no + 1, "req": c_req + 1, "doc": (c_doc + 1) if c_doc is not None else None},
                       "human": [c + 1 for c in human], "aiCols": [c + 1 for c in ai_cols], "lastHead": last_head + 1,
                       "rows": rows, "title": title})

    stacked = any(b["bidder"] is not None for b in blocks)
    if not stacked:
        blocks = blocks[:1]
    first = next((b for b in blocks if any(x["kind"] == "item" for x in b["rows"])), blocks[0])
    todo0 = [x for x in first["rows"] if x["kind"] == "item" and not x.get("group")]
    verdict_cols = first["human"] or list(range(first["cols"]["req"] + 1, first["lastHead"] + 1))
    shown = _labels(ws, todo0[0]["row"], verdict_cols) if todo0 else {k: k for k in LABELS}
    sample = ws.Cells(todo0[0]["row"] if todo0 else first["headerRow"], first["cols"]["req"])
    sheet_title = next((v for row in grid[:first["headerTop"] - 1] for v in row if v and not BIDDER_ROW.match(v)), ws.Name)

    targets = []
    if stacked:
        ai_col = next((b["aiCols"][0] for b in blocks if b["aiCols"]), None)
        for b in blocks:
            items = [x for x in b["rows"] if x["kind"] == "item" and not x.get("group")]
            ready = bool(ai_col and b["aiCols"])
            counts, filled, edited = _status(grid, items, ai_col - 1, shown) if ready else ({k: 0 for k in LABELS}, [], [])
            targets.append(dict(b, bidder=b["bidder"] or "", col=ai_col if ready else None, toEvaluate=len(items),
                                counts=counts, filled=filled, edited=edited))
        start = max(b["lastHead"] for b in blocks)               # 0-based index of the first column after the table
        free = start
        while free < width and any((row[free + k] if free + k < len(row) else "") for k in range(3) for row in grid):
            free += 1
    else:
        ai_col, free = None, width
        items = [x for x in first["rows"] if x["kind"] == "item" and not x.get("group")]
        for c in first["aiCols"]:
            head = grid[first["headerRow"] - 1][c - 1]
            name = head.split("\n", 1)[1].strip() if "\n" in head else ""
            counts, filled, edited = _status(grid, items, c - 1, shown)
            targets.append(dict(first, bidder=name, col=c, toEvaluate=len(items), counts=counts, filled=filled, edited=edited))

    return {
        "sheet": ws.Name, "mode": "stacked" if stacked else "side", "title": first["title"] or sheet_title,
        "labels": shown, "targets": targets, "table": first, "toEvaluate": len(todo0),
        "aiCol": ai_col, "freeCol": free + 1,
        "lastRow": max((x["row"] for b in blocks for x in b["rows"]), default=first["headerBottom"]),
        "font": {"name": str(sample.Font.Name or "Calibri"), "size": float(sample.Font.Size or 11)},
    }


def row_extras(ws, target):
    """Other filled cells of each requirement row (thresholds, bidder information ...), with their headings.

    Returns {row: [(heading, value), ...]} for the columns between Requirement and the human verdict columns.
    """
    c_req, c_doc = target["cols"]["req"], target["cols"]["doc"]
    stop = min(target["human"]) if target["human"] else target["lastHead"] + 1
    cols = [c for c in range(c_req + 1, stop) if c != c_doc]
    if not cols:
        return {}
    heading = {}
    for c in cols:
        parts = []
        for r in range(target["headerTop"], target["headerBottom"] + 1):
            v = txt(ws.Cells(r, c).MergeArea.Cells(1, 1).Value)
            v = re.sub(r"\s+", " ", v)
            if v and v not in parts and AI not in v:
                parts.append(v)
        heading[c] = " / ".join(parts)
    out = {}
    for it in target["rows"]:
        if it["kind"] != "item":
            continue
        vals = ws.Range(ws.Cells(it["row"], cols[0]), ws.Cells(it["row"], cols[-1])).Value
        vals = vals[0] if isinstance(vals, tuple) else (vals,)
        got = [(heading[c], txt(v)[:500]) for c, v in zip(range(cols[0], cols[-1] + 1), vals) if c in heading and txt(v)]
        if got:
            out[it["row"]] = got
    return out


# --------------------------------------------------------------------- writing
def _unique_sheet_name(wb, wanted):
    base = re.sub(r"[\[\]:*?/\\]", " ", wanted).strip()[:28] or "Criteria"
    names = {ws.Name.lower() for ws in wb.Worksheets}
    name, n = base, 2
    while name.lower() in names:
        name = f"{base} {n}"
        n += 1
    return name


def create_sheet(wb, title, items):
    """Build a simple criteria sheet from an imported or pasted criteria list."""
    has_doc = any(i.get("doc") for i in items if i["kind"] == "item")
    ncols = 3 if has_doc else 2
    ws = wb.Worksheets.Add()
    ws.Move(None, wb.Worksheets(wb.Worksheets.Count))                              # after the last sheet
    ws = wb.Worksheets(wb.Worksheets.Count)
    ws.Name = _unique_sheet_name(wb, title)
    ws.Cells(1, 1).Value = safe(title)
    ws.Cells(1, 1).Font.Bold = True
    ws.Cells(1, 1).Font.Size = 14
    heads = ["No.", "Requirement", "Doc Required"][:ncols]
    table = [heads]
    for it in items:
        if it["kind"] == "section":
            table.append(["", safe(it["text"]), ""][:ncols])
        else:
            table.append([safe(it.get("no", "")), safe(it["requirement"]), safe(it.get("doc", ""))][:ncols])
    last = 1 + len(table)
    rng = ws.Range(ws.Cells(2, 1), ws.Cells(last, ncols))
    ws.Range(ws.Cells(2, 1), ws.Cells(last, 1)).NumberFormat = "@"
    rng.Value = tuple(tuple(r) for r in table)
    rng.WrapText = True
    rng.VerticalAlignment = XL_TOP
    rng.Borders.LineStyle = XL_CONTINUOUS
    rng.Borders.Weight = XL_THIN
    ws.Range(ws.Cells(2, 1), ws.Cells(last, 1)).HorizontalAlignment = XL_CENTER
    head = ws.Range(ws.Cells(2, 1), ws.Cells(2, ncols))
    head.Font.Bold = True
    head.Font.Color = rgb("#FFFFFF")
    head.Interior.Color = rgb("#1F4E78")
    head.HorizontalAlignment = XL_CENTER
    head.VerticalAlignment = XL_CENTER
    for i, it in enumerate(items):
        if it["kind"] == "section":
            sec = ws.Range(ws.Cells(3 + i, 1), ws.Cells(3 + i, ncols))
            sec.Font.Bold = True
            sec.Interior.Color = rgb("#D9D9D9")
    for col, width in zip(range(1, ncols + 1), (9, 80, 36)):
        ws.Columns(col).ColumnWidth = width
    ws.Range(ws.Cells(3, 1), ws.Cells(last, ncols)).Rows.AutoFit()
    ws.Activate()
    return ws


def _write_headers(ws, block, col, names, font):
    """Three header cells over the block's header rows, styled like the table's own header."""
    ref = ws.Cells(block["headerRow"], block["cols"]["req"])
    has_fill = ref.Interior.ColorIndex != XL_NONE
    top, bottom = block["headerTop"], block["headerBottom"]
    for i, text in enumerate(names):
        area = ws.Range(ws.Cells(top, col + i), ws.Cells(bottom, col + i))
        if bottom > top:
            area.Merge()
        ws.Cells(top, col + i).Value = text
        area.WrapText = True
        area.HorizontalAlignment = XL_CENTER
        area.VerticalAlignment = XL_CENTER
        area.Font.Name = ref.Font.Name
        area.Font.Size = ref.Font.Size
        area.Font.Bold = True
        area.Font.Color = int(ref.Font.Color) if has_fill else rgb("#000000")
        area.Interior.Color = int(ref.Interior.Color) if has_fill else rgb("#D9E1F2")
        area.Borders.LineStyle = XL_CONTINUOUS
        area.Borders.Weight = XL_THIN
    if top == bottom and ws.Rows(top).RowHeight < 45:
        ws.Rows(top).RowHeight = 45


def _format_body(ws, block, col, font, shown):
    items = [x for x in block["rows"] if x["kind"] == "item"]
    if not items:
        return
    first, last = block["headerBottom"] + 1, max(x["row"] for x in block["rows"])
    body = ws.Range(ws.Cells(first, col), ws.Cells(last, col + 2))
    body.WrapText = True
    body.VerticalAlignment = XL_TOP
    body.Font.Name = font["name"]
    body.Font.Size = font["size"]
    body.Borders.LineStyle = XL_CONTINUOUS
    body.Borders.Weight = XL_THIN
    options = ",".join(shown[k] for k in LABELS)
    for it in items:
        if it.get("group"):
            continue
        try:                                            # same dropdown as the human verdict column
            v = ws.Cells(it["row"], col).Validation
            v.Delete()
            v.Add(XL_LIST, 1, 1, options)
        except pythoncom.com_error:
            pass


def prepare_stacked(ws, prof):
    """Add the single AI Evaluation column set to every bidder block that lacks it. Returns the column."""
    col = prof["aiCol"] or prof["freeCol"]
    added = 0
    for t in prof["targets"]:
        if t["col"]:
            continue
        _write_headers(ws, t, col, HEADERS, prof["font"])
        _format_body(ws, t, col, prof["font"], prof["labels"])
        added += 1
    if added:
        for i, w in enumerate(WIDTHS):
            ws.Columns(col + i).ColumnWidth = w
    return col


def add_bidder(ws, prof, name):
    """Side layout: add this bidder's own three AI Evaluation columns (once)."""
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        raise ExcelError("Give the bidder a name.")
    if any(t["bidder"].lower() == name.lower() for t in prof["targets"]):
        raise ExcelError(f"'{name}' already has AI Evaluation columns on this sheet.")
    col = prof["freeCol"]
    _write_headers(ws, prof["table"], col, [h + "\n" + name for h in HEADERS], prof["font"])
    _format_body(ws, prof["table"], col, prof["font"], prof["labels"])
    for i, w in enumerate(WIDTHS):
        ws.Columns(col + i).ColumnWidth = w
    return col


def snapshot(ws, target):
    """Current contents of one bidder's AI cells, kept on disk before a rerun."""
    out = []
    for it in target["rows"]:
        if it["kind"] != "item":
            continue
        cells = [txt(ws.Cells(it["row"], target["col"] + i).Value) for i in range(3)]
        if any(cells):
            out.append({"row": it["row"], "no": it["no"], "label": cells[0], "note": cells[1], "refs": cells[2]})
    return out


def write_result(ws, row, col, res, font, shown):
    """Write one requirement's verdict, bilingual note and attached-document list."""
    label = ws.Cells(row, col)
    fill, ink = LABEL_COLOURS[res["label"]]
    label.Value = shown.get(res["label"], res["label"])
    label.Interior.Color = rgb(fill)
    label.Font.Color = rgb(ink)
    label.Font.Bold = True
    label.HorizontalAlignment = XL_CENTER
    label.VerticalAlignment = XL_TOP
    label.WrapText = True

    note = ws.Cells(row, col + 1)
    text = res["note"]
    note.Value = safe(text)
    note.WrapText = True
    note.VerticalAlignment = XL_TOP
    note.Font.Name, note.Font.Size = font["name"], font["size"]
    note.Font.Bold = False
    note.Font.Color = rgb("#000000")
    blue_from = res["en_len"] + 1                      # 1-based position of "\n\nID: ..."
    if len(text) >= blue_from:
        try:
            part = note.GetCharacters(blue_from, len(text) - res["en_len"])
        except AttributeError:
            part = note.Characters(blue_from, len(text) - res["en_len"])
        part.Font.Color = rgb("#0000FF")

    refs = ws.Cells(row, col + 2)
    refs.Hyperlinks.Delete()
    refs.Value = safe(res["refs"])
    refs.WrapText = True
    refs.VerticalAlignment = XL_TOP
    if res.get("link") and res["refs"]:
        # one file: the cell opens it.  Several files: no link, so a click never opens the wrong one.
        # positional: Anchor, Address, SubAddress, ScreenTip, TextToDisplay
        ws.Hyperlinks.Add(refs, res["link"], "", "Open " + os.path.basename(res["link"]), res["refs"])
        refs.Font.Color = rgb("#0563C1")
        refs.Font.Underline = 2
    else:
        refs.Font.Color = rgb("#000000")
        refs.Font.Underline = XL_NONE
    refs.Font.Name, refs.Font.Size = font["name"], font["size"]
    # Make the row tall enough to show the note, but never shrink a row the user sized.
    try:
        before = ws.Rows(row).RowHeight
        ws.Rows(row).AutoFit()
        if ws.Rows(row).RowHeight < before:
            ws.Rows(row).RowHeight = before
    except pythoncom.com_error:
        pass
