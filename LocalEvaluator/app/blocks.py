"""Add one more bidder to a workbook whose sheets hold one block per bidder.

Such workbooks have room for a fixed number of bidders. A new bidder needs, on every block-per-bidder
sheet, a new block of rows, and usually a new row on a summary sheet that the bidder names come from.

How it is done (nothing is hard-coded to one workbook):
  * The FIRST block of each sheet is the pattern: it is copied below the last block with Excel's own
    row copy, so formats, merged cells, dropdowns and row heights come along.
  * Every formula in the new block is then rebuilt from the first block's formula by meaning:
      - a reference inside the block            -> the same cell of the new block
      - a reference to another bidder sheet     -> the same cell of that sheet's NEW block
      - a reference to bidder 1's summary row   -> the new bidder's summary row
      - anything else                           -> unchanged
  * What evaluators typed for bidder 1 (bidder information, determinations, remarks, AI results)
    is emptied in the new block; requirement texts and thresholds stay.
  * The summary row is copied from the last bidder's row; each formula column takes the wiring that
    most existing bidders share and that stays inside the bidder's own block.
A copy of the workbook as it was is saved first.
"""
import collections
import datetime
import os
import re

import excel_io
from excel_io import AI, BIDDER_ROW, ExcelError, XL_NONE, rgb, txt

STRING = re.compile(r'"(?:[^"]|"")*"')
REF = re.compile(
    r"(?<![A-Za-z0-9_.!'$])"
    r"(?:(?P<sheet>'(?:[^']|'')+'|[A-Za-z_][A-Za-z0-9_.]*)!)?"
    r"(?P<c1>\$?[A-Z]{1,3})(?P<a1>\$?)(?P<n1>\d+)"
    r"(?::(?P<c2>\$?[A-Z]{1,3})(?P<a2>\$?)(?P<n2>\d+))?"
    r"(?![A-Za-z0-9_(!])")
SINGLE = re.compile(r"^=\s*(?:'((?:[^']|'')+)'|([A-Za-z_][A-Za-z0-9_.]*))!\$?([A-Z]{1,3})\$?(\d+)\s*$")
INPUT_HEADER = re.compile(r"bidder|proposer|peserta|penawar|penyedia", re.I)


def map_rows(formula, fn):
    """Rewrite the row numbers of every cell reference in a formula.

    fn(sheet name or None for the formula's own sheet, row number) returns the new row (int or text).
    Text inside double quotes is left alone.
    """
    def piece(part):
        def sub(m):
            raw = m.group("sheet")
            sheet = None if raw is None else (raw[1:-1].replace("''", "'") if raw.startswith("'") else raw)
            out = f"{m.group('c1')}{m.group('a1')}{fn(sheet, int(m.group('n1')))}"
            if m.group("c2"):
                out += f":{m.group('c2')}{m.group('a2')}{fn(sheet, int(m.group('n2')))}"
            return (raw + "!" if raw else "") + out
        return REF.sub(sub, part)

    out, pos = [], 0
    for m in STRING.finditer(formula):
        out.append(piece(formula[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(piece(formula[pos:]))
    return "".join(out)


def _col(letters):
    n = 0
    for ch in letters.replace("$", ""):
        n = n * 26 + ord(ch) - 64
    return n


def _formulas(ws, row1, row2, cols):
    vals = ws.Range(ws.Cells(row1, 1), ws.Cells(row2, cols)).Formula
    if not isinstance(vals, tuple):
        vals = ((vals,),)
    return [["" if v is None else str(v) for v in row] for row in vals]


def _get_formula(cell):
    """(formula text, is array formula). Dynamic-array formulas are read without the implicit-intersection '@'."""
    try:
        return str(cell.Formula2), bool(cell.HasArray)
    except Exception:
        return (str(cell.FormulaArray) if cell.HasArray else str(cell.Formula)), bool(cell.HasArray)


def _set_formula(cell, formula, array):
    if array:
        try:
            cell.Formula2 = formula
            return
        except Exception:
            cell.FormulaArray = formula
            return
    cell.Formula = formula


def _clear(cell):
    cell.MergeArea.ClearContents()


def survey(wb, need_free_row=True):
    """Read-only look at the workbook: its bidder sheets, the summary sheet and where a new bidder would go."""
    sheets = {}
    for ws in wb.Worksheets:
        prof = excel_io.profile(ws)
        if not prof or prof["mode"] != "stacked":
            continue
        grid = excel_io._grid(ws)
        names = []
        for t in prof["targets"]:
            # the "Name of Bidder" row sits a little above the block's header
            for r in range(t["headerTop"] - 2, max(t["headerTop"] - 12, -1), -1):
                hit = next((c for c, v in enumerate(grid[r][:8]) if BIDDER_ROW.match(v)), None) if r >= 0 else None
                if hit is not None:
                    names.append((r + 1, hit + 1))
                    break
        if len(names) != len(prof["targets"]) or not names:
            continue
        n1 = names[0][0]
        last_content = max(i + 1 for i, row in enumerate(grid) if any(row))
        if len(names) > 1:
            pitch = names[1][0] - n1                       # block 1 = rows 1 .. pitch
        else:
            pitch = last_content + 2
        b1_end = max(i + 1 for i, row in enumerate(grid[:pitch]) if any(row))
        label_col = names[0][1]
        name_col = next((c + 1 for c in range(label_col, len(grid[n1 - 1])) if grid[n1 - 1][c] and grid[n1 - 1][c] != "0"), label_col + 1)
        new_top = last_content + (pitch - b1_end) + 1
        sheets[ws.Name] = {"ws": ws, "prof": prof, "nameRows": [r for r, _ in names], "nameCol": name_col, "n1": n1,
                           "pitch": pitch, "d": new_top - 1, "newTop": new_top, "newName": n1 + new_top - 1,
                           "width": max(len(r) for r in grid), "count": len(names)}
    if not sheets:
        raise ExcelError("This workbook has no sheet with one block per bidder.")
    counts = {s["count"] for s in sheets.values()}
    if len(counts) != 1:
        detail = ", ".join(f"{n}: {s['count']}" for n, s in sheets.items())
        raise ExcelError(f"The bidder sheets do not hold the same number of bidder blocks ({detail}). Make them equal first.")
    count = counts.pop()

    # Where do the bidder names come from?  Follow block 1's name cell: =Summary!B4, possibly through another bidder sheet.
    summary = None
    for name, s in sheets.items():
        sheet, hops = name, 0
        while hops < 6:
            cur = sheets[sheet]
            m = SINGLE.match(str(cur["ws"].Cells(cur["n1"], cur["nameCol"]).Formula))
            if not m:
                break
            target = (m.group(1) or m.group(2)).replace("''", "'")
            if target in sheets:
                sheet, hops = target, hops + 1
                continue
            summary = {"sheet": target, "col": _col(m.group(3)), "base": int(m.group(4))}
            break
        if summary:
            break
    if summary:
        try:
            sws = wb.Worksheets(summary["sheet"])
        except Exception:
            raise ExcelError(f"The bidder names refer to a sheet named \"{summary['sheet']}\" that was not found.")
        summary.update(ws=sws, last=summary["base"] + count - 1, new=summary["base"] + count)
        ur = sws.UsedRange
        summary["width"] = min(ur.Column + ur.Columns.Count - 1, 60)
        row = sws.Range(sws.Cells(summary["new"], 1), sws.Cells(summary["new"], summary["width"])).Formula
        row = row[0] if isinstance(row, tuple) else (row,)
        if need_free_row and any(str(v or "").strip() for v in row):
            raise ExcelError(f"Row {summary['new']} of \"{summary['sheet']}\" is not empty, so the new bidder's row cannot go there. "
                             f"Free that row first.")
    return sheets, summary, count


def _wiring(summary, sheets, count):
    """For each formula column of the summary sheet: which existing bidder's formula to use as the pattern.

    A formula is sound when every reference into a bidder sheet stays inside that bidder's own block. Among
    sound formulas the wiring shared by most bidders wins. Returns (templates, problems).
    """
    sws, base = summary["ws"], summary["base"]
    templates, problems = {}, {}
    for col in range(1, summary["width"] + 1):
        if col == summary["col"]:
            continue
        groups, unsound, any_formula = collections.OrderedDict(), [], False
        for k in range(count):
            formula, is_array = _get_formula(sws.Cells(base + k, col))
            if not formula.startswith("="):
                continue
            any_formula = True
            sound = "#REF!" not in formula

            def norm(sheet, row, k=k):
                nonlocal sound
                if sheet in sheets:
                    off = row - sheets[sheet]["nameRows"][k]
                    if not (-(sheets[sheet]["n1"] - 1) <= off <= sheets[sheet]["pitch"] - sheets[sheet]["n1"]):
                        sound = False
                    return "{%+d}" % off
                if (sheet is None or sheet == summary["sheet"]) and row == base + k:
                    return "{row}"
                return row
            pattern = map_rows(formula, norm)
            if sound:
                groups.setdefault(pattern, []).append(k)
            else:
                unsound.append(k + 1)
        if not any_formula:
            continue
        if unsound:
            problems[col] = unsound
        if groups:
            best = max(groups.values(), key=len)
            templates[col] = best[0]
    return templates, problems


def plan(wb):
    """What adding a bidder would change, without changing anything."""
    sheets, summary, count = survey(wb)
    _, problems = _wiring(summary, sheets, count) if summary else ({}, {})
    return {"number": count + 1,
            "sheets": [{"sheet": n, "rows": f"{s['newTop']}-{s['newTop'] + s['pitch'] - 1}"} for n, s in sheets.items()],
            "summary": {"sheet": summary["sheet"], "row": summary["new"]} if summary else None,
            "wiringProblems": [{"sheet": summary["sheet"], "column": excel_col(c), "bidders": b} for c, b in problems.items()]}


def add_bidder(wb, name, backup_dir):
    """Add a block for `name` on every bidder sheet and a row on the summary sheet. Returns a report."""
    name = re.sub(r"\s+", " ", str(name or "")).strip()
    if not name:
        raise ExcelError("Give the new bidder a name.")
    sheets, summary, count = survey(wb)
    existing = {t["bidder"].strip().lower() for s in sheets.values() for t in s["prof"]["targets"]}
    if name.lower() in existing:
        raise ExcelError(f"\"{name}\" is already in this workbook.")
    templates, problems = _wiring(summary, sheets, count) if summary else ({}, {})

    os.makedirs(backup_dir, exist_ok=True)
    stem, ext = os.path.splitext(wb.Name)
    backup = os.path.join(backup_dir, f"{stem} (before adding bidder {count + 1}, {datetime.datetime.now():%Y-%m-%d %H%M%S}){ext or '.xlsx'}")
    wb.SaveCopyAs(backup)

    xl = wb.Application
    report = {"bidder": name, "number": count + 1, "backup": backup, "sheets": [], "summary": None,
              "notExtended": [], "wiringProblems": []}
    interactive, updating = xl.Interactive, xl.ScreenUpdating
    xl.Interactive, xl.ScreenUpdating = False, False            # nobody types into the sheet half-way through
    try:
        for sheet_name, s in sheets.items():
            ws, d, pitch, width = s["ws"], s["d"], s["pitch"], s["width"]
            source = _formulas(ws, 1, pitch, width)             # block 1 as it is now
            ws.Range(f"1:{pitch}").Copy(ws.Range(f"{s['newTop']}:{s['newTop']}"))

            def rewire(sheet, row, me=sheet_name):
                target = me if sheet is None else sheet
                if target in sheets:
                    return row + sheets[target]["d"] if 1 <= row <= sheets[target]["pitch"] else row
                if summary and target == summary["sheet"] and row == summary["base"]:
                    return summary["new"]
                return row
            for r, row in enumerate(source, 1):
                for c, f in enumerate(row, 1):
                    if f.startswith("="):
                        ws.Cells(r + d, c).Formula = map_rows(f, rewire)

            t0 = s["prof"]["targets"][0]
            items = [x for x in t0["rows"] if x["kind"] == "item"]
            if items:
                first, last = t0["headerBottom"] + 1, max(x["row"] for x in t0["rows"])
                heads = _formulas(ws, t0["headerTop"], t0["headerBottom"], width)
                start = next((c + 1 for c in range(t0["cols"]["req"], width)
                              if any(INPUT_HEADER.search(row[c]) for row in heads)), None)
                if start is None and t0["human"]:
                    start = min(t0["human"])
                if start:
                    for r in range(first, last + 1):
                        for c in range(start, width + 1):
                            f = source[r - 1][c - 1]
                            if f and not f.startswith("="):
                                _clear(ws.Cells(r + d, c))
                    if t0["col"]:                               # the AI Evaluation cells start clean
                        ai = ws.Range(ws.Cells(first + d, t0["col"]), ws.Cells(last + d, t0["col"] + 2))
                        ai.Hyperlinks.Delete()
                        ai.Interior.ColorIndex = XL_NONE
                        ai.Font.Color = rgb("#000000")
                        ai.Font.Bold = False
                        ai.Font.Underline = XL_NONE
            name_cell = ws.Cells(s["newName"], s["nameCol"])
            if not str(name_cell.Formula).startswith("="):
                name_cell.Value = excel_io.safe(name)           # names typed straight into the block
            report["sheets"].append({"sheet": sheet_name, "rows": f"{s['newTop']}-{s['newTop'] + pitch - 1}", "nameRow": s["newName"]})

        if summary:
            sws, base, new, last = summary["ws"], summary["base"], summary["new"], summary["last"]
            before = _formulas(sws, base, last, summary["width"])
            sws.Range(f"{last}:{last}").Copy(sws.Range(f"{new}:{new}"))
            used, blank = {}, []
            for col in range(1, summary["width"] + 1):
                cell = sws.Cells(new, col)
                if col == summary["col"]:
                    cell.Value = excel_io.safe(name)
                elif col in templates:
                    k = templates[col]
                    formula, is_array = _get_formula(sws.Cells(base + k, col))

                    def place(sheet, row, k=k):
                        if sheet in sheets:
                            return row - sheets[sheet]["nameRows"][k] + sheets[sheet]["newName"]
                        if (sheet is None or sheet == summary["sheet"]) and row == base + k:
                            return new
                        return row
                    _set_formula(cell, map_rows(formula, place), is_array)
                    used[excel_col(col)] = k + 1
                else:
                    value = before[-1][col - 1]
                    number = txt(sws.Cells(last, col).Value)
                    if col < summary["col"] and number == str(count):
                        cell.Value = count + 1                  # the running number
                    elif value:
                        _clear(cell)                            # the previous bidder's typed notes
                        if value.startswith("="):               # no soundly wired formula to follow: left empty
                            blank.append(excel_col(col))
            report["summary"] = {"sheet": summary["sheet"], "row": new, "patternFrom": used, "leftEmpty": blank}
            for col, bad in problems.items():
                report["wiringProblems"].append({"sheet": summary["sheet"], "column": excel_col(col), "bidders": bad})

            # Other sheets that list the bidders are not extended; say which.
            ref = re.compile(r"(?:'%s'|%s)!\$?%s\$?(\d+)" % (re.escape(summary["sheet"]), re.escape(summary["sheet"]), excel_col(summary["col"])))
            for ws in wb.Worksheets:
                if ws.Name in sheets or ws.Name == summary["sheet"]:
                    continue
                try:
                    grid = _formulas(ws, 1, 120, 80)
                except Exception:
                    continue
                if any(base <= int(m.group(1)) <= last for row in grid for f in row if f.startswith("=") for m in ref.finditer(f)):
                    report["notExtended"].append(ws.Name)
    finally:
        xl.ScreenUpdating, xl.Interactive = updating, interactive
        try:
            xl.CutCopyMode = False
        except Exception:
            pass
    return report


AND_LIST = re.compile(r"^(?P<head>=\s*IF\(\s*AND\()(?P<terms>.*?)(?P<tail>\)\s*,\s*\"[^\"]*\"\s*,\s*\"[^\"]*\"\s*\)\s*)$", re.S)
AND_TERM = re.compile(r"(?P<sheet>(?:'(?:[^']|'')+'|[A-Za-z_][A-Za-z0-9_.]*)!)\$?(?P<col>[A-Z]{1,3})\$?\d+\s*=\s*(?P<lit>\"[^\"]*\")")


def _study(summary, sheets, count, col):
    """One summary column, bidder by bidder: formula, whether it is an array formula, whether it is soundly
    wired (every reference into a bidder sheet stays inside that bidder's own block, no #REF!), its wiring
    pattern and its shape (the formula with all row numbers masked)."""
    sws, base = summary["ws"], summary["base"]
    out = []
    for k in range(count):
        formula, is_array = _get_formula(sws.Cells(base + k, col))
        if not formula.startswith("="):
            out.append(None)
            continue
        state = {"sound": "#REF!" not in formula}

        def norm(sheet, row, k=k, state=state):
            if sheet in sheets:
                s = sheets[sheet]
                off = row - s["nameRows"][k]
                nxt = s["nameRows"][k + 1] - s["nameRows"][k] if k + 1 < count else s["pitch"] + 12
                if not (-(s["n1"] - 1) <= off < nxt - (s["n1"] - 1)):
                    state["sound"] = False
                return "{%+d}" % off
            if (sheet is None or sheet == summary["sheet"]) and row == base + k:
                return "{row}"
            return row
        pattern = map_rows(formula, norm)
        out.append({"k": k, "formula": formula, "array": is_array, "sound": state["sound"], "pattern": pattern,
                    "shape": map_rows(formula, lambda s, r: "#")})
    return out


def _to_block(sheets, t, k):
    """Row of bidder t's block on a bidder sheet -> the matching row of bidder k's block (same requirement)."""
    cache = {}

    def fn(sheet, row):
        s = sheets[sheet]
        if sheet not in cache:
            a = [x["row"] for x in s["prof"]["targets"][t]["rows"]]
            b = [x["row"] for x in s["prof"]["targets"][k]["rows"]]
            cache[sheet] = dict(zip(a, b)) if len(a) == len(b) else {}
        return cache[sheet].get(row, row - s["nameRows"][t] + s["nameRows"][k])
    return fn


def repair_summary(wb, and_items=None, log_sheet="Resume repair log"):
    """Rewire the summary sheet's result formulas that do not point at their own bidder's block.

    Soundly wired formulas are never touched. A broken formula is replaced by the wiring of a sound formula
    of the same shape, moved to the bidder's own block requirement by requirement. For a column whose sound
    formula is IF(AND(cell="x", cell="x", ...), a, b) and whose broken formulas have other shapes, `and_items`
    gives the requirements to test: positions (0-based) among the evaluated requirement rows of a block.
    Every change is listed on a new log sheet. Returns a report.
    """
    sheets, summary, count = survey(wb, need_free_row=False)
    if not summary:
        raise ExcelError("The bidder names do not come from a summary sheet, so there is nothing to repair.")
    sws, base = summary["ws"], summary["base"]
    xl = wb.Application
    changes, skipped = [], []
    for col in range(1, summary["width"] + 1):
        if col == summary["col"]:
            continue
        rows = _study(summary, sheets, count, col)
        sound = [r for r in rows if r and r["sound"]]
        broken = [r for r in rows if r and not r["sound"]]
        if not broken:
            continue
        by_shape = collections.defaultdict(list)
        for r in sound:
            by_shape[r["shape"]].append(r)
        and_style = next((AND_LIST.match(r["formula"]) for r in sound if AND_LIST.match(r["formula"])), None)
        for r in broken:
            k, new = r["k"], None
            same = by_shape.get(r["shape"])
            if same:
                groups = collections.OrderedDict()
                for s in same:
                    groups.setdefault(s["pattern"], []).append(s)
                t = max(groups.values(), key=len)[0]
                mapper = _to_block(sheets, t["k"], k)

                def place(sheet, row, t=t, k=k, mapper=mapper):
                    if sheet in sheets:
                        return mapper(sheet, row)
                    if (sheet is None or sheet == summary["sheet"]) and row == base + t["k"]:
                        return base + k
                    return row
                new, how = map_rows(t["formula"], place), f"same wiring as bidder {t['k'] + 1}"
            elif and_style and and_items is not None:
                term = AND_TERM.search(and_style.group("terms"))
                raw = term.group("sheet")[:-1]
                target = raw[1:-1].replace("''", "'") if raw.startswith("'") else raw
                if target in sheets:
                    block = [x for x in sheets[target]["prof"]["targets"][k]["rows"] if x["kind"] == "item" and not x.get("group")]
                    if max(and_items) < len(block):
                        terms = ",".join(f"{term.group('sheet')}{term.group('col')}{block[i]['row']}={term.group('lit')}" for i in and_items)
                        new, how = and_style.group("head") + terms + and_style.group("tail"), "chosen requirement rows of the bidder's own block"
            cell = sws.Cells(base + k, col)
            if new is None:
                skipped.append(f"{excel_col(col)}{base + k}")
                continue
            changes.append({"cell": f"{excel_col(col)}{base + k}", "bidder": txt(sws.Cells(base + k, summary["col"]).Text), "number": k + 1,
                            "before": txt(cell.Text), "old": r["formula"], "new": new, "how": how, "row": base + k, "col": col})
            _set_formula(cell, new, r["array"])
        # A correctly wired formula can still display an error it picked up in another program (for example
        # #NAME? on a function saved under a foreign prefix). Entering the very same formula again clears that.
        for r in sound:
            cell = sws.Cells(base + r["k"], col)
            if txt(cell.Text).startswith("#"):
                changes.append({"cell": f"{excel_col(col)}{base + r['k']}", "bidder": txt(sws.Cells(base + r["k"], summary["col"]).Text),
                                "number": r["k"] + 1, "before": txt(cell.Text), "old": r["formula"], "new": r["formula"],
                                "how": "formula unchanged, entered again because it displayed an error", "row": base + r["k"], "col": col})
                _set_formula(cell, r["formula"], r["array"])
    xl.Calculate()
    for c in changes:
        c["after"] = txt(sws.Cells(c["row"], c["col"]).Text)

    # a sheet that lists every change, so the repair can be checked cell by cell
    log = wb.Worksheets.Add()
    log.Move(None, wb.Worksheets(wb.Worksheets.Count))
    log = wb.Worksheets(wb.Worksheets.Count)
    log.Name = log_sheet[:31]
    log.Cells(1, 1).Value = f"Formulas on \"{summary['sheet']}\" that did not point at their own bidder's rows, and what they were replaced with."
    log.Cells(2, 1).Value = "Formulas that were already wired to their own bidder's block were not changed."
    heads = ["Cell", "Bidder no.", "Bidder", "Result before", "Result after", "Changed?", "How it was rewired", "Formula before", "Formula after"]
    table = [heads] + [[c["cell"], c["number"], excel_io.safe(c["bidder"]), excel_io.safe(c["before"]), excel_io.safe(c["after"]),
                        "RESULT CHANGED" if c["before"] != c["after"] else "", c["how"], "'" + c["old"], "'" + c["new"]] for c in changes]
    rng = log.Range(log.Cells(4, 1), log.Cells(3 + len(table), len(heads)))
    rng.Value = tuple(tuple(r) for r in table)
    log.Range(log.Cells(4, 1), log.Cells(4, len(heads))).Font.Bold = True
    log.Range(log.Cells(1, 1), log.Cells(1, 1)).Font.Bold = True
    for i, w in enumerate((8, 9, 34, 22, 22, 17, 44, 70, 70), 1):
        log.Columns(i).ColumnWidth = w
    return {"summary": summary["sheet"], "changed": [{k: c[k] for k in ("cell", "number", "before", "after", "how")} for c in changes],
            "skipped": skipped, "log": log.Name}


def excel_col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s
