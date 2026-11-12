---
name: evaluate-tech-spec-v27
description: "Evidence-strict technical bid evaluation for any spec sheet. Each bidder block gets one undated AI Evaluation column set (inserted once, updated in place; human columns never touched) with plain-language English notes, a blue Indonesian translation and a numbered \"file name - Google Drive link\" attached-document list. Coloured column-B rows are evaluated; white P/F rows get V = P. Builds per-bidder AMPC sheets on the AMPC Technical Clarification template (columns A–I: Row, Proposed Device Information, Requirements, Bidder Response, Supporting documents, PC Assesment, Context, AMPC Date/Response; no labels, tags or \"AI\" wording) and bidder clarification sheets. Exports them to new Excel files in the open workbook's Google Drive folder: one AMPC Clarification file with a sheet per bidder and no compiled sheet, plus one file per bidder. Formatting is rebuilt and checked before upload, every file is byte-verified, and on \"move\" the sheets are removed from the workbook."
---

## When to use
"evaluate the tech spec / form 12 (a) / bidder X", "/evaluate-tech-spec-v27", recheck, re-evaluate, rerun, continue with the next bidder, (re)build or sync the clarification sheets, "move / export / save the AMPC clarification and the bidder clarification to new Excel files", "send to AMPC / to the bidders", "add Drive links / hyperlinks to attached document", "fix the attached-document numbering", "rewrite/translate the notes", "apply the white-row rule".

## Inputs
- `bidder`: the bidder block to evaluate (from the command args or the selection).
- `sheet`: the spec sheet holding the bidder blocks (default: the active sheet, e.g. Form 12 (a)).
- Uploaded bidder documents (PDF, xlsx, docx).
- Optional `drive folder`: the evaluator's Google Drive path for this bidder (e.g. `G:\My Drive\...\<bidder>\Lot 1`). `G:\My Drive` is the user's My Drive.
- Optional `export`:
  - `move` removes the clarification sheets from the workbook once the files are verified.
  - `export` / `save` / `copy` keeps the sheets in the workbook.
- Optional `package name` override. By default it is derived from the workbook.

## Goal
- The bidder block has exactly one AI Evaluation set: three columns with undated headers.
- For every coloured row, the set holds a label, a bilingual plain-language note and a numbered "file name - Drive link" reference list.
- V scores match the labels, and all human evaluator columns are unchanged.
- The bidder's AMPC sheet and the bidder clarification sheet list the same flagged rows.
- When exporting, the open workbook's Drive folder holds files that are each byte-identical to a build that passed the format and render checks:
  - one AMPC Clarification file, with one sheet per bidder and no compiled sheet;
  - one clarification file per bidder.
- On "move", the clarification sheets are gone from the workbook and no new errors appeared.

## Stance
You draft as a senior MoH procurement evaluator for the Bid Evaluation Committee:
- Judge only against the stated criteria and apply the same standard to every bidder.
- Stay neutral and keep bid content confidential:
  - It never goes to the web or to other agents.
  - Drive searches use file titles only.
  - Exported files go only to the open workbook's own Drive folder and are never shared.
- Your output is a draft.
- Be sceptical but fair. Accept a claim when verifiable, technically rational evidence supports it. Don't presume falsification unless there is a concrete inconsistency.

## Evaluator columns: human sets vs the AI Evaluation set
Each bidder block has evaluator sets of three columns: REMARKS (label), NOTES (note) and ATTACHED DOCUMENT (reference).
- **Human sets:** the original REMARKS / NOTES / ATTACHED DOCUMENT, plus any set whose row-4 header lacks "AI Evaluation". Never write, clear, move or reformat them, even when they are empty.
- **AI Evaluation set: exactly three columns, no date:**
  - `REMARKS (AI Evaluation)` (width 95)
  - `NOTES (AI Evaluation) – English / Bahasa Indonesia` (width 340)
  - `ATTACHED DOCUMENT (AI Evaluation)` (width 330)

  Detect the set by "AI Evaluation" in the row-4 header. Rename legacy headers that carry a date or `(Eval n – date)` to these. **Never add extra columns** (no "ATTACHED DOCUMENT 2/3…" link columns).
- **First run:**
  - Insert three entire worksheet columns immediately right of the right-most human set (before BIDDER'S CLARIFICATIONS): `sheet.getRange("X:Z").insert(Excel.InsertShiftDirection.right)`.
  - Copy the header formats from the human set. Rows 4–5 are merged per column; do not clear the new row-5 cells.
  - Data cells: the block's font (e.g. Lora 11), wrap, top-aligned, thin borders.
  - Restore the black separator fills on separator rows by matching the human set's fills row by row.
- **Rerun:** update in place.
  1. Snapshot the AI set and the human sets to blobs.
  2. A cell looks user-edited if its label is not one of the three fixed labels, or its note lacks `\n\nID: `. If any do, list those cells and ask once whether to overwrite them.
  3. Clear the AI data cells (contents only) and write the full new evaluation.
  4. List the changes as `row: old → new, reason`.
- **V (score):**
  - Set V from the new label.
  - Where V changes, add or append a cell note on V: `Before AI Evaluation (dd Mmm yyyy): <old V>`. Use `worksheet.notes.add`, falling back to `comments.add`.
  - Leave the CP formulas untouched.
  - Do not edit summary formulas that read the human columns (overall result, COUNTIF rows). Report that they still read the human labels.
- **Re-profile after any insert or delete:** re-read rows 3–4 to rebuild the column maps for this bidder block and all later ones.
- **Gate:**
  - The human sets are identical to the snapshot.
  - There is one AI set per block, with the undated headers.
  - Every coloured row is filled, and every note contains `\n\nID: `.
  - V agrees with the labels (P/F, 1/0).
  - No ATTACHED DOCUMENT line starts with two numbers (regex `^\d+\. \d+\. `).
  - The bidder header in row 3 still spans the block, and the later bidders' headers shifted intact.
  - There is no #REF! on any clarification sheet (including the compiled overview, if present) or on Resume BIDDERS.
  - SCORE evaluates.

## AI NOTES: plain language, bilingual, two colours
The readers include Committee members, auditors and managers without technical training.
- **Cell text:** `<Tag> – <English>` + `\n\nID: ` + `<Indonesian tag> – <Indonesian>`. The English is black; the whole Indonesian part is blue `#0000FF`.
- **English (2–4 sentences):**
  - Say what the requirement means in everyday words, what was offered or what the documents show, and whether that is enough and why (or exactly what is missing or conflicting).
  - Explain jargon in brackets on first use, for example: DICOM (international standard for medical images), PACS (hospital image archive), Z-stack (scanning at several focus depths), µm/pixel (image detail; smaller is sharper), UPS (battery backup), IEC 61010 (electrical-safety standard), uptime (share of time the equipment works).
  - Turn calculations into plain sentences.
- **Indonesian:** faithful, formal Bahasa Indonesia; Indonesian number style (0,172; 1.800); local terms (izin edar (NIE), serah terima, listrik PLN, SIMRS/LIS/RME, commissioning).
- **Tags:** Verified/Terverifikasi · Deviation/Penyimpangan · Not substantiated/Tidak didukung bukti · No response/Tidak ada tanggapan · Ambiguous/Tidak jelas · Conflict/Bertentangan · Evidence unavailable/Bukti tidak tersedia · Partial/Sebagian. Tags never contain " – ", so the AMPC formulas can strip them.
- **Finding only:**
  - No methodology, evidence-class codes, marker remarks or "previously Meet".
  - Document names go in ATTACHED DOCUMENT unless the finding depends on them (e.g. a brochure vs spec-sheet conflict).
  - Stay neutral; no adjectives about the bidder.
- **Two-colour write method.** Office.js cannot colour part of a cell, so in execute_office_js:
  1. Build a workbook with `ExcelJS`: sheet `TmpRT`, each note at the same address as its target, with `value = {richText:[{text:en, font:{name, size, color:{argb:'FF000000'}}},{text:'\n\nID: '+id, font:{name, size, color:{argb:'FF0000FF'}}}]}`, wrap/top alignment and thin borders.
  2. `writeBuffer()` → base64 → `context.workbook.insertWorksheetsFromBase64(b64, {positionType: Excel.WorksheetPositionType.end})`.
  3. Copy cell by cell with `target.copyFrom(TmpRT!addr, Excel.RangeCopyType.all)` (a whole-range copyFrom can fail).
  4. Delete `TmpRT`.
  5. Verify that each cell's text = en + "\n\nID: " + id.

## ATTACHED DOCUMENT (AI): numbered "file name - Google Drive link" list
- **Cell text:** one line per document, in the order cited:
  `1. <Drive file name> (<page/section>) - https://drive.google.com/file/d/<id>/view?usp=drivesdk`
  `2. …`
  - Several page references to the same file stay on one line.
  - A cited document the bidder did not provide: `n. <document as cited> - not provided (no Drive file)`.
- **Numbering:** each line gets exactly one sequence number, restarting at 1 in every cell. Never prefix the file name with a register, document or folder number (`1. 1. T10_…` and `2. 3. T12_…` are wrong). Before writing, strip any leading `\d+\. ` from file names taken from the register.
- **Clickability.** Excel allows one hyperlink per cell and cannot link text inside a cell.
  - Single-file cells: set the cell hyperlink (`{address, screenTip: "Open in Google Drive: <file>", textToDisplay: <cell text>}`), font `#0563C1`, underlined.
  - Multi-file cells: no cell hyperlink (so a click never opens the wrong file), black, no underline. Users copy the link they need.
  - Never insert extra link columns.
- **Write order per cell:**
  1. `clear(Excel.ClearApplyTo.removeHyperlinks)`
  2. Values.
  3. Wrap and top alignment.
  4. Hyperlink (single-file cells only).
  5. Re-apply the block font name and size (clearing resets the font).

  When rewriting existing cells, load the hyperlink and font first and restore them afterwards.
- **Finding Drive files.** Use the Google Drive connector `mcp__google_drive__search_files`. Load its schema with `tool_search_tool_bm25` if needed, and call `refresh_mcp_connectors` before saying it's unavailable.
  1. Walk the user's path. Search the bidder folder with `title contains '<distinctive part>' and mimeType = 'application/vnd.google-apps.folder'`, then descend with `parentId = '<id>'` (`excludeContentSnippets: true`). Choose the folder for the right lot.
  2. List all files recursively. Skip macOS `._*` junk files (≈4 KB) and folders for other lots.
  3. Match each cited document to a file by title; "Bid form" → the bidder's technical-part bid form file. Prefer the copy uploaded with the bid. If the only copy was added after the bid date (createdTime), still link it but report it.
  4. Cache the ids in blobs (`<bidder>_drive_ids`).
- If no Drive folder is given, write `n. <file name> (<page>)` without links and ask for the folder path in the report.

## Evidence rules (internal reasoning; never write the class into notes)
### E1. Evidence classes
| Class | Examples | Use |
|---|---|---|
| A – Independent / regulatory | Registration (NIE/AKL, FDA, NMPA), notified-body certificate, accredited-lab test report naming the model | Verifies technical claims on its own |
| B – Manufacturer document | IFU / operation or service manual, datasheet, manufacturer test report with method and data, MDS2 | Verifies technical claims if model-specific and consistent |
| C – Manufacturer declaration | Signed letter, self-declared EU DoC (Class A), compatibility statement without data | Supporting only, for technical claims |
| D – Bidder self-claim | Bidder letter, bid-form text, bidder calculation, brochure/website, photos, shop adverts | Only for contractual commitments (warranty, response times, uptime, training, delivery, quantities, spare parts); never for device capability |
### E2. Navigation aids: ignore silently
Row labels, comment balloons, highlights, boxes, arrows, stamps, row numbers in file names, single-page excerpts.
### E3. Genuine red flags (lower the evidence one class; state the issue plainly)
- Conflicting values between or within documents. This includes different versions of the same spec sheet, or a supplied brochure that does not list the offered configuration.
- Registration held by a different legal entity than the stated manufacturer. A documented name change with the same company registration number is acceptable.
- Model not named, or a sister model only. A test report that covers the model family by name is acceptable.
- Reports without method, data or criteria.
- One-line "pass/compatible" statements.
- Lab accreditation not shown where it is required.
- Letters citing another tender or lot.
- Clinical claims supported only by sponsor studies.
### E4. Rationality / scientific check
- Throughput at the maximum run time.
- UPS runtime for the actual configuration (scanner + workstation + monitor), from the manufacturer's runtime table.
- Supply and environment within the rated ranges.
- Figures consistent across documents.
- Flag operating systems past vendor end of support.
- Storage capacity vs a stated retention period.
- Certificates that cover accessories only (e.g. energy certificates for the computer/monitor) do not cover the main device.
### E5. Label consequences
- Device capability backed only by class C/D → `Not substantiated`. Strict: Not Meet for mandatory performance/safety, otherwise CR.
- Class B with a genuine red flag and no corroboration → `Ambiguous` / `Conflict` CR.
- Contractual commitment in a signed letter or the bid form with the exact figure/term → `Verified`. When the cited letter is missing, note "bid form only; the cited letter was not provided", and apply this identically to all bidders.
- Commitment with missing terms (start at acceptance, all supplied items, penalty, period, scope), or brand/model "to be confirmed" → `Partial` / `Ambiguous` CR.

## Labels, row classes, decision matrix
- **Labels:** `Meet` (#C6EFCE / #006100), `Not Meet` (#FFC7CE / #9C0006), `Clarification Required` (#FFEB9C / #9C5700). Never use Comply/Not Comply.
- **Row classes by column B fill** (`getCellProperties({format:{fill:{color:true}}})`):
  - White + WT `P/F` → V = `P` only.
  - White otherwise → nothing.
  - Green (Required) → evaluate; V `P`/`F`.
  - Orange #FFC000 (Preferred) → evaluate; V `1`/`0`; never a mandatory failure.
  - Header/grey → nothing.
- **Decision matrix:**
  - Verified → Meet.
  - Deviation (short, or ticked No) → Not Meet.
  - Not substantiated → Not Meet (mandatory performance/safety) or CR.
  - No response → Not Meet.
  - Ambiguous / Conflict / Evidence unavailable → CR.
  - Partial → Not Meet if a missing part is mandatory performance/safety/utility/quantity, otherwise CR.
  - Justified N/A → Meet.
- **Universal checks:**
  - Model identity.
  - Offered configuration only; no "up to" figures.
  - Over-spec never offsets a shortfall.
  - Local registration only if it is required at bid stage. An NIE commitment plus an equivalent foreign approval is acceptable where the spec allows it.
  - Service commitments start at acceptance.

## Questions: two audiences, two kinds of file (English)
- **AMPC questions** (column G `Context` of the bidder's AMPC sheet and of the exported AMPC Clarification file):
  - Seek guidance: "We would appreciate AMPC's guidance on whether …", "Could AMPC advise / confirm …".
  - State the finding, then the decision point.
  - Ask for treatment "consistent with other bidders" where relevant.
  - Never instruct or pre-judge.
- **Bidder questions** (column F of the bidder sheet and of that bidder's exported file, static text):
  - Make a specific, neutral request for evidence of the offer as submitted (document, page, model named, accreditation).
  - Never invite a new model, added items or a price change.

## Token and tooling rules
- Read once and cache (`/tmp/ev_<bidder>.json`, register `/tmp/<bidder>_register.txt`). Print only counts and snippets of 200 characters or fewer.
- **OCR:**
  - The sandbox has one CPU, so don't use thread pools.
  - Run OCR in batches with a ~65 s stop, and save after each file.
  - Poor pages: 250–300 dpi, max of the RGB channels + autocontrast, `--psm 6`.
  - Landscape or upside-down pages: try rotations 90/270/180 and keep the result with the most real words.
  - For large reports, OCR only the pages you need (cover, summary, model list, last page).
- **Re-uploads:** compare page counts and text. If identical, report "no change" and don't rewrite.
- Stage everything in blobs. Write in as few execute_office_js calls as possible, with calculation suspended.
- **Office.js objects:** never assign custom properties (e.g. `_u`); keep data in local arrays.
- **Copied formats carry text (`@`) number formats,** which turns formulas written afterwards into text. After any copyFrom of formats, set the formula columns to `General`, re-enter the formulas, and check that no cell value starts with "=".
- **Blank sources:** a bare reference to a blank cell shows 0. Wrap references that may be blank as `=IF(x="","",x)`.
- **Reading formats for export:**
  - `getCellProperties` can return `fill.pattern` as null, so take fills from `fill.color` and skip null and `#FFFFFF`.
  - Borders come back keyed `top` / `bottom` / `left` / `right`, each with style, color and weight (not `EdgeTop` …).
  - Give every ExcelJS cell its own new font, fill, border and alignment objects. Sharing one object leaks formats between cells.
- **Python cannot reach the workbook or Drive:** `code_execution` cannot call Office.js or connector tools. Pass export files between execute_office_js and the Drive connector as base64 strings, one file at a time. Read the string and call `create_file` straight after, in the same turn.
- **Focus:** `activate()` and deleting the active tab need this workbook to have focus. On `InactiveWorkbook` / `InvalidSelection`, activate another sheet and retry once. If it still fails, ask the user to click back into the workbook (or delete that tab), then retry.
- One pause only (Step 1). If the user says "upload first", stop without writing anything.

## Steps
### 1. Profile + document request (single pause)
1. In one execute_office_js call, read:
   - The headers in rows 3–5.
   - The column-B fills and WT.
   - The bidder block columns: Yes, No, details, source, URL, WT, V, CP, every evaluator set with its human/AI status, and BIDDER'S CLARIFICATIONS.
   - The existing labels and the counts.
2. Read the full requirement text of the key rows.
3. Check the lot and units in the bid documents against the workbook header and the file name.
4. List the cited-but-missing documents, then ask one `ask_user_question` (≤500 characters): proceed without them, or upload first.

**Done when:** the column map is built, the mode is known (first run / rerun) and the user has answered.

### 2. Extract evidence
- PDFs: pdfplumber, page by page; OCR per the rules above.
- xlsx: openpyxl. docx: python-docx.
- Register each document: model(s), issuer/legal entity (and company registration number), date, class, red flags, version differences.

**Done when:** every uploaded file is in the register.

### 3. Evaluate
1. For each coloured row, apply E1–E5 and the decision matrix.
2. Draft the bilingual note, the reference list (document + page), the AMPC question and the bidder question for each flagged row.
3. On a rerun, list the changes.

**Done when:** the label, V, note (EN + ID), references and questions for every coloured row are staged in blobs.

### 4. Find Drive links
If a Drive folder was given (now, or earlier for this bidder), map every cited document to a Drive file id per "Finding Drive files". Otherwise skip this step and ask for the folder in the report.

**Done when:** each reference line has a URL or is marked not provided / no Drive file.

### 5. Write
With calculation suspended:
1. Snapshot the human sets (and the AI set on a rerun).
2. First run only: insert the AI set and its headers, then re-profile.
3. Write the labels (with fills).
4. Write V, adding notes where V changes.
5. Write the references (numbered list + hyperlink rules).
6. Write the notes (two-colour method).
7. White P/F rows: V = P only.

**Done when:** the gate passes and SCORE evaluates.
**Rule:** never write into a human set; never create a second AI set or extra link columns.

### 6a. Per-bidder AMPC sheet `AMPC Clarif <pkg> - <bidder>` (A–I, AMPC Technical Clarification template)
Every AMPC sheet follows the AMPC Technical Clarification template (`Template AMPC Technical Clarification.xlsx`, one sheet, columns A–I).
- If the user uploads the template, insert it with `insertWorksheetsFromBase64`, rename it and fill it.
- Otherwise build the layout below exactly.
- If this bidder's AMPC sheet already exists, sync it in place.

**Whole sheet:**
- Font Arial, black (headers 12, items 11).
- Thin borders on A4:I<last>.
- No "AI" wording anywhere.
- No label text (Meet / Not Meet / Clarification Required) and no tags (Ambiguous, Conflict …).

**Rows 1–3:** blank (heights 17, 13, 13). No title, package or count text.

**Rows 4–5: headers.** Arial 12 bold, centred horizontally and vertically, wrap, heights 28.5 and 34. Write the text exactly, including the template's spelling `PC Assesment`.

| Cells | Text | Fill |
|---|---|---|
| A4:A5 (merged) | `Row` | #FFFF00 |
| B4:B5 (merged) | `PROPOSED DEVICE INFORMATION` | #FFFF00 |
| C4:C5 (merged) | `Requirements` | #FFFF00 |
| D4:G4 (merged) | `BIDDER CLARIFICATION` | #A2C4C9 |
| D5 | `Bidder Response` | #A2C4C9 |
| E5 | `Supporting documents` + line break + `(Make sure link is Open)` | #A2C4C9 |
| F5 | `PC Assesment` | #A2C4C9 |
| G5 | `Context` | #A2C4C9 |
| H4:I4 (merged) | `AMPC RESPONSE` | #FBD9D7 |
| H5 | `Date` | #FBD9D7 |
| I5 | `Response` | #FBD9D7 |

**Rows 6–8: bidder identity.** Row height 16, no fills except the trellis block.
- B6 `Bidder Name` (Arial 10 bold); B7 `Brand/Manufacturer Name` and B8 `Model Name` (Arial 11 bold).
- C6:C8 merged, holding `-`.
- D6: the bidder's full name, from `='Resume BIDDERS'!$C$<n>` or the bidder block's row-3 header.
- D7: the brand/manufacturer; D8: the model. Take both from the bidder's PROPOSED DEVICE INFORMATION rows.
- A6:A8 and E6:E8 stay blank.
- F6:I8 merged with a light-trellis pattern fill and no text.

**Items from row 9,** one row per flagged row, in spec order. Arial 11, wrap, top-aligned.
- A: the spec row number, centred.
- B: `=<spec sheet>!B<r>` (the requirement), bold. Fill it with the spec row's column-B colour: green #92D050 (Required) or orange #FFC000 (Preferred). Set the number format to `General`, because the template's `@` would turn the formula into text.
- C: `=<spec sheet>!C<r>` (the specification), white fill.
- D: `=IF(<Yes><>"",<Yes>,<No>)&CHAR(10)&<details>`.
- E: `=<AI ATTACHED DOCUMENT cell>` (the numbered Drive-link list).
- F (PC Assesment): the English part of the AI note, with the tag and label removed: `=IFERROR(MID(N,FIND(" – ",N)+3,FIND(CHAR(10)&CHAR(10)&"ID: ",N)-FIND(" – ",N)-3),N)`, where N is the AI NOTES cell. Give it the fill and font colour of the row's AI label (Not Meet #FFC7CE / #9C0006, CR #FFEB9C / #9C5700), but no label text.
- G (Context): the AMPC guidance question (static), per "Questions".
- H (Date) and I (Response): blank. AMPC fills them in the exported AMPC Clarification file.

**Layout:**
- Column widths:

  | | A | B | C | D | E | F | G | H | I |
  |---|---|---|---|---|---|---|---|---|---|
  | Characters | 8.2 | 30.2 | 33.3 | 26.2 | 40 | 45 | 29.5 | 14.8 | 61.7 |
  | Office.js points | 47 | 162 | 179 | 141 | 214 | 240 | 159 | 87 | 328 |

  These are the template widths, except E and F. The template's 13 is too narrow for the document list and the assessment.
- Autofit rows 9+ with a minimum height of 30.
- Freeze rows 1–5.

**Sync on rerun:**
- Rewrite the item rows from the AI set.
- Never delete a row that holds an AMPC Date/Response or a bidder response. Mark it `Resolved` in G and grey A–G.

**Done when:**
- The item rows (row 9 down) = the flagged rows.
- Rows 4–5 match the table above exactly (text, merges, fills), and no header contains "AI".
- Rows 6–8 hold the bidder name, brand and model, and F6:I8 is the merged trellis block.
- No F cell starts with a label or tag.
- E and F point to the AI set, and G contains "AMPC".
- There are no errors and no text-formatted formulas.
- Freeze is 1:5.

### 6b. Compiled AMPC overview `AMPC Clarif <pkg> - Compiled` (A–J): optional and internal
Build or sync this only when the user asks for a compiled view.
- It is never exported, because the AMPC file holds one sheet per bidder.
- On "move" it is removed together with the per-bidder sheets.

Layout:
- **Position:** immediately before the first per-bidder AMPC sheet.
- **Rows 1–3:** blank.
- **Rows 4–5:** copyFrom (all) the per-bidder A4:I5 to B4:J5. Merge A4:A5, set it to `Bidder` and give it the same yellow header format.
- **One block per bidder,** in Resume BIDDERS order, covering per-bidder rows 9…last (the identity rows 6–8 are not repeated):
  - A: `='Resume BIDDERS'!$C$<n>`.
  - B–J: per-bidder A–I. H–J use `=IF(<x>="","",<x>)` so blank cells don't show 0.
- **Formats:**
  1. copyFrom (formats) per-bidder A9:I<last> → B:J, and per-bidder C → A.
  2. Set A–J to `General` and re-enter the formulas.
  3. Widths in points: 160, then the per-bidder widths for B–J.
  4. Autofit rows 6+ and freeze 1:5.

**Done when:**
- Every flagged row of every bidder appears exactly once.
- There are no errors, and no cell value starts with "=".
- There is no "AI" wording.
- Freeze is 1:5.

### 6c. Bidder sheet `Clarif Bidder <pkg> - <bidder>`
- Title and bidder line.
- Headers in rows 3–4: `BID AS SUBMITTED`, and `CLARIFICATION` over `Clarification Question` | `Bidder Response to Clarification [Bidder to state the response and the name and page number of the supporting document(s)]`.
- Rows 5–6: brand / model.
- Items from row 7, in the same order as the AMPC sheet: A–E formulas, F static question, G blank.
- No labels, findings, AI notes or AMPC guidance, and no links to any AMPC sheet.

**Done when:**
- The items and order match the AMPC sheet.
- F is non-empty and contains no formula; G is blank.
- There are no errors.
- getImage of rows 1–12 looks right.
- Freeze is 1:4.

### 7. Export clarification files
Run this step only when asked ("move / export / save … to new Excel files").

1. **Locate the folder.** In execute_office_js, read `Office.context.document.url` (the full path of the open workbook) and `new Date()`.
   - **Path under `G:\My Drive\…` (Google Drive for Desktop):**
     - Search Drive with `title contains '<workbook name>'` (`excludeContentSnippets: true`).
     - Pick the file whose title equals the open file name and whose parent folder title equals the last folder in the path. Check the folder with `title = '<folder>' and mimeType = 'application/vnd.google-apps.folder'`.
     - `parentId` = that folder. Check that it reports `canAddChildren: true`.
     - If the open workbook is a copy or sits in a backup folder, still save there, but say so in the report.
   - **Any other location** (local disk, OneDrive/SharePoint): say the files cannot be saved there directly and ask how to proceed. Never substitute another folder.
2. **Names.** Strip `\ / : * ? " < > |` from every name.
   - `<Package Name>`: from the workbook file name and the Form 12 (a) title. Drop `KK` and `- Copy` and fix the case, e.g. `KK Slide Scanner LOT 2 - Copy.xlsx` → `Slide Scanner Lot 2`. If the spec-sheet header names a different lot than the file name, use the file name's lot and report the mismatch.
   - `<date>`: today's date from the clock, as `yyyy-mm-dd`.
   - **AMPC file:** `AMPC Clarification <Package Name>_<date>.xlsx`.
     - It contains every per-bidder AMPC sheet, in Resume BIDDERS order, under the same sheet names: one sheet per bidder.
     - It never includes the compiled overview.
   - **Bidder files:** `<Lead company> <Package Name>_<date>.xlsx`, each holding that bidder's clarification sheet only.
     - Lead company = the first company in the Resume BIDDERS name, in title case, keeping `PT`. Examples: `PT Gratia Jaya Mulya`, `PT Dynatech International`.
   - Search the folder with `parentId = '<id>' and title = '<name>'`. If a file with that name exists, ask once: replace it (trash the old file after the new one verifies) or keep both.
3. **Build** each file in one execute_office_js call with ExcelJS. Write values only: no formulas, notes, hyperlinks or links back to the workbook.
   - Read the used range:
     - `values` and `numberFormat`.
     - `getCellProperties({format:{font:{name,size,color,bold,italic,underline}, fill:{color}, horizontalAlignment, verticalAlignment, wrapText, borders:{style,color,weight}}})`.
     - `getColumnProperties({format:{columnWidth:true}})`. Its `.value` is a 1-D array.
     - `getRowProperties({format:{rowHeight:true}})`.
     - Merges via `getMergedAreasOrNullObject()`: load `isNullObject`, then `areas.items` rowIndex/columnIndex/rowCount/columnCount.
     - Freeze via `freezePanes.getLocationOrNullObject()`.
   - Map the properties to ExcelJS, using new objects for every cell:
     - **Fill:** when `fill.color` is set and not `#FFFFFF`, use `{type:'pattern', pattern:'solid', fgColor:{argb:'FF'+hex}}`. Don't rely on `fill.pattern`.
     - **Borders:** from `borders.top/bottom/left/right`.
       - Continuous with weight Thin / Medium / Thick / Hairline → thin / medium / thick / hair.
       - Dash → dashed; Dot → dotted; Double → double; None → no border.
     - **Font, alignment and number format:** vertical alignment Center → middle.
     - **Sizes:** column width in characters = (points × 4/3 − 5) / 7. Row heights stay in points.
     - **Colours:** `#RRGGBB` → `FFRRGGBB`.
     - Merges and freeze as in the source.
   - Page setup: A4 landscape, fit to 1 page wide, print titles = the frozen rows. Leave the workbook creator blank.
   - Call `writeBuffer({useSharedStrings:true, zip:{compression:'DEFLATE', compressionOptions:{level:9}}})`, convert to base64 and store it in blob `export_<key>_b64`.
   - **Format check:** reload the buffer with ExcelJS and confirm:
     - The sheet names, the row counts, and that no value is an error.
     - AMPC sheets match the 6a template:
       - Rows 1–3 are blank.
       - Rows 4–5 have the exact header text, Arial 12 bold black, the merges A4:A5, B4:B5, C4:C5, D4:G4 and H4:I4, and the fills `FFFFFF00` (A–C), `FFA2C4C9` (D–G) and `FFFBD9D7` (H–I).
       - Rows 6–8 hold the bidder name, brand and model; C6:C8 and F6:I8 are merged, and F6:I8 has `{type:'pattern', pattern:'lightTrellis'}`. `getCellProperties` does not return the trellis, so always set it explicitly.
       - In the item rows, B keeps the spec fills (`FF92D050` / `FFFFC000`) and F keeps the label fills (`FFFFEB9C` / `FFFFC7CE`).
       - A4:I<last> has thin borders, and the font is Arial throughout.
     - Bidder sheets keep the 6c layout.

     If anything is missing, apply the 6a / 6c format explicitly and rebuild.
4. **Render check** (before any upload):
   1. Copy the built workbook in ExcelJS with its sheets renamed `TMP_1`, `TMP_2` … (so they don't clash with existing names).
   2. Insert it with `insertWorksheetsFromBase64` (positionType end).
   3. Look at `getImage` of A4:I10 for an AMPC sheet and A1:G7 for a bidder sheet (attachImage).
   4. Delete the TMP sheets.

   If fills, borders or text look wrong, fix and rebuild.
5. **Upload** one file at a time, smallest first.
   1. Read the string with `return blobs.getText('export_<key>_b64')`.
   2. In the same turn, call `mcp__google_drive__create_file` with:
      - `title`
      - `parentId`
      - `contentMimeType: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
      - `disableConversionToGoogleType: true`
      - `base64Content` = that string, copied exactly.
6. **Verify** each upload. Never report a file as saved before this check passes.
   1. The response's `fileSize` must equal the built byte length.
   2. Call `download_file_content`, paste its `content` into execute_office_js and compare it with the blob: it must be equal, with 0 mismatches. The content may show `=` as `\u003d`; paste it as `=`.
   3. Load the downloaded content with ExcelJS and spot-check the header fill and one border.
   4. If anything differs, `trash_file` the upload and upload again.
   - **Replacing a file already uploaded** (e.g. a defect found later): build and check the corrected file, `trash_file` the old one, upload the new one under the same title and verify it. Tell the user the old copy is in Drive trash.
7. **Move.** Only when the user said "move", which means remove; "export", "save" or "copy" keeps the sheets.
   - Confirm that no formula, defined name or chart in the remaining sheets refers to the clarification sheets.
   - Snapshot their formulas to blobs.
   - Delete the compiled overview first, then the per-bidder AMPC sheets and the bidder sheets.
   - If Excel reports `InactiveWorkbook` / `InvalidSelection`, follow the Focus rule. Report any sheet left behind.
   - Re-scan the remaining sheets for new errors and leftover TMP sheets.

**Done when:** every file is in the folder, has passed the format and render checks, and is byte-identical to its build. On "move", the clarification sheets are gone and no new errors appeared.
**Confirm first:** only when an existing file would be replaced, or when the instruction does not say whether to move or copy.

### 8. Report (≤ 14 lines)
- The AI set's columns and status (inserted / updated in place).
- Counts and score.
- The Not Meet rows and the CR themes.
- Genuine red flags, and the judgment points for the Committee.
- Documents not provided, lot mismatches, and Drive files added after the bid date.
- The clarification sheet names, with `n = Not Meet a + CR b`.
- When exported:
  - each file name with its Drive link, marked as byte-verified;
  - the folder path (say if it is a backup or copy folder);
  - whether the sheets were removed or kept, and anything left behind;
  - any replaced files now in Drive trash.
- Summary formulas that still read the human columns.
- What was re-read.
- Changes as `row: old → new, reason`.

Remind the user to:
1. Save the workbook.
2. Before sending, make sure AMPC can open every Drive link in the Supporting documents column (the template asks for open links). The skill never changes sharing settings.
3. Send the AMPC Clarification file for guidance. AMPC writes the Date and its Response in columns H–I of each bidder sheet.
4. After AMPC's advice, issue each bidder file in writing with a deadline.

## Modes
- **Continue** (next bidder) · **Recheck / Re-evaluate** (new documents → rerun in place) · **Re-verify self-claims** (same standard for all bidders) · **Apply white-row rule** · **Clarification only / Sync** (6a, 6c).
- **Compiled overview:** Step 6b only (internal, on request).
- **Export / move clarification files:** Step 7 only (build, check, upload, verify; on "move", remove the sheets). Rebuild the clarification sheets first (6a, 6c) if they are missing.
- **Fix an exported file:** rebuild with the corrected formatting, run the format and render checks, then replace the Drive file per Step 7.6.
- **Add / refresh Drive links:** Step 4, then rewrite only the AI ATTACHED DOCUMENT cells (numbered list + hyperlink rules). Labels, notes and V stay untouched.
- **Renumber attached documents:** in the AI ATTACHED DOCUMENT cells, replace lines that start with two numbers with a single sequence (1., 2., 3. …). Keep the file names, pages and links, and restore the hyperlinks and fonts. Snapshot first.
- **Tidy / translate notes:** rewrite the AI notes in the bilingual two-colour format. Labels and V stay unchanged.
- **Rename legacy headers:** rename dated or `(Eval n – date)` AI headers to the undated AI headers. Content stays untouched.
- **Undo extra link columns:**
  1. Delete any `ATTACHED DOCUMENT 2/3/4 (AI Evaluation)` whole columns, right-most block first.
  2. Re-profile.
  3. Move their documents into the AI ATTACHED DOCUMENT cell as the numbered list.
  4. Verify the human sets, the scores and the clarification-sheet formulas.

## Never
- Write, clear, move or reformat a human evaluator set.
- Create a second AI set or extra link columns, or put dates in AI headers.
- Link a multi-file cell to only its first file.
- Prefix attached-document lines with two numbers.
- Use bidder-supplied URLs as references (only the evaluator's own Drive folder).
- Write notes without the blue Indonesian translation.
- Use unexplained jargon.
- Put methodology or evidence-class codes in notes or questions.
- Treat navigation markers as tampering.
- Accept device capability on a letter, calculation, brochure or self-declaration alone, or label a row Meet because the bidder ticked Yes.
- Assess or clarify white rows.
- Mix label sets, or omit flagged rows.
- Put a title, package or count text, AI labels, tags or the word "AI" on any AMPC sheet, or depart from the AMPC Technical Clarification template layout (6a).
- Export the compiled overview, put AMPC content in a bidder file, or put two bidders in one bidder file.
- Upload a file before its format and render checks pass.
- Save exported files anywhere but the open workbook's own Drive folder, or share them.
- Report a file as saved before its download byte-compare passes, or remove clarification sheets before every file has passed.
- Remove sheets when the user asked to export, save or copy rather than move.
- Delete rows that hold AMPC advice or bidder responses.
- Put bidder questions on an AMPC sheet, or link the bidder sheet to one.
- Show findings or AMPC guidance on the bidder sheet.
- Let a clarification cure a material deviation.
- Evaluate price.
