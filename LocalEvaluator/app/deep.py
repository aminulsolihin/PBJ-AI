"""Careful evaluation of one requirement for one bidder, for small local models.

A small model judges badly when it gets a long requirement and a handful of keyword-matched
fragments at once. So the work is split the way a careful evaluator works:

  1. plan     Break the requirement into separate checks: what must be shown, by whom (each KSO
              partner, the lead, the manufacturer ...), any condition, any minimum.  Bid-independent,
              so it is worked out once per requirement and reused for every bidder.
  2. choose   Code picks the files to read: the evaluators' pointers in the sheet, file names that
              match the check, keyword search over the contents, and for a check required from each
              KSO partner the best file of every partner.
  3. judge    The model reads those files (whole, or their best pages) and reasons before answering,
              one result per check and party, each with a word-for-word quote and its page.
  4. verify   Code checks every quote against the page it cites, compares dates and minimums, and
              checks the document holder against the bidder / KSO partners.  An unproven "met" is
              never accepted.  A short second call then sees only the check and the quote and must
              agree that the quote itself shows the finding.  The verdict follows by fixed rules.
  5. write    The model writes the English / Indonesian note from the verified results only.
"""
import datetime
import hashlib
import json
import os
import re

import engine
from engine import Cancelled, ollama_chat, tokens

# ---------------------------------------------------------------------- step 1: plan
PLAN_SYSTEM = """You prepare the evaluation of ONE requirement of a public tender in Indonesia (World Bank / national rules), before any bid is read. Break the requirement into the separate facts an evaluator must confirm in a bidder's documents.

Rules
- One check per document or figure that must be found. What one document proves is ONE check: do not split a letter into its wording, its date and its signature. Most requirements need 1 or 2 checks; never more than 4. Keep the requirement's own numbers, years and units exactly.
- applies_when: if the whole requirement applies only in some situation ("apabila", "dalam hal", "in the event", "if", "for a bidder who ...", "untuk peserta luar negeri"), describe that situation in plain words. Otherwise "".
- who: which party must show the fact.
  bidder = the bidder as a whole (for a joint operation / KSO: the partners together may show it)
  each_partner = every partner of a joint operation separately (for a single company: that company)
  lead_partner = the lead partner only
  any_partner = at least one partner
  manufacturer = the manufacturer of the goods
  Use the "Compliance requirement" columns when given: "must meet requirement" under a per-partner column means each_partner; a figure under "all partners combined" means bidder; "N/A" means the fact is not required from that party.
  When those columns are empty, follow World Bank / Indonesian tender practice for joint operations: eligibility, statements and declarations (integrity pact, no non-performance, not blacklisted), business licences and registrations (NIB, izin usaha, IDAK / distribution licence), tax status (NPWP, KSWP), deeds of establishment, identity documents and powers of attorney are required from each_partner; past contract experience, production capacity and financial turnover are usually met by the bidder (partners combined) unless the requirement says otherwise; the joint operation agreement itself is about the bidder.
- evidence: the kind of document that proves the fact, in plain words.
- own_statement_ok: true only when the requirement itself asks for a statement, letter, form or commitment from the bidder; false for licences, registrations, experience, capacity and finances, which need the issuing party's document or records.
- minimum: when the fact has one numeric minimum, the number as plain digits without separators (for example 193261948000). Otherwise "".
- search_terms: up to 8 short words or phrases likely printed in that document, in Bahasa Indonesia and English."""

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "applies_when": {"type": "string"},
        "checks": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "what": {"type": "string"},
                "who": {"type": "string", "enum": ["bidder", "each_partner", "lead_partner", "any_partner", "manufacturer"]},
                "evidence": {"type": "string"},
                "own_statement_ok": {"type": "boolean"},
                "minimum": {"type": "string"},
                "search_terms": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["what", "who", "evidence", "own_statement_ok", "minimum", "search_terms"]}},
    },
    "required": ["applies_when", "checks"],
}


def _requirement_text(item):
    lines = []
    if item.get("section"):
        lines.append(f"Section: {item['section']}")
    if item.get("parent"):
        lines.append(f"Parent requirement: {item['parent']}")
    lines.append(f"Requirement {item.get('no', '')}: {item['requirement']}")
    lines.append(f"Document required: {item.get('doc') or 'not specified'}")
    rules = [(h, v) for h, v in item.get("extra", []) if not _is_bidder_info(h)]
    if rules:
        lines.append("Compliance requirement columns of the evaluation sheet:")
        lines += [f"- {h or 'Unlabelled column'}: {v}" for h, v in rules]
    return "\n".join(lines)


def _is_bidder_info(heading):
    """Columns where evaluators note what the bidder submitted (a hint, not a rule of the tender)."""
    return bool(re.search(r"bidder|proposer|peserta|information|informasi|reference|referensi", heading or "", re.I))


def _cache(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _store(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=0)
    os.replace(tmp, path)


def plan(item, settings, cache_file, cancel, log):
    text = _requirement_text(item)
    # the instructions are part of the key: improving them makes old plans be worked out again
    key = hashlib.sha1((settings["model"] + "|" + PLAN_SYSTEM + "|" + text).encode("utf-8")).hexdigest()
    cache = _cache(cache_file)
    if key in cache:
        return cache[key]
    log("    planning the checks for this requirement (done once, reused for every bidder)")
    _step("Planning the checks for this requirement")
    data = _call(settings, PLAN_SYSTEM, text, PLAN_SCHEMA, cancel, think=True, num_predict=5000)
    checks = [c for c in data.get("checks") or [] if str(c.get("what", "")).strip()][:4]
    # a minimum the model states must be printed in the requirement or the sheet's own columns
    source_digits = {re.sub(r"\D", "", m) for m in re.findall(r"\d[\d.,]*\d|\d", text)}
    source_digits |= {d.rstrip("0") for d in source_digits if d.rstrip("0")}
    for c in checks:
        m = re.sub(r"\D", "", str(c.get("minimum") or ""))
        if m and m not in source_digits and m.rstrip("0") not in source_digits:
            log(f"    (the plan's minimum {c['minimum']} is not in the requirement; ignored)")
            c["minimum"] = ""
    if not checks:
        checks = [{"what": item["requirement"], "who": "bidder", "evidence": item.get("doc") or "",
                   "own_statement_ok": False, "minimum": "", "search_terms": []}]
    result = {"applies_when": str(data.get("applies_when") or "").strip(), "checks": checks}
    cache = _cache(cache_file)
    cache[key] = result
    _store(cache_file, cache)
    return result


_PER_PARTNER = re.compile(
    r"statement|declar|pernyataan|surat keterangan|suket|pakta|integrity|integritas|non[- ]?performance|wanprestasi|"
    r"blacklist|daftar hitam|sanction|eligib|licen[cs]e|izin|ijin|NIB\b|nomor induk berusaha|registration|"
    r"NPWP|KSWP|taxpayer|wajib pajak|\btax\b|akta|deed|establishment|pendirian|identity|identitas|KTP|passport|"
    r"power of attorney|surat kuasa|kuasa\b|IDAK|distribution licen|sertifikat standar|CDAKB", re.I)
_COMBINED = re.compile(r"experience|pengalaman|turnover|omzet|omset|financial|keuangan|capacity|kapasitas|"
                       r"joint operation agreement|perjanjian (KSO|kerja sama)|JV agreement|KSO agreement", re.I)


def partner_rule(the_plan, item, members):
    """World Bank / Indonesian practice for joint operations, applied in code because a small model
    does not apply it reliably: when the sheet's own compliance columns say nothing, statements,
    licences, registrations, tax papers, deeds and identity papers are needed from every KSO partner."""
    if len(members["partners"]) < 2:
        return the_plan
    if any(not _is_bidder_info(h) for h, _ in item.get("extra", [])):
        return the_plan                                   # the sheet states the rule itself
    checks = []
    for c in the_plan["checks"]:
        text = " ".join([c.get("what", ""), c.get("evidence", ""), item.get("requirement", ""), item.get("doc", "")])
        if c.get("who") in ("bidder", "any_partner") and _PER_PARTNER.search(text) and not _COMBINED.search(text):
            c = dict(c, who="each_partner")
        checks.append(c)
    return dict(the_plan, checks=checks)


# -------------------------------------------------------------------- KSO partners
_LOOKS_JOINT = re.compile(r"^\s*(KSO|JO|JV|Konsorsium|Consortium)\b|\s[-–]\s|\b(PT|CV)\b.*\b(PT|CV|LTD|Co)\b", re.I)
SPLIT_SYSTEM = """A bidder's name in a tender may be a joint operation (KSO / JO / consortium) that lists its partner companies, joined by hyphens, slashes or "and". Hyphens can also be part of a company's own name (for example "UNI-MEDIKA"). List each partner company exactly as written in the name, without the KSO / JO prefix. If the name is a single company, list just that company."""
SPLIT_SCHEMA = {"type": "object", "properties": {"partners": {"type": "array", "items": {"type": "string"}}},
                "required": ["partners"]}


def partners(bidder, hints=(), settings=None, cache_file=None, cancel=lambda: False):
    """The partners of a joint operation (KSO): from the evaluation sheet's own column headings when they
    name them, otherwise read from the bidder's name by the model (cached). A single company gives one item."""
    bidder = str(bidder or "").strip()
    names = []
    for h in hints:
        h = re.sub(r"\s+", " ", str(h or "")).strip()
        named = engine._COMPANY_WORD.search(h) or len([w for w in engine._entity(h).split() if len(w) >= 3]) >= 2
        if h and named and h.lower() != bidder.lower() and engine.same_entity(h, bidder) and h not in names:
            names.append(h)
    if len(names) >= 2:
        return names
    if not settings or not _LOOKS_JOINT.search(bidder):
        return [bidder]
    key = "partners|" + bidder.lower()
    cache = _cache(cache_file) if cache_file else {}
    if key in cache:
        return cache[key]
    try:
        data = _call(settings, SPLIT_SYSTEM, f"Bidder name: {bidder}", SPLIT_SCHEMA, cancel, think=False, num_predict=200)
        got = [re.sub(r"\s+", " ", str(p)).strip(" -–") for p in data.get("partners") or []]
        # keep only names that really are part of the bidder's name
        got = [p for p in got if p and engine.same_entity(p, bidder)]
    except Cancelled:
        raise
    except Exception:
        got = []
    result = got if len(got) >= 2 else [bidder]
    if cache_file:
        cache = _cache(cache_file)
        cache[key] = result
        _store(cache_file, cache)
    return result


# ------------------------------------------------------------------- step 2: choose
_GENERIC = set("""the and for with from that this which bidder bidders peserta document documents dokumen letter surat
shall must have has been years year tahun lampiran attachment file pdf copy evidence proof bukti showing shows
requirement persyaratan partner partners each every company perusahaan""".split())


_JOINT_WORDS = re.compile(r"joint\s*operation|joint\s*venture|konsorsium|consortium|kerja\s*sama\s*operasi|(?<![a-z])jv(?![a-z])", re.I)


def _squash(text):
    """Letters and digits only, lower case, with the many names of a joint operation (JV, joint
    venture, konsorsium ...) written as "kso", so "KSO Uni Medica" finds "1bJVAgreementPTUniMedica1"."""
    t = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", str(text or ""))
    t = _JOINT_WORDS.sub("kso", t)
    return re.sub(r"[^a-z0-9]", "", t.lower())


def _pointer_hit(pointer, name_sq):
    """True when an evaluator's pointer names this file: as a whole, nearly, or every distinctive word of it."""
    import difflib

    psq = _squash(re.sub(r"\.pdf$", "", pointer, flags=re.I))
    if not psq:
        return False
    if psq in name_sq or difflib.SequenceMatcher(None, psq, name_sq).ratio() >= 0.75:
        return True
    words = [_squash(w) for w in re.split(r"[\s_.,;:/()-]+", _JOINT_WORDS.sub("kso", pointer))]
    words = [w for w in words if len(w) >= 2 and w not in _GENERIC and w not in ("pt", "cv", "tbk", "co", "ltd")]
    return len(words) >= 2 and all(w in name_sq for w in words)


def _words(text):
    return {w for w in _norm_tokens(text) if len(w) >= 4 and w not in _GENERIC and not w.isdigit()}


def _pointer_pieces(item):
    """The evaluators' own pointers to the bidder's files ("Suket Wanprestasi PT GBU", "7a14 ... .pdf")."""
    pieces = []
    for h, v in item.get("extra", []):
        if _is_bidder_info(h):
            pieces += [p.strip() for p in re.split(r"\s*/\s*|\n", v) if len(p.strip()) >= 4]
    return pieces


def owner_of(doc, members):
    """The KSO partners a file belongs to, by its file name or its first two pages."""
    if len(members["partners"]) < 2:
        return set(members["partners"])
    head = doc["name"] + "\n" + "\n".join(p for p in doc.get("pages", [])[:2])
    name_sq = _squash(doc["name"])
    owners = set()
    for p in members["partners"]:
        words = [w for w in engine._entity(p).split() if len(w) >= 3]
        initials = "".join(w[0] for w in words)
        if (len(initials) >= 3 and initials in name_sq) or any(len(w) >= 5 and w in name_sq for w in words) \
                or name_on_page(p, head):
            owners.add(p)
    return owners


def choose(item, the_plan, docs, chunks, members):
    """Files to read for each check, chosen in code (fast and predictable): the evaluators' pointers in
    the sheet, file names that match the check, and keyword search over the contents. For a check
    required from each KSO partner, the best file of every partner is taken."""
    import difflib

    readable = [d for d in docs if d["status"] == "ok"]
    pointers = _pointer_pieces(item)
    result = {}
    for n, c in enumerate(the_plan["checks"], 1):
        terms = c.get("search_terms") or []
        strong = _words(" ".join([c.get("what", ""), c.get("evidence", ""), item.get("doc", "")] + terms))
        query = " ".join([c.get("what", ""), c.get("evidence", ""), item["requirement"], item.get("doc", "")])
        ranked = []
        for h in engine.search(chunks, query, terms, budget=10 ** 7, per_file=1):
            if h["file"] not in ranked:
                ranked.append(h["file"])
        score = {}
        for d in readable:
            name_sq = _squash(d["name"])
            s = 0.0
            for p in pointers:                          # evaluators' pointer: strongest signal
                if _pointer_hit(p, name_sq):
                    s += 10
            if strong:
                s += 6 * sum(1 for w in strong if w in name_sq) / len(strong)
            if d["name"] in ranked:
                s += 3 / (1 + ranked.index(d["name"]))
            score[d["name"]] = s
        best = sorted((f for f in score if score[f] > 0), key=lambda f: -score[f])
        # a weak match next to strong ones only costs reading time and invites wrong answers
        strong_enough = lambda fs: [f for f in fs if score[f] >= 0.3 * score[fs[0]]] if fs else []
        if c.get("who") == "each_partner" and len(members["partners"]) > 1:
            owners = {d["name"]: owner_of(d, members) for d in readable}
            files = []
            for p in members["partners"]:
                files += strong_enough([f for f in best if p in owners[f]])[:2]
            files += [f for f in strong_enough(best)[:2] if f not in files]
        else:
            files = strong_enough(best)[:4]
        result[n] = list(dict.fromkeys(files))[:8]
    return result


# -------------------------------------------------------------------- step 3: judge
JUDGE_SYSTEM = """You are a careful member of a Bid Evaluation Committee for a public tender in Indonesia. You check the facts listed below for ONE bidder, using only the document pages given. Think it through step by step before you answer.

How to judge
- Only what the pages show counts. Never assume a document exists or says something that is not on the pages. If the needed page is not given, the status is not_found.
- You know only the pages printed below. A file name alone proves nothing: never say what a file you were not shown contains, and never assume two documents say "the same".
- Every quote, holder, date and figure you give must be printed on the page you cite. Your answer is checked against the pages word by word; anything not found there is rejected.
- Check the name printed on the document: it must be the party the check is about (the bidder, or the named KSO partner, or the manufacturer when the check is about the manufacturer). A document in another company's name does not count for this party.
- If the document shows an end of validity, compare it with today's date: a document that ended before today has expired (not_met).
- If own_statement_ok is false, a statement written by the bidder itself is not enough: the issuing party's document is needed (status claim_only when that is all there is).
- For figures: find the figure for exactly the thing asked (same item, same year or period, same unit) and compare it with the minimum. Say the figure and the minimum.
- For a check required from each partner, give one result per partner. For other checks, one result with party "bidder" (or the partner that shows it).
- If the requirement only applies in a situation that does not apply to this bidder, the status is not_applicable and the quote shows why (for example, the bidder is a single company and the requirement is about joint operations).
- Signatures, stamps and seals are images: they never appear in the text. A document is shown to be signed by the sentence saying it is signed (for example "ditandatangani ... oleh semua anggota") or by the signatories' names and positions at the end. Never say a document is not signed because you see no signature in the text.
- The quote must prove the status for this exact check. For signing, quote the signing sentence or the signatory block, not another clause.

status
- met: the pages show the fact.
- not_met: a page positively shows the fact is not met (wrong scope, wrong party, expired, below the minimum), and the quote shows that failure itself. Something the pages do not show is not_found or unclear, never not_met.
- not_found: no page given shows it.
- claim_only: only the bidder's own statement, where an issuing party's document is needed.
- unclear: the pages are ambiguous, or the text is too garbled to rely on.
- not_applicable: see above.

For each result
- quote: copy the words from the page that prove the status, exactly as printed (5 to 40 words, keep the original spelling and language). Empty only when not_found.
- file and page: taken from the page header where the quote is.
- holder: the company the document is issued to or is about, exactly as printed; "" if none.
- valid_until: end of validity printed on the document as YYYY-MM-DD; "" if none.
- value_found: when the check has a minimum, the figure found as plain digits in the same unit as the minimum; "" otherwise.
- reason: one plain English sentence: what the document is and why it meets or does not meet the check."""

STATUSES = ["met", "not_met", "not_found", "claim_only", "unclear", "not_applicable"]
JUDGE_SCHEMA = {
    "type": "object",
    "properties": {"results": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "check": {"type": "integer"}, "party": {"type": "string"},
            "status": {"type": "string", "enum": STATUSES},
            "quote": {"type": "string"}, "file": {"type": "string"}, "page": {"type": "integer"},
            "holder": {"type": "string"}, "valid_until": {"type": "string"}, "value_found": {"type": "string"},
            "reason": {"type": "string"}},
        "required": ["check", "party", "status", "quote", "file", "page", "holder", "valid_until", "value_found",
                     "reason"]}}},
    "required": ["results"],
}


def evidence_pages(files, docs, the_plan, item, budget):
    """The pages to show: whole files when short, otherwise their best-matching pages."""
    by_name = {d["name"]: d for d in docs}
    query = " ".join([item["requirement"], item.get("doc", "")] + [c["what"] + " " + c["evidence"] for c in the_plan["checks"]])
    terms = [t for c in the_plan["checks"] for t in c.get("search_terms") or []]
    want = set(tokens(query + " " + " ".join(terms)))
    share = budget // max(1, len(files))
    shown = []
    for name in files:
        d = by_name.get(name)
        if not d or d["status"] != "ok":
            continue
        pages = [(n, p.strip()) for n, p in enumerate(d["pages"], 1) if len(p.strip()) >= 20]
        if sum(len(p) for _, p in pages) > share:
            # keep page 1 (title, holder, number) plus the pages that match the checks best
            score = {n: len(want & set(tokens(p))) for n, p in pages}
            best = sorted(pages[1:], key=lambda x: -score[x[0]])
            keep, used = [pages[0]] if pages else [], len(pages[0][1]) if pages else 0
            for n, p in best:
                if used + len(p) > share:
                    continue
                keep.append((n, p))
                used += len(p)
            pages = sorted(keep)
        used = 0
        for n, p in pages:
            text = p[: max(0, share - used)]
            if not text:
                break
            shown.append({"file": name, "page": n, "text": text})
            used += len(text)
    return shown


def judge(item, the_plan, members, shown, docs, settings, cancel, today):
    lines = [f"Today's date: {today.strftime('%d %B %Y')}.", f"Bidder: {members['bidder']}"]
    if len(members["partners"]) > 1:
        lines.append("This bidder is a joint operation (KSO). Partners: " + "; ".join(members["partners"]))
    else:
        lines.append("This bidder is a single company (not a joint operation).")
    lines.append(_requirement_text(item))
    if the_plan["applies_when"]:
        lines.append(f"The requirement applies only when: {the_plan['applies_when']}")
    lines.append("Checks:")
    for n, c in enumerate(the_plan["checks"], 1):
        mn = f"; minimum: {c['minimum']}" if c.get("minimum") else ""
        lines.append(f"{n}. {c['what']} (from: {c['who'].replace('_', ' ')}; evidence: {c['evidence']}; "
                     f"own_statement_ok: {str(bool(c.get('own_statement_ok'))).lower()}{mn})")
    notes = [(h, v) for h, v in item.get("extra", []) if _is_bidder_info(h)]
    if notes:
        lines.append("Evaluators' notes on where the bidder put its documents (a pointer, not evidence):")
        lines += [f"- {h}: {v}" for h, v in notes]
    lines.append("")
    seen = {s["file"] for s in shown}
    unseen = [d["name"] for d in docs if d["name"] not in seen]
    if unseen:
        # Names only, so the model knows they exist. It has NOT read them and must not describe them.
        lines.append(f"Other files of the bidder, NOT shown to you ({len(unseen)}). You do not know what they say: "
                     f"never describe their content and never use them as evidence: " + "; ".join(unseen[:120]))
        lines.append("")
    if shown:
        lines.append("Pages:")
        for s in shown:
            lines.append(f"=== FILE: {s['file']} | PAGE: {s['page']} ===")
            lines.append(s["text"])
    else:
        lines.append("Pages: none of the bidder's files matched these checks.")
    _step(f"Reading {len(shown)} page(s) and reasoning (the longest step)")
    data = _call(settings, JUDGE_SYSTEM, "\n".join(lines), JUDGE_SCHEMA, cancel, think=True, num_predict=6000)
    return [r for r in data.get("results") or [] if r.get("status") in STATUSES]


# ------------------------------------------------------------------- step 4: verify
def _norm_tokens(text):
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


def quote_found(quote, page_text):
    """True when the quote really is on the page (allowing for small reading differences)."""
    q = _norm_tokens(quote)
    if len(q) < 3:
        return False
    p = _norm_tokens(page_text)
    pset = set(p)
    if sum(1 for t in q if t in pset) < 0.85 * len(q):
        return False
    # the words must also appear close together, not scattered over the page
    joined, target = " ".join(p), " ".join(q)
    if target in joined:
        return True
    import difflib
    m = difflib.SequenceMatcher(None, p, q, autojunk=False)
    return sum(b.size for b in m.get_matching_blocks()) >= 0.75 * len(q)


def quote_span(quote, page_text):
    """The words as printed on the page for a quote that quote_found accepted, so the evidence shows the
    page itself rather than the model's copy of it (which may have changed a word)."""
    import difflib

    toks = [(m.group(0).lower(), m.start(), m.end()) for m in re.finditer(r"[A-Za-z0-9]+", page_text or "")]
    q = _norm_tokens(quote)
    blocks = [b for b in difflib.SequenceMatcher(None, [t[0] for t in toks], q, autojunk=False)
              .get_matching_blocks() if b.size]
    if not blocks:
        return quote
    start, end = blocks[0].a, blocks[-1].a + blocks[-1].size
    if end - start > 1.6 * len(q) + 5:
        return quote
    return re.sub(r"\s+", " ", page_text[toks[start][1]:toks[end - 1][2]]).strip()


def name_on_page(name, page_text):
    """True when a company name is printed on the page (allowing for scan errors and spelling variants)."""
    import difflib

    words = [w for w in engine._entity(name).split() if len(w) >= 3]
    if not words:
        return True
    pool = set(_norm_tokens(page_text))
    hits = sum(1 for w in words if w in pool or any(difflib.SequenceMatcher(None, w, p).ratio() >= 0.8
                                                    for p in pool if abs(len(p) - len(w)) <= 2))
    return hits >= max(1, round(0.6 * len(words)))


def figure_on_page(value, page_text):
    """True when the figure is printed on the page, whatever the thousands separators or a
    'thousands' / 'millions' presentation (trailing zeros dropped)."""
    v = re.sub(r"\D", "", str(value or ""))
    if not v:
        return True
    digits = [re.sub(r"\D", "", m) for m in re.findall(r"\d[\d.,\s]*\d|\d", page_text)]
    core = v.rstrip("0") or v
    return any(d == v or (len(core) >= 3 and d.rstrip("0") == core) for d in digits)


def date_on_page(iso, page_text):
    """True when the date's year is printed on the page (dates are written in many formats)."""
    d = engine._date(iso)
    return d is None or str(d.year) in page_text


def _strict_file(name, files):
    """The shown file the model cited, matched exactly (ignoring case, folders and spacing). No fuzzy
    matching: bid files differ by one code or partner ('2a ... PT GBU' / '2c ... PT AMS')."""
    if not name:
        return None
    key = lambda f: re.sub(r"\s+", " ", os.path.basename(str(f).replace("\\", "/"))).strip().lower()
    want = key(name)
    return next((f for f in files if key(f) == want), None)


def _partner_of(party, members):
    """The KSO partner a result is about, or None when it is about the bidder as a whole."""
    if len(members["partners"]) < 2 or not party:
        return None
    best = [p for p in members["partners"] if engine.same_entity(party, p)]
    return best[0] if len(best) == 1 else None


def verify(results, the_plan, shown, members, today):
    """Check every result against the pages in code. Nothing the model states is accepted unless it is
    printed on a page it was shown. Returns the results with status corrected and 'fix' saying why."""
    pages = {(s["file"], s["page"]): s["text"] for s in shown}
    files = sorted({s["file"] for s in shown})
    out = []
    for r in results:
        r = dict(r)
        n = r.get("check") if isinstance(r.get("check"), int) else 1
        n = min(max(n, 1), len(the_plan["checks"]))
        check = the_plan["checks"][n - 1]
        r["check"] = n
        cited = r.get("file")
        r["file"] = _strict_file(cited, files) or ""
        r["fix"] = ""
        if r["status"] == "not_found":
            # nothing to verify, and nothing the model "says" about unseen files is kept
            r.update(quote="", holder="", valid_until="", value_found="", file="", page=None,
                     reason="No page shown to the checker shows this.")
            out.append(r)
            continue
        if r["status"] == "not_applicable" and not r.get("quote"):
            # Without a page, "does not apply" is accepted only when code itself can confirm it:
            # the requirement is about joint operations and the bidder is a single company.
            about_jo = re.search(r"joint|KSO|kerja sama operasi|konsorsium|consortium|JV\b|JO\b",
                                 the_plan["applies_when"] + " " + check.get("what", ""), re.I)
            if about_jo and len(members["partners"]) == 1:
                r.update(fix="", reason="The bidder is a single company, not a joint operation (KSO).")
            else:
                r["status"], r["fix"] = "unclear", "no_quote"
            out.append(r)
            continue
        # 1. the quote must be on the cited page (or, if the page number is off, on another page shown)
        here = pages.get((r["file"], r.get("page")))
        if cited and not r["file"]:
            r["fix"] = "file_not_shown"                 # cites a file the model never saw
        elif not r.get("quote"):
            r["fix"] = "no_quote"
        elif not (here and quote_found(r["quote"], here)):
            where = next(((f, p) for (f, p), t in pages.items() if quote_found(r["quote"], t)), None)
            if where:
                r["file"], r["page"] = where
                here = pages[where]
            else:
                r["fix"] = "quote_not_found"
        if not r["fix"]:
            r["quote"] = quote_span(r["quote"], here)
        if r["fix"]:
            if r["status"] != "not_applicable":
                r["status"] = "unclear"                 # a verdict either way needs proof
            out.append(r)
            continue
        # 2. every detail the model read off the page must be printed there
        holder = re.sub(r"\s+", " ", str(r.get("holder") or "")).strip()
        if holder and not name_on_page(holder, here):
            r["holder"] = holder = ""                   # not trusted, not used
        if r.get("valid_until") and not date_on_page(r["valid_until"], here):
            r["valid_until"] = ""
        if r.get("value_found") and not figure_on_page(r["value_found"], here):
            if r["status"] == "met" and check.get("minimum"):
                r["status"], r["fix"] = "unclear", f"value_not_on_page:{r['value_found']}"
                out.append(r)
                continue
            r["value_found"] = ""
        # 3. a result about one KSO partner must rest on a page that names that partner
        partner = _partner_of(r.get("party"), members)
        if partner and r["status"] in ("met", "claim_only") and not name_on_page(partner, here):
            r["status"], r["fix"] = "unclear", f"partner_not_on_page:{partner}"
            out.append(r)
            continue
        # 4. dates, minimums and the document holder, compared in code
        if r["status"] == "met":
            end = engine._date(r.get("valid_until"))
            need, got = engine._number(check.get("minimum")), engine._number(r.get("value_found"))
            about_maker = check.get("who") == "manufacturer"
            if end and end < today:
                r["status"], r["fix"] = "not_met", f"expired:{end.isoformat()}"
            elif need is not None and got is None:
                r["status"], r["fix"] = "unclear", "no_figure"
            elif need is not None and got < need:
                r["status"], r["fix"] = "unclear", f"below_minimum:{got:.0f}<{need:.0f}"
            elif (holder and engine._COMPANY_WORD.search(holder) and not about_maker
                  and not engine.same_entity(holder, members["bidder"])
                  and not any(engine.same_entity(holder, p) for p in members["partners"])):
                r["status"], r["fix"] = "unclear", f"other_company:{holder}"
        out.append(r)
    return cover(out, the_plan, members)


CONFIRM_SYSTEM = """You double-check one finding of a bid evaluation. You get a check, the finding and a passage copied from the bidder's document. Decide from the passage alone: does this passage itself show the finding?

- "yes" only if anyone reading just this passage would agree it shows the finding.
- "no" if the passage is about something else, shows only part of it, or the finding needs something the passage does not say.
- Which company the document belongs to is checked separately: do not judge that.
- Signatures are images and never appear in text: a sentence saying the document is signed by the parties, or the signatories' names and positions, shows that it is signed."""
CONFIRM_SCHEMA = {"type": "object", "properties": {"shows": {"type": "string", "enum": ["yes", "no"]},
                                                   "why": {"type": "string"}}, "required": ["shows", "why"]}
_MEANING = {
    "met": "the passage shows that this check is met",
    "not_met": "the passage shows that this check is NOT met (it shows a failure, not merely that something is absent)",
    "claim_only": "the passage is the bidder's own statement of this, not a document from the issuing party",
}


def confirm(results, the_plan, settings, cancel, log=print):
    """A second, independent look at every accepted finding: a short call that sees only the check and
    the quote. A quote that is genuinely on the page but does not prove the finding (a clause about
    profit shares cited for 'not signed') is not accepted."""
    asked = {}
    out = []
    _step("Second look: does each quote really show the finding?")
    for r in results:
        if r["status"] not in _MEANING or r.get("fix") or not r.get("quote"):
            out.append(r)
            continue
        c = the_plan["checks"][r["check"] - 1]
        key = (r["check"], r["status"], r["quote"])
        if key not in asked:
            user = (f"Check: {c['what']}\nFinding: {_MEANING[r['status']]}\n"
                    f"Passage (page {r.get('page')} of the document): \"{r['quote']}\"")
            try:
                ans = _call(settings, CONFIRM_SYSTEM, user, CONFIRM_SCHEMA, cancel, think=False, num_predict=200)
            except Cancelled:
                raise
            except Exception:                         # no second look possible: do not accept on trust
                ans = {"shows": "no", "why": "the second check could not be done"}
            asked[key] = ans
        ans = asked[key]
        r = dict(r)
        if ans.get("shows") != "yes":
            log(f"    second check rejected the {r['status']} finding for {r.get('party') or 'bidder'}: "
                f"{str(ans.get('why', ''))[:160]}")
            r["status"], r["fix"] = "unclear", "quote_does_not_show"
        out.append(r)
    return out


def collapse(results, the_plan, members):
    """One answer per check (or per partner for a check needed from each partner). For a check about the
    bidder as a whole one proven document is enough; repeated answers are dropped."""
    kso = len(members["partners"]) > 1
    out = []
    for n, check in enumerate(the_plan["checks"], 1):
        mine = [r for r in results if r["check"] == n]
        groups = {}
        if check.get("who") == "each_partner" and kso:
            for r in mine:
                p = _partner_of(r.get("party"), members)
                if p is not None:                     # whole-bidder answers to a per-partner check are dropped
                    groups.setdefault(p, []).append(r)
        else:
            groups[None] = mine
        for rs in groups.values():
            met = [r for r in rs if r["status"] == "met"]
            if met:
                out.append(met[0])
                continue
            seen = set()
            for r in rs:
                k = (r["status"], r.get("quote"), r.get("fix"))
                if k not in seen:
                    seen.add(k)
                    out.append(r)
    return cover(out, the_plan, members)


def cover(results, the_plan, members):
    """Every check needs a result, and a check required from each KSO partner needs one per partner.
    What the model left out is recorded as not found, so a KSO is never passed on one partner's papers."""
    out = list(results)
    for n, check in enumerate(the_plan["checks"], 1):
        mine = [r for r in out if r["check"] == n]
        if check.get("who") == "each_partner" and len(members["partners"]) > 1:
            for p in members["partners"]:
                if not any(_partner_of(r.get("party"), members) == p for r in mine):
                    out.append({"check": n, "party": p, "status": "not_found", "quote": "", "file": "", "page": None,
                                "holder": "", "valid_until": "", "value_found": "", "fix": "missing_partner",
                                "reason": "No page shown to the checker shows this for this partner."})
        elif not mine:
            out.append({"check": n, "party": members["bidder"], "status": "not_found", "quote": "", "file": "",
                        "page": None, "holder": "", "valid_until": "", "value_found": "", "fix": "",
                        "reason": "No page shown to the checker shows this."})
    return out


def decide(results, the_plan, members):
    """The finding for the requirement, from the verified check results, by fixed rules."""
    if not results:
        return "ambiguous"
    by_check = {}
    for r in results:
        by_check.setdefault(r["check"], []).append(r["status"])
    # every check needs an answer; a check the model skipped is unanswered
    for n in range(1, len(the_plan["checks"]) + 1):
        by_check.setdefault(n, ["not_found"])
    every = [s for v in by_check.values() for s in v]
    if all(s == "not_applicable" for s in every):
        return "not_applicable"
    every = [s for s in every if s != "not_applicable"]
    if "not_met" in every:
        return "deviation"
    if all(s == "met" for s in every):
        return "verified"
    if all(s == "not_found" for s in every):
        return "no_document"
    if "unclear" in every:
        return "ambiguous"
    if "claim_only" in every and "met" not in every:
        return "not_substantiated"
    if "claim_only" in every:
        return "partial"
    return "partial"                                  # some met, some not found


# --------------------------------------------------------------------- step 5: write
WRITE_SYSTEM = """You write the evaluation note for ONE requirement of ONE bidder in an Indonesian public tender, for readers with no technical or legal training. You get the requirement, the verdict (already decided, do not change it) and the verified check results.

- note_en: 2 to 4 plain English sentences: what the requirement asks in everyday words; what the documents show (company names, numbers, dates, the kind of document); and why that is enough, or exactly what is missing or wrong. Explain each abbreviation in brackets the first time. Refer to documents by what they are, not by file number. Do not start with the verdict word. No remarks about how the check was done.
- Every statement about a document must come from the verified check results: what is "printed on the page" or the checker's finding. Do not add details (who signed, positions, addresses, dates, amounts) that are not there. Each statement is checked against the results and a note with unsupported statements is rejected.
- note_id: the same content in faithful, formal Bahasa Indonesia with Indonesian number style (1.800; 0,5). Call the bidder "peserta", the requirement "persyaratan", a joint operation "KSO".
- bidder_question: if the verdict is not Meet: one neutral, specific request in English for evidence of the bid as submitted, naming the document and the party it is needed from. Never invite a new or changed offer. If the verdict is Meet: ""."""

WRITE_SCHEMA = {
    "type": "object",
    "properties": {"note_en": {"type": "string"}, "note_id": {"type": "string"}, "bidder_question": {"type": "string"}},
    "required": ["note_en", "note_id", "bidder_question"],
}

FIX_TEXT = {
    "quote_not_found": "the passage given as proof could not be found on the cited page, so it is not accepted",
    "file_not_shown": "the answer relied on a document the checker was not shown, so it is not accepted",
    "no_quote": "no passage was given as proof, so it is not accepted",
    "expired": "the document's validity ended on {0}, before today",
    "below_minimum": "the figure found ({0}) is below the minimum ({1})",
    "no_figure": "no figure could be read for the required minimum",
    "value_not_on_page": "the figure given ({0}) is not printed on the cited page, so it is not accepted",
    "other_company": "the document is in the name of {0}, which is not the bidder or one of its KSO partners",
    "partner_not_on_page": "the cited page does not name {0}, so it does not show this for that partner",
    "missing_partner": "no document for this KSO partner was found among the pages read",
    "quote_does_not_show": "the passage given as proof does not itself show this, so it is not accepted",
}
FIX_TEXT_ID = {
    "quote_not_found": "kutipan yang dijadikan bukti tidak ditemukan pada halaman yang dirujuk, sehingga tidak diterima",
    "file_not_shown": "jawaban merujuk dokumen yang tidak dibaca oleh pemeriksa, sehingga tidak diterima",
    "no_quote": "tidak ada kutipan bukti, sehingga tidak diterima",
    "expired": "masa berlaku dokumen berakhir pada {0}, sebelum tanggal hari ini",
    "below_minimum": "angka yang ditemukan ({0}) di bawah batas minimum ({1})",
    "no_figure": "tidak ada angka yang terbaca untuk batas minimum yang disyaratkan",
    "value_not_on_page": "angka yang disebut ({0}) tidak tercantum pada halaman yang dirujuk, sehingga tidak diterima",
    "other_company": "dokumen atas nama {0}, yang bukan peserta atau anggota KSO peserta",
    "partner_not_on_page": "halaman yang dirujuk tidak mencantumkan {0}, sehingga tidak membuktikan hal ini untuk anggota KSO tersebut",
    "missing_partner": "tidak ditemukan dokumen untuk anggota KSO ini pada halaman yang dibaca",
    "quote_does_not_show": "kutipan yang dijadikan bukti tidak menunjukkan hal ini, sehingga tidak diterima",
}


def _fix_words(fix, table=FIX_TEXT):
    if not fix:
        return ""
    kind, _, rest = fix.partition(":")
    args = rest.split("<") if kind == "below_minimum" else [rest]
    try:
        return table[kind].format(*args)
    except (KeyError, IndexError):
        return ""


def _facts_for_writer(item, the_plan, members, results, finding):
    """Only verified material: quotes that are on the page, and the checker's own corrections.
    The judge's free-text reasons are passed only for results that survived every check."""
    tag_en, _, label = engine.DECISION[finding]
    lines = [f"Bidder: {members['bidder']}"]
    if len(members["partners"]) > 1:
        lines.append("KSO partners: " + "; ".join(members["partners"]))
    lines += [_requirement_text(item), f"Verdict: {label} ({tag_en})", "Verified check results:"]
    for r in results:
        c = the_plan["checks"][min(max(r["check"], 1), len(the_plan["checks"])) - 1]
        fix = _fix_words(r.get("fix"))
        line = f"- {c['what']} | party: {r.get('party') or 'bidder'} | status: {r['status']}"
        # file names are left out on purpose: the note describes documents, the Evidence list names them
        if r.get("quote") and not fix:
            line += f' | printed on the page: "{r["quote"]}"'
        if r.get("holder") and not fix:
            line += f" | issued to: {r['holder']}"
        if r.get("valid_until") and not fix:
            line += f" | valid until: {r['valid_until']}"
        if r.get("value_found") and not fix:
            line += f" | figure: {r['value_found']} (minimum {c.get('minimum')})"
        if fix:
            line += f" | checker's finding: {fix}"
        elif r.get("reason") and r["status"] != "not_found":
            line += f" | note: {r['reason']}"
        lines.append(line)
    return "\n".join(lines)


_COMPANY_IN_TEXT = re.compile(r"\b(?:PT|CV|UD)\.?\s+(?:[A-Z][\w&'.-]*\s*){1,5}|(?:[A-Z][\w&'.-]*\s+){1,5}(?:Co\.?,?\s*Ltd|Ltd|Inc|GmbH|Corporation|Limited)\b\.?")


def check_note(text, allowed_text, members, holders):
    """Problems in a written note: figures, company names or file references that do not come from
    the verified material. An empty list means the note is grounded."""
    problems = []
    allowed_digits = {re.sub(r"\D", "", m) for m in re.findall(r"\d[\d.,]*\d|\d", allowed_text)}
    allowed_digits |= {d.rstrip("0") for d in allowed_digits if d.rstrip("0")}
    for m in re.findall(r"\d[\d.,]*\d|\d{2,}", text):
        d = re.sub(r"\D", "", m)
        if len(d) >= 2 and d not in allowed_digits and d.rstrip("0") not in allowed_digits:
            problems.append(f'the figure "{m}" is not in the verified results')
    for m in _COMPANY_IN_TEXT.finditer(text):
        name = m.group(0).strip()
        known = [members["bidder"], *members["partners"], *holders]
        if not any(engine.same_entity(name, k) for k in known if k):
            problems.append(f'the company "{name}" is not in the verified results')
    # an abbreviation (SIUP, SKD, NIB ...) names a kind of document: it must come from the verified material
    for ab in dict.fromkeys(re.findall(r"\b[A-Z]{2,6}\b", text)):
        if ab not in {"KSO", "JO", "JV", "PT", "CV", "ID", "UD"} and not re.search(rf"\b{ab}\b", allowed_text, re.I):
            problems.append(f'"{ab}" is not in the verified results')
    if re.search(r"\.pdf\b|\b(file|berkas|document|dokumen|lampiran|attachment)\s+(no\.?\s*)?\d+[a-z]?\b", text, re.I):
        problems.append("it refers to a file by name or number; describe the document instead")
    return problems


# Words any note may use without them being in the verified results. Kinds of document (licence,
# certificate, agreement ...) and details such as "signed" are deliberately NOT here: they must come
# from the requirement or the quotes, or the note is describing a document nobody verified.
_NOTE_WORDS = set("""requirement requirements requires required require asks asked bidder bidders document documents documentation
submitted submit provides provided provide shows showing shown show states stated dated valid validity
expired expiry partner partners joint operation operations member members company companies issued meets meet
met missing absent found needed needs evidence proof proves prove confirm confirms confirming clarification
each together combined therefore because however although which their there these those this that with from
within without other another every only also both either neither enough sufficient insufficient minimum
maximum figure figures amount total years year period preceding before after since until deadline submission
bids bid tender procurement page pages name names named about under whether should would could must shall
given read none checked cannot does contain contains contained containing include includes including included
covers cover covering refers mentioned regarding concerning respect relevant same different second third
first one two three four five state stating says saying past last never broken break breaking failed fail
failure failures have been having kind type everyday means meaning words wording written
""".split())


def ungrounded_sentences(note_en, allowed_text):
    """Sentences of the English note that contain several descriptive words found neither in the verified
    results nor in the requirement: a sign the writer added something the documents do not say."""
    allowed = set(_norm_tokens(allowed_text))
    bad = []
    for sentence in re.split(r"(?<=[.!?])\s+", note_en or ""):
        words = [w for w in _norm_tokens(sentence) if len(w) >= 4 and not w.isdigit()]
        novel = [w for w in words if w not in allowed and w not in _NOTE_WORDS and w.rstrip("s") not in allowed
                 and w.rstrip("ed") not in allowed and w.rstrip("ing") not in allowed]
        if len(novel) >= 3 and len(novel) > 0.25 * max(1, len(words)):
            bad.append(f'"{sentence.strip()[:120]}" says things not in the verified results ({", ".join(novel[:5])})')
    return bad


def template_note(item, the_plan, members, results, finding):
    """A plain note built only from verified results, used when the written note cannot be grounded.
    Files and pages are not repeated here: they are in the Evidence list below the note."""
    en, idn = [], []
    for n, c in enumerate(the_plan["checks"], 1):
        parts_en, parts_id = [], []
        for r in (r for r in results if r["check"] == n):
            who = r.get("party") or members["bidder"]
            fix_en, fix_id = _fix_words(r.get("fix")), _fix_words(r.get("fix"), FIX_TEXT_ID)
            if r["status"] == "met":
                parts_en.append(f"{who}: shown by the document")
                parts_id.append(f"{who}: dibuktikan oleh dokumen")
            elif r["status"] == "not_applicable":
                parts_en.append(f"{who}: does not apply")
                parts_id.append(f"{who}: tidak berlaku")
            elif r["status"] == "not_met" and not fix_en:
                parts_en.append(f"{who}: not met, see the quoted words")
                parts_id.append(f"{who}: tidak terpenuhi, lihat kutipan")
            else:
                parts_en.append(f"{who}: {fix_en or 'no document showing this was found among the pages read'}")
                parts_id.append(f"{who}: {fix_id or 'tidak ditemukan dokumen yang membuktikan hal ini pada halaman yang dibaca'}")
        if parts_en:
            en.append(f"{c['what']}. " + "; ".join(parts_en) + ".")
            idn.append(f"{c['what']}. " + "; ".join(parts_id) + ".")
    return {"note_en": " ".join(en), "note_id": " ".join(idn)}


def write(item, the_plan, members, results, finding, settings, cancel, log=print):
    facts = _facts_for_writer(item, the_plan, members, results, finding)
    holders = [r["holder"] for r in results if r.get("holder") and not r.get("fix")]
    allowed = facts + " " + datetime.date.today().isoformat() + " " + datetime.date.today().strftime("%d %m %Y")
    if not any(r.get("quote") and not r.get("fix") for r in results):
        # nothing was verified, so there is nothing true to describe: a written note could only invent
        plain = template_note(item, the_plan, members, results, finding)
        asks = list(dict.fromkeys(the_plan["checks"][r["check"] - 1]["what"] for r in results
                                  if r["status"] not in ("met", "not_applicable")))
        question = ("Please indicate the document and page in the bid as submitted that show: " + "; ".join(asks) + "."
                    if asks else "")
        return dict(plain, bidder_question=question)
    user = facts
    for attempt in range(2):
        _step("Writing the note" + (" again" if attempt else ""))
        text = _call(settings, WRITE_SYSTEM, user, WRITE_SCHEMA, cancel, think=False, num_predict=900)
        problems = check_note(f"{text.get('note_en', '')}\n{text.get('note_id', '')}", allowed, members, holders)
        problems += ungrounded_sentences(text.get("note_en", ""), allowed)
        if not problems:
            return text
        log("    the note mentioned things not in the verified results (" + "; ".join(problems[:3])
            + ")" + ("; writing it again" if attempt == 0 else "; using a plain note built from the results"))
        user = (facts + "\n\nYour previous note was rejected because " + "; ".join(problems)
                + ". Write it again using only the verified check results above.")
    plain = template_note(item, the_plan, members, results, finding)
    return dict(plain, bidder_question=text.get("bidder_question", ""))


def evidence_block(results, the_plan, shown):
    """The support for every statement, printed in the cell: document, page and the exact words, or
    what was searched when nothing was found. Built by code from verified results only."""
    lines = ["Evidence / Bukti:"]
    read = sorted({s["file"] for s in shown})
    for i, r in enumerate(results, 1):
        who = r.get("party") or "bidder"
        fix = _fix_words(r.get("fix"))
        if r["status"] in ("met", "not_met", "claim_only", "not_applicable") and r.get("quote") and not fix:
            lines.append(f'{i}. {who}: {r["file"]}, p. {r.get("page")}: "{r["quote"]}"')
        elif r["status"] == "not_applicable" and not fix:
            lines.append(f"{i}. {who}: {r.get('reason') or 'does not apply'}")
        elif fix:
            lines.append(f"{i}. {who}: not accepted - {fix}.")
        else:
            lines.append(f"{i}. {who}: not found in the documents read.")
    lines.append("Documents read / Dokumen yang dibaca: " + ("; ".join(read) if read else "none matched"))
    return "\n".join(lines)


# ---------------------------------------------------------------------- the whole
def _step(text, log=None):
    """Tell the pane (and the log) which step is running."""
    engine.ACTIVITY["step"] = text
    if log:
        log("    " + text)


def _call(settings, system, user, schema, cancel, think, num_predict):
    num_ctx = int(settings.get("carefulCtx", 16384))
    try:
        data, _ = ollama_chat(settings["model"], system, user, schema, cancel, num_ctx=num_ctx,
                              num_predict=num_predict, think=think)
        return data
    except Cancelled:
        raise
    except RuntimeError:
        if not think:
            raise
        # reasoning ran past the room it had: answer directly rather than fail the row
        data, _ = ollama_chat(settings["model"], system, user, schema, cancel, num_ctx=num_ctx,
                              num_predict=1500, think=False)
        return data


def evaluate_item(item, bidder, title, docs, chunks, settings, cache_dir, cancel=lambda: False, log=print,
                  partner_hints=(), state=None):
    """Same result shape as engine.evaluate_item. `state` is a dict kept per bidder (file catalogue)."""
    import time

    started = time.time()
    today = datetime.date.today()
    state = state if state is not None else {}
    plans_file = os.path.join(cache_dir, "plans.json")
    if "partners" not in state:
        state["partners"] = partners(bidder, partner_hints, settings, plans_file, cancel)
        if len(state["partners"]) > 1:
            log("    KSO partners: " + "; ".join(state["partners"]))
    members = {"bidder": bidder, "partners": state["partners"]}
    _step("Choosing the documents to read")
    the_plan = partner_rule(plan(item, settings, plans_file, cancel, log), item, members)
    chosen = choose(item, the_plan, docs, chunks, members)
    files = []
    for n in sorted(chosen):
        for f in chosen[n]:
            if f not in files:
                files.append(f)
    files = files[:8]
    shown = evidence_pages(files, docs, the_plan, item, int(settings.get("evidenceChars", 18000)))
    log(f"    {len(the_plan['checks'])} check(s); reading {len(files)} file(s): " + "; ".join(files))
    results = verify(judge(item, the_plan, members, shown, docs, settings, cancel, today),
                     the_plan, shown, members, today)
    results = collapse(confirm(results, the_plan, settings, cancel, log), the_plan, members)
    finding = decide(results, the_plan, members)
    unreadable = [d["name"] for d in docs if d["status"] != "ok"]
    if finding == "no_document" and unreadable:
        finding = "evidence_unreadable"
    text = write(item, the_plan, members, results, finding, settings, cancel, log)

    tag_en, tag_id, label = engine.DECISION[finding]
    note_en, note_id = engine._clean(text.get("note_en")), engine._clean(text.get("note_id"))
    en_part = f"{tag_en} – {note_en}\n\n" + evidence_block(results, the_plan, shown)
    refs = {}
    for r in results:
        # only pages whose quote was verified are listed as references
        if r.get("file") and r["status"] != "not_found" and not r.get("fix", "").startswith(
                ("quote_not_found", "file_not_shown", "no_quote", "value_not_on_page", "partner_not_on_page",
                 "quote_does_not_show")):
            refs.setdefault(r["file"], set()).add(r.get("page"))
    paths = {d["name"]: d["path"] for d in docs}
    lines = []
    for i, (f, pages) in enumerate(refs.items(), 1):
        pg = sorted(p for p in pages if isinstance(p, int))
        lines.append(f"{i}. {re.sub(r'^[0-9]+[.]\s+', '', f)}" + (f" (p. {', '.join(map(str, pg))})" if pg else ""))
    question = engine._clean(text.get("bidder_question")) if label != "Meet" else ""
    if label != "Meet" and not question:
        question = "Please indicate the document and page in the bid as submitted that show this requirement is met."
    return {
        "row": item.get("row"), "no": item.get("no", ""), "finding": finding, "label": label,
        "note": en_part + engine.ID_MARK + f"{tag_id} – {note_id}", "en_len": len(en_part),
        "refs": "\n".join(lines), "link": paths.get(next(iter(refs))) if len(refs) == 1 else None,
        "question": question, "facts": json.dumps(results, ensure_ascii=False)[:4000],
        "seconds": round(time.time() - started), "keywords": [t for c in the_plan["checks"] for t in c.get("search_terms") or []],
        "excerpts": [f"{s['file']} p.{s['page']}" for s in shown], "plan": the_plan, "checks": results,
    }
