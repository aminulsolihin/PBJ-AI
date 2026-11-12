---
name: evaluate-tech-spec-v2
description: Evaluate one bidder's responses on a technical specification / requirements matrix (e.g., medical equipment RFQ) against the bidder's uploaded supporting documents, and fill the Evaluator's Note, Determination (Comply / Not Comply / Clarification Required) and REFERENCE columns.
---

## When to use
- The user asks to evaluate, assess or score a bidder's compliance on a tender/RFQ technical sheet ("evaluate the tech spec", "evaluate D6:H128 and put it in I5:K128", "/evaluate-tech-spec-v2").
- The sheet is a requirements matrix: Row no. | Requirement item | Requirement text, then one block per bidder (Yes [√] / No [x], Device Details, Source Data, Source Data URL), then that bidder's evaluator columns (Evaluator's Note, Evaluator's Determination, REFERENCE).
- Example layout (OAE sheet): spec in A:C; Bidder 1 (row 4 name) response D:H → evaluator I (Note), J (Determination), K (REFERENCE); Bidder 2 response M:Q → R, S, T. Header rows 5–6, data from row 7. Sheet row = Row no. + 5.

## Inputs
- `bidder_range`: the bidder response block (e.g., `D6:H128`). Default: ask, or use the first bidder block.
- `output_range`: the evaluator block (e.g., `I5:K128`). Default: the three columns right after the bidder block.
- `supporting files`: the bidder's documents, uploaded by the user into the chat.
- Evaluate **one bidder per run** unless the user asks for more.

## Goal
Every evaluable row in the output range has an English note, one of the three labels (coloured), and a REFERENCE entry naming the uploaded file and page that was checked (or "File not provided"). Header cells are left as they are, and the counts reconcile.

## Fixed rules
- **Labels:** exactly `Comply`, `Not Comply`, `Clarification Required`.
- **Strict evidence:** `Comply` only when (1) Yes is ticked, (2) Device Details gives concrete values/features that meet or beat the requirement, and (3) **the uploaded document actually contains the claim on the cited page**. Placeholders (`Enter Responses Here!`), blanks, or a ticked No = missing.
- **Write only into the output range.** Do not edit the bidder columns or other bidders' blocks. Keep the existing header cells (e.g., I5 "EVALUATOR'S REMARK'S", I6:K6 sub-headers) and start writing at the first data row.
- **REFERENCE column** = the evidence *you verified*: `<uploaded file name> – p.<page> (<section/table>)`. Use `File not provided – <document cited by bidder>` when the bidder cited a file that wasn't uploaded.
- **Don't open external URLs** (Google Drive links etc.). Judge only the sheet and the uploaded files.
- **Language:** English.

## Steps

### 1. Map the sheet and the bidder block
- Read the spec columns and the `bidder_range` (get_range_as_csv in chunks, or execute_office_js returning trimmed strings; never dump everything into chat).
- Identify the bidder name (header row above the block), the tick/details/source/URL columns, and the output columns.
- Classify rows: **section header** (col C = "REQUIREMENTS", or a group title with blank requirement) → skip; **sub-header** ("Yes [√] / No [x]") → skip; **note row** ("Unless otherwise stated… minimum performance requirements") → apply as a rule; **N/A row** → write `N/A – not evaluated.` in Note only; **evaluable** → everything else.
- Check the output range for existing content other than headers. If any exists, ask before overwriting.
**Done when:** you can state the bidder name, the column letters, and the evaluable row count.

### 2. Ask for the supporting documents
- Build a list of the distinct documents the bidder cites in Source Data (group by URL/name, e.g., Brochure, NIE/AKL, Technical Manual, Spec sheet, Patient Record images, Clinical study, Statement Letters, Training Rundown, Installation Check, Installation Base, Software screenshot).
- Ask the user to upload them in chat (you cannot browse their local folders). Suggest the Technical Manual and spec sheet first if they don't want to upload everything. Then **end the turn and wait**.
**Done when:** the files are uploaded, or the user says to proceed without some of them (those rows get "File not provided").

### 3. Extract the documents
- Use code_execution: `pdfplumber` for text PDFs, `python-docx` (paragraphs and tables) for .docx. For **scanned PDFs with no text**, OCR them with `pdf2image` + `pytesseract` (eng). Images uploaded in chat can be read visually.
- Keep the text per page in a dict, then grep keywords for each requirement (e.g., calibrat, pause, alternat, memory, Bluetooth, USB, encrypt, password, temperature, humidity, alcohol, charger, plug). Note that the PDF page index can differ from the printed page number; cite the printed number when they differ.
- Print only short snippets (±200 chars). Record the key facts per document in your response text, because the raw extracts are large.
**Done when:** for every cited document you know whether it was uploaded and which pages hold the relevant values.

### 4. Evaluate each row
Apply the requirement logic:
- **Thresholds** (≥, ≤, within X h): compare numbers after converting units.
- **Ranges** ("1.5–12 kHz"): the device range must cover the whole required range.
- **Single values / units**: unit or reference mismatch (dB SPL vs dB peSPL) → `Clarification Required`.
- **Multi-part** (a/b, voltage + plug type, per-unit quantities): every part must be evidenced. A missing part → `Not Comply`, naming that part.
- **Quantities**: do the arithmetic (e.g., 105 ear tips vs a kit for 1,000 procedures → `Not Comply`).
- **"Bidder to specify/provide"**: a specific answer plus a verified source → `Comply`. Generic text → `Clarification Required`. Blank → `Not Comply`.
- **"If applicable/if offered"**: an explicit "No/N/A" with justification → `Comply`. Blank → `Not Comply` (strict).

Evidence checks learned in practice:
- **The cited page doesn't contain the claim** (e.g., a ">10,000 tests" claim citing a manual that only says "memory is limited"; a charger/Type F plug claim citing an EMC table) → `Not Comply`, with the note "Claim not supported by the cited document".
- **The document is for a different model** (e.g., a clinical study or brochure for "Neuro-Audio-Screen" when the offer is "aScreen") → `Clarification Required`, naming the mismatch.
- **Bidder-prepared spec sheet vs manufacturer manual**: the manufacturer document prevails. If they conflict (e.g., the spec sheet says "Bluetooth, USB" and the manual says Bluetooth only), say so; mark `Clarification Required` unless another manufacturer source settles it.
- **Blank templates** (empty check sheets, empty BA/training forms) prove a procedure exists, not the specific requirement (e.g., an electrical safety test or training duration). Partial → `Clarification Required`.
- **Signed statement letters** from the bidder are acceptable evidence for service commitments (warranty, PM frequency, response times, uptime, spare parts, training, manuals) if they state the required figure. If the Device Details omit the figure but the letter states it, it's `Comply`; say so in the note.
- **Features that aren't documented** (alternating mode, auto pause, encryption, anti-malware, port disabling): the claim alone isn't enough → `Not Comply`.
- **Screenshot of PC/manager software** offered as proof of device firmware version → `Clarification Required`.
- **Environmental ranges**: compare the device's operating range from the manual with the site range (e.g., 22–32 °C and 50–80 % RH inside +10–35 °C and 30–85 % → `Comply`). Don't accept a bidder who just restates the site range.
**Done when:** every evaluable row has a determination, a note and a reference.

### 5. Write the results
- Note format (1–2 sentences): `Required <X>; offered <Y> – <reason>. <evidence comment>.`
- Write I/J/K in batches by section (execute_office_js or set_cell_range), one call per spec section, so progress is visible.
- Colour J: Comply #C6EFCE / font #006100; Not Comply #FFC7CE / #9C0006; Clarification Required #FFEB9C / #9C5700; bold and centred. Set wrap text and top alignment on I and K. Don't change row heights unless asked.
**Done when:** the writes have landed without errors.

### 6. Verify and report
- Re-read the output range. Check that no evaluable row has a blank note, that J contains only the three labels, and that the counts per label add up to the evaluable count. Render a small sample with getImage to check the formatting.
- Report in chat: bidder name, counts per label, the main Not Comply items (Row no. + reason), the key clarification points (model mismatches, unit mismatches), and which cited files were not provided. State what you re-read, and that Drive links were not opened.
**Done when:** the counts reconcile and the report is posted.

## Example
Row no. 32 "Frequency Range | Required; 1.5 – 12 kHz":
- Bidder offers 0.5–12 kHz; the TM p.76 Annex 1 Table 2 confirms it → **Comply**. Note: "Required 1.5–12 kHz; offered 0.5–12 kHz – covers the range. Verified in TM." REFERENCE: `aScreen_TM_002.004.pdf – p.76 (Annex 1, Table 2)`.
- Row no. 74 charger with Type F plug, citing TM p.81 → **Not Comply**. Note: "Cited p.81 is an EMC immunity table; no charger rating or Type F plug in any document." REFERENCE: `aScreen_TM_002.004.pdf – p.81 (Annex 3) – claim not found`.
