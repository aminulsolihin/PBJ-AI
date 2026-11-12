---
name: evaluate-tech-spec-v3
description: "Universal tender/RFQ technical evaluation: auto-detects every bidder block on any equipment package sheet, checks each response against the bidder's uploaded documents, fills Evaluator's Note / Determination / REFERENCE for all bidders, and generates a clarification-questions sheet."
---

## When to use
- The user asks to evaluate or score bidder compliance on a technical specification sheet for **any** equipment package (OAE, ventilator, patient monitor, ultrasound, X-ray, lab analyser, etc.): "evaluate the tech spec", "evaluate all bidders", "/evaluate-tech-spec-v3".
- The sheet is a requirements matrix: Row no. | Requirement item | Requirement text, followed by one block per bidder (Yes [√] / No [x], Device Details, Source Data, Source Data URL) and that bidder's evaluator columns (Evaluator's Note, Evaluator's Determination, REFERENCE). Bidder names sit in a header row above the blocks.
- It also covers generating clarification questions from an evaluation that already exists ("make the clarification list").

## Inputs
- `sheet`: the package sheet. Default: the active sheet.
- `bidders`: default **all bidder blocks detected**. The user may limit it ("only bidder 2") or give explicit ranges (e.g., `D6:H128 → I5:K128`).
- `supporting files`: each bidder's documents, uploaded into the chat. Reuse files already uploaded earlier in the conversation.

## Goal
1. For every bidder, every evaluable row has an English note, one of the three labels (coloured) and a REFERENCE entry giving the verified file and page (or "File not provided").
2. A sheet named `Clarif - <package sheet>` lists one clarification question per Clarification Required / Not Comply row, for every bidder, linked by formula to the evaluation.
3. The counts per bidder reconcile, and header cells are left as they are.

## Fixed rules
- **Labels:** exactly `Comply`, `Not Comply`, `Clarification Required`.
- **Strict evidence:** `Comply` only when (1) Yes is ticked, (2) the details give concrete values/features that meet or beat the requirement, and (3) **an uploaded document actually contains the claim on the cited page**. Placeholders (`Enter Responses Here!`), blanks, or a ticked No = missing.
- **Write only** into each bidder's evaluator columns and the new clarification sheet. Never edit bidder response columns, spec columns, or other sheets (REKAP, Teknis, etc.) unless asked.
- **Keep the header cells** (e.g., "EVALUATOR'S REMARK'S", "Evaluator's Note") and start writing at the first data row.
- **REFERENCE** = the evidence *you verified*: `<file name> – p.<printed page> (<section/table>)`, or `File not provided – <document the bidder cited>`.
- **Don't open external URLs** (Drive links, websites) unless the user explicitly asks. Judge only the sheet and the uploaded files.
- **Keep each bidder's documents separate.** Never use one bidder's files as evidence for another bidder.
- **Language:** English notes and questions, even when bidder responses or documents are in Bahasa Indonesia (translate when quoting).
- **Procurement fairness:** clarification questions must ask the bidder to *clarify or evidence what they already offered*. They must not invite a change to the offer's substance, price or model.

## Steps

### 1. Auto-detect the layout (no hardcoded columns)
- Read the used range of `sheet` in chunks (get_range_as_csv ≤100 rows, or execute_office_js returning trimmed strings). Never dump it all into chat.
- Find the **spec columns**: the header row containing "Row no." / "REQUIREMENTS" (typically A = Row no., B = item, C = requirement).
- Find the **bidder blocks**: scan the header rows for "BIDDER RESPONSE" and "EVALUATOR'S REMARK'S" (or "Evaluator's Note" / "Evaluator's Determination" / "REFERENCE"). Each BIDDER RESPONSE span plus the evaluator span after it is one bidder. Take the bidder name from the row above (the merged company-name cell).
- **Column meanings can change between sections.** Each section usually has its own sub-header row ("Yes [√] | No [x] | Device Details | Source Data | Source Data URL"). Re-map the tick/details/source/URL columns for every section from its own sub-header. (Example: in the first "Proposed Device Information" section, details are in the first response column with no tick columns.)
- Classify rows: **section header** (requirement col = "REQUIREMENTS", or a group title with a blank requirement) → skip; **sub-header** → re-map and skip; **note row** ("Unless otherwise stated… minimum performance requirements") → apply as a rule; **N/A row** (requirement "N/A") → Note `N/A – not evaluated.` only; **evaluable** → everything else.
- Check every evaluator range for existing content below the headers. If any exists, show the count and a sample and ask before overwriting.
- Identify the **offered brand/model per bidder** (Brand/Model rows). It's needed for the model-mismatch check.
**Done when:** you can state, per bidder: name, offered model, response columns, evaluator columns, and the evaluable row count.
**Produces:** a bidder map `{name, model, responseCols per section, noteCol, detCol, refCol}`.

### 2. Confirm the map and request documents (pause)
- Per bidder, list the distinct documents cited in Source Data (grouped by name/URL: brochure, registration licence (NIE/AKL, FDA, CE), technical/user manual, spec sheet, test reports/images, clinical study, statement letters, training plan, installation checklist, installation base, software screenshot).
- In one message: show the bidder map (name → columns) and the document list per bidder, and ask the user to upload the files **one bidder per message, or with the bidder name in the file name**. Note that you can't browse their local folders. Suggest uploading the technical/user manual and the spec sheet first if they don't want to upload everything. **End the turn and wait.**
- If a file's ownership is unclear, match it by brand/model/company letterhead in its content. If it's still unclear, ask.
**Done when:** each bidder's files are uploaded and assigned, or the user says to proceed without some (those rows get "File not provided").

### 3. Extract the documents (per bidder)
- code_execution: `pdfplumber` for text PDFs, `python-docx` (paragraphs and tables) for .docx. **Scanned PDFs with no text** → `pdf2image` + `pytesseract` (eng; Indonesian text OCRs acceptably with eng). Read images uploaded in chat visually.
- Store `texts[bidder][file] = [page texts]`. For each requirement, derive keywords from the item and requirement text (the parameter name, units, key nouns) and grep with ±200-char snippets. Print only snippets.
- Check the **printed page number** vs the PDF index, and cite the printed one.
- Write a short fact list per document into your response text (key values + pages), because the raw extracts are large.
**Done when:** for every cited document you know whether it was uploaded and where the relevant values are.

### 4. Evaluate each row (per bidder)
Requirement logic:
- **Thresholds** (≥, ≤, minimum, within X h): compare after converting units (Hz/kHz, g/kg, mm/cm, h/min, V, W, dB).
- **Ranges** ("1.5–12 kHz"): the device range must cover the whole required range.
- **Single values / unit references** (e.g., dB SPL vs dB peSPL, V AC vs V DC): mismatch or ambiguity → `Clarification Required`.
- **Multi-part requirements** (a/b lists, voltage + plug type, per-unit sets): every part must be evidenced. A missing part → `Not Comply`, naming it.
- **Quantities** (per unit, kit for N procedures, spare sets): do the arithmetic. Short or unstated → `Not Comply`. Use `Clarification Required` only if another sheet (e.g., "Proposed Consumables") may hold the number.
- **"Bidder to specify/provide"**: a specific answer plus verified evidence → `Comply`. Generic text → `Clarification Required`. Blank → `Not Comply`.
- **"If applicable / if offered / if any"**: an explicit No/N/A with justification → `Comply`. Blank → `Not Comply`.
- **Ticked No** on a "Required" row → `Not Comply`.

Evidence checks (apply to every package):
- **The cited page doesn't contain the claim** → `Not Comply`: "Claim not supported by the cited document."
- **The document is for a different model/brand** than the one offered → `Clarification Required`, naming the mismatch.
- **Bidder-prepared spec sheet vs manufacturer document**: the manufacturer document prevails. A conflict → `Clarification Required`, stating both values.
- **Blank templates** (empty checklists, blank minutes/BA forms) show a procedure exists, not the specific requirement → `Clarification Required`.
- **Signed bidder statement letters** are acceptable for service commitments (warranty, PM frequency, response/turnaround times, uptime, spare parts, training, manuals, software upgrades) if they state the required figure. If the Device Details omit the figure but the letter states it → `Comply`, and say so.
- **Undocumented features** (modes, alarms, pause, encryption, anti-malware, port disabling, telemedicine): the claim alone → `Not Comply`.
- **Software/firmware version proof** via a screenshot of PC/companion software rather than the device → `Clarification Required`.
- **Environmental requirements**: the site range must fall inside the device's operating range from the manual. A bidder who just restates the site range → `Clarification Required` unless the manual confirms it.
- **Regulatory approval**: check the licence names the offered brand/model/type and is valid (expiry date). Note the number and expiry.
**Done when:** every evaluable row has a determination, a note and a reference for each bidder.

### 5. Write the evaluation (per bidder, per section)
- Note format (1–2 sentences): `Required <X>; offered <Y> – <reason>. <evidence comment>.`
- Write Note/Determination/REFERENCE with execute_office_js or set_cell_range, **one call per section per bidder**, so progress is visible. Finish bidder 1, then bidder 2, and so on.
- Colour Determination cells: Comply #C6EFCE / font #006100; Not Comply #FFC7CE / #9C0006; Clarification Required #FFEB9C / #9C5700; bold and centred. Set wrap text and top alignment on the Note and REFERENCE columns. Don't change row heights or column widths unless asked.
**Done when:** all writes have landed without errors.

### 6. Generate the clarification-questions sheet
- Create (or, after confirming, replace) a sheet `Clarif - <package sheet>` (≤31 characters), placed after the package sheet.
- Row 1: a title (`Clarification Questions – <package title>`). Header row 3:
  `No | Bidder | Row no. | Requirement Item | Requirement | Determination | Issue Found | Clarification Question | Document / Evidence Requested | Bidder Reply | Evaluator Follow-up`
- One row per Clarification Required **and** Not Comply row, grouped by bidder, then by Row no.
- **Link by formula** to the package sheet so the list stays traceable: Bidder `='<sheet>'!<name cell>`, Row no. `='<sheet>'!A<r>`, Requirement Item `='<sheet>'!B<r>`, Requirement `='<sheet>'!C<r>`, Determination `='<sheet>'!<detCol><r>`. No = `=ROW()-3` or a running count. Issue Found and Clarification Question are authored text. Leave Bidder Reply and Evaluator Follow-up blank, as inputs for the user.
- Question style: specific, neutral, and pointing to the evidence needed. For example:
  - "Please confirm the battery charger rating (input voltage/frequency) and plug type of the offered model, and indicate the page of the manufacturer document where this is stated."
  - "The clinical study submitted refers to model <X>, while the offered model is <Y>. Please clarify whether the study applies to the offered model, or provide model-specific evidence."
  - Never ask "Would you like to change…" or invite a new model or price.
- Format: bold header with fill #D9E1F2, wrap text, top alignment, freeze panes below the header (freezeRows(3)), and reasonable column widths for the text columns.
**Done when:** the row count on the sheet equals the total Not Comply + Clarification Required across bidders, and the linked formulas return no errors.

### 7. Verify and report
- Re-read each bidder's evaluator columns. Check that no evaluable row has a blank note, that Determination contains only the three labels, and that the counts add up to the evaluable count per bidder. Re-read the clarification sheet: formula_results have no #REF!/#VALUE!, and the row count matches. Render one small sample per output with getImage.
- Report in chat, kept brief: a table of counts per bidder (Comply / Not Comply / Clarification), the 3–5 key Not Comply items per bidder (Row no. + reason), cross-bidder observations (e.g., both fail Row no. X), documents not provided, and the location of the clarification sheet. State what you re-read, and that external links were not opened.
**Done when:** the counts reconcile for every bidder and the report is posted.

## Examples (illustrative, OAE package)
- "Frequency Range | Required; 1.5 – 12 kHz". Bidder A offers 0.5–12 kHz, confirmed in the manual p.76 → **Comply**; REFERENCE `aScreen_TM_002.004.pdf – p.76 (Annex 1, Table 2)`. Bidder B offers 2–5 kHz → **Not Comply** ("does not cover 1.5–2 kHz or 5–12 kHz").
- "Battery charger, 230 V ±10 %, Type F plug", citing a manual EMC table → **Not Comply**: "Cited page is an EMC immunity table; no charger rating or plug type in any document." Clarification question: "Please confirm the charger input rating and plug type, and indicate the supporting manufacturer document and page."
- "Referral rate ≤4 %", supported by a clinical study of a different model → **Clarification Required**: "Study refers to Neuro-Audio-Screen, not the offered aScreen; it reports sensitivity/specificity, not a referral rate."
