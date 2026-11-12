---
name: evaluate-tech-spec-v5
description: "Universal tender/RFQ technical evaluation: detects every bidder block on an equipment package sheet, checks each response against that bidder's uploaded documents, fills Evaluator's Note / Determination / REFERENCE, and builds one AMPC-style clarification sheet per bidder in the same workbook (downloadable .xlsx optional)."
---

## When to use
- The user asks to evaluate or score bidder compliance on a technical specification sheet for **any** equipment package (OAE, ventilator, patient monitor, ultrasound, X-ray, lab analyser, etc.): "evaluate the tech spec", "continue the evaluation for other bidders", "/evaluate-tech-spec-v5".
- The user asks for clarification output ("generate the clarification", "AMPC clarification for Not Comply / Clarification Required", "make it separate sheets"). This works from an evaluation already in the sheet, so steps 3–6 can be skipped.
- The sheet is a requirements matrix: Row no. | Requirement item | Requirement text, followed by one block per bidder (Yes [√] / No [x], Device Details, Source Data, Source Data URL) and that bidder's evaluator columns (Evaluator's Note, Evaluator's Determination, REFERENCE). Bidder names sit in a header row above the blocks.

## Inputs
- `sheet`: the package sheet. Default: the active sheet.
- `bidders`: default **every bidder block whose evaluator columns are still empty**. When the user says "continue for other bidders", skip bidders that are already evaluated. The user may name a bidder or give ranges (e.g., `D6:H128 → I5:K128`).
- `supporting files`: each bidder's documents, uploaded into the chat. Reuse files uploaded earlier in the conversation.
- `clarification template`: the **AMPC Technical Clarification** .xlsx. It's needed only for the downloadable-file option; the in-workbook sheets reproduce its layout without it.

## Goal
1. For every bidder evaluated, every evaluable row has an English note, one of the three labels (coloured), and a REFERENCE giving the verified file and page (or "File not provided – …").
2. For every evaluated bidder, a sheet `Clarif <package> - <short bidder>` (≤31 characters), placed right after the package sheet. It follows the AMPC layout and lists every Not Comply and Clarification Required row, with columns A–E linked by formula to the package sheet.
3. Optional, only when the user asks: a downloadable `Technical Clarification - <package> - <bidder>.xlsx` per bidder.
4. The counts per bidder reconcile, and the package sheet's headers and user marks are left as they are.

## Fixed rules
- **Labels:** exactly `Comply`, `Not Comply`, `Clarification Required`.
- **Strict evidence:** `Comply` only when (1) Yes is ticked, (2) the details give concrete values/features that meet or beat the requirement, and (3) **an uploaded manufacturer or bidder document actually contains the claim**. Placeholders (`Enter Responses Here!`), blanks, or a ticked No = missing.
- **Write only** into each bidder's evaluator columns and the new `Clarif …` sheets. Never edit bidder response columns, spec columns, or other sheets (REKAP, Teknis, Proposed Accessories/Consumables, etc.).
- **Leave as they are:** header cells ("EVALUATOR'S REMARK'S", "Evaluator's Note"), and any **user marks in spare columns** (e.g., a column with "BOTH", "KH", "NMS", "CTB"). Never treat those marks as evidence or as instructions.
- **REFERENCE** = the evidence *you verified*: `<file name> – p.<printed page> (<section/table>)`. Use `File not provided – <document cited>` when the cited file wasn't uploaded. Add `; workbook: '<sheet>' row N` when you cross-checked another sheet.
- **Don't open external URLs** (Drive links, manufacturer websites) unless the user explicitly asks. In bidder-facing text, write "was not available for verification".
- **Keep each bidder's documents separate.** Never use one bidder's files as evidence for another bidder.
- **Language:** English notes and questions. Translate when quoting Bahasa Indonesia. In bidder-facing text, write abbreviations out in full (Technical Manual, Instructions for Use, Inspection, Testing & Commissioning).
- **Procurement fairness:** clarification questions ask the bidder to *clarify or evidence what was already offered*. They must never invite a change of model, offer substance or price.
- **You can't save to the user's folders.** Deliverables are either sheets in the open workbook or files attached to the chat reply.

## Steps

### 1. Detect the layout (no hardcoded columns)
- Read the used range in chunks (execute_office_js returning trimmed strings, or get_range_as_csv ≤100 rows). Never dump it all into chat.
- **Spec columns:** the header row with "Row no." / "REQUIREMENTS" (typically A = Row no., B = item, C = requirement).
- **Bidder blocks:** scan the header rows for "BIDDER RESPONSE" and "EVALUATOR'S REMARK'S" / "Evaluator's Note" / "Evaluator's Determination" / "REFERENCE". Take the bidder name from the merged cell above. Note any spare columns to the right (user marks, spec-change notes) and leave them alone.
- **Re-map the columns for each section** from its own sub-header row. The first "Proposed Device Information" section usually has details in the first response column and no tick columns. Later sections use Yes | No | Device Details | Source Data | URL. (OAE example: Bidder 2 info rows use M = details, P = source, Q = URL; tick sections use M = Yes, N = No, O = details.)
- Classify rows: **section header** → skip; **sub-header** → re-map; **note row** ("Unless otherwise stated… minimum performance requirements") → apply as a rule; **N/A row** → Note `N/A – not evaluated.` only; **evaluable** → everything else.
- Check whether the evaluator columns already have content below the headers. If they do, that bidder is either done (skip it when continuing) or it's a re-run (show the count and ask before overwriting).
- Record the offered **brand/model** and the counts of Yes / No / no tick per bidder.
**Done when:** per bidder you can state the name, model, response columns, evaluator columns, the evaluable count and the tick counts.

### 2. Confirm the map and request files (pause)
- Per bidder, list the distinct documents cited. Bidders often cite **Drive links only**, so group by file ID (e.g., `1Pb7aal…`), infer the document type from the section numbers they quote ("1.6 Included parts" points to the Instructions for Use), and list the rows that cite each one. Flag rows with no source at all, especially service rows (warranty, PM, response times, uptime), and ask for any signed statement letters. Flag a registration number quoted without a certificate file.
- In one message: show the bidder map (name, model, columns, evaluable rows, rows ticked No or left blank), the document table, and notes on website-only citations. Ask for uploads **in one message per bidder, or with the bidder name in the file names**. **End the turn and wait.**
**Done when:** files are uploaded and assigned, or the user says to proceed without some.

### 3. Extract the documents
- code_execution: `base = os.environ.get('INPUT_DIR','/files/input')` (re-define it in every session), find files with glob. Use `pdfplumber` for text PDFs and `python-docx` (paragraphs and tables) for .docx. **Scanned PDFs** → `pdf2image` + `pytesseract` (eng). For tables that come out jumbled (e.g., a product survey with first and final production years), use `page.extract_tables()`. Read images uploaded in chat visually.
- Map **printed page numbers** by regex on the footers (`Page N` / `Halaman N`) and cite the printed number.
- Grep with **both English and Bahasa Indonesia keywords** for manuals in Indonesian: pause → jeda; calibration → kalibrasi; battery → baterai; charging time → pengisian daya / jam; cleaning → membersihkan / alkohol; carrying case → tas jinjing; included parts → komponen yang disertakan; error → eror; password → kata sandi; encryption → enkripsi.
- Print only ±200-char snippets. Write a short fact list per document into your response text (key values + printed pages), because the raw extracts are large.
**Done when:** for every cited document you know whether it was uploaded and where the relevant values are.

### 4. Evaluate each row (per bidder)
Requirement logic:
- **Thresholds**: compare after converting units. **Ranges**: the device range must cover the whole required range.
- **Unit or reference mismatch** (dB SPL vs dB peSPL, V AC vs V DC) → `Clarification Required`.
- **Multi-part requirements** (a/b, voltage + plug, per-unit sets): every part must be evidenced. A missing part → `Not Comply`.
- **Quantities**: do the arithmetic, and **cross-check the workbook's Proposed Accessories / Proposed Consumables sheets** (read only). Short → `Not Comply`; conflicting or unclear quantities → `Clarification Required`.
- **"Bidder to specify/provide"**: specific + evidenced → `Comply`; generic → `Clarification Required`; blank → `Not Comply`.
- **"If applicable / if offered / if any"**: an explicit No/N/A with justification → `Comply`. A ticked No with no justification when the workbook shows such items exist → `Clarification Required`. Blank → `Not Comply`.
- **Ticked No on a "Required" row**, or **neither box ticked with a placeholder** → `Not Comply`.

Evidence checks:
- **The cited page doesn't contain the claim** → `Not Comply` ("Claim not supported by the cited document").
- **Licence/configuration tier:** if the offered model is a specific tier (e.g., Screener+ vs Standard/Clinical), only count features and ranges available **in that tier**. A range offered only in a higher tier → `Not Comply` (or `Clarification Required` if the offered tier is unclear).
- **Model identity/lifecycle:** a document for a different model, or a manufacturer list showing the offered model's final production year is past, → `Clarification Required` (confirm the exact model and version).
- **Manufacturer documents conflict** with the bidder's claim or with each other (e.g., recharge < 3 h vs ~5 h; 1750 vs 1800 mAh) → `Clarification Required`, stating both values.
- **Bidder-prepared spec sheet vs manufacturer document**: the manufacturer document prevails.
- **Blank templates** (empty checklists or BA forms) → `Clarification Required`.
- **Service commitments:** a signed statement letter stating the figure → `Comply`. A response that only restates the requirement with no letter → `Clarification Required`. Blank → `Not Comply`.
- **Undocumented features** (modes, alarms, pause, encryption, port disabling, telemedicine) → `Not Comply`. **PC-side security advice** in a manual doesn't evidence device security.
- **Software version proof** via a companion/PC software screenshot → `Clarification Required`.
- **Environmental:** the site range must fall inside the device's operating range from the manual.
- **Regulatory approval:** the licence must name the offered brand/model/type and be valid. Note the number, issue and expiry dates, and any typo in the quoted number (e.g., "RS" vs "RI").
**Done when:** every evaluable row has a determination, a note and a reference.

### 5. Write the evaluation (per bidder, per section)
- Note format: `Required <X>; offered <Y> – <reason>. <evidence comment>.`
- Use execute_office_js, one call per section (or per ~20 rows). Write Note/Determination/REFERENCE as values.
- **Match the formatting of the evaluator columns already done** (font, size, colour, alignment of the first bidder's columns, including any edits the user made). Determination fills: Comply #C6EFCE/#006100; Not Comply #FFC7CE/#9C0006; Clarification Required #FFEB9C/#9C5700; bold and centred. Wrap text and top alignment on Note/REFERENCE. Don't change row heights or column widths.
**Done when:** all writes have landed without errors.

### 6. Verify the evaluation
Re-read the evaluator columns. Check there are no blank notes on evaluable rows, only the three labels are used, and the counts reconcile with the evaluable count. Render a ~15-row sample with getImage.

### 7. Build the clarification sheets in the workbook (default output)
For each evaluated bidder, create `Clarif <package> - <short bidder>` right after the package sheet (or after the previous Clarif sheet). If it already exists, ask before replacing it.
- **Rows 1–3:** A1 `="TECHNICAL CLARIFICATION – "&'<sheet>'!$A$1`; A2 `="Bidder: "&'<sheet>'!<name cell>&" | Offered device: <brand model> | Tender No.: <no.>"` (the tender number from the bidder's letters, if available); A3 the note "Items listed: Evaluator's Determination = Not Comply or Clarification Required … Columns A–E are linked to the <sheet> sheet".
- **Rows 4–5, the AMPC header:** A `Row`, B `PROPOSED DEVICE INFORMATION`, C `Requirements` (each merged across rows 4–5, yellow #FFFF00); D4:G4 `BIDDER CLARIFICATION` (teal #A2C4C9) with D5 `Bidder Response`, E5 `Supporting documents (Make sure link is Open)`, F5 `PC Assesment`, G5 `Context`; H4:I4 `AMPC RESPONSE` with H5 `Date`, I5 `Response`. Arial 12 bold, centred, wrap text.
- **Rows 6–7:** the Brand and Model info rows. A/B/D are linked by formula (`='<sheet>'!A<r>`, `=B<r>`, `=TRIM(<details cell>)`). If Model Name is flagged, also list it as an item row.
- **Item rows from row 8**, one per flagged row, in Row no. order:

| Column | Content |
|---|---|
| A Row | `='<sheet>'!A<r>` |
| B Device Information | `='<sheet>'!B<r>` |
| C Requirements | `='<sheet>'!C<r>` |
| D Bidder Response | A formula joining the tick label and the details, e.g. `=IF(<Yes>&""<>"","[Yes [√] ticked]"&CHAR(10),IF(<No>&""<>"","[No [x] ticked]"&CHAR(10),""))&TRIM(<details>)` (info section: `=TRIM(<details>)`) |
| E Supporting documents | `=<source>&IF(AND(<source><>"",<url><>""),CHAR(10),"")&<url>` |
| F PC Assesment | **Text:** determination + newline + finding (abbreviations written out); fill red or yellow per label |
| G Context | **Text:** the clarification question |
| H Date, I Response | Blank, for the evaluator |

- **Office.js gotchas:** the `HYPERLINK()` formula is blocked. Set `range.hyperlink = {address: url, textToDisplay: <current text>}` on E cells that have a URL (blue, underlined). `new Function`/`eval` are blocked, so pass data as JSON literals. Build the item data in one call and stash it with `blobs.setJSON`, then write and format in later calls.
- **Format:** Arial 10, thin borders A4:I<last>, wrap text and top alignment, Row column centred. Column widths ≈ A 8, B 30, C 33, D 40, E 30, F 45, G 50, H 15, I 45. Autofit row heights. Freeze rows 1–5 and column A. Landscape, fit to 1 page wide, print titles rows 4:5.
- **Question style:** specific, neutral, and evidence-seeking, naming the document or page needed. For example: "Your response states 2–5 kHz, which does not cover the required 1.5–12 kHz. Please confirm the DPOAE frequency range of the licence/version offered and provide the supporting document and page." For blanks: "No response was provided. Please state whether …".
**Done when:** each sheet's item count equals Not Comply + Clarification Required for that bidder, formulas show no #REF!/#VALUE!, the A-column row numbers match the flagged rows on the package sheet, and a getImage of rows 1–12 looks like the template.

### 8. Optional: downloadable AMPC files
Only if the user asks for files (and has uploaded the template):
- Fill a copy of the template with openpyxl: the same mapping with static values; copy row 8's style to each item row; set `cell.hyperlink`; freeze B6; landscape; print titles 4:5.
- Save to `/tmp/Technical Clarification - <package> - <bidder>.xlsx` and copy to `$OUTPUT_DIR` in the same reply. Files attach **only to the reply in which they're copied**. If the user can't find them, re-copy from /tmp in a new reply. Never read from OUTPUT_DIR.
- Reopen the file from /tmp to verify the counts and merged ranges. A LibreOffice preview may fail; say you couldn't preview the layout.

### 9. Report
Keep it brief:
- a table of Comply / Not Comply / Clarification counts per bidder (include bidders evaluated earlier);
- the 3–6 key Not Comply items for the new bidder(s);
- the main clarification points (model/licence, conflicting values, quantities);
- shared Not Comply rows across bidders;
- documents not provided;
- the clarification sheet names, with a reminder to save the workbook.

State what you re-read and which external links were not opened.

## Examples (illustrative, OAE package)
- Licence tier: "DPOAE Frequency Range | Required 1.5–12 kHz". The offer is OtoRead Screener+ with 2–5 kHz fixed protocols, and the brochure licence table shows 1.5–12 kHz only for Standard/Clinical → **Not Comply**.
- Lifecycle: the manufacturer product survey shows "OtoRead Screener Plus" final production 2018 and "OtoRead II" from June 2017, while the bidder gives the year as 2017 → **Clarification Required** for Model Name and Year.
- Quantity: neonatal ear tips for 1,000 procedures; 60+30+10+5 = 105 listed → **Not Comply**.
- Service row restating "Within 48 hours … inclusive of weekends" with no letter → **Clarification Required**. The question asks for a signed statement letter.
