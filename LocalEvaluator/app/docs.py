"""Turn a bidder's document folder into page texts, with a local cache.

PDF text comes from PyMuPDF. Pages with no text layer (scans) are rendered to
images and read by the OCR engine built into Windows (ocr.ps1). Nothing here
touches the network.
"""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

from criteria import read_docx_text

APP_DIR = os.path.dirname(os.path.abspath(__file__))
OCR_SCRIPT = os.path.join(APP_DIR, "ocr.ps1")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
SUPPORTED = {".pdf", ".docx", ".xlsx", ".xlsm", ".txt"} | IMAGE_EXT
MIN_TEXT = 40          # a page with fewer characters than this is treated as a scan
MAX_OCR_PAGES = 150    # per file, to keep run time bounded
NO_WINDOW = 0x08000000


def list_files(folder):
    out = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in sorted(files):
            if f.startswith(("._", "~$", ".")) or f.lower() in ("thumbs.db", "desktop.ini"):
                continue
            full = os.path.join(root, f)
            out.append((full, os.path.relpath(full, folder)))
    return sorted(out, key=lambda x: x[1].lower())


def run_ocr(image_paths):
    """OCR a list of image files; returns {path: text}. Empty dict if OCR is unavailable."""
    if not image_paths:
        return {}
    tmp = tempfile.mkdtemp(prefix="le_ocr_")
    try:
        lst, out = os.path.join(tmp, "list.txt"), os.path.join(tmp, "out.json")
        with open(lst, "w", encoding="utf-8") as fh:
            fh.write("\n".join(image_paths))
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", OCR_SCRIPT, "-ListFile", lst, "-OutFile", out],
            capture_output=True, timeout=60 + 20 * len(image_paths), creationflags=NO_WINDOW)
        if not os.path.exists(out):
            return {}
        with open(out, encoding="utf-8") as fh:
            return {r["path"]: r.get("text") or "" for r in json.load(fh)}
    except Exception:
        return {}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _pdf(path, cancel):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz  # older PyMuPDF

    pages, ocr_count, note = [], 0, ""
    tmp = tempfile.mkdtemp(prefix="le_pdf_")
    try:
        with fitz.open(path) as doc:
            if doc.needs_pass:
                return [], 0, "password-protected"
            todo = []
            for i, page in enumerate(doc):
                if cancel():
                    break
                text = (page.get_text("text") or "").strip()
                pages.append(text)
                if len(text) < MIN_TEXT:
                    if len(todo) < MAX_OCR_PAGES:
                        img = os.path.join(tmp, f"p{i:04d}.png")
                        page.get_pixmap(dpi=200).save(img)
                        todo.append((i, img))
                    else:
                        note = f"only the first {MAX_OCR_PAGES} scanned pages were read"
            for start in range(0, len(todo), 20):
                if cancel():
                    break
                batch = todo[start:start + 20]
                texts = run_ocr([img for _, img in batch])
                for i, img in batch:
                    t = texts.get(img, "").strip()
                    if t:
                        pages[i] = t
                        ocr_count += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return pages, ocr_count, note


def _xlsx(path):
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    pages = []
    for ws in wb.worksheets:
        lines = [f"[Sheet: {ws.title}]"]
        size = 0
        for row in ws.iter_rows(values_only=True):
            cells = [str(v).strip() for v in row if v not in (None, "")]
            if cells:
                line = " | ".join(cells)
                lines.append(line)
                size += len(line)
                if size > 20000:
                    break
        pages.append("\n".join(lines))
    wb.close()
    return pages


def _split(text, size=3000):
    """Word and text files have no pages; cut them into page-sized pieces."""
    parts, cur = [], ""
    for line in text.splitlines():
        if len(cur) + len(line) > size and cur:
            parts.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        parts.append(cur)
    return parts


def extract(path, cancel=lambda: False):
    ext = os.path.splitext(path)[1].lower()
    ocr_count, note = 0, ""
    if ext == ".pdf":
        pages, ocr_count, note = _pdf(path, cancel)
    elif ext == ".docx":
        pages = _split(read_docx_text(path))
    elif ext in (".xlsx", ".xlsm"):
        pages = _xlsx(path)
    elif ext == ".txt":
        with open(path, encoding="utf-8", errors="replace") as fh:
            pages = _split(fh.read())
    elif ext in IMAGE_EXT:
        text = run_ocr([path]).get(path, "")
        pages, ocr_count = [text], (1 if text.strip() else 0)
    else:
        return {"pages": [], "ocr": 0, "status": "unsupported", "note": "file type not read"}
    readable = sum(1 for p in pages if len(p.strip()) >= MIN_TEXT)
    status = "ok" if readable else "no-text"
    if note == "password-protected":
        status = "no-text"
    return {"pages": pages, "ocr": ocr_count, "status": status, "note": note}


def index_folder(folder, cache_dir, log=print, cancel=lambda: False):
    """Read every file under folder. Returns a list of document records."""
    os.makedirs(cache_dir, exist_ok=True)
    docs = []
    files = list_files(folder)
    for n, (full, rel) in enumerate(files, 1):
        if cancel():
            break
        st = os.stat(full)
        key = hashlib.sha1(f"{full.lower()}|{st.st_size}|{int(st.st_mtime)}|v2".encode("utf-8")).hexdigest()
        cache = os.path.join(cache_dir, key + ".json")
        rec = None
        if os.path.exists(cache):
            try:
                with open(cache, encoding="utf-8") as fh:
                    rec = json.load(fh)
            except Exception:
                rec = None
        if rec is None:
            log(f"Reading {n}/{len(files)}: {rel}")
            try:
                rec = extract(full, cancel)
            except Exception as exc:  # one bad file must not stop the run
                rec = {"pages": [], "ocr": 0, "status": "error", "note": str(exc)[:200]}
            if not cancel():
                with open(cache, "w", encoding="utf-8") as fh:
                    json.dump(rec, fh, ensure_ascii=False)
        rec = dict(rec, name=rel.replace("\\", "/"), path=full)
        docs.append(rec)
    return docs
