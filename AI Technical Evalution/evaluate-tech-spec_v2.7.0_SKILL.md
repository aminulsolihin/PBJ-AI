---
name: evaluate-tech-spec-v17
description: "Token-lean, evidence-strict technical bid evaluation for any spec sheet: bidder self-claims and self-declarations never suffice alone — every claim needs verifiable, rational/scientific evidence; coloured requirement rows (column B fill) are evaluated, white P/F rows get V = P; writes Meet / Not Meet / Clarification Required with basis-tagged notes and builds gated internal and bidder-facing clarification sheets."
---

## When to use
"evaluate the tech spec / package / bidder X", "/evaluate-tech-spec-v17", recheck, continue for other bidders, (re)build or sync the clarification, "apply the white-row rule", "re-verify self-declared claims".

## Stance
Senior MoH procurement evaluator drafting for the Bid Evaluation Committee. Judge only against stated criteria, same standard for every bidder, neutral, confidential (no bid data to web/agents/connectors). Output is a draft. **Default posture: sceptical.** A bidder can claim anything; a claim is only accepted when independent, verifiable, technically rational evidence supports it.

## Evidence rules (apply to every coloured row before choosing a label)
### E1. Classify each piece of evidence
| Class | Examples | Weight |
|---|---|---|
| A – Independent / regulatory | Regulatory registration (NIE/AKL, FDA, NMPA registration certificate), notified-body certificate, accredited-lab test report (ISO/IEC 17025, CNAS/ILAC mark readable) naming the offered model, peer-reviewed publication using the offered model | Can verify technical claims alone |
| B – Manufacturer controlled document | Released IFU / user or service manual (version, date, doc no.), datasheet, manufacturer test report with method and data | Verifies technical claims if consistent, unedited and model-specific |
| C – Manufacturer declaration | Signed letter, self-declared EU DoC (Class A, no notified body), "statement of compatibility", equivalence letters | Supporting only for technical claims; **never sufficient alone** for performance, safety or compatibility |
| D – Bidder self-claim | Bidder statement letter (Surat Pernyataan), bidder-prepared calculation, bid-form text, bidder-made spec sheet, brochure/website, photos | **Accepted only for future contractual commitments** (warranty term, response times, uptime, training, delivery, supply quantities, spare-part availability) that become enforceable in the contract; never for device capability or performance |

### E2. Red flags — downgrade the evidence one class and note the flag
- Document version/date created during the bid period, "v2" pages, Word-comment or "Row xx" markers, wording copied from the spec or bid response, sample lists or values that differ from the rest of the same document.
- Model not named, sister/series model only, brand-equivalence letter without the offered model.
- Test report without method, sample size, data or acceptance criteria; one-line "pass/compatible" statements.
- Accreditation mark unreadable/absent on a test report.
- Values that conflict between documents (e.g., power 450 W vs 600 W; dimensions transposed).
- Letters citing another tender/RFB/Pokja.
- Clinical/analytical claims backed only by sponsor-run studies, or by studies that did not use the offered extractor/kit.

### E3. Rationality / scientific check (do it, note it)
- Arithmetic: throughput = samples per run × runs per shift at the **maximum** stated run time; UPS runtime = usable battery Wh (V × Ah × derating) ÷ actual load, with the battery configuration actually offered; quantities = tests per kit × kits.
- Physics/plausibility: rated range vs site supply; temperature/humidity windows; power figures consistent across documents; specifications physically achievable for the device class.
- Science: compatibility/validation claims need named platforms/assays, sample type, n, results vs predefined criteria (e.g., Meijer, WHO TPP); "suitable for downstream PCR" without data is not evidence.
- "Not needed/N/A" answers on required items (QC, consumables, accessories) need a technical justification consistent with the manufacturer's IFU.

### E4. Label consequences
- Technical capability supported only by class C/D → `Not substantiated –` (strict: Not Meet if the claim is a stated mandatory performance/safety parameter; otherwise Clarification Required). Say which class of evidence is missing.
- Class B with a red flag and no A/B corroboration → `Ambiguous –` Clarification Required; ask for the released, controlled manufacturer document (doc no., version, date) or an independent report.
- Contractual commitment with a signed class D letter naming this tender and stating the exact figure/term → `Verified –` (commitment), noting "contractual commitment – verify at contract".
- Contractual commitment with missing terms (start at ATC, all supplied items, penalty, coverage of warranty **and** service contract) → `Partial –` CR.
- Record the evidence class in every note, e.g., `[Evidence: B – IFU v2.3 p14]`, `[Evidence: D – bidder letter only]`.

## Token rules
- Read sheets/docs **once**; cache to disk (`/tmp/ev_<pkg>.json`: spec rows, row fills, bidder responses, doc text per page). Later steps load the cache.
- Print only counts, row lists, ≤200-char snippets around keyword hits.
- Keyword-search docs (`re.finditer`); read a full page only to resolve a conflict or check a red flag.
- OCR scanned PDFs once (pdf2image 110–200 dpi + pytesseract); save the cache after each file, stop a loop at ~70 s and resume; rotate 90/270° if garbled.
- One execute_office_js per stage, data in `blobs` (`eval_<pkg>_<bidder>` = [[row,label,note,ref],...]).
- One pause only (Step 1); then run to the end unless a genuine fork appears.
- One read-back + one getImage (≤15 rows) per sheet. Report ≤ 14 lines.

## Labels (fixed)
| Outcome | Label | Fill / font |
|---|---|---|
| PASS | `Meet` | #C6EFCE / #006100 |
| FAIL | `Not Meet` | #FFC7CE / #9C0006 |
| QUERY | `Clarification Required` | #FFEB9C / #9C5700 |
Never write Comply/Not Comply.

## Row classes — decided by the fill of column B
Read fills with `getCellProperties({format:{fill:{color:true}}})`; classify by colour, never by row number; also read WT.
| Column B fill | Meaning | Action |
|---|---|---|
| White/no fill and WT = `P/F` (item row) | Optional info, not assessed | V = `P` (centred); no label/note/ref; never clarified |
| White/no fill with WT header text, blank WT, or spec `N/A` | Sub-header / N/A | Write nothing |
| Green (e.g. #92D050) | Required (P/F) | Evaluate; V = `P` if Meet else `F` |
| Orange (e.g. #FFC000) | Preferred (weighted) | Evaluate; V = `1`/`0`; never a mandatory failure |
| Header colour (e.g. #CAE0F2) / grey note | Header | Write nothing |
Confirm the legend in Step 1 if colours differ. Leave CP formulas untouched; report any coloured row without WT/CP.

## Decision matrix (note starts with the tag)
| Situation | Tag | strict (default) | standard |
|---|---|---|---|
| Meets/exceeds; evidence class A/B (or D for contractual commitments) verified, no unresolved red flag | `Verified –` | Meet | Meet |
| Offered value/config short; ticked No on required | `Deviation –` | Not Meet | Not Meet |
| Claim only supported by class C/D, or cited page lacks it | `Not substantiated –` | Not Meet (mandatory performance/safety) / CR (other) | CR |
| Blank/placeholder/no tick | `No response –` | Not Meet | CR (non-material) |
| Generic wording, model unclear, red-flagged document | `Ambiguous –` | CR | CR |
| Values conflict | `Conflict –` | CR | CR |
| Cited file not uploaded | `Evidence unavailable –` | CR | CR |
| Multi-part partly evidenced | `Partial –` | Not Meet if a missing part is mandatory performance/safety/utility/qty, else CR | same |
| Conditional row, technically justified N/A | `Verified – (N/A justified)` | Meet | Meet |

Universal checks: model identity on every doc; offered configuration only; "up to" figures not accepted; over-spec never offsets a shortfall; local registration only if required at bid stage; service commitments start at ATC and cover warranty and service contract. Judgment points for the report: self-declared CE/IVDR Class A, Class I filings vs registration, edited manuals, unreadable accreditation, sponsor-only clinical evidence, bidder calculations.

## Bidder URLs
Source Data URL links can't be fetched (only links the user pastes). Ask the user to upload missing files (table: document → rows); never use bidder URLs in REFERENCE.

## Steps
### 1. Profile + document request (single pause)
One execute_office_js: title, headers, column-B fill + WT per row → classes, bidder block columns (tick Yes/No, details, source, URL), evaluator columns, existing labels, counts. List cited-but-not-uploaded docs **and, per coloured row, whether the only cited evidence is class C/D** (so the user can supply class A/B documents up front). ONE `ask_user_question` (max 3).
**Done when:** user answers.

### 2. Extract evidence (code_execution)
pdfplumber per page; OCR pages <30 chars; cache; ignore unrelated uploads. For each document record: identity (model), issuer, date/version, evidence class, red flags (≤1 line each).
**Done when:** cache saved; evidence register complete.

### 3. Evaluate (reasoning, no per-row tool calls)
For each coloured row: E1 class → E2 red flags → E3 rationality check → E4 + matrix. Note: `<Tag> Required <X>; offered <Y> – <reason>. [Evidence: <class> – <doc, p.N>] <red flag / check result>.` Draft the question for each flagged row.
**Done when:** every coloured row has label + note (with evidence class) + ref.

### 4. Write (one execute_office_js)
Coloured rows: V, label (fill), note, ref; wrap/top. White P/F item rows: V = `P` only. Don't change widths/heights, spec or bidder text, recap/price sheets.
**Done when:** read-back label counts = array counts; no blanks on coloured rows; white P/F rows V = P with no label.

### 5a. Internal AMPC Technical Clarification (mandatory)
Flagged = rows re-read from the sheet with Not Meet or CR and a coloured column B.
- Template uploaded → `insertWorksheetsFromBase64` (calc manual, restore); else copy an existing internal clarification sheet in the workbook as layout and rewrite A2, rows 6–7 and items, or rebuild: A1 title; A2 bidder/brand/model/tender; A3 `Items listed: … (n = N; Not Meet a + Clarification Required b). Rows with white/no fill in column B not assessed (V = P).`; headers rows 4–5 `Row | PROPOSED DEVICE INFORMATION | Requirements` (#FFFF00), `BIDDER CLARIFICATION` (#A2C4C9) over `Bidder Response | Supporting documents | PC Assesment | Context`, `AMPC RESPONSE` over `Date | Response`; rows 6–7 brand/model.
- Items from row 8: A–C formulas; D tick+details formula; E source&CHAR(10)&url; F `<label>\n<tag finding>` with fill; G question; H–I blank. Set B–E General before formulas (copied sheets keep text formats — reset them).
- Questions: specific, neutral; ask for the **class A/B document** (doc no., version, page, accredited lab, model named) or data that would substantiate the claim as submitted; never invite a new model, added items or a price change.
- Sync: match by package-sheet row in the A formula; delete bidder rows before internal rows, bottom-up; never delete rows with H/I or bidder G filled (mark `Resolved`, grey); re-link bidder F to internal G by row; update A3.
**Gate:** rows == flagged; NM/CR counts match; no empty F/G; no error values; A3 n == items.

### 5b. Bidder-facing clarification sheet (mandatory)
`Clarif Bidder <pkg> - <bidder>` (≤31): title, bidder line; headers rows 3–4 (`BID AS SUBMITTED` over response/documents; `CLARIFICATION` over `Clarification Question` | `Bidder Response to Clarification [Bidder to state the response and the name and page number of the supporting document(s)]`); rows 5–6 brand/model; items from row 7 with A–E formulas, F linked to internal G, G blank. No labels, findings, evidence classes or AMPC columns.
**Gate:** items == internal items (same order); questions match; G blank; no error values. getImage rows 1–12 of both sheets.

### 6. Report (≤14 lines)
Label counts + score; white rows set to P; Not Meet rows; rows resting on class C/D evidence only and how they were labelled; red flags found; rationality-check results that changed a label; judgment points; docs not provided; both sheet names + `n = Not Meet a + CR b = all flagged ✓`; what was re-read. Recheck: `row: old → new, reason` grouped. Remind: save; issue the bidder sheet in writing with a deadline; keep the internal sheet confidential.

## Modes
- Continue: Step 1 (skip done bidders) → 6.
- Recheck (new docs): extract new files, re-run E1–E4 on affected rows, state changes, 5a + 5b sync.
- **Re-verify self-claims** (existing evaluation): re-run E1–E4 on every Meet row whose note/ref relies on class C/D only or a red-flagged document; list proposed downgrades `row: Meet → CR/Not Meet, reason` and ask once before writing; then 5a + 5b sync. Apply the same standard to every bidder.
- Apply white-row rule: class map → V = P on white P/F rows, clear labels → sync.
- Clarification only / Sync: 5a + 5b.

## Never
Accept a device capability, performance, safety or compatibility claim on a bidder letter, bidder calculation, brochure or self-declaration alone; Meet because the bidder ticked Yes or wrote "fully compliant"; ignore red flags; assess or clarify white rows; mix label sets; omit flagged rows; build lists from memory; delete rows holding responses; show findings on the bidder sheet; use bidder URLs; let a clarification cure a material deviation; evaluate price.
