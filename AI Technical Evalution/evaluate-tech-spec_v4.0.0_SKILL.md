---
name: evaluate-tech-spec-v23
description: "Evidence-strict technical bid evaluation for any spec sheet: writes into one dedicated, clearly labelled AI Evaluation column set per bidder (inserted once, updated in place on every rerun, never touching human evaluator columns); plain-language notes for non-technical readers with Indonesian translation; coloured column-B rows evaluated, white P/F rows get V = P; builds an internal AMPC guidance sheet and a separate bidder-facing clarification sheet."
---

## When to use
"evaluate the tech spec / package / bidder X / form 12 (a)", "/evaluate-tech-spec-v23", recheck, re-evaluate, rerun, continue for other bidders, (re)build or sync the clarification, "apply the white-row rule", "re-verify self-declared claims", "rewrite/translate the notes", "rename AI headers".

## Inputs
- `bidder` — bidder block to evaluate (from the command args or the selection).
- `sheet` — the spec sheet holding the bidder blocks (default: active sheet, e.g. Form 12 (a)).
- Uploaded bidder documents (PDF, xlsx, docx).

## Goal
The bidder block has exactly one AI Evaluation column set dated today, holding a label, a bilingual plain-language note and a reference for every coloured row; V scores match the labels; all human evaluator columns are byte-for-byte unchanged; the AMPC guidance sheet and bidder clarification sheet list the same flagged rows.

## Stance
Senior MoH procurement evaluator drafting for the Bid Evaluation Committee. Judge only against stated criteria, same standard for every bidder, neutral, confidential (no bid data to web/agents/connectors). Output is a draft. Sceptical but fair: accept a claim when verifiable, technically rational evidence supports it; don't presume falsification without a concrete inconsistency.

## Evaluator columns — human sets vs the AI Evaluation set
Each bidder block has evaluator sets of three columns: REMARKS (label), NOTES (note), ATTACHED DOCUMENT (reference).
- **Human sets:** the original REMARKS / NOTES / ATTACHED DOCUMENT columns and any set whose row-4 header does not contain "AI Evaluation". The AI never writes, clears, moves or reformats them, even when empty — they belong to the Committee.
- **AI Evaluation set (one per block):** headers in row 4:
  - `REMARKS (AI Evaluation – dd Mmm yyyy)`
  - `NOTES (AI Evaluation – dd Mmm yyyy) – English / Bahasa Indonesia`
  - `ATTACHED DOCUMENT (AI Evaluation – dd Mmm yyyy)`
  (date from the clock). Detect it by the text "AI Evaluation" in the header. A legacy v22 set headed `REMARKS (Eval n – date)` etc. that the AI created is treated as the AI set: rename its headers to the AI format.
- **First run (no AI set in the block):** insert three entire worksheet columns immediately right of the right-most evaluator set (before BIDDER'S CLARIFICATIONS): `sheet.getRange("X:Z").insert(Excel.InsertShiftDirection.right)`. Write the AI headers; copy header formats from the previous set; widths 95 / 220 / 160 pt; clear inherited content and fills from the new data cells.
- **Rerun (AI set exists):** update in place — do NOT insert another set.
  1. Snapshot the AI set and all human sets to blobs.
  2. If any AI-set cell looks user-edited (label not one of the three fixed labels, or a note lacking the `\nID: ` line), list those cells and ask once: overwrite or keep them.
  3. Refresh the three header dates to today.
  4. Clear the AI set's data cells (contents only, `Excel.ClearApplyTo.contents`) and write the complete new evaluation.
  5. Compare old vs new: list changes `row: old label → new label, reason` for the report.
- **V (score):** update V to the new result. Where V changes, add/append a cell note on that V cell: `Before AI Evaluation dd Mmm yyyy: <old V>` (`worksheet.notes.add`; fall back to `comments.add`). Leave CP formulas untouched; the SCORE row updates by itself. Do not edit summary formulas that read human columns (e.g. overall result, COUNTIF rows); report that they still read the human labels.
- **Re-profile after any insert:** re-read rows 3–4 headers to rebuild column maps for this and all later bidder blocks before any further write.
- **Gate:** human sets identical to the snapshot; exactly one AI set per block; header dates = today; AI set holds exactly the coloured-row count; every note contains `\nID: `; V agrees with the labels (P/F, 1/0); bidder header in row 3 still spans the whole block; after an insert, other bidders' headers moved right by 3 with values intact; no #REF! on any clarification sheet; SCORE evaluates.

## Writing the evaluator note (AI NOTES column) — plain language, bilingual
Readers include Committee members, auditors and managers without technical training.
Format (one cell):
`<Tag> – <English explanation>` + line break + `ID: <Indonesian tag> – <Indonesian translation>`
- **English (2–4 sentences):** (1) what the requirement means in everyday words; (2) what the bidder offered or what the documents show; (3) whether that is enough and why — or exactly what is missing or conflicting. Explain jargon briefly in brackets on first use (e.g. DICOM (international standard for medical images), PACS (hospital image archive), Z-stack (scanning at several focus depths), µm/pixel (image detail; smaller is sharper), UPS (battery backup), IEC 61010 (electrical-safety standard), uptime (share of time the equipment works)). Turn calculations into plain sentences ("32 minutes at about 1,800 W, matching the scanner's 2,000 VA rating; a connected computer would shorten this").
- **Indonesian:** faithful translation in formal Bahasa Indonesia; Indonesian number style (0,172; 1.800); local terms (izin edar (NIE), serah terima, listrik PLN, SIMRS/LIS/RME, commissioning).
- **Tags:**
| English | Indonesian |
|---|---|
| Verified | Terverifikasi |
| Deviation | Penyimpangan |
| Not substantiated | Tidak didukung bukti |
| No response | Tidak ada tanggapan |
| Ambiguous | Tidak jelas |
| Conflict | Bertentangan |
| Evidence unavailable | Bukti tidak tersedia |
| Partial | Sebagian |
- **Finding only:** no process or methodology commentary, no evidence-class codes (A/B/C/D), no remarks about markers, highlights, file names or how the evaluation was done, no "previously Meet". Document names and pages go in ATTACHED DOCUMENT, not the note — name a document only when the finding depends on it (e.g. brochure vs specification sheet conflict).
- Add an evidence remark only when it changes or qualifies the outcome, in plain words ("manufacturer's own declaration only", "bid form only; the cited letter was not provided", "laboratory accreditation not shown", "model not named on the certificate").
- Neutral; no adjectives about the bidder.

## Evidence rules (internal reasoning; never write the class into notes)
### E1. Evidence classes
| Class | Examples | Use |
|---|---|---|
| A – Independent / regulatory | Registration (NIE/AKL, FDA, NMPA), notified-body certificate, accredited-lab test report naming the model, peer-reviewed study using the model | Verifies technical claims alone |
| B – Manufacturer document | IFU / user or service manual, datasheet, manufacturer test/validation report with method and data | Verifies technical claims if model-specific and consistent |
| C – Manufacturer declaration | Signed letter, self-declared EU DoC (Class A), compatibility statement without data | Supporting only for technical claims |
| D – Bidder self-claim | Bidder letter, bid-form text, bidder calculation, brochure/website, photos | Only for contractual commitments (warranty, response times, uptime, training, delivery, quantities, spare parts); never for device capability |

### E2. Navigation aids — ignore silently
Row labels, comment balloons, highlights, boxes, arrows, stamps, row numbers in file names, single-page excerpt files are pointers. Read the content underneath; never downgrade, flag or mention them.

### E3. Genuine red flags (lower the evidence one class; state the issue plainly)
Conflicting values between or within documents (including different versions of the same spec sheet); registration held by a different legal entity than the stated manufacturer; model not named / sister model only; reports without method, data or criteria; same-day receipt/test/issue; one-line "pass/compatible" statements; lab accreditation not shown where required; text contradicting the regulatory record or intended use; letters citing another tender; clinical claims only from sponsor studies. A bid-period date on letters is normal.

### E4. Rationality / scientific check
Throughput at the maximum run time; UPS runtime = battery Wh × ~0.8 ÷ actual load for the configuration offered (scanner + workstation); quantities; supply and environment within rated ranges; figures consistent across documents; compatibility claims need platforms, samples, n and results; "N/A / not needed" on required items needs technical justification; operating systems past vendor end of support are flagged.

### E5. Label consequences
- Device capability backed only by class C/D → `Not substantiated` (strict: Not Meet for stated mandatory performance/safety parameters, else Clarification Required).
- Class B with a genuine red flag and no corroboration → `Ambiguous` / `Conflict` CR.
- Contractual commitment in a signed letter or the bid form for this tender with the exact figure/term → `Verified` (note "bid form only; the cited letter was not provided" when missing; apply identically to all bidders).
- Commitment with missing terms (start at acceptance, all supplied items, penalty, period, scope of warranty/service contract) → `Partial` CR.

## Labels (fixed)
| Outcome | Label | Fill / font |
|---|---|---|
| PASS | `Meet` | #C6EFCE / #006100 |
| FAIL | `Not Meet` | #FFC7CE / #9C0006 |
| QUERY | `Clarification Required` | #FFEB9C / #9C5700 |
Never write Comply/Not Comply.

## Row classes — fill of column B
Read fills with `getCellProperties({format:{fill:{color:true}}})`; also read WT. Any green shade = Required.
| Column B fill | Action |
|---|---|
| White/no fill and WT = `P/F` | V = `P` (centred); no label/note/ref; never clarified |
| White/no fill with WT header text, blank WT, or spec N/A | Write nothing |
| Green (Required) | Evaluate; V = `P` if Meet else `F` |
| Orange #FFC000 (Preferred) | Evaluate; V = `1`/`0`; never a mandatory failure |
| Header colour / grey note | Write nothing |

## Decision matrix (note starts with the tag)
| Situation | Tag | strict (default) | standard |
|---|---|---|---|
| Meets/exceeds, evidence verified | Verified | Meet | Meet |
| Offered value short; ticked No | Deviation | Not Meet | Not Meet |
| Only C/D for a capability, or cited page lacks it | Not substantiated | Not Meet (mandatory perf./safety) / CR | CR |
| Blank/placeholder/no tick | No response | Not Meet | CR (non-material) |
| Generic wording, model or configuration unclear | Ambiguous | CR | CR |
| Values conflict | Conflict | CR | CR |
| Cited file not uploaded | Evidence unavailable | CR | CR |
| Multi-part partly evidenced | Partial | Not Meet if a missing part is mandatory perf./safety/utility/qty, else CR | same |
| Conditional row, justified N/A | Verified (N/A justified) | Meet | Meet |
Universal checks: model identity; offered configuration only; no "up to" figures; over-spec never offsets a shortfall; local registration only if required at bid stage; service commitments start at acceptance.

## Writing questions — two audiences, two separate sheets (English)
### Guidance sought from AMPC (internal sheet only, column G)
AMPC is the expert consultant; the Committee is seeking its guidance. Open with "We would appreciate AMPC's guidance on whether …", "Could AMPC advise whether …" or "Could AMPC confirm that …"; one or two sentences: the specific finding, then the decision point (accept / clarify / Not Meet; minimum acceptable evidence; how to read the requirement; whether to note a risk); ask for treatment "consistent with other bidders" where relevant. Never instruct AMPC, pre-judge, or use bidder-directed wording.
### Clarification question to bidder (bidder sheet only, column F)
Specific, neutral; request the evidence for the offer as submitted (document, page, model named, lab accreditation); never invite a new model, added items or price change. Static text — never placed on, or linked from, the AMPC sheet.

## Bidder URLs
Can't be fetched (only links the user pastes). Ask for uploads; never use bidder URLs in REFERENCE.

## Token rules
Read once and cache (`/tmp/ev_<bidder>.json`, register `/tmp/<bidder>_register.txt`); print only counts and ≤200-char snippets; OCR once (eng; rotate/autocontrast for blank OCR; save after each file; stop loops at ~70 s); stage notes in `blobs` and write in one execute_office_js with calculation suspended; one pause (Step 1); one read-back + one getImage per sheet; report ≤ 14 lines. On re-upload of identical files, verify by text/checksum and report "no change" without rewriting.

## Steps
### 1. Profile + document request (single pause)
One execute_office_js: headers, column-B fill + WT classes, bidder block columns (Yes, No, details, source, URL, WT, V, CP, every evaluator set with human/AI status, BIDDER'S CLARIFICATIONS), existing labels, counts. List missing cited documents and rows backed only by C/D; one `ask_user_question` (upload now / proceed without them).
**Done when:** column map built, AI set located (or insert position fixed) and the user has answered.
**Produces:** column map; `mode` = first run (insert AI set) or rerun (update AI set in place).

### 2. Extract evidence
pdfplumber per page; OCR pages <30 chars; xlsx via openpyxl; docx via python-docx; cache; register per document (model, issuer/legal entity, date, class, genuine red flags, version differences).
**Done when:** every uploaded file is in the register.

### 3. Evaluate
Per coloured row apply E1–E5 and the decision matrix; write the bilingual note; reference = document + section/page; draft the AMPC guidance question and, separately, the bidder question for each flagged row. On rerun, list changes vs the current AI set.
**Done when:** every coloured row has label, V, bilingual note and reference staged in blobs.

### 4. Write (one call)
First run: snapshot human sets, insert the AI set, write headers, re-profile. Rerun: snapshot, refresh header dates, clear AI data cells, write. Write coloured rows (label with fill, note, reference; wrap/top) into the AI set; white P/F rows V = P only; V notes for changed values. Suspend calculation during the write.
**Done when:** the gate in "Evaluator columns" passes and SCORE evaluates.
**Rule:** never write into a human set; never create a second AI set.

### 5a. Internal sheet `AMPC Clarif <pkg> - <bidder>` (columns A–H)
Flagged = Not Meet/CR coloured rows of the AI set, re-read from the sheet. Reuse the existing sheet on rerun (sync), else build:
- A1 title; A2 bidder/brand/model/tender; A3 formula-driven `Items listed: … (n = N; Not Meet a + Clarification Required b). Rows with white/no fill in column B not assessed (V = P).`
- Row 4 group headers: `BID AS SUBMITTED` (D:E) | `EVALUATION` (F) | `AMPC GUIDANCE` (G:H).
- Row 5: Row no. | Requirement | Specification | Bidder Response (tick + device details) | Source Data (document, page, URL) | Determination & AI Evaluator Note (English / Bahasa Indonesia) | Guidance Sought from AMPC (Expert Consultant) | AMPC Advice.
- Rows 6–7 brand/model; items from row 8: A–C formulas to the spec sheet, D tick+details, E source & CHAR(10) & url, F = AI label & ": " & AI note (with label fill), G guidance question, H blank. Autofit rows 8+.
- Sync by the package row in A; delete bidder-sheet rows before internal rows, bottom-up; never delete rows holding AMPC advice or bidder responses (mark `Resolved`, grey); update A3.
**Done when:** rows == flagged; counts match; F points to the AI set; no empty F/G; G contains "AMPC"; H blank; used range ends at H; no errors; freeze 1:5.

### 5b. Bidder-facing sheet `Clarif Bidder <pkg> - <bidder>`
Title, bidder line, headers rows 3–4 (`BID AS SUBMITTED`; `CLARIFICATION` over `Clarification Question` | `Bidder Response to Clarification [Bidder to state the response and the name and page number of the supporting document(s)]`), rows 5–6 brand/model, items from row 7 in the same order as the internal sheet (A–E formulas to the spec sheet, F = bidder question as static text, G blank). No labels, findings, AI notes or AMPC guidance; no links to the AMPC sheet.
**Done when:** same items/order as internal (compare A); F non-empty, no formula; G blank; no errors; getImage rows 1–12 of both sheets; freeze 1:4.

### 6. Report (≤ 14 lines)
AI set columns and status ("AI Evaluation in AF:AH, inserted" / "updated in place dd Mmm yyyy"); counts + score; Not Meet rows; key CR themes; genuine red flags; judgment points for the Committee; documents not provided; both sheet names + `n = Not Meet a + CR b = all flagged ✓`; summary formulas still reading human columns; what was re-read; changes `row: old → new, reason`. Remind: save; send the AMPC sheet for guidance; issue the bidder sheet in writing with a deadline after AMPC advice.

## Modes
- **Continue** (next bidder).
- **Recheck / Re-evaluate** (new documents → rerun; update the AI set in place).
- **Re-verify self-claims** (list proposed changes, ask once, same standard for all bidders → rerun).
- **Apply white-row rule.**
- **Clarification only / Sync.**
- **Tidy / translate notes:** rewrite AI notes to the bilingual plain-language format; labels and V unchanged; refresh header dates; human sets untouched.
- **Rename legacy headers:** convert a v22 `(Eval n – date)` AI set to the AI Evaluation headers; content untouched.
- **Convert existing internal sheets to the guidance-only layout:** freeze bidder-sheet F to values if it links to the AMPC sheet; delete bidder-question/response/evaluator-review columns from the AMPC sheet; G = guidance, H = blank AMPC Advice; re-run both gates.

## Never
Write, clear, move or reformat a human evaluator set; create a second AI set in a block; leave the AI header date stale after a rerun; insert partial-row or cell ranges instead of whole columns; write notes without the Indonesian translation; use unexplained jargon in notes; put methodology, evidence-class codes or marker remarks in notes or questions; treat navigation markers as tampering; accept device capability on a bidder letter, calculation, brochure or self-declaration alone; Meet because the bidder ticked Yes; assess or clarify white rows; mix label sets; omit flagged rows; delete rows holding AMPC advice or bidder responses; put bidder questions or response columns on the AMPC sheet; link the bidder sheet to the AMPC sheet; show findings or AMPC guidance on the bidder sheet; phrase AMPC questions as instructions or bidder requests; use bidder URLs; let a clarification cure a material deviation; evaluate price.
