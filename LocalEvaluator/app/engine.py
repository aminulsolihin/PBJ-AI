"""Evaluate one requirement for one bidder with a local model (Ollama on this machine).

Pipeline per requirement:  search the bidder's pages  ->  ask the model for a
structured finding  ->  apply the fixed decision rules in code  ->  build the
cell texts. The model never decides the label directly and never sees the web.
"""
import datetime
import difflib
import hashlib
import http.client
import json
import math
import os
import re
import time

OLLAMA_HOST, OLLAMA_PORT = "127.0.0.1", 11434   # loopback only, by design


class Cancelled(Exception):
    pass


# ----------------------------------------------------------------- local model
def ollama_models():
    conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=5)
    try:
        conn.request("GET", "/api/tags")
        data = json.loads(conn.getresponse().read())
        return sorted(m["name"] for m in data.get("models", []))
    finally:
        conn.close()


def ensure_ollama(wait=25):
    """Start the local Ollama service if it is not answering. Returns True when it is reachable."""
    import shutil
    import subprocess

    try:
        ollama_models()
        return True
    except Exception:
        pass
    exe = shutil.which("ollama") or os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
    if not os.path.isfile(exe):
        return False
    env = dict(os.environ, OLLAMA_HOST=f"{OLLAMA_HOST}:{OLLAMA_PORT}", OLLAMA_NO_CLOUD="1")   # this computer only
    try:
        subprocess.Popen([exe, "serve"], env=env, creationflags=0x08000000,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return False
    end = time.time() + wait
    while time.time() < end:
        try:
            ollama_models()
            return True
        except Exception:
            time.sleep(1)
    return False


def ollama_chat(model, system, user, schema, cancel=lambda: False, num_ctx=8192, num_predict=900):
    """One structured-output chat call, streamed so it can be cancelled."""
    body = json.dumps({
        "model": model, "stream": True, "think": False, "format": schema, "keep_alive": "30m",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "options": {"temperature": 0, "num_ctx": num_ctx, "num_predict": num_predict},
    })
    conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=3600)
    text, side, stats = "", "", {}
    try:
        conn.request("POST", "/api/chat", body, {"Content-Type": "application/json"})
        resp = conn.getresponse()
        if resp.status != 200:
            raise RuntimeError(f"Ollama error {resp.status}: {resp.read()[:300].decode('utf-8', 'replace')}")
        for line in resp:
            if cancel():
                raise Cancelled()
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj.get("error"):
                raise RuntimeError("Ollama: " + obj["error"])
            msg = obj.get("message", {})
            text += msg.get("content") or ""
            side += msg.get("thinking") or ""
            if obj.get("done"):
                stats = obj
    finally:
        conn.close()
    # Some Ollama versions return the structured answer in the "thinking" field for thinking-capable
    # models when thinking is switched off, so both fields are tried.
    for candidate in (text, side):
        try:
            return json.loads(candidate), stats
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", candidate, re.S)
            if m:
                try:
                    return json.loads(m.group(0)), stats
                except json.JSONDecodeError:
                    pass
    if stats.get("done_reason") == "length":
        raise RuntimeError("The model's answer was cut off before it finished.")
    raise RuntimeError("The model did not return a usable answer.")


# ---------------------------------------------------------------------- search
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = set("""yang dan di ke dari untuk dengan atau pada adalah ini itu sesuai dalam oleh sebagai tidak akan telah
dapat harus bahwa serta juga para atas secara masih berupa lain bagi the of and to in for a an is are be by or as on at
shall has have that which with its it this from not who where any each been was were will may must their""".split())


def tokens(text):
    return [t for t in _TOKEN.findall(text.lower()) if len(t) > 1 and t not in _STOP]


def make_chunks(docs, size=1400):
    """Cut every page into pieces of about `size` characters, keeping file and page."""
    chunks = []
    for d in docs:
        for pno, page in enumerate(d.get("pages", []), 1):
            page = page.strip()
            if len(page) < 20:
                continue
            cur = ""
            for line in page.splitlines():
                if len(cur) + len(line) > size and cur:
                    chunks.append({"file": d["name"], "page": pno, "text": cur.strip()})
                    cur = ""
                cur += line + "\n"
            if cur.strip():
                chunks.append({"file": d["name"], "page": pno, "text": cur.strip()})
    for c in chunks:
        c["tok"] = tokens(c["text"])
    return chunks


def search(chunks, query_text, keywords, budget=9000, per_file=3):
    """BM25 keyword search with a bonus for file names that match. Returns chunks in reading order."""
    if not chunks:
        return []
    weights = {}
    for t in tokens(query_text):
        weights[t] = max(weights.get(t, 0), 1.0)
    for kw in keywords:
        for t in tokens(kw):
            weights[t] = 2.0
    n = len(chunks)
    avg = sum(len(c["tok"]) for c in chunks) / n or 1
    df = {}
    for c in chunks:
        for t in set(c["tok"]):
            if t in weights:
                df[t] = df.get(t, 0) + 1
    scored = []
    for c in chunks:
        tf = {}
        for t in c["tok"]:
            if t in weights:
                tf[t] = tf.get(t, 0) + 1
        score = 0.0
        for t, f in tf.items():
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            score += weights[t] * idf * f * 2.5 / (f + 1.5 * (0.25 + 0.75 * len(c["tok"]) / avg))
        name_hits = sum(weights[t] for t in set(tokens(c["file"])) if t in weights)
        if name_hits:
            score += 1.5 * name_hits + (1.0 if c["page"] == 1 else 0)
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    picked, used, per = [], 0, {}
    for score, c in scored:
        if per.get(c["file"], 0) >= per_file or used + len(c["text"]) > budget:
            continue
        picked.append(c)
        per[c["file"]] = per.get(c["file"], 0) + 1
        used += len(c["text"])
    order = {}
    for c in picked:                     # best file first, pages in order inside a file
        order.setdefault(c["file"], len(order))
    return sorted(picked, key=lambda c: (order[c["file"]], c["page"]))


# --------------------------------------------------------------------- prompts
SYSTEM = """You help a government procurement Bid Evaluation Committee in Indonesia draft a document-based evaluation. You check ONE requirement for ONE bidder, using only the excerpts of the documents that bidder submitted.

How to judge
- Judge only against the requirement as written, literally and neutrally. Never describe the bidder with adjectives.
- Use only what the excerpts show. If the needed document is not among the excerpts or the file list, it was not found. Never guess or assume.
- A document supports the requirement only if it belongs to this bidder (or a named joint-operation member, or the manufacturer when the requirement is about the manufacturer), covers what the requirement asks, and is still valid on today's date when it shows an expiry date.
- The bidder's own statement is enough only when the requirement itself asks for a statement, form or commitment from the bidder. Capability, experience, licences, finances and registrations need the issuing party's document or records.
- Where the requirement sets a number (amount, quantity, years, codes), state the figure found and compare it plainly with the minimum.
- Conditional requirements ("apabila", "dalam hal", "if", "in the event", alternatives for foreign bidders): if the evidence shows the condition does not apply to this bidder, the finding is not_applicable.
- Excerpts may come from scanned pages and contain reading errors. If the relevant text is too garbled to rely on, use evidence_unreadable.

finding values
- verified: the excerpts show the requirement is met.
- not_applicable: a conditional requirement whose condition does not apply to this bidder.
- deviation: the documents show the requirement is not met (wrong scope, expired, below the minimum).
- no_document: no relevant document was found among the bidder's files.
- not_substantiated: only the bidder's own claim, where an issuing party's document is needed.
- partial: part of the requirement is shown and part is missing.
- ambiguous: the documents are unclear on a point that decides the matter.
- conflict: the documents contradict each other.
- evidence_unreadable: a relevant document exists but cannot be read reliably.

Writing
- facts: the key facts found, with file and page, in short note form. Write this first.
- document_holder: the company or organisation that the document you rely on was issued to or is about (the licence holder, the taxpayer, the company established, the contracting party), exactly as printed. Empty string if no company is named. Compare it with the bidder's name: a document in another company's name does not support the requirement, unless that company is a named joint-operation partner, or the manufacturer where the requirement is about the manufacturer.
- valid_until: only when the document you rely on is a licence, certificate, registration or similar with a printed end of validity: that end date as YYYY-MM-DD. Otherwise an empty string. Compare it with today's date: a document whose validity ended before today has expired, which is a deviation.
- minimum_required and value_found: only when the requirement sets one numeric minimum (amount, quantity, years): the minimum, and the figure the documents show for the same thing in the same unit, each as plain digits without separators (for example 24048154000). Otherwise empty strings.
- note_en: 2 to 4 plain sentences for readers with no technical or legal training: what the requirement asks in everyday words, what the documents show (names, numbers, dates), and whether that is enough and why, or exactly what is missing. Explain each abbreviation in brackets the first time. Refer to a document by what it is (for example "the deed of establishment"), not by a file number. No remarks about your method. Do not begin with the finding word.
- note_id: the same content in faithful, formal Bahasa Indonesia, using Indonesian number style (1.800; 0,5). Call the bidder "peserta" and the requirement "persyaratan".
- references: the files and page numbers, taken from the excerpt headers, that your finding is based on, whether they support the requirement or show that it is not met. Empty only when no relevant document was found.
- bidder_question: when the finding is neither verified nor not_applicable, one neutral, specific request in English for evidence of the bid as submitted, naming the document needed. Never invite a new or changed offer. Otherwise an empty string."""

FINDINGS = ["verified", "not_applicable", "deviation", "no_document", "not_substantiated",
            "partial", "ambiguous", "conflict", "evidence_unreadable"]

SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {"type": "string"},
        "document_holder": {"type": "string"},
        "valid_until": {"type": "string"},
        "minimum_required": {"type": "string"},
        "value_found": {"type": "string"},
        "note_en": {"type": "string"},
        "finding": {"type": "string", "enum": FINDINGS},
        "note_id": {"type": "string"},
        "references": {"type": "array", "items": {
            "type": "object",
            "properties": {"file": {"type": "string"}, "page": {"type": "integer"}},
            "required": ["file", "page"]}},
        "bidder_question": {"type": "string"},
    },
    "required": ["facts", "document_holder", "valid_until", "minimum_required", "value_found", "note_en", "finding", "note_id",
                 "references", "bidder_question"],
}

KEYWORD_SYSTEM = """You prepare search terms for finding a supporting document inside a bidder's submission for an Indonesian public tender. Given one requirement, list up to 10 short search terms that are likely to be printed in the document that proves it: document titles, form names, issuing bodies, abbreviations, registration codes and numbers, in both Bahasa Indonesia and English. Terms of 1 to 4 words. No explanations."""
KEYWORD_SCHEMA = {"type": "object", "properties": {"keywords": {"type": "array", "items": {"type": "string"}}},
                  "required": ["keywords"]}

# finding -> (English tag, Indonesian tag, label).  Tags never contain " – ".
DECISION = {
    "verified": ("Verified", "Terverifikasi", "Meet"),
    "not_applicable": ("Not applicable", "Tidak berlaku", "Meet"),
    "deviation": ("Deviation", "Penyimpangan", "Not Meet"),
    "no_document": ("No response", "Tidak ada tanggapan", "Not Meet"),
    "not_substantiated": ("Not substantiated", "Tidak didukung bukti", "Clarification Required"),
    "partial": ("Partial", "Sebagian", "Clarification Required"),
    "ambiguous": ("Ambiguous", "Tidak jelas", "Clarification Required"),
    "conflict": ("Conflict", "Bertentangan", "Clarification Required"),
    "evidence_unreadable": ("Evidence unavailable", "Bukti tidak tersedia", "Clarification Required"),
}
LABELS = ("Meet", "Not Meet", "Clarification Required")
ID_MARK = "\n\nID: "


def expand_keywords(item, model, cache_file, cancel=lambda: False, num_ctx=8192, log=print):
    """Ask the model once per requirement for search terms; cached on disk."""
    key = hashlib.sha1((item["requirement"] + "|" + item.get("doc", "")).encode("utf-8")).hexdigest()
    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, encoding="utf-8") as fh:
                cache = json.load(fh)
        except Exception:
            cache = {}
    if key in cache:
        return cache[key]
    user = f"Requirement: {item['requirement']}\nDocument required: {item.get('doc') or 'not specified'}"
    try:
        # same context size as the main call: changing it would make Ollama reload the model each time
        data, _ = ollama_chat(model, KEYWORD_SYSTEM, user, KEYWORD_SCHEMA, cancel, num_ctx=num_ctx, num_predict=300)
        kws = [str(k).strip() for k in data.get("keywords", []) if str(k).strip()][:10]
    except Cancelled:
        raise
    except Exception as exc:
        log(f"  (no search words suggested: {exc})")
        return []                      # not cached, so it is tried again next time
    cache[key] = kws
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=0)
    return kws


def build_prompt(item, bidder, title, docs, excerpts, today=None):
    today = today or datetime.date.today().strftime("%d %B %Y")
    lines = [f"Today's date: {today}. A document whose validity ended before this date has expired.", f"Bidder: {bidder}"]
    if title:
        lines.append(f"Criteria set: {title}")
    if item.get("section"):
        lines.append(f"Section: {item['section']}")
    if item.get("parent"):
        lines.append(f"Parent requirement: {item['parent']}")
    lines.append(f"Requirement {item.get('no', '')}: {item['requirement']}")
    lines.append(f"Document required: {item.get('doc') or 'not specified'}")
    if item.get("extra"):
        lines.append("Other cells in this row of the evaluation sheet (thresholds set by the tender, and information "
                     "the evaluators noted about the bidder; bidder information is a claim to verify, not evidence):")
        for heading, value in item["extra"]:
            lines.append(f"- {heading or 'Unlabelled column'}: {value}")
    lines.append("")
    lines.append(f"Files submitted by this bidder ({len(docs)}):")
    for d in docs[:80]:
        state = "" if d["status"] == "ok" else " - could not be read"
        lines.append(f"- {d['name']} ({len(d.get('pages', []))} pages){state}")
    lines.append("")
    if excerpts:
        lines.append("Excerpts:")
        for c in excerpts:
            lines.append(f"=== FILE: {c['file']} | PAGE: {c['page']} ===")
            lines.append(c["text"])
    else:
        lines.append("Excerpts: none. No page in the bidder's files matched this requirement.")
    return "\n".join(lines)


def _clean(text):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    # the model sometimes repeats a tag; tags are added in code
    return re.sub(r"^(?:[A-Za-z ]{3,24})\s[–-]\s", "", text) if re.match(
        r"^(Verified|Terverifikasi|Deviation|Penyimpangan|Partial|Sebagian|Ambiguous|Conflict|Not [a-z]+|Tidak [a-z ]+)\s[–-]\s",
        text) else text


def _match_file(name, shown):
    """Map a file name the model wrote to one of the files actually shown to it."""
    if not name:
        return None
    low = {f.lower(): f for f in shown}
    n = str(name).strip().lower().replace("\\", "/")
    if n in low:
        return low[n]
    base = {os.path.basename(f).lower(): f for f in shown}
    if os.path.basename(n) in base:
        return base[os.path.basename(n)]
    close = difflib.get_close_matches(n, list(low), n=1, cutoff=0.8)
    return low[close[0]] if close else None


_MONTHS_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
              "November", "Desember"]


def _date(text):
    m = re.match(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$", str(text or ""))
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
    except ValueError:
        return None


def _number(text):
    s = re.sub(r"[\s_]", "", str(text or ""))
    return float(s) if re.fullmatch(r"\d+(\.\d+)?", s) else None


def _d_en(d):
    return f"{d.day} {d.strftime('%B %Y')}"


def _d_id(d):
    return f"{d.day} {_MONTHS_ID[d.month - 1]} {d.year}"


def _n_id(n):
    return f"{n:,.0f}".replace(",", ".")


_COMPANY_WORD = re.compile(r"\b(pt|cv|tbk|ltd|limited|co|corp|corporation|inc|persero|llc|gmbh|company|firma|yayasan|koperasi)\b\.?", re.I)
_MAKER = re.compile(r"manufactur|pabrik|produsen|principal|prinsipal", re.I)


def _entity(name):
    return re.sub(r"[^a-z0-9]+", " ", _COMPANY_WORD.sub(" ", str(name or "").lower())).strip()


def same_entity(a, b):
    """True unless the two names clearly belong to different companies."""
    na, nb = _entity(a), _entity(b)
    if not na or not nb or na in nb or nb in na:
        return True
    return difflib.SequenceMatcher(None, na, nb).ratio() >= 0.75


def finalize(raw, item, docs, excerpts, today=None, bidder=""):
    """Apply the fixed rules and build the three cell texts."""
    finding = raw.get("finding") if raw.get("finding") in DECISION else "ambiguous"
    note_en, note_id = _clean(raw.get("note_en")), _clean(raw.get("note_id"))
    shown = {}
    for c in excerpts:
        shown.setdefault(c["file"], set()).add(c["page"])
    refs = {}
    for r in raw.get("references") or []:
        f = _match_file(r.get("file"), shown)
        if f:
            refs.setdefault(f, [])
            if r.get("page") in shown[f] and r["page"] not in refs[f]:
                refs[f].append(r["page"])
    unreadable = [d["name"] for d in docs if d["status"] != "ok"]
    today = today or datetime.date.today()
    # Dates and minimums are compared here, in code: small models get this arithmetic wrong.
    expiry = _date(raw.get("valid_until"))
    if finding == "verified" and expiry and expiry < today:
        finding = "deviation"
        src = f" ({next(iter(refs))})" if refs else ""
        note_en = (f"The document relied on{src} shows that it was valid until {_d_en(expiry)}. That is before today's "
                   f"date ({_d_en(today)}), so it has expired and does not show that the requirement is currently met.")
        note_id = (f"Dokumen yang dijadikan dasar{src} menunjukkan masa berlaku sampai dengan {_d_id(expiry)}. Tanggal tersebut "
                   f"sebelum tanggal hari ini ({_d_id(today)}), sehingga dokumen sudah tidak berlaku dan belum membuktikan "
                   f"bahwa persyaratan saat ini terpenuhi.")
        raw = dict(raw, bidder_question="Please provide the currently valid version of this document, or evidence that "
                                        "its validity was extended before the bid submission deadline.")
    # A document in another company's name cannot be accepted on the model's word alone.
    holder = re.sub(r"\s+", " ", str(raw.get("document_holder") or "")).strip()
    about_maker = _MAKER.search(item.get("requirement", "") + " " + item.get("parent", ""))
    if (finding == "verified" and bidder and holder and _COMPANY_WORD.search(holder) and not about_maker
            and not same_entity(holder, bidder)):
        finding = "conflict"
        src = f" ({next(iter(refs))})" if refs else ""
        note_en = (f"The document relied on{src} is in the name of {holder}, not the bidder ({bidder}). It supports this "
                   f"requirement only if {holder} is a joint-operation partner or otherwise entitled to stand in for the "
                   f"bidder, and the documents read do not show that.")
        note_id = (f"Dokumen yang dijadikan dasar{src} atas nama {holder}, bukan atas nama peserta ({bidder}). Dokumen "
                   f"tersebut hanya mendukung persyaratan ini apabila {holder} merupakan anggota KSO atau pihak yang berhak "
                   f"mewakili peserta, dan hal itu tidak terlihat dari dokumen yang dibaca.")
        raw = dict(raw, bidder_question=f"Please confirm the relationship between {holder} and the bidder, or indicate "
                                        f"where this document in the bidder's own name appears in the bid as submitted.")
    need, got = _number(raw.get("minimum_required")), _number(raw.get("value_found"))
    if finding == "verified" and need is not None and got is not None and got < need:
        finding = "ambiguous"
        note_en += (f" However, the figure read from the documents ({got:,.0f}) is below the stated minimum ({need:,.0f}), "
                    f"so this needs to be checked by hand.")
        note_id += (f" Namun, angka yang terbaca dari dokumen ({_n_id(got)}) berada di bawah batas minimum "
                    f"({_n_id(need)}), sehingga perlu diperiksa secara manual.")
    # A "met" finding must rest on a page that was really shown to the model.
    if finding == "verified" and not refs:
        finding = "ambiguous"
        note_en += " The supporting page could not be pinpointed automatically; please check the bidder's documents."
        note_id += " Halaman pendukung tidak dapat ditentukan secara otomatis; mohon periksa dokumen peserta."
    # "Nothing found" is not reliable while some files could not be read.
    if finding == "no_document" and unreadable:
        finding = "evidence_unreadable"
        note_en += f" {len(unreadable)} submitted file(s) could not be read, so the document may be among them."
        note_id += f" Sebanyak {len(unreadable)} berkas yang disampaikan tidak dapat dibaca, sehingga dokumen tersebut mungkin ada di antaranya."
    tag_en, tag_id, label = DECISION[finding]
    en_part = f"{tag_en} – {note_en}"
    note_cell = en_part + ID_MARK + f"{tag_id} – {note_id}"
    paths = {d["name"]: d["path"] for d in docs}
    lines = []
    for i, (f, pages) in enumerate(refs.items(), 1):
        pg = f" (p. {', '.join(str(p) for p in sorted(pages))})" if pages else ""
        lines.append(f"{i}. {re.sub(r'^\d+\.\s+', '', f)}{pg}")
    question = _clean(raw.get("bidder_question")) if label != "Meet" else ""
    if label != "Meet" and not question:
        question = "Please indicate the document and page in the bid as submitted that show this requirement is met."
    return {
        "row": item.get("row"), "no": item.get("no", ""), "finding": finding, "label": label,
        "note": note_cell, "en_len": len(en_part), "refs": "\n".join(lines),
        "link": paths.get(next(iter(refs))) if len(refs) == 1 else None,
        "question": question, "facts": _clean(raw.get("facts")),
    }


def evaluate_item(item, bidder, title, docs, chunks, settings, cache_file, cancel=lambda: False, log=print):
    model = settings["model"]
    num_ctx = int(settings.get("numCtx", 8192))
    keywords = expand_keywords(item, model, cache_file, cancel, num_ctx, log) if settings.get("expandKeywords", True) else []
    query = " ".join([item["requirement"], item.get("doc", ""), item.get("parent", "")])
    excerpts = search(chunks, query, keywords, budget=int(settings.get("excerptChars", 9000)))
    prompt = build_prompt(item, bidder, title, docs, excerpts)
    started = time.time()
    raw, stats = ollama_chat(model, SYSTEM, prompt, SCHEMA, cancel, num_ctx=num_ctx, num_predict=1100)
    res = finalize(raw, item, docs, excerpts, bidder=bidder)
    res["seconds"] = round(time.time() - started)
    res["keywords"] = keywords
    res["excerpts"] = [f"{c['file']} p.{c['page']}" for c in excerpts]
    return res


# ---------------------------------------------------------------- self-test CLI
if __name__ == "__main__":
    # python engine.py <criteria file> <bidder folder> <bidder name> [model] [item numbers...]
    import sys
    from criteria import load_criteria
    from docs import index_folder

    crit, folder, bidder = sys.argv[1], sys.argv[2], sys.argv[3]
    model = sys.argv[4] if len(sys.argv) > 4 else "qwen3-vl:8b"
    only = set(sys.argv[5:])
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    items, section, parent = [], "", ""
    for it in load_criteria(crit):
        if it["kind"] == "section":
            section = it["text"]
            continue
        if it.get("group"):
            parent = it["requirement"]
            continue
        items.append(dict(it, section=section, parent=parent if it.get("child") else ""))
    docs = index_folder(folder, os.path.join(data_dir, "cache"))
    chunks = make_chunks(docs)
    print(f"{len(docs)} files, {len(chunks)} chunks, {len(items)} requirements, model {model}")
    settings = {"model": model, "numCtx": 8192, "excerptChars": 9000, "expandKeywords": True}
    for it in items:
        if only and it["no"] not in only:
            continue
        r = evaluate_item(it, bidder, "", docs, chunks, settings, os.path.join(data_dir, "keywords.json"))
        print(f"\n--- {it['no']} [{r['label']}] {r['seconds']}s  keywords={r['keywords']}")
        print("excerpts:", r["excerpts"])
        print(r["note"])
        print("refs:", r["refs"].replace("\n", " ; "), "| question:", r["question"])
