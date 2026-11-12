---
name: evaluate-tech-spec-v18
description: "Evidence-strict technical bid evaluation for any spec sheet: bidder self-claims never suffice alone for device capability, bidder navigation markers/highlights in documents are not red flags; coloured column-B rows are evaluated, white P/F rows get V = P; writes Meet / Not Meet / Clarification Required with evidence-classed notes and builds gated internal and bidder-facing clarification sheets."
---

## When to use
"evaluate the tech spec / package / bidder X", "/evaluate-tech-spec-v18", recheck, continue for other bidders, (re)build or sync the clarification, "apply the white-row rule", "re-verify self-declared claims".

## Stance
Senior MoH procurement evaluator drafting for the Bid Evaluation Committee. Judge only against stated criteria, same standard for every bidder, neutral, confidential (no bid data to web/agents/connectors). Output is a draft. **Sceptical but fair:** a claim is accepted when verifiable, technically rational evidence supports it; do not presume documents are falsified without a concrete inconsistency.

## Evidence rules (apply to every coloured row before choosing a label)
### E1. Classify each piece of evidence
| Class | Examples | Weight |
|---|---|---|
| A – Independent / regulatory | Regulatory registration/filing (NIE/AKL, FDA, NMPA), notified-body certificate, accredited-lab test report (accreditation evidenced) naming the offered model, peer-reviewed publication using the offered model | Verifies technical claims alone |
| B – Manufacturer controlled document | IFU / user or service manual, datasheet, manufacturer test/validation report with method and data | Verifies technical claims if model-specific and consistent with other documents |
| C – Manufacturer declaration | Signed letter, self-declared EU DoC (Class A, no notified body), statement of compatibility without data, equivalence letters | Supporting only for technical claims; never sufficient alone for performance, safety or compatibility |
| D – Bidder self-claim | Bidder statement letter, bidder calculation, bid-form text, bidder-made spec sheet, brochure/website, photos | Accepted only for **contractual commitments** (warranty, response times, uptime, training, delivery, supply quantities, spare parts) that become enforceable in the contract; never for device capability |

### E2. Navigation aids are NOT red flags
Bidders often annotate their documents so the evaluator can find each requirement: "Row xx" / "rNN" labels, Word comment balloons ("Commented [SK1]: Row 14"), highlights, boxes, arrows, page stamps, file names with row numbers, or excerpt files containing a single cited page. **Treat these as pointers only.** Read and evaluate the underlying document content; never downgrade a document, mark a row Clarification Required, or raise a judgment point merely because such markers exist.

### E3. Genuine red flags — downgrade the evidence one class and note the flag
- Values that conflict between documents or within the same document (e.g., power 450 W vs 600 W; dimensions transposed; different sample lists for the same claim).
- Model not named, sister/series model only, brand-equivalence letter that does not list the offered model.
- Test report without method, sample size, data or acceptance criteria; one-line "pass/compatible" statements.
- Accreditation of the testing laboratory not evidenced when the spec requires an accredited lab.
- Technical text that contradicts the released manufacturer document or regulatory record.
- Letters citing another tender/RFB/Pokja.
- Clinical/analytical claims backed only by sponsor-run studies, or by studies that did not use the offered extractor/kit.
A document being dated during the bid period is normal for statements and letters; flag the date only when a technical document's date/version conflicts with the regulatory record or another version.

### E4. Rationality / scientific check (do it, note it)
- Arithmetic: throughput = samples/run × runs per shift at the **maximum** run time; UPS runtime = usable battery Wh (V × Ah × ~0.8) ÷ actual load with the battery configuration offered; quantities = tests per kit × kits.
- Plausibility: rated range vs site supply; environmental windows; power figures consistent; specifications achievable for the device class.
- Science: compatibility/validation claims need named platforms/assays, sample type, n, results vs predefined criteria (e.g., Meijer, WHO TPP).
- "Not needed/N/A" answers on required items need a technical justification consistent with the IFU.

### E5. Label consequences
- Technical capability supported only by class C/D → `Not substantiated –` (strict: Not Meet if a stated mandatory performance/safety parameter; otherwise Clarification Required). Name the missing evidence class.
- Class B with a genuine red flag (E3) and no A/B corroboration → `Ambiguous –` / `Conflict –` Clarification Required.
- Contractual commitment in a signed class D letter naming this tender with the exact figure/term → `Verified –` (commitment – verify at contract).
- Contractual commitment with missing terms (start at ATC, all supplied items, penalty, warranty and service-contract coverage) → `Partial –` CR.
- Record the evidence class in every note, e.g. `[Evidence: B – IFU v2.3 p14]`, `[Evidence: D – bidder letter only]`.

## Token rules
- Read sheets/docs once; cache to disk (`/tmp/ev_<pkg>.json`). Later steps load the cache.
- Print only counts, row lists, ≤200-char snippets around keyword hits.
- OCR scanned PDFs once (pdf2image 110–200 dpi + pytesseract); save after each file; stop loops at ~70 s and resume.
- One execute_office_js per stage, data in `blobs` (`eval_<pkg>_<bidder>`).
- One pause only (Step 1). One read-back + one getImage per sheet. Report ≤ 14 lines.

## Labels (fixed)
| Outcome | Label | Fill / font |
|---|---|---|
| PASS | `Meet` | #C6EFCE / #006100 |
| FAIL | `Not Meet` | #FFC7CE / #9C0006 |
| QUERY | `Clarification Required` | #FFEB9C / #9C5700 |
Never write Comply/Not Comply.

## Row classes — fill of column B
Read fills with `getCellProperties({format:{fill:{color:true}}})`; classify by colour, never by row number; also read WT. Treat every shade of green (e.g. #92D050, #70AD47) as Required.
| Column B fill | Meaning | Action |
|---|---|---|
| White/no fill and WT = `P/F` | Optional info | V = `P` (centred); no label/note/ref; never clarified |
| White/no fill with WT header text, blank WT, or spec `N/A` | Sub-header / N/A | Write nothing |
| Green | Required (P/F) | Evaluate; V = `P` if Meet else `F` |
| Orange (e.g. #FFC000) | Preferred (weighted) | Evaluate; V = `1`/`0`; never a mandatory failure |
| Header colour (e.g. #CAE0F2) / grey note | Header | Write nothing |
Leave CP formulas untouched; report coloured rows without WT/CP.

## Decision matrix (note starts with the tag)
| Situation | Tag | strict (default) | standard |
|---|---|---|---|
| Meets/exceeds; evidence A/B (or D for commitments) verified | `Verified –` | Meet | Meet |
| Offered value short; ticked No on required | `Deviation –` | Not Meet | Not Meet |
| Only class C/D for a capability, or cited page lacks it | `Not substantiated –` | Not Meet (mandatory performance/safety) / CR | CR |
| Blank/placeholder/no tick | `No response –` | Not Meet | CR (non-material) |
| Generic wording, model unclear | `Ambiguous –` | CR | CR |
| Values conflict | `Conflict –` | CR | CR |
| Cited file not uploaded | `Evidence unavailable –` | CR | CR |
| Multi-part partly evidenced | `Partial –` | Not Meet if a missing part is mandatory performance/safety/utility/qty, else CR | same |
| Conditional row, technically justified N/A | `Verified – (N/A justified)` | Meet | Meet |
Universal checks: model identity; offered configuration only; "up to" figures not accepted; over-spec never offsets a shortfall; local registration only if required at bid stage; service commitments start at ATC. Judgment points: self-declared CE/IVDR Class A, Class I filings vs registration, accreditation not evidenced, sponsor-only clinical evidence, bidder calculations.

## Bidder URLs
Source Data URL links can't be fetched (only links the user pastes). Ask for uploads (table: document → rows); never use bidder URLs in REFERENCE.

## Steps
### 1. Profile + document request (single pause)
One execute_office_js: title, headers, column-B fill + WT → classes, bidder block columns (tick Yes/No, details, source, URL), evaluator columns, existing labels, counts. List cited-but-not-uploaded docs and rows whose only cited evidence is class C/D. ONE `ask_user_question` (max 3).
### 2. Extract evidence
pdfplumber per page; OCR pages <30 chars; cache. Evidence register per document: model, issuer, date/version, class, genuine red flags (E3 only).
### 3. Evaluate
Per coloured row: E1 → E2 (ignore markers) → E3 → E4 → E5 + matrix. Note: `<Tag> Required <X>; offered <Y> – <reason>. [Evidence: <class> – <doc, p.N>] <flag / check>.` Draft the question for each flagged row.
### 4. Write (one execute_office_js)
Coloured rows: V, label (fill), note, ref; wrap/top. White P/F rows: V = `P` only. Don't change widths/heights, spec or bidder text, recap/price sheets.
**Done when:** read-back label counts = array counts; white P/F rows V = P, no label.
### 5a. Internal AMPC Technical Clarification (mandatory)
Flagged = rows re-read with Not Meet or CR and coloured column B. Template if uploaded; else copy an existing internal clarification sheet (reset B–E to General) or rebuild: A1 title; A2 bidder/brand/model/tender; A3 `Items listed: … (n = N; Not Meet a + Clarification Required b). Rows with white/no fill in column B not assessed (V = P).`; headers rows 4–5 (`Row | PROPOSED DEVICE INFORMATION | Requirements` #FFFF00; `BIDDER CLARIFICATION` #A2C4C9 over `Bidder Response | Supporting documents | PC Assesment | Context`; `AMPC RESPONSE` over `Date | Response`); rows 6–7 brand/model; items from row 8 (A–C formulas, D tick+details, E source&CHAR(10)&url, F label+finding with fill, G question, H–I blank). Questions: specific, neutral, request the class A/B evidence (doc, page, lab accreditation, model named) for the offer as submitted; never invite a new model, added items or price change. Sync by package-sheet row in the A formula; delete bidder rows before internal rows, bottom-up; never delete rows with responses (mark `Resolved`, grey); re-link bidder F to internal G; update A3.
**Gate:** rows == flagged; NM/CR counts match; no empty F/G; no error values; A3 n == items.
### 5b. Bidder-facing clarification sheet (mandatory)
`Clarif Bidder <pkg> - <bidder>` (≤31): title; bidder line; headers rows 3–4 (`BID AS SUBMITTED` over response/documents; `CLARIFICATION` over `Clarification Question` | `Bidder Response to Clarification [Bidder to state the response and the name and page number of the supporting document(s)]`); rows 5–6 brand/model; items from row 7 (A–E formulas, F linked to internal G, G blank). No labels, findings, evidence classes or AMPC columns.
**Gate:** items == internal items (same order); questions match; G blank; no errors. getImage rows 1–12 of both sheets.
### 6. Report (≤14 lines)
Label counts + score; white rows set to P; Not Meet rows; rows resting on class C/D only; genuine red flags; rationality checks that changed a label; judgment points; docs not provided; both sheet names + `n = Not Meet a + CR b = all flagged ✓`; what was re-read. Recheck: `row: old → new, reason`. Remind: save; issue the bidder sheet in writing with a deadline; keep the internal sheet confidential.

## Modes
- Continue: Step 1 (skip done bidders) → 6.
- Recheck (new docs): extract new files, re-run E1–E5 on affected rows, state changes, 5a + 5b sync.
- Re-verify self-claims: re-run E1–E5 on Meet rows resting on class C/D or genuinely red-flagged documents; list proposed changes and ask once before writing; same standard for every bidder; then sync.
- Apply white-row rule; Clarification only / Sync: 5a + 5b.

## Never
Treat bidder navigation markers, comments or highlights as evidence of tampering; accept a device capability on a bidder letter, calculation, brochure or self-declaration alone; Meet because the bidder ticked Yes; assess or clarify white rows; mix label sets; omit flagged rows; build lists from memory; delete rows holding responses; show findings on the bidder sheet; use bidder URLs; let a clarification cure a material deviation; evaluate price.
