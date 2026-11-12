"""Read an evaluation-criteria table out of a Word (.docx) file.

Standard library only. A .docx is a zip of XML; we walk the tables in
word/document.xml and turn them into a flat list of criteria:

    {"kind": "section", "text": "Kriteria Administrasi"}
    {"kind": "item", "no": "1", "requirement": "...", "doc": "..."}
"""
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _para_text(p):
    parts = []
    for node in p.iter():
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif node.tag == W + "tab":
            parts.append(" ")
        elif node.tag in (W + "br", W + "cr"):
            parts.append("\n")
    return "".join(parts).strip()


def _cell(tc):
    """Text, grid span and vertical-merge state of one table cell."""
    text = "\n".join(t for t in (_para_text(p) for p in tc.iter(W + "p")) if t)
    span, vmerge = 1, None
    pr = tc.find(W + "tcPr")
    if pr is not None:
        gs = pr.find(W + "gridSpan")
        if gs is not None:
            span = int(gs.get(W + "val", "1"))
        vm = pr.find(W + "vMerge")
        if vm is not None:
            vmerge = vm.get(W + "val", "continue")
    return {"text": text, "span": span, "vmerge": vmerge}


def read_docx_tables(path):
    """Return every top-level table as rows of cells laid out on the grid."""
    with open(path, "rb") as fh, zipfile.ZipFile(fh) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    tables = []
    for tbl in body.iter(W + "tbl"):
        rows = []
        for tr in tbl.findall(W + "tr"):
            grid = []
            for tc in tr.findall(W + "tc"):
                c = _cell(tc)
                grid.append(c)
                # pad spanned grid columns so column positions stay aligned
                grid.extend({"text": "", "span": 0, "vmerge": c["vmerge"]} for _ in range(c["span"] - 1))
            rows.append(grid)
        if rows:
            tables.append(rows)
    return tables


def read_docx_text(path):
    """All paragraph text of a .docx, used when a bidder document is a Word file."""
    with open(path, "rb") as fh, zipfile.ZipFile(fh) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    return "\n".join(t for t in (_para_text(p) for p in root.iter(W + "p")) if t)


# "1", "1.", "(3)", "5a", "2 (a)", "2.1"
_NUM = re.compile(r"^[(\[]?\d+[a-zA-Z]?[.)\]]?(\s*[(\[]?[a-zA-Z0-9]{1,4}[.)\]]?)?$")


def parse_pasted(text):
    """Criteria pasted from Excel or Word: tab-separated cells, multi-line cells in quotes."""
    import csv
    import io

    rows = list(csv.reader(io.StringIO(text.replace("\r\n", "\n")), delimiter="\t", quotechar='"'))
    width = max((len(r) for r in rows), default=0)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return parse_criteria(rows_to_tables(rows))
_SUB = re.compile(r"^\(?([a-zA-Z])[.)]\s+(.+)$", re.S)
_HEADER_WORDS = ("requirement", "persyaratan", "kriteria", "uraian", "doc", "dokumen", "spesifikasi", "specification")


def rows_to_tables(rows):
    """Wrap plain rows (lists of strings, e.g. read from an Excel file) in the table shape used here."""
    return [[[{"text": "" if v is None else str(v), "span": 1, "vmerge": None} for v in row] for row in rows]]


def parse_criteria(tables):
    """Turn raw table rows into sections and numbered items."""
    out = []
    for rows in tables:
        for row in rows:
            real = [c for c in row if c["span"] > 0]
            texts = [c["text"].strip() for c in real]
            filled = [t for t in texts if t]
            if not filled:
                continue
            first = texts[0]
            # column-header row: "No." | "Requirement" | "Doc Required"
            if first.lower().rstrip(".") in ("no", "nomor", "#") and any(
                w in " ".join(texts[1:]).lower() for w in _HEADER_WORDS
            ):
                continue
            if _NUM.match(first):
                rest = [t for t in texts[1:] if t]
                req = rest[0] if rest else ""
                doc = "\n".join(rest[1:])
                out.append({"kind": "item", "no": first.strip().rstrip("."), "requirement": req, "doc": doc})
                continue
            if first == "" and out and out[-1]["kind"] == "item" and len(real) > 1:
                # row with no number: a lettered sub-item ("a. Akta ...") or a continuation
                sub = _SUB.match(filled[0])
                if sub:
                    parent = next(i for i in reversed(out) if i["kind"] == "item" and not i.get("child"))
                    parent["group"] = True
                    out.append({"kind": "item", "child": True, "no": parent["no"] + sub.group(1).lower(),
                                "requirement": sub.group(2).strip(), "doc": "\n".join(filled[1:])})
                    continue
                if len(filled) == 1 and not _looks_like_section(filled[0], real):
                    tail = out[-1]
                    key = "doc" if texts.index(filled[0]) >= 2 else "requirement"
                    tail[key] = (tail[key] + "\n" + filled[0]).strip()
                    continue
            if len(set(filled)) == 1:
                out.append({"kind": "section", "text": filled[0]})
                continue
            # unnumbered multi-cell row: keep it as an item so nothing is lost
            out.append({"kind": "item", "no": "", "requirement": filled[0], "doc": "\n".join(filled[1:])})
    # a table title that came before any column header is a section too
    return out


def _looks_like_section(text, real_cells):
    """A short title in a wide merged cell, e.g. 'Penawaran Teknis'."""
    wide = any(c["span"] >= 2 and c["text"].strip() == text for c in real_cells)
    listy = bool(re.match(r"^([a-z]\.|\d+\.|[-•])\s", text))
    return (wide or len(text) <= 40) and not listy and "\n" not in text


def load_criteria(path):
    """Criteria from a Word table (.docx) or the first sheet of an Excel file (.xlsx/.xlsm)."""
    if path.lower().endswith((".xlsx", ".xlsm")):
        import openpyxl  # installed by install.ps1

        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        rows = [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
        wb.close()
        width = max((len(r) for r in rows), default=0)
        while width and all((r[width - 1] if len(r) >= width else None) in (None, "") for r in rows):
            width -= 1
        rows = [[(r[i] if i < len(r) else None) for i in range(width)] for r in rows]
        return parse_criteria(rows_to_tables(rows))
    return parse_criteria(read_docx_tables(path))


if __name__ == "__main__":
    import json

    p = sys.argv[1]
    if "--raw" in sys.argv:
        for ti, rows in enumerate(read_docx_tables(p)):
            for ri, row in enumerate(rows):
                print(ti, ri, [(c["text"][:40], c["span"], c["vmerge"]) for c in row])
    else:
        print(json.dumps(load_criteria(p), ensure_ascii=False, indent=1))
