---
name: evaluate-tech-spec-v4
description: "Universal tender/RFQ technical evaluation: auto-detects every bidder block on any equipment package sheet, checks responses against each bidder's uploaded documents, fills Evaluator's Note / Determination / REFERENCE, and generates one downloadable AMPC Technical Clarification file per bidder from the user's template."
---

## When to use
- The user asks to evaluate or score bidder compliance on a technical specification sheet for **any** equipment package (OAE, ventilator, patient monitor, ultrasound, X-ray, lab analyser, etc.): "evaluate the tech spec", "evaluate all bidders", "/evaluate-tech-spec-v4".
- The user asks to generate clarification files ("make the clarification file", "generate AMPC clarification", "clarification for Not Comply / Clarification Required"). This works from an evaluation already in the sheet, so the evaluation steps can be skipped.
- The sheet is a requirements matrix: Row no. | Requirement item | Requirement text, followed by one block per bidder (Yes [√] / No [x], Device Details, Source Data, Source Data URL) and that bidder's evaluator columns (Evaluator's Note, Evaluator's Determination, REFERENCE). Bidder names sit in a header row above the blocks.

## Inputs
- `sheet`: the package sheet. Default: the active sheet.
- `bidders`: default **all bidder blocks detected**. The user may limit it ("only bidder 2") or give explicit ranges (e.g., `D6:H128 → I5:K128`).
- `supporting files`: each bidder's documents, uploaded into the chat. Reuse files already uploaded earlier in the conversation.
- `clarification template`: the **AMPC Technical Clarification** .xlsx, uploaded into the chat. Skills can't store files, so ask for it each conversation if it isn't already uploaded.

## Goal
1. For every bidder evaluated, every evaluable row has an English note, one of the three labels (coloured) and a REFERENCE entry giving the verified file and page (or "File not provided").
2. For every bidder evaluated, a downloadable file `Technical Clarification - <package> - <bidder>.xlsx` built from the AMPC template, listing every Not Comply and Clarification Required row.
3. The counts per bidder reconcile, and header cells in the package sheet are left as they are.

## Fixed rules
- **Labels:** exactly `Comply`, `Not Comply`, `Clarification Required`.
- **Strict evidence:** `Comply` only when (1) Yes is ticked, (2) the details give concrete values/features that meet or beat the requirement, and (3) **an uploaded document actually contains the claim on the cited page**. Placeholders (`Enter Responses Here!`), blanks, or a ticked No = missing.
- **Write only** into each bidder's evaluator columns. Never edit bidder response columns, spec columns, or other sheets (REKAP, Teknis, etc.) unless asked. Clarification output goes into separate files, not the workbook.
- **Keep the header cells** (e.g., "EVALUATOR'S REMARK'S", "Evaluator's Note") and start writing at the first data row.
- **REFERENCE** = the evidence *you verified*: `<file name> – p.<printed page> (<section/table>)`, or `File not provided – <document the bidder cited>`.
- **Don't open external URLs** (Drive links, websites) unless the user explicitly asks. Judge only the sheet and the uploaded files. In bidder-facing text, say "was not available for verification", not "not provided by you".
- **Keep each bidder's documents separate.** Never use one bidder's files as evidence for another bidder.
- **Language:** English notes and questions, even when bidder responses or documents are in Bahasa Indonesia (translate when quoting). In bidder-facing files, write abbreviations out in full ("Technical Manual", not "TM").
- **Procurement fairness:** clarification questions ask the bidder to *clarify or evidence what they already offered*. They must not invite a change to the offer's substance, price or model.
- **Only bidders that have been evaluated get a clarification file.** If a bidder's Determination column is empty, say so and offer to evaluate them first.

## Steps

### 1. Auto-detect the layout (no hardcoded columns)
- Read the used range of `sheet` in chunks (get_range_as_csv ≤100 rows, or execute_office_js returning trimmed strings). Never dump it all into chat.
- Find the **spec columns**: the header row containing "Row no." / "REQUIREMENTS" (typically A = Row no., B = item, C = requirement).
- Find the **bidder blocks**: scan the header rows for "BIDDER RESPONSE" and "EVALUATOR'S REMARK'S" (or "Evaluator's Note" / "Evaluator's Determination" / "REFERENCE"). Each BIDDER RESPONSE span plus the evaluator span after it is one bidder. Take the bidder name from the row above (the merged company-name cell).
- **Column meanings can change between sections.** Each section usually has its own sub-header row ("Yes [√] | No [x] | Device Details | Source Data | Source Data URL"). Re-map per section. (Example: in "Proposed Device Information", details are in the first response column with no tick columns.)
- Classify rows: **section header** → skip; **sub-header** → re-map and skip; **note row** ("Unless otherwise stated… minimum performance requirements") → apply as a rule; **N/A row** → Note `N/A – not evaluated.` only; **evaluable** → everything else.
- Check every evaluator range for existing content below the headers. If any exists, show the count and a sample and ask before overwriting. (If the user only wants clarification files, existing determinations are the input; don't overwrite them.)
- Identify the **offered brand/model per bidder** (Brand/Model rows). It's needed for the model-mismatch check and the clarification header.
**Done when:** per bidder you can state the name, offered model, response columns, evaluator columns, and the evaluable row count.
**Produces:** a bidder map `{name, model, responseCols per section, noteCol, detCol, refCol}`.

### 2. Confirm the map and request files (pause)
- Per bidder, list the distinct documents cited in Source Data (brochure, registration licence (NIE/AKL, FDA, CE), technical/user manual, spec sheet, test reports/images, clinical study, statement letters, training plan, installation checklist, installation base, software screenshot).
- In one message: show the bidder map and the document list per bidder. Ask the user to upload the files **one bidder per message, or with the bidder name in the file name**, and to upload the **AMPC Technical Clarification template** if it isn't already in the chat. Note that you can't browse their local folders. **End the turn and wait.**
- If a file's ownership is unclear, match it by brand/model/company letterhead in its content. If it's still unclear, ask.
**Done when:** files are uploaded and assigned, or the user says to proceed without some (those rows get "File not provided").

### 3. Extract the documents (per bidder)
- code_execution: set `base = os.environ.get('INPUT_DIR','/files/input')` and find files with glob (re-define it in every new session). Use `pdfplumber` for text PDFs and `python-docx` (paragraphs and tables) for .docx. **Scanned PDFs with no text** → `pdf2image` + `pytesseract` (eng). Read images uploaded in chat visually.
- Store `texts[bidder][file] = [page texts]`. Derive keywords from each requirement (the parameter name, units, key nouns) and grep with ±200-char snippets. Print only snippets.
- Cite the **printed page number** where it differs from the PDF index.
- Write a short fact list per document into your response text (key values + pages).
**Done when:** for every cited document you know whether it was uploaded and where the relevant values are.

### 4. Evaluate each row (per bidder)
Requirement logic:
- **Thresholds** (≥, ≤, minimum, within X h): compare after converting units.
- **Ranges**: the device range must cover the whole required range.
- **Single values / unit references** (dB SPL vs dB peSPL, V AC vs V DC): mismatch → `Clarification Required`.
- **Multi-part** (a/b lists, voltage + plug, per-unit sets): every part must be evidenced. A missing part → `Not Comply`.
- **Quantities**: do the arithmetic (e.g., 105 ear tips vs a kit for 1,000 procedures → `Not Comply`).
- **"Bidder to specify/provide"**: a specific answer plus verified evidence → `Comply`. Generic → `Clarification Required`. Blank → `Not Comply`.
- **"If applicable / if offered"**: an explicit No/N/A with justification → `Comply`. Blank → `Not Comply`.
- **Ticked No** on a "Required" row → `Not Comply`.

Evidence checks:
- **The cited page doesn't contain the claim** → `Not Comply` ("Claim not supported by the cited document").
- **The document is for a different model/brand** → `Clarification Required`.
- **Manufacturer document vs bidder-prepared spec sheet**: the manufacturer document prevails. A conflict → `Clarification Required`.
- **Blank templates** (empty checklists, blank minutes/BA forms) → `Clarification Required`.
- **Signed statement letters** are OK for service commitments (warranty, PM, response times, uptime, spare parts, training, manuals, upgrades) if they state the figure.
- **Undocumented features** (modes, alarms, pause, encryption, anti-malware, port disabling, telemedicine) → `Not Comply`.
- **Software version proof** that is a PC/companion-software screenshot → `Clarification Required`.
- **Environmental requirements**: the site range must fall inside the device's operating range from the manual.
- **Regulatory approval**: the licence must name the offered model and be valid; note the number and expiry.
**Done when:** every evaluable row has a determination, a note and a reference for each bidder.

### 5. Write the evaluation (per bidder, per section)
- Note format: `Required <X>; offered <Y> – <reason>. <evidence comment>.`
- Write one call per section per bidder. Colour Determination: Comply #C6EFCE/#006100; Not Comply #FFC7CE/#9C0006; Clarification Required #FFEB9C/#9C5700; bold and centred. Set wrap text and top alignment on Note/REFERENCE. Don't change row heights or column widths.
**Done when:** all writes have landed without errors.

### 6. Generate the AMPC Technical Clarification file (one per bidder)
**6a. Collect the flagged rows.** Use execute_office_js to read, for each bidder, every row whose Determination is `Not Comply` or `Clarification Required`: Row no., item, **full** requirement text, tick (Yes/No/none), **full** Device Details, Source Data, URL, Note, Determination. Don't truncate the strings; if the payload is large, read in two calls. The Python sandbox can't call Excel tools, so the data has to be passed into code_execution as literals.

**6b. Write a clarification question per row.** It should be specific, neutral and evidence-seeking, and reference the document or page needed. Examples:
- "Please provide the manufacturer document (name and page) specifying the charger input rating (230 ± 10 V AC, 50 Hz) and confirming the Type F plug supplied with the offered device."
- "The clinical study submitted refers to «X», while the offered model is «Y». Please clarify whether it applies to the offered model and provide model-specific evidence of the referral rate."
- For a blank response: "No response was provided. Please state whether <feature> is available on the offered device."

**6c. Inspect the template with openpyxl.** Locate the columns by header text, not by fixed position. The expected AMPC layout:
- Row 4–5 headers: `Row` | `PROPOSED DEVICE INFORMATION` | `Requirements` | **BIDDER CLARIFICATION** (`Bidder Response`, `Supporting documents (Make sure link is Open)`, `PC Assesment`, `Context`) | **AMPC RESPONSE** (`Date`, `Response`).
- Rows 6–7: `Brand/Manufacturer Name`, `Model Name` info rows (C6:C7 and F6:I7 merged).
- Row 8: `[Specs]` style row (item label with green fill); row 9 `[Specs] - Add row if needed`.
If the template differs, map by header names and tell the user how you mapped it.

**6d. Fill a copy of the template** (`openpyxl.load_workbook(template)`). Name the sheet `<package> - <short bidder>` (≤31 characters).
- Rows 1–3: A1 `TECHNICAL CLARIFICATION – <package title>`; A2 `Bidder: <name> | Offered device: <brand model> | Tender No.: <no.>` (from the sheet or the bidder's letters, if available); A3 a short note that the items are the Not Comply / Clarification Required determinations from the technical evaluation.
- Rows 6–7: A = Row no., D = brand and model **as submitted**. If Model Name is flagged, also list it as an item row (the merged F6:I7 leaves no room for an assessment).
- Item rows start at row 8, one per flagged row, in Row no. order. Copy row 8's cell style to each new row, and clear the `[Specs]` placeholder text.

| Template column | Value |
|---|---|
| Row | Row no. |
| Proposed Device Information | Requirement item |
| Requirements | Full requirement text |
| Bidder Response | `[Yes [√] ticked]` / `[No [x] ticked]` + newline + the original Device Details (for a blank: "No response provided (placeholder …; no tick)") |
| Supporting documents | Source Data + newline + URL. Set the cell hyperlink to the URL (blue, underlined) |
| PC Assesment | Determination + newline + finding (the evaluator note, with abbreviations written out); fill #FFC7CE/#9C0006 or #FFEB9C/#9C5700 |
| Context | Clarification question |
| Date, Response (AMPC) | Leave blank |

- Format: thin borders on all cells of rows 6..last, wrap text and top alignment, Row column centred. Estimate row height from text length vs column width (≈12.75 pt per line, min 40, max 409). Freeze panes at B6, landscape, fit to 1 page wide, print titles rows 4:5.
- Save to `/tmp/Technical Clarification - <package> - <bidder>.xlsx`, then copy to `$OUTPUT_DIR` (same tool call or a later one) so it downloads. Never read from OUTPUT_DIR afterwards.

**6e. Verify each file.** Reopen it from /tmp with openpyxl and check: the item row count equals Not Comply + Clarification Required for that bidder, the label counts match the sheet, the template's merged ranges are intact, and no item is missing a question. A LibreOffice PDF render may fail; don't rely on it, and tell the user you couldn't preview the layout.

**Fallback:** if no template is uploaded and the user doesn't want to provide one, create an in-workbook sheet `Clarif - <package sheet>` with columns `No | Bidder | Row no. | Requirement Item | Requirement | Determination | Issue Found | Clarification Question | Document / Evidence Requested | Bidder Reply | Evaluator Follow-up`. Link Bidder/Row no./Item/Requirement/Determination by formula to the package sheet, use a header fill of #D9E1F2, and freezeRows(3).
**Done when:** every evaluated bidder has a file in OUTPUT_DIR whose item count reconciles.

### 7. Verify and report
- Re-read each bidder's evaluator columns: no blank notes on evaluable rows, only the three labels, and counts that add up.
- Report in chat, kept brief: a table of counts per bidder, the 3–5 key Not Comply items per bidder, cross-bidder observations, documents not provided, the clarification file names and the column mapping used. Mention any bidder skipped because it wasn't evaluated. State what you re-read, and that external links were not opened.
**Done when:** the counts reconcile for every bidder and the report is posted.

## Examples (illustrative, OAE package)
- "Frequency Range | Required; 1.5 – 12 kHz". Bidder A offers 0.5–12 kHz, confirmed in the manual p.76 → **Comply**; REFERENCE `aScreen_TM_002.004.pdf – p.76 (Annex 1, Table 2)`. Bidder B offers 2–5 kHz → **Not Comply**.
- "Battery charger, 230 V ±10 %, Type F plug", citing a manual EMC table → **Not Comply**. In the clarification file: PC Assesment = "Not Comply\nCited Technical Manual p.81 is the EMC immunity table; no charger rating or plug type is documented." Context = "Please provide the manufacturer document (name and page) specifying the charger input rating and confirming the Type F plug."
- "Neonatal ear tips for 1,000 procedures"; offered 60+30+10+5 = 105 → **Not Comply**. Context = "The quantities listed total 105 ear tips. Please clarify the total quantity included in the offered starter kit, as stated in your 'Proposed Consumables' sheet."
