"""Attach the Local Evaluator pane to workbook files.

Excel switches a locally registered ("developer") add-in on only for a workbook that refers to it AND has
its pane flagged visible. This module writes that reference into the .xlsx/.xlsm package: small XML parts
under xl/webextensions plus their relationships - the same thing Excel itself stores when an add-in pane
is left open in a workbook. Nothing else in the workbook is touched.

    python launcher.py new "C:\\path\\Open Local Evaluator.xlsx"   create the small launcher workbook
    python launcher.py add ["C:\\path\\Evaluation.xlsx"]           attach the pane to a CLOSED workbook
                                                                 (asks for the file when none is given;
                                                                 a backup copy is kept the first time)
"""
import os
import re
import shutil
import sys
import uuid
import zipfile

ADDIN_ID = "7c1f0f5e-3b7a-4d0e-9c55-2a6b8e41d9a3"
ADDIN_VERSION = "1.0.0.0"       # must equal <Version> in manifest.xml, which is kept fixed
PART = "webextension_le.xml"
DIR = "xl/webextensions/"
CT_PANES = "application/vnd.ms-office.webextensiontaskpanes+xml"
CT_EXT = "application/vnd.ms-office.webextension+xml"
REL_PANES = "http://schemas.microsoft.com/office/2011/relationships/webextensiontaskpanes"
REL_EXT = "http://schemas.microsoft.com/office/2011/relationships/webextension"
NS_PANES = "http://schemas.microsoft.com/office/webextensions/taskpanes/2010/11"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
EMPTY_RELS = XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'


def _pane(rid, show, row):
    return (f'<wetp:taskpane dockstate="right" visibility="{1 if show else 0}" width="380" row="{row}">'
            f'<wetp:webextensionref xmlns:r="{NS_R}" r:id="{rid}"/></wetp:taskpane>')


def _webextension():
    return (XML + '<we:webextension xmlns:we="http://schemas.microsoft.com/office/webextensions/webextension/2010/11" '
            f'id="{{{str(uuid.uuid4()).upper()}}}">'
            f'<we:reference id="{ADDIN_ID}" version="{ADDIN_VERSION}" store="developer" storeType="Registry"/>'
            '<we:alternateReferences/><we:properties>'
            '<we:property name="Office.AutoShowTaskpaneWithDocument" value="true"/></we:properties><we:bindings/>'
            f'<we:snapshot xmlns:r="{NS_R}"/></we:webextension>')


def _free_id(rels):
    used = set(re.findall(r'\bId="([^"]+)"', rels))
    return next(f"rId{n}" for n in range(1, 1000) if f"rId{n}" not in used)


def _rewrite(path, changes):
    """Rewrite a zip package: parts named in `changes` (name -> bytes) are replaced or added."""
    tmp = path + ".le-tmp"
    try:
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
            seen = set()
            for item in src.infolist():
                seen.add(item.filename)
                dst.writestr(item, changes.get(item.filename, src.read(item.filename)))
            for name, data in changes.items():
                if name not in seen:
                    dst.writestr(name, data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def has_pane(path):
    with zipfile.ZipFile(path) as z:
        return any(n.startswith(DIR) and n.endswith(".xml") and ADDIN_ID in z.read(n).decode("utf-8", "replace")
                   for n in z.namelist())


def _show_existing(path):
    """The workbook already refers to the add-in: make sure its pane is flagged visible."""
    with zipfile.ZipFile(path) as z:
        panes = z.read(DIR + "taskpanes.xml").decode("utf-8")
        rels = z.read(DIR + "_rels/taskpanes.xml.rels").decode("utf-8")
        mine = {os.path.basename(n) for n in z.namelist()
                if n.startswith(DIR + "webextension") and ADDIN_ID in z.read(n).decode("utf-8", "replace")}
    ids = set()
    for rel in re.findall(r"<Relationship\b[^>]*>", rels):
        rid, target = re.search(r'\bId="([^"]+)"', rel), re.search(r'\bTarget="([^"]+)"', rel)
        if rid and target and os.path.basename(target.group(1)) in mine:
            ids.add(rid.group(1))

    def fix(match):
        block = match.group(0)
        if any(f'r:id="{i}"' in block for i in ids):
            block = re.sub(r'visibility="[01]"', 'visibility="1"', block, count=1)
        return block

    fixed = re.sub(r"<wetp:taskpane\b.*?</wetp:taskpane>", fix, panes, flags=re.S)
    changes = {}
    if fixed != panes:
        changes[DIR + "taskpanes.xml"] = fixed.encode("utf-8")
    with zipfile.ZipFile(path) as z:                    # a reference to another version would be orphaned
        for name in mine:
            part = z.read(DIR + name).decode("utf-8")
            same = re.sub(r'(<we:reference\b[^>]*\bid="%s"[^>]*\bversion=")[^"]*(")' % ADDIN_ID,
                          r"\g<1>%s\g<2>" % ADDIN_VERSION, part)
            if same != part:
                changes[DIR + name] = same.encode("utf-8")
    if not changes:
        return "present"
    _rewrite(path, changes)
    return "shown"


def add_pane(path, show=True):
    """Attach the pane to a closed .xlsx/.xlsm.

    Returns 'added' (new reference), 'shown' (reference was there, pane now flagged visible) or 'present'.
    A workbook that already stores other add-in panes (for example Claude's) keeps them; ours is added beside them.
    """
    if has_pane(path):
        return _show_existing(path) if show else "present"
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        types = z.read("[Content_Types].xml").decode("utf-8")
        root_rels = z.read("_rels/.rels").decode("utf-8")
        panes = z.read(DIR + "taskpanes.xml").decode("utf-8") if DIR + "taskpanes.xml" in names else None
        pane_rels = (z.read(DIR + "_rels/taskpanes.xml.rels").decode("utf-8")
                     if DIR + "_rels/taskpanes.xml.rels" in names else EMPTY_RELS)
    changes = {}
    rid = _free_id(pane_rels)
    if panes is None:                                   # no add-in pane stored yet
        panes = XML + f'<wetp:taskpanes xmlns:wetp="{NS_PANES}">{_pane(rid, show, 1)}</wetp:taskpanes>'
        types = types.replace("</Types>", f'<Override PartName="/{DIR}taskpanes.xml" ContentType="{CT_PANES}"/></Types>')
        changes["_rels/.rels"] = root_rels.replace(
            "</Relationships>",
            f'<Relationship Id="{_free_id(root_rels)}" Type="{REL_PANES}" Target="{DIR}taskpanes.xml"/></Relationships>'
        ).encode("utf-8")
    else:                                               # other add-ins' panes are kept; ours goes beside them
        if "</wetp:taskpanes>" not in panes:
            raise ValueError("This workbook stores add-in panes in a form that could not be extended.")
        row = len(re.findall(r"<wetp:taskpane\b", panes)) + 1
        panes = panes.replace("</wetp:taskpanes>", _pane(rid, show, row) + "</wetp:taskpanes>")
    pane_rels = pane_rels.replace("</Relationships>",
                                  f'<Relationship Id="{rid}" Type="{REL_EXT}" Target="{PART}"/></Relationships>')
    types = types.replace("</Types>", f'<Override PartName="/{DIR}{PART}" ContentType="{CT_EXT}"/></Types>')
    changes.update({"[Content_Types].xml": types.encode("utf-8"), DIR + "taskpanes.xml": panes.encode("utf-8"),
                    DIR + "_rels/taskpanes.xml.rels": pane_rels.encode("utf-8"), DIR + PART: _webextension().encode("utf-8")})
    _rewrite(path, changes)
    return "added"


def attach(path):
    """Attach the pane to a workbook file, keeping a backup copy the first time. The workbook must be closed."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".xlsx", ".xlsm"):
        raise ValueError("Choose an Excel workbook (.xlsx or .xlsm).")
    if not has_pane(path):
        backup = os.path.splitext(path)[0] + " (before Local Evaluator)" + ext
        if not os.path.exists(backup):
            shutil.copyfile(path, backup)
    try:
        return add_pane(path)
    except PermissionError:
        raise ValueError("The workbook is open. Close it in Excel first, then try again.")


def new_workbook(path):
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Start"
    ws["A1"] = "Local Evaluator"
    ws["A3"] = "This workbook switches the Local Evaluator add-in on. Its pane is on the right."
    ws["A5"] = "To evaluate a workbook:"
    ws["A6"] = "   1. Close that workbook if it is open."
    ws["A7"] = "   2. In the pane on the right, click  Attach to a workbook  and choose it."
    ws["A8"] = "   3. It opens with its own Local Evaluator pane, now and every time you open it."
    ws["A10"] = "While this workbook is open, the Local Evaluator button is also at the far right of the Home tab of every workbook."
    ws["A1"].font = openpyxl.styles.Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 110
    wb.save(path)
    return add_pane(path)


def _ask_file():
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return filedialog.askopenfilename(parent=root, title="Choose the evaluation workbook (it must be closed)",
                                      filetypes=[("Excel workbook", "*.xlsx *.xlsm")])


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "add"
    target = sys.argv[2] if len(sys.argv) > 2 else ""
    if mode == "new":
        print(new_workbook(os.path.abspath(target)), target)
    else:
        target = target or _ask_file()
        if not target:
            sys.exit("Nothing chosen.")
        try:
            result = attach(os.path.abspath(target))
        except ValueError as exc:
            sys.exit(str(exc))
        print({"added": "Local Evaluator was attached to", "shown": "The Local Evaluator pane was switched back on in",
               "present": "Local Evaluator is already attached to"}[result], target)
        os.startfile(os.path.abspath(target))
