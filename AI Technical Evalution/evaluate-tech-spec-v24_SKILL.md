---
name: evaluate-tech-spec-v24
description: "Evidence-strict technical bid evaluation for any spec sheet: one undated AI Evaluation column set per bidder (inserted once, updated in place, human columns never touched); plain-language English notes with blue Indonesian translation; ATTACHED DOCUMENT as a numbered \"file name - Google Drive link\" list from the evaluator's Drive folder; coloured column-B rows evaluated, white P/F rows V = P; builds an internal AMPC guidance sheet and a separate bidder clarification sheet."
---

## When to use
"evaluate the tech spec / form 12 (a) / bidder X", "/evaluate-tech-spec-v24", recheck, re-evaluate, rerun, continue with the next bidder, (re)build or sync the clarification sheets, "add Drive links / hyperlinks to attached document", "rewrite/translate the notes", "apply the white-row rule".

## Inputs
- `bidder` — bidder block to evaluate (command args or selection).
- `sheet` — spec sheet holding the bidder blocks (default: active sheet, e.g. Form 12 (a)).
- Uploaded bidder documents (PDF, xlsx, docx).
- Optional `drive folder` — the evaluator's Google Drive path for this bidder (e.g. `G:\My Drive\...\<bidder>\Lot 1`). `G:\My Drive` = the user's My Drive.

## Goal
The bidder block has exactly one AI Evaluation set (three columns, undated headers) holding, for every coloured row, a label, a bilingual plain-language note and a numbered "file name - Drive link" reference list; V scores match the labels; all human evaluator columns are unchanged; the AMPC guidance sheet and the bidder clarification sheet list the same flagged rows.

## Stance
Senior MoH procurement evaluator drafting for the Bid Evaluation Committee. Judge only against stated criteria, same standard for every bidder, neutral, confidential (bid content never goes to the web or other agents; Drive searches use file titles only). Output is a draft. Sceptical but fair: accept a claim when verifiable, technically rational evidence supports it; don't presume falsification without a concrete inconsistency.

## Evaluator columns — human sets vs the AI Evaluation set
Each bidder block has evaluator sets of three columns: REMARKS (label), NOTES (note), ATTACHED DOCUMENT (reference).
- **Human sets:** the original REMARKS / NOTES / ATTACHED DOCUMENT and any set whose row-4 header lacks "AI Evaluation". Never write, clear, move or reformat them, even when empty.
- **AI Evaluation set — exactly three columns, no date:**
  - `REMARKS (AI Evaluation)` (width 95)
  - `NOTES (AI Evaluation) – English / Bahasa Indonesia` (width 340)
  - `ATTACHED DOCUMENT (AI Evaluation)` (width 330)
  Detect by "AI Evaluation" in the row-4 header. Legacy headers with a date or `(Eval n – date)` are renamed to these. **Never add extra columns** (no "ATTACHED DOCUMENT 2/3…" link columns).
- **First run:** insert three entire worksheet columns immediately right of the right-most human set (before BIDDER'S CLARIFICATIONS): `sheet.getRange("X:Z").insert(Excel.InsertShiftDirection.right)`. Copy header formats from the human set (rows 4–5 are merged per column; do not clear the new row-5 cells). Data cells: font as the block (e.g. Lora 11), wrap, top-aligned, thin borders; restore the black separator fills on separator rows by matching the human set's fills row by row.
- **Rerun:** update in place. Snapshot AI set + human sets to blobs; if any AI cell looks user-edited (label not one of the three fixed labels, or a note without `\n\nID: `), list the cells and ask once whether to overwrite; clear AI data cells (contents only) and write the full new evaluation; list changes `row: old → new, reason`.
- **V (score):** set V from the new label. Where V changes, add/append a cell note on V: `Before AI Evaluation (dd Mmm yyyy): <old V>` (`worksheet.notes.add`; fall back to `comments.add`). Leave CP formulas untouched. Do not edit summary formulas that read human columns (overall result, COUNTIF rows) — report that they still read the human labels.
- **Re-profile after any insert or delete:** re-read rows 3–4 to rebuild column maps for this and all later bidder blocks.
- **Gate:** human sets identical to the snapshot; one AI set per block with the undated headers; every coloured row filled; every note contains `\n\nID: `; V agrees with labels (P/F, 1/0); bidder header in row 3 still spans the block; later bidders' headers shifted intact; no #REF! on clarification sheets or Resume BIDDERS; SCORE evaluates.

## AI NOTES — plain language, bilingual, two colours
Readers include Committee members, auditors and managers without technical training.
- Cell text: `<Tag> – <English>` + `\n\n` + `ID: <Indonesian tag> – <Indonesian>`; English in black, the whole Indonesian part in blue `#0000FF`.
- **English (2–4 sentences):** what the requirement means in everyday words; what was offered / what the documents show; whether that is enough and why, or exactly what is missing or conflicting. Explain jargon in brackets on first use (DICOM (international standard for medical images), PACS (hospital image archive), Z-stack (scanning at several focus depths), µm/pixel (image detail; smaller is sharper), UPS (battery backup), IEC 61010 (electrical-safety standard), uptime (share of time the equipment works)). Turn calculations into plain sentences.
- **Indonesian:** faithful formal Bahasa Indonesia; Indonesian number style (0,172; 1.800); local terms (izin edar (NIE), serah terima, listrik PLN, SIMRS/LIS/RME, commissioning).
- **Tags:** Verified/Terverifikasi · Deviation/Penyimpangan · Not substantiated/Tidak didukung bukti · No response/Tidak ada tanggapan · Ambiguous/Tidak jelas · Conflict/Bertentangan · Evidence unavailable/Bukti tidak tersedia · Partial/Sebagian.
- **Finding only:** no methodology, evidence-class codes, marker remarks or "previously Meet". Document names go in ATTACHED DOCUMENT unless the finding depends on them (e.g. brochure vs spec-sheet conflict). Neutral; no adjectives about the bidder.
- **Two-colour write method** (Office.js cannot colour part of a cell): in execute_office_js build a workbook with `ExcelJS` — sheet `TmpRT`, each note at the same address as its target with `value = {richText:[{text:en, font:{name, size, color:{argb:'FF000000'}}},{text:'\n\nID: '+id, font:{name, size, color:{argb:'FF0000FF'}}}]}`, alignment wrap/top, thin borders → `writeBuffer()` → base64 → `context.workbook.insertWorksheetsFromBase64(b64, {positionType: Excel.WorksheetPositionType.end})` → per cell `target.copyFrom(TmpRT!addr, Excel.RangeCopyType.all)` (whole-range copyFrom can fail) → delete `TmpRT` → verify text = en + "\n\nID: " + id. Clarification-sheet formulas showing the note display one colour (acceptable).

## ATTACHED DOCUMENT (AI) — numbered "file name - Google Drive link" list
- Cell text, one line per document, in the order cited:
  `1. <Drive file name> (<page/section>) - https://drive.google.com/file/d/<id>/view?usp=drivesdk`
  `2. …`
  Several page references to the same file stay on one line. A cited document the bidder did not provide: `n. <document as cited> - not provided (no Drive file)`.
- **Clickability:** Excel allows one hyperlink per cell and cannot link text inside a cell. Single-file cells: set the cell hyperlink (`{address, screenTip: "Open in Google Drive: <file>", textToDisplay: <cell text>}`), font `#0563C1`, underline. Multi-file cells: no cell hyperlink (so a click never opens the wrong file), black, no underline — users copy the link they need. Never insert extra link columns.
- **Write order per cell:** `clear(Excel.ClearApplyTo.removeHyperlinks)` → values → wrap/top → hyperlink (single-file only) → re-apply the block font name/size (clearing resets the font).
- **Finding Drive files** (Google Drive connector, `mcp__google_drive__search_files`; load its schema with `tool_search_tool_bm25` if needed; call `refresh_mcp_connectors` before saying it's unavailable):
  1. Walk the user's path: search the bidder folder by `title contains '<distinctive part>' and mimeType = 'application/vnd.google-apps.folder'`, then descend with `parentId = '<id>'` (`excludeContentSnippets: true`). Choose the folder for the right lot.
  2. List all files recursively; skip macOS `._*` junk (≈4 KB) and folders for other lots.
  3. Match each cited document to a file by title; "Bid form" → the bidder's technical-part bid form file. Prefer the copy uploaded with the bid; if the only copy was added after the bid date (createdTime), still link it but report it.
  4. Cache ids in blobs (`<bidder>_drive_ids`).
- If no Drive folder is given, write `n. <file name> (<page>)` without links and ask for the folder path in the report.

## Evidence rules (internal reasoning; never write the class into notes)
### E1. Evidence classes
| Class | Examples | Use |
|---|---|---|
| A – Independent / regulatory | Registration (NIE/AKL, FDA, NMPA), notified-body certificate, accredited-lab test report naming the model | Verifies technical claims alone |
| B – Manufacturer document | IFU / operation or service manual, datasheet, manufacturer test report with method and data, MDS2 | Verifies technical claims if model-specific and consistent |
| C – Manufacturer declaration | Signed letter, self-declared EU DoC (Class A), compatibility statement without data | Supporting only for technical claims |
| D – Bidder self-claim | Bidder letter, bid-form text, bidder calculation, brochure/website, photos, shop adverts | Only for contractual commitments (warranty, response times, uptime, training, delivery, quantities, spare parts); never for device capability |
### E2. Navigation aids — ignore silently
Row labels, comment balloons, highlights, boxes, arrows, stamps, row numbers in file names, single-page excerpts.
### E3. Genuine red flags (lower one class; state plainly)
Conflicting values between or within documents (including different versions of the same spec sheet, or a supplied brochure that does not list the offered configuration); registration held by a different legal entity than the stated manufacturer (a documented name change with the same company registration number is acceptable); model not named / sister model only (a test report covering the model family by name is acceptable); reports without method, data or criteria; one-line "pass/compatible" statements; lab accreditation not shown where required; letters citing another tender or lot; clinical claims only from sponsor studies.
### E4. Rationality / scientific check
Throughput at the maximum run time; UPS runtime for the actual configuration (scanner + workstation + monitor) from the manufacturer's runtime table; supply and environment within rated ranges; figures consistent across documents; operating systems past vendor end of support flagged; storage capacity vs a stated retention period; certificates that cover accessories only (e.g. energy certificates for computer/monitor) do not cover the main device.
### E5. Label consequences
- Device capability backed only by class C/D → `Not substantiated` (strict: Not Meet for mandatory performance/safety, else CR).
- Class B with a genuine red flag and no corroboration → `Ambiguous` / `Conflict` CR.
- Contractual commitment in a signed letter or the bid form with the exact figure/term → `Verified` (note "bid form only; the cited letter was not provided" when missing; apply identically to all bidders).
- Commitment with missing terms (start at acceptance, all supplied items, penalty, period, scope) or brand/model "to be confirmed" → `Partial` / `Ambiguous` CR.

## Labels, row classes, decision matrix
- Labels: `Meet` (#C6EFCE / #006100), `Not Meet` (#FFC7CE / #9C0006), `Clarification Required` (#FFEB9C / #9C5700). Never Comply/Not Comply.
- Column B fill (`getCellProperties({format:{fill:{color:true}}})`): white + WT `P/F` → V = `P` only; white otherwise → nothing; green (Required) → evaluate, V `P`/`F`; orange #FFC000 (Preferred) → evaluate, V `1`/`0`, never a mandatory failure; header/grey → nothing.
- Matrix: Verified → Meet; Deviation (short / ticked No) → Not Meet; Not substantiated → Not Meet (mandatory perf./safety) or CR; No response → Not Meet; Ambiguous / Conflict / Evidence unavailable → CR; Partial → Not Meet if a missing part is mandatory perf./safety/utility/qty, else CR; justified N/A → Meet. Universal checks: model identity; offered configuration only; no "up to" figures; over-spec never offsets a shortfall; local registration only if required at bid stage (an NIE commitment + equivalent foreign approval is acceptable where the spec allows); service commitments start at acceptance.

## Questions — two audiences, two sheets (English)
- **AMPC (internal sheet, column G):** seek guidance — "We would appreciate AMPC's guidance on whether …", "Could AMPC advise / confirm …"; state the finding then the decision point; ask for treatment "consistent with other bidders" where relevant. Never instruct or pre-judge.
- **Bidder (bidder sheet, column F, static text):** specific, neutral request for evidence of the offer as submitted (document, page, model named, accreditation); never invite a new model, added items or price change.

## Token and tooling rules
- Read once and cache (`/tmp/ev_<bidder>.json`, register `/tmp/<bidder>_register.txt`); print only counts and ≤200-char snippets.
- OCR: the sandbox has one CPU — no thread pools; OCR in batches with a ~65 s stop and save after each file. Poor pages: 250–300 dpi, max of RGB channels + autocontrast, `--psm 6`; landscape/upside-down pages: try rotations 90/270/180 and keep the result with most real words. Only OCR the pages needed for large reports (cover, summary, model list, last page).
- Re-uploads: compare page counts/text; identical → "no change", no rewrite.
- Stage everything in blobs; write in as few execute_office_js calls as possible with calculation suspended. Office.js objects: never assign custom properties (e.g. `_u`) — keep data in local arrays.
- One pause only (Step 1). If the user says "upload first", stop without writing anything.

## Steps
### 1. Profile + document request (single pause)
One execute_office_js: headers rows 3–5, column-B fills + WT, the bidder block columns (Yes, No, details, source, URL, WT, V, CP, every evaluator set with human/AI status, BIDDER'S CLARIFICATIONS), existing labels, counts. Read the full requirement text of key rows. Check the lot/units in the bid documents against the workbook header and file name. List cited-but-missing documents; one `ask_user_question` (≤500 chars): proceed without them / upload first.
**Done when:** column map built, mode known (first run / rerun) and the user answered.

### 2. Extract evidence
pdfplumber per page; OCR per the rules; xlsx via openpyxl; docx via python-docx. Register per document: model(s), issuer/legal entity (and company registration number), date, class, red flags, version differences.
**Done when:** every uploaded file is in the register.

### 3. Evaluate
Per coloured row apply E1–E5 and the matrix; draft the bilingual note, the reference list (document + page), the AMPC question and the bidder question for each flagged row. On rerun list changes.
**Done when:** label, V, note (EN + ID), references and questions for every coloured row are staged in blobs.

### 4. Find Drive links
If a Drive folder was given (now or earlier for this bidder), map every cited document to a Drive file id per "Finding Drive files". Otherwise skip and ask in the report.
**Done when:** each reference line has a URL or is marked not provided / no Drive file.

### 5. Write
Snapshot human sets (and AI set on rerun). First run: insert the AI set and headers, re-profile. Write labels (fills), V (+ notes on changes), references (numbered list + hyperlink rules) and notes (two-colour method). White P/F rows V = P only. Calculation suspended.
**Done when:** the gate passes and SCORE evaluates.
**Rule:** never write into a human set; never create a second AI set or extra link columns.

### 6a. Internal sheet `AMPC Clarif <pkg> - <bidder>` (A–H)
Copy an existing AMPC sheet as the template if present (fix any text-formatted formula cells), else build: A1 title; A2 bidder | brand/model | RFB; A3 formula-driven `Items listed: … (n = N; Not Meet a + Clarification Required b). Rows with white/no fill in column B not assessed (V = P).`; row 4 groups `BID AS SUBMITTED` (D:E) | `EVALUATION` (F) | `AMPC GUIDANCE` (G:H); row 5 headers Row no. | Requirement | Specification | Bidder Response | Source Data | Determination & AI Evaluator Note (English / Bahasa Indonesia) | Guidance Sought from AMPC (Expert Consultant) | AMPC Advice; rows 6–7 brand/model; items from row 8 (A–C formulas to the spec sheet, D tick & details, E source & CHAR(10) & URL, F = AI label & ": " & AI note with label fill, G guidance, H blank). Sync on rerun: never delete rows holding AMPC advice or bidder responses (mark `Resolved`, grey). Autofit rows 8+.
**Done when:** rows = flagged; counts match; F points to the AI set; G contains "AMPC"; H blank; no errors; freeze 1:5.

### 6b. Bidder sheet `Clarif Bidder <pkg> - <bidder>`
Title, bidder line, headers rows 3–4 (`BID AS SUBMITTED`; `CLARIFICATION` over `Clarification Question` | `Bidder Response to Clarification [Bidder to state the response and the name and page number of the supporting document(s)]`), rows 5–6 brand/model, items from row 7 in the same order (A–E formulas, F static question, G blank). No labels, findings, AI notes or AMPC guidance; no links to the AMPC sheet.
**Done when:** same items/order as internal; F non-empty, no formula; G blank; no errors; getImage rows 1–12 of both sheets; freeze 1:4.

### 7. Report (≤ 14 lines)
AI set columns and status (inserted / updated in place); counts + score; Not Meet rows; CR themes; genuine red flags; judgment points for the Committee; documents not provided; lot mismatches; Drive files added after the bid date; both sheet names + `n = Not Meet a + CR b`; summary formulas still reading human columns; what was re-read; changes `row: old → new, reason`. Remind: save; send the AMPC sheet for guidance; issue the bidder sheet in writing with a deadline after AMPC advice.

## Modes
- **Continue** (next bidder) · **Recheck / Re-evaluate** (new documents → rerun in place) · **Re-verify self-claims** (same standard for all bidders) · **Apply white-row rule** · **Clarification only / Sync**.
- **Add / refresh Drive links:** Step 4 + rewrite only the AI ATTACHED DOCUMENT cells (numbered list + hyperlink rules); labels, notes, V untouched.
- **Tidy / translate notes:** rewrite AI notes in the bilingual two-colour format; labels and V unchanged.
- **Rename legacy headers:** dated or `(Eval n – date)` AI headers → undated AI headers; content untouched.
- **Undo extra link columns:** delete any `ATTACHED DOCUMENT 2/3/4 (AI Evaluation)` whole columns (right-most block first), re-profile, move their documents into the AI ATTACHED DOCUMENT cell as the numbered list, verify human sets, scores and clarification-sheet formulas.

## Never
Write, clear, move or reformat a human evaluator set; create a second AI set or extra link columns; put dates in AI headers; link a multi-file cell to only its first file; use bidder-supplied URLs as references (only the evaluator's own Drive folder); write notes without the blue Indonesian translation; use unexplained jargon; put methodology or evidence-class codes in notes or questions; treat navigation markers as tampering; accept device capability on a letter, calculation, brochure or self-declaration alone; Meet because the bidder ticked Yes; assess or clarify white rows; mix label sets; omit flagged rows; delete rows holding AMPC advice or bidder responses; put bidder questions on the AMPC sheet or link the bidder sheet to it; show findings or AMPC guidance on the bidder sheet; let a clarification cure a material deviation; evaluate price.
