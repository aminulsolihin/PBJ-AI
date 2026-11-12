"""Local Evaluator engine: a small web server on this computer only (127.0.0.1).

It serves the Excel task pane, talks to Excel, reads bidder documents and calls
the local model. It never opens a connection to any other machine.

    python server.py            HTTPS on https://localhost:47821 (needs certs\\server.crt/.key)
    python server.py --http     plain HTTP on http://localhost:47822 (development only)
"""
import concurrent.futures
import datetime
import difflib
import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

APP = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(APP)
WEB = os.path.join(APP, "web")
DATA = os.path.join(BASE, "data")
CERTS = os.path.join(BASE, "certs")
sys.path.insert(0, APP)
os.makedirs(DATA, exist_ok=True)

DEV_HTTP = "--http" in sys.argv
PORT = 47822 if DEV_HTTP else 47821
if sys.stdout is None or not DEV_HTTP:           # started without a console: log to a file
    sys.stdout = sys.stderr = open(os.path.join(DATA, "engine.log"), "a", encoding="utf-8", buffering=1)

import criteria  # noqa: E402
import engine    # noqa: E402
import launcher  # noqa: E402
from docs import index_folder  # noqa: E402

try:
    import pythoncom
    import excel_io
    import blocks
    EXCEL_LINK = True
except ImportError:
    EXCEL_LINK = False

SETTINGS_FILE = os.path.join(DATA, "settings.json")
DEFAULTS = {"model": "qwen3-vl:8b", "numCtx": 8192, "excerptChars": 9000, "expandKeywords": True}
MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".png": "image/png", ".json": "application/json", ".map": "application/json", ".svg": "image/svg+xml",
        ".xml": "text/xml", ".ico": "image/x-icon", ".txt": "text/plain; charset=utf-8"}


def load_settings():
    s = dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as fh:
            s.update(json.load(fh))
    except Exception:
        pass
    return s


def save_settings(s):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=1)


class ApiError(Exception):
    def __init__(self, message, status=400, **extra):
        super().__init__(message)
        self.status, self.extra = status, extra


# ------------------------------------------------------------------ Excel calls
# All short Excel calls run on one dedicated thread, so they never overlap.
_excel_pool = concurrent.futures.ThreadPoolExecutor(
    max_workers=1, initializer=(lambda: pythoncom.CoInitialize()) if EXCEL_LINK else None)


def in_excel(fn, *args, once=False):
    """Run fn on the Excel thread. Read-style calls are retried while Excel is busy; once=True runs a
    multi-step change exactly one time, so it can never be applied twice."""
    if not EXCEL_LINK:
        raise ApiError("The Excel link (pywin32) is not installed yet. Run install.ps1.", 503)
    try:
        job = (lambda: fn(*args)) if once else (lambda: excel_io.with_retry(lambda: fn(*args), 20))
        return _excel_pool.submit(job).result(timeout=300)
    except excel_io.ExcelError as exc:
        raise ApiError(str(exc), 409)
    except pythoncom.com_error as exc:
        detail = exc.excepinfo[2] if exc.excepinfo and exc.excepinfo[2] else str(exc)
        raise ApiError(f"Excel could not do that right now ({detail}). Finish any cell edit and try again.", 409)


def _sheet(wb, name):
    """The named sheet, or the active one when no name is given. A named sheet that is missing is an error."""
    if not name:
        return wb.ActiveSheet
    for ws in wb.Worksheets:
        if ws.Name == name:
            return ws
    raise excel_io.ExcelError(f"Sheet \"{name}\" was not found in {wb.Name}.")


# Bidder -> documents folder, remembered per workbook on this computer (shared by all its sheets).
def _folders_file(path):
    return os.path.join(DATA, "workbooks", hashlib.sha1(path.lower().encode("utf-8")).hexdigest()[:16] + ".json")


def load_folders(path):
    try:
        with open(_folders_file(path), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_folder(path, name, folder):
    folders = load_folders(path)
    folders[name.strip().lower()] = folder
    os.makedirs(os.path.dirname(_folders_file(path)), exist_ok=True)
    with open(_folders_file(path), "w", encoding="utf-8") as fh:
        json.dump(folders, fh, ensure_ascii=False, indent=1)


def x_plan_block(workbook):
    xl, wb = excel_io.connect(workbook)
    return blocks.plan(wb)


def x_add_block(workbook, name):
    xl, wb = excel_io.connect(workbook)
    return blocks.add_bidder(wb, name, os.path.join(DATA, "backups"))


def x_layout(workbook, sheet=None):
    xl, wb = excel_io.connect(workbook)
    ws = _sheet(wb, sheet)
    prof = excel_io.profile(ws)
    path = wb.FullName
    if prof:
        folders = load_folders(path)
        for t in prof["targets"]:
            t["folder"] = folders.get(t["bidder"].strip().lower(), "")
    return {"workbook": wb.Name, "path": path, "sheet": ws.Name, "profile": prof}


def x_create(workbook, title, items):
    xl, wb = excel_io.connect(workbook)
    ws = excel_io.create_sheet(wb, title, items)
    return x_layout(workbook, ws.Name)


def _profiled(workbook, sheet):
    xl, wb = excel_io.connect(workbook)
    ws = _sheet(wb, sheet)
    prof = excel_io.profile(ws)
    if prof is None:
        raise excel_io.ExcelError("This sheet has no criteria table.")
    return wb, ws, prof


def x_add_bidder(workbook, sheet, name, folder):
    wb, ws, prof = _profiled(workbook, sheet)
    if prof["mode"] != "side":
        raise excel_io.ExcelError("This sheet already has one block per bidder; bidders are taken from the sheet.")
    excel_io.add_bidder(ws, prof, name)
    if folder:
        save_folder(wb.FullName, name, folder)
    return x_layout(workbook, ws.Name)


def x_prepare(workbook, sheet):
    wb, ws, prof = _profiled(workbook, sheet)
    if prof["mode"] != "stacked":
        raise excel_io.ExcelError("Add a bidder to create its AI Evaluation columns.")
    excel_io.prepare_stacked(ws, prof)
    return x_layout(workbook, ws.Name)


_COMPANY = re.compile(r"\b(pt|cv|tbk|ltd|co|inc|persero|llc|gmbh)\b\.?", re.I)


def _norm(name):
    return re.sub(r"[^a-z0-9]+", " ", _COMPANY.sub(" ", name.lower())).strip()


def automatch(layout, parent):
    """Pair bidders that have no folder yet with sub-folders of `parent` whose names resemble theirs."""
    subs = [d for d in os.listdir(parent) if os.path.isdir(os.path.join(parent, d))]
    matched = 0
    for t in layout["profile"]["targets"]:
        if not t["bidder"] or t.get("folder"):
            continue
        want = _norm(t["bidder"])
        best, score = None, 0.0
        for d in subs:
            have = _norm(d)
            s = difflib.SequenceMatcher(None, want, have).ratio()
            if want and have and (want in have or have in want):
                s = max(s, 0.9)
            if s > score:
                best, score = d, s
        if best and score >= 0.72:
            save_folder(layout["path"], t["bidder"], os.path.join(parent, best))
            matched += 1
    return matched


# ------------------------------------------------------------------------- job
class Job:
    """One long-running evaluation at a time."""

    def __init__(self):
        self.lock = threading.Lock()
        self.reset("idle")

    def reset(self, state):
        self.state, self.title, self.error = state, "", ""
        self.log, self.results = [], []
        self.total = self.done = 0
        self.started = time.time()
        self.cancel = False

    def say(self, message):
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log.append(f"{stamp}  {message}")
        print(f"[job] {message}")

    def view(self):
        eta = None
        if self.state == "running" and self.results:
            per = sum(r.get("seconds", 0) for r in self.results) / len(self.results)
            eta = round(per * (self.total - self.done))
        return {"state": self.state, "title": self.title, "error": self.error, "total": self.total,
                "done": self.done, "log": self.log[-200:], "results": self.results[-300:],
                "elapsed": round(time.time() - self.started), "eta": eta}


JOB = Job()


def run_evaluation(p):
    pythoncom.CoInitialize()
    settings = load_settings()
    try:
        wb, ws, prof = excel_io.with_retry(lambda: _profiled(p.get("workbook"), p.get("sheet")))
        path, shown = wb.FullName, prof["labels"]
        folders = load_folders(path)
        wanted = {int(n) for n in p.get("rows") or []}
        plan = []
        for name in p.get("bidders") or []:
            t = next((t for t in prof["targets"] if t["bidder"] == name), None)
            if t is None or not t["col"]:
                raise ApiError(f"{name} has no AI Evaluation columns on this sheet yet.")
            items = [r for r in t["rows"] if r["kind"] == "item" and not r.get("group")]
            if p.get("mode") == "empty":
                items = [r for r in items if r["row"] not in t["filled"]]
            if wanted:
                items = [r for r in items if r["row"] in wanted]
            plan.append((t, folders.get(name.strip().lower(), ""), items))
        JOB.total = sum(len(items) for _, _, items in plan)
        if not engine.ensure_ollama():
            raise ApiError("The local model service (Ollama) is not running and could not be started.")
        if settings["model"] not in engine.ollama_models():
            raise ApiError(f"Model \"{settings['model']}\" is not installed in Ollama. Choose another under Settings.")

        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        for t, folder, items in plan:
            if JOB.cancel:
                raise engine.Cancelled()
            name = t["bidder"]
            JOB.say(f"=== {name} ({len(items)} requirement(s))")
            if not folder or not os.path.isdir(folder):
                JOB.say(f"  Skipped: documents folder not found ({folder or 'not set'}).")
                JOB.total -= len(items)
                continue
            key = hashlib.sha1(f"{path}|{ws.Name}|{name}".lower().encode("utf-8")).hexdigest()[:16]
            run_dir = os.path.join(DATA, "runs", key)
            os.makedirs(run_dir, exist_ok=True)
            before = excel_io.with_retry(lambda: excel_io.snapshot(ws, t))
            if before:
                with open(os.path.join(run_dir, f"before-{stamp}.json"), "w", encoding="utf-8") as fh:
                    json.dump(before, fh, ensure_ascii=False, indent=1)
            JOB.say(f"  Reading documents in {folder}")
            docs = index_folder(folder, os.path.join(DATA, "cache"), lambda m: JOB.say("  " + m), lambda: JOB.cancel)
            if not docs:
                JOB.say("  Skipped: the documents folder is empty.")
                JOB.total -= len(items)
                continue
            unread = [d["name"] for d in docs if d["status"] != "ok"]
            JOB.say(f"  {len(docs)} files read, {sum(d.get('ocr', 0) for d in docs)} scanned pages recognised, "
                    f"{len(unread)} could not be read.")
            for bad in unread[:10]:
                JOB.say(f"    not readable: {bad}")
            chunks = engine.make_chunks(docs)
            extras = excel_io.with_retry(lambda: excel_io.row_extras(ws, t))
            mine, pending = [], []
            for it in items:
                if JOB.cancel:
                    raise engine.Cancelled()
                JOB.say(f"  Requirement {it['no']} (row {it['row']}): thinking...")
                res = engine.evaluate_item(dict(it, extra=extras.get(it["row"], [])), name, t["title"] or prof["title"],
                                           docs, chunks, settings, os.path.join(DATA, "keywords.json"),
                                           lambda: JOB.cancel, lambda m: JOB.say("  " + m))
                try:
                    excel_io.with_retry(lambda: excel_io.write_result(ws, it["row"], t["col"], res, prof["font"], shown), 120)
                except pythoncom.com_error:
                    pending.append((it, res))
                    JOB.say(f"    Excel was busy; row {it['row']} will be written at the end.")
                entry = {"bidder": name, "row": res["row"], "no": res["no"], "label": res["label"],
                         "shown": shown.get(res["label"], res["label"]), "finding": res["finding"],
                         "question": res["question"], "seconds": res["seconds"]}
                mine.append(entry)
                JOB.results.append(entry)
                JOB.done += 1
                JOB.say(f"    {entry['shown']} ({res['seconds']} s)")
            for it, res in pending:
                excel_io.with_retry(lambda: excel_io.write_result(ws, it["row"], t["col"], res, prof["font"], shown), 300)
            with open(os.path.join(run_dir, f"results-{stamp}.json"), "w", encoding="utf-8") as fh:
                json.dump(mine, fh, ensure_ascii=False, indent=1)
        counts = {shown[k]: sum(1 for r in JOB.results if r["label"] == k) for k in engine.LABELS}
        JOB.say("Finished. " + ", ".join(f"{k}: {v}" for k, v in counts.items())
                + ". This is a draft; review each row, then save the workbook.")
        JOB.state = "done"
    except engine.Cancelled:
        JOB.say("Stopped. Rows already written stay in the sheet.")
        JOB.state = "cancelled"
    except Exception as exc:
        traceback.print_exc()
        JOB.error = str(exc)
        JOB.say("Stopped with an error: " + str(exc))
        JOB.state = "error"


# ------------------------------------------------------------------- dialogs
PICKER = r"""
import sys, tkinter as tk
from tkinter import filedialog
root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
if sys.argv[1] == 'folder':
    p = filedialog.askdirectory(parent=root, title="Choose the bidder's documents folder")
elif sys.argv[1] == 'workbook':
    p = filedialog.askopenfilename(parent=root, title='Choose the evaluation workbook (it must be closed)',
        filetypes=[('Excel workbook', '*.xlsx *.xlsm')])
else:
    p = filedialog.askopenfilename(parent=root, title='Choose the criteria file',
        filetypes=[('Criteria (Word or Excel)', '*.docx *.xlsx *.xlsm'), ('All files', '*.*')])
sys.stdout.buffer.write((p or '').encode('utf-8'))
"""


def pick(kind):
    exe = sys.executable.replace("pythonw.exe", "python.exe")
    out = subprocess.run([exe, "-c", PICKER, kind], capture_output=True, timeout=600, creationflags=0x08000000)
    return os.path.normpath(out.stdout.decode("utf-8")) if out.stdout else ""


# ------------------------------------------------------------------------ HTTP
def _folder_arg(body):
    folder = os.path.normpath(body.get("folder", "").strip().strip('"')) if body.get("folder") else ""
    if folder and not os.path.isdir(folder):
        raise ApiError("That folder does not exist.")
    return folder


def api(method, path, body):
    if path == "/api/status":
        try:
            ollama_ok = engine.ensure_ollama()
            models = engine.ollama_models() if ollama_ok else []
        except Exception:
            models, ollama_ok = [], False
        return {"engine": True, "excelLink": EXCEL_LINK, "ollama": ollama_ok, "models": models,
                "settings": load_settings(), "job": JOB.state}
    if path == "/api/job":
        return JOB.view()
    if method != "POST":
        raise ApiError("Not found", 404)
    wbk, sheet = body.get("workbook"), body.get("sheet")
    if path == "/api/layout":
        return in_excel(x_layout, wbk, sheet)
    if path == "/api/settings":
        s = load_settings()
        s.update({k: body[k] for k in DEFAULTS if k in body})
        save_settings(s)
        return s
    if path == "/api/pick":
        return {"path": pick("folder" if body.get("kind") == "folder" else "file")}
    if path == "/api/attach":
        # Put the pane into another workbook file, so that workbook opens with its own Local Evaluator pane.
        target = (body.get("path") or "").strip().strip('"') or pick("workbook")
        if not target:
            return {"result": "cancelled"}
        target = os.path.normpath(target)
        if not os.path.isfile(target):
            raise ApiError("That workbook was not found.")
        if EXCEL_LINK:
            def is_open():
                try:
                    excel_io.connect(target)
                    return True
                except excel_io.ExcelError:
                    return False
            if in_excel(is_open):
                raise ApiError(f"\"{os.path.basename(target)}\" is open in Excel. Close it first, then attach it.")
        try:
            result = launcher.attach(target)
        except ValueError as exc:
            raise ApiError(str(exc))
        os.startfile(target)
        return {"result": result, "path": target, "name": os.path.basename(target)}
    if path == "/api/criteria/import":
        src = body.get("path", "").strip().strip('"')
        if body.get("text"):
            items, default_title = criteria.parse_pasted(body["text"]), "Criteria"
        elif os.path.isfile(src):
            items = criteria.load_criteria(src)
            default_title = os.path.splitext(os.path.basename(src))[0]
        else:
            raise ApiError("Choose a criteria file, or paste the criteria table.")
        if not any(i["kind"] == "item" for i in items):
            raise ApiError("No numbered requirements were found. The table needs a number column and a requirement column.")
        title = body.get("title") or (items[0]["text"] if items[0]["kind"] == "section" else default_title)
        if items[0]["kind"] == "section" and items[0]["text"] == title:
            items = items[1:]
        return in_excel(x_create, wbk, title, items)
    if path == "/api/prepare":
        return in_excel(x_prepare, wbk, sheet)
    if path == "/api/bidder/plan-block":          # read-only: what adding a bidder would change
        return in_excel(x_plan_block, wbk)
    if path == "/api/bidder/add-block":           # a new block on every bidder sheet + a summary row
        folder = _folder_arg(body)
        report = in_excel(x_add_block, wbk, body.get("name", ""), once=True)
        layout = in_excel(x_layout, wbk, sheet)
        if folder:
            save_folder(layout["path"], report["bidder"], folder)
            layout = in_excel(x_layout, wbk, sheet)
        return dict(layout, report=report)
    if path == "/api/bidder/add":
        return in_excel(x_add_bidder, wbk, sheet, body.get("name", ""), _folder_arg(body))
    if path == "/api/bidder/folder":
        folder = _folder_arg(body)
        if not folder:
            raise ApiError("Choose a folder.")
        layout = in_excel(x_layout, wbk, sheet)
        save_folder(layout["path"], body.get("name", ""), folder)
        return in_excel(x_layout, wbk, sheet)
    if path == "/api/bidder/automatch":
        parent = _folder_arg(body)
        if not parent:
            raise ApiError("Choose the folder that holds one sub-folder per bidder.")
        layout = in_excel(x_layout, wbk, sheet)
        if not layout["profile"]:
            raise ApiError("This sheet has no criteria table.")
        matched = automatch(layout, parent)
        return dict(in_excel(x_layout, wbk, sheet), matched=matched)
    if path == "/api/evaluate":
        if not EXCEL_LINK:
            raise ApiError("The Excel link (pywin32) is not installed yet. Run install.ps1.", 503)
        names = body.get("bidders") or []
        if not names:
            raise ApiError("Choose at least one bidder.")
        with JOB.lock:
            if JOB.state == "running":
                raise ApiError("An evaluation is already running.", 409)
            JOB.reset("running")
            JOB.title = (names[0] if len(names) == 1 else f"{len(names)} bidders") + f" - {sheet or ''}"
        threading.Thread(target=run_evaluation, args=(body,), daemon=True).start()
        return JOB.view()
    if path == "/api/cancel":
        JOB.cancel = True
        return JOB.view()
    raise ApiError("Not found", 404)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "LocalEvaluator"

    def setup(self):
        if isinstance(self.request, ssl.SSLSocket):
            self.request.settimeout(10)
            self.request.do_handshake()
            self.request.settimeout(None)
        super().setup()

    def log_message(self, *args):
        pass

    def _send(self, status, payload, ctype="application/json"):
        data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _local(self):
        # Only this computer, only this page: blocks other sites from calling the engine.
        return self.headers.get("Host", "") in (f"localhost:{PORT}", f"127.0.0.1:{PORT}")

    def _handle(self, method):
        if not self._local():
            return self._send(403, {"error": "Forbidden"})
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            try:
                body = {}
                if method == "POST":
                    if self.headers.get("X-Local-Evaluator") != "1":
                        return self._send(403, {"error": "Forbidden"})
                    raw = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
                    body = json.loads(raw or b"{}")
                result = api(method, path, body)
                if method == "POST":                      # a short trail for troubleshooting (no document content)
                    book = os.path.basename(str(body.get("workbook") or "")) or "(active workbook)"
                    print(f"[api] {datetime.datetime.now():%H:%M:%S} {path} ok  workbook={book}")
                return self._send(200, result)
            except ApiError as exc:
                print(f"[api] {datetime.datetime.now():%H:%M:%S} {path} {exc.status} {exc}")
                return self._send(exc.status, dict({"error": str(exc)}, **exc.extra))
            except Exception as exc:
                traceback.print_exc()
                return self._send(500, {"error": str(exc)})
        if method != "GET":
            return self._send(405, {"error": "Method not allowed"})
        rel = "taskpane.html" if path in ("/", "") else path.lstrip("/")
        full = os.path.normpath(os.path.join(WEB, rel))
        found = full.startswith(WEB + os.sep) and os.path.isfile(full)
        if rel.endswith((".html", ".png")) or not found:      # a short trail of who loaded the pane, for troubleshooting
            agent = self.headers.get("User-Agent", "")
            client = "Excel pane" if "Edg/" in agent or "Office" in agent else ("browser" if agent else "no agent")
            print(f"[web] {datetime.datetime.now():%H:%M:%S} {'200' if found else '404'} /{rel} ({client})")
        if not found:
            return self._send(404, b"Not found", "text/plain")
        with open(full, "rb") as fh:
            self._send(200, fh.read(), MIME.get(os.path.splitext(full)[1].lower(), "application/octet-stream"))

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")


class Server(ThreadingHTTPServer):
    daemon_threads = True
    tls = None

    def get_request(self):
        sock, addr = self.socket.accept()
        if self.tls:
            sock = self.tls.wrap_socket(sock, server_side=True, do_handshake_on_connect=False)
        return sock, addr

    def handle_error(self, request, client_address):
        pass  # dropped connections and failed handshakes are routine


def main():
    httpd = Server(("127.0.0.1", PORT), Handler)       # loopback only
    if not DEV_HTTP:
        crt, key = os.path.join(CERTS, "server.crt"), os.path.join(CERTS, "server.key")
        if not (os.path.exists(crt) and os.path.exists(key)):
            print("No certificate found. Run install.ps1 first.")
            sys.exit(2)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(crt, key)
        httpd.tls = ctx
    print(f"Local Evaluator engine listening on {'http' if DEV_HTTP else 'https'}://localhost:{PORT}  (Excel link: {EXCEL_LINK})")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
