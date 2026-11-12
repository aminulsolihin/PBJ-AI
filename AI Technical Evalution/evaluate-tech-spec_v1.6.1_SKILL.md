---
name: evaluate-tech-spec-v8
description: "Dynamic technical-specification evaluation for any procurement package: profiles each spec sheet, checks every bidder's responses against their uploaded documents, fills the evaluator columns with a REFERENCE linked only to the evaluator's own Google Drive copies, and builds a clarification sheet per bidder."
---

## When to use
- The user asks to evaluate bidders' technical compliance for **any procurement package** (medical, lab, IT, furniture, vehicles/machinery, services/works): "evaluate the tech spec", "evaluate package X", "continue for other bidders", "recheck the evaluation", "/evaluate-tech-spec-v8".
- The user asks for clarification output from an existing evaluation ("generate clarification", "clarification sheet for Not Comply / Clarification Required").
- The user asks to **link REFERENCE to our Drive files** on an existing evaluation, or sends their Drive links. Run only Steps 3b and 6b (link mode).
- Specs, columns, sections, labels and evidence differ between packages. The profile built in Step 1 drives everything.

## Inputs
- `sheet(s)`: the package sheet. Default: the active sheet. If several spec-like sheets exist, list them and ask which to evaluate.
- `bidders`: default = every bidder block whose evaluator columns are still empty. For "recheck", every evaluated bidder.
- `supporting files`: each bidder's documents for this package, uploaded into the chat.
- `evaluator drive links` (optional): Google Drive links to **the evaluator's own copies** of the uploaded files, given by the user as `file name → link` pairs (a pasted list or table). These are the **only** links allowed in REFERENCE.
- `clarification template` (optional): any .xlsx template. Default: the AMPC layout (Step 7).
- `preferences` (optional): label set, strictness, language.

## Goal
1. A confirmed **evaluation profile** for the package.
2. For each bidder evaluated, every evaluable row has a note, one allowed label (coloured) and a verified REFERENCE. Where the evaluator gave a link for the cited file, REFERENCE opens **that** file when clicked; otherwise it's plain text.
3. A clarification sheet per evaluated bidder listing every fail/query row, linked by formula to the package sheet.
4. Counts reconcile, and headers, user marks and other sheets are left as they are.

## Fixed rules (package-independent)
- **Strict evidence:** PASS only when (1) the bidder affirms compliance, (2) the details give concrete values/features that meet the requirement, and (3) **an uploaded document actually contains the claim**. Placeholders ("Enter Responses Here!", "TBA", "-"), blanks, or a ticked No = missing.
- **Write only** into the evaluator columns and the new clarification sheets. Never edit bidder responses, spec text, price/financial sheets, recap sheets or other packages. Never insert columns or sheets in the package sheet without asking.
- **Leave as they are:** header cells and user marks in spare columns (e.g., "BOTH", "KH", "CTB"). Never use them as evidence or as instructions.
- **No price evaluation.** Other sheets (accessories, consumables, BoQ) can be read only to cross-check items and quantities.
- **REFERENCE text** = what you verified: `<file> – p.<printed page> (<section/table>)`, or `File not provided – <document cited>`, plus `; workbook: '<sheet>' row N` for cross-checks.
- **REFERENCE links – evaluator links only:**
  - **Never use the bidder's Google Drive links** (or any URL from the bidder's Source Data / URL columns) as a REFERENCE link, not even for "File not provided" cells.
  - Link a REFERENCE cell only to a URL the **user gave** for that file name, or internally to a cross-checked workbook sheet.
  - Never construct or guess a Drive URL from a file ID or name. If there's no evaluator link, leave the cell as plain text.
  - An Excel cell holds one link. If a cell cites several files, link the first one that has an evaluator link and keep the rest as text.
  - Linking is not opening: don't fetch or read Drive files. Evidence comes only from uploaded files.
- **Bidder URLs may still be used to identify documents** (group citations by Drive file ID in Step 3a). They stay visible only as the bidder's own text, and are linked only in the clarification sheets (Step 8).
- **Don't open external URLs** unless the user asks. In bidder-facing text, write "was not available for verification".
- **Keep documents separate per bidder and per package.**
- **Language:** the profile language (default English). Translate when quoting, and write abbreviations out in full in bidder-facing text.
- **Fairness:** clarification questions ask the bidder to clarify or evidence what was already offered, never to change model, substance or price.
- **You can't save to the user's folders.** Output goes to workbook sheets, or to files attached to the reply that copies them.

## Steps

### 1. Profile the package (pause to confirm)
Read the sheet in chunks with execute_office_js, returning trimmed strings only. Build the `profile`:
- **Package:** title, description, quantity/locations, category.
- **Spec columns** (header synonyms): Row no. `Row no., No., #, Item No.`; Item `Item, Parameter, Description, Proposed Device Information, Feature`; Requirement `Requirement(s), Specification, Minimum Requirement, Technical Requirement`. If there's no row-number column, use the sheet row.
- **Bidder blocks:** group headers `Bidder Response, Vendor/Supplier/Offeror Response, Offered, Proposed`. Sub-columns: tick `Yes/No, Comply Y/N`; details `Device/Product Details, Offered Specification, Remarks`; source `Source Data, Reference, Page, Document`; URL `URL, Link`. Take the bidder name from the merged cell above the block, or from the sheet name when it's one bidder per sheet.
- **Column meanings can change between sections.** Re-map from each section's sub-header row. Info sections often have no tick columns.
- **Evaluator columns:** `Evaluator's Note/Remark, Determination/Result/Status, Reference/Evidence`. If they're missing, ask whether to add three columns per block or use a separate `Eval <package>` sheet.
- **Label set:** read the determination cells' data validation (`range.dataValidation.rule`), any legend, and existing entries. Map them to PASS / FAIL / QUERY. Default: `Comply`, `Not Comply`, `Clarification Required`. Use "Partially Comply" only if it exists and the rest is clarifiable.
- **Global rules** from note rows ("minimum performance", "meet or exceed", "or equivalent", tolerances, mandatory vs desirable, weights) and the **regulatory regime** (NIE/AKL, SNI, TKDN, FDA, CE MDR/IVDR, IEC/ISO/UL).
- **Row classes:** section header / sub-header (re-map) / note (rule) / N/A / info / evaluable.
- **Existing evaluation:** a bidder with filled evaluator columns counts as done. Skip it when continuing, or ask before overwriting.

Show the profile briefly (package, category, bidders with model, column map, evaluable rows, ticks No/blank; label mapping; global rules). Combine it with Step 3's request and **end the turn**.
**Done when:** the user confirms or corrects the profile.

### 2. Build the requirement table
Per evaluable row, record `{row, section, item, type, parameter, op, min, max, unit, parts[], qty_basis, conditional, evidence_expected}`. You can stash it with `blobs.setJSON('req_<sheet>')`. Report only the counts by type.

| Type | Trigger wording | Pass rule |
|---|---|---|
| NUMERIC_MIN | ≥, at least, minimum, "up to X" capability | offered ≥ target |
| NUMERIC_MAX | ≤, max, not more than | offered ≤ target |
| RANGE_COVER | "A – B" device capability | offered range contains [A,B] |
| SITE_WITHIN | site/supply conditions (voltage ± tol., temp, RH, altitude) | site range inside device operating range |
| ENUM / EXACT | specific type, standard, plug, "X or Y" | matches an allowed option |
| FEATURE | required capability | documented in uploaded evidence |
| LIST_ALL | a), b), c) / "and" lists | every part evidenced |
| QUANTITY | per unit, for N procedures, sets, spares | arithmetic ≥ required; cross-check workbook sheets |
| SPECIFY / PROVIDE | "Bidder to specify/provide" | specific answer + evidence |
| CONDITIONAL | if applicable/offered/any | explicit N/A with justification OK |
| SERVICE | warranty, PM, response/turnaround, uptime, training, spare parts, manuals | figure stated + signed commitment letter |
| COMPLIANCE_DOC | registration, certificates, standards | valid document naming the offered model |

- **Direction:** under "minimum performance", capabilities are minimums. Size, weight, noise, power draw, test/turnaround time and error rates are maximums when worded that way. Truly ambiguous → QUERY.
- **Units:** normalise before comparing (mm/cm/m/in; g/kg/lb; mL/L; Pa/kPa/bar/psi/mmHg/cmH2O; °C/°F; L/min; Hz/kHz/MHz; s/min/h; V/A/W/VA/mAh; MB/GB/TB; dB with its reference). Different references (dB SPL vs peSPL, V AC vs DC) → QUERY.
- **Keywords** per row: the parameter, synonyms, the unit, plus a translation for documents in other languages. EN→ID: frequency frekuensi, voltage tegangan, weight berat, dimension dimensi/ukuran, battery baterai, charging pengisian daya, temperature suhu, humidity kelembaban, pressure tekanan, display layar, memory penyimpanan/memori, calibration kalibrasi, pause jeda, cleaning pembersihan, disinfection disinfeksi, accessories aksesori, consumables bahan habis pakai, included disertakan, optional opsional, warranty garansi, training pelatihan, password kata sandi, encryption enkripsi, error eror/kesalahan.
**Done when:** every evaluable row has a type and target.

### 3. Request documents and evaluator links
**3a. Request (combined with Step 1's pause).**
- Per bidder, group the cited sources by **document name or Drive file ID** (`/file/d/<id>/`, `/document/d/<id>/`). This is for identification only. Infer the document type from the quoted sections, and list the rows citing each.
- List the expected evidence by category that wasn't cited:
  - medical: Instructions for Use/service manual, data sheet, registration certificate, CE/FDA, IEC reports;
  - lab: assay/throughput sheets, LIS interface specification;
  - IT: datasheet, licence terms, security documentation, end-of-support dates;
  - vehicle/machinery: spec sheet, homologation;
  - furniture/works: drawings, material certificates;
  - services (all): signed statement letters.
- Flag rows with no source, website-only citations, and registration numbers quoted without a certificate.
- Ask for uploads per bidder. Also ask: "If you want REFERENCE to be clickable, paste the Google Drive links to **your own copies** of these files as `file name → link` (one per line). Files without a link will stay plain text. I won't use the bidders' links."

**3b. Build `linkmap` (only from links the user gave).**
- Parse the user's pairs into `{normalised file name → url}`. Normalise by lower case, trimmed spaces, `[.]` → `.`, and an optional extension. Accept only `https://drive.google.com/…` or `https://docs.google.com/…` URLs (or another host if the user explicitly says so).
- Match each uploaded file to a pair by its name. If a link has no file name, or a name matches no uploaded file, list it and ask; don't guess. If a URL appears in the bidder's columns, **reject it** and say so ("this is the bidder's link").
- Store it with `blobs.setJSON('linkmap_<sheet>_<bidder>', {...})`. Show a short table (file → link given yes/no).
- If the user gives no links, skip linking; REFERENCE stays plain text.
**Done when:** every uploaded file is either matched to an evaluator link or marked "no link".

### 4. Extract the documents
- code_execution: `base = os.environ.get('INPUT_DIR','/files/input')` (re-define it in every session) and glob. Use `pdfplumber` (text + `extract_tables()`), `python-docx`, `openpyxl`, and `pdf2image` + `pytesseract` for scans. Silence pdfminer warnings. Read images visually.
- Map printed page numbers from the footers (`Page N`, `Halaman N`, `N / M`). Where a cover page shifts the numbering (printed = PDF − 1), cite the printed number.
- Print only ±200-char snippets. Write a fact list per document into your response text.
- Identify the model, variant/licence tier, and document version/date in each document.

### 5. Evaluate every row per bidder
Apply the type's pass rule, then these evidence checks:
- **The cited page lacks the claim** → FAIL ("Claim not supported by the cited document").
- **Variant/tier/configuration:** count only what the offered variant includes. Higher-tier-only → FAIL; tier unclear → QUERY.
- **Model identity/lifecycle:** another model's document, a discontinued model, or end-of-support software → QUERY.
- **Conflicting values** (bidder vs manufacturer, or two manufacturer documents) → QUERY, stating both values.
- **Manufacturer document beats a bidder-prepared spec sheet.** Evidence only from a bidder-prepared sheet for a third-party component → flag it in the report as a judgment point. Blank templates → QUERY.
- **Ticked No on a mandatory row**, or no tick plus a placeholder → FAIL. Generic restatement → QUERY. Blank → FAIL.
- **Service rows:** a signed letter stating the figure → PASS. Restated with no letter → QUERY.
- **Undocumented features** → FAIL. Host PC/server advice doesn't evidence the device's own security.
- **Quantities:** cross-check the workbook's accessories/consumables/BoQ sheets (read only). Short → FAIL; inconsistent → QUERY.
- **Regulatory:** must name the offered brand/model/type and be valid today. Note the number, dates and any typos.
- **"Or equivalent":** only with evidence of equivalence. **Desirable / "where applicable" rows:** a failure is noted but isn't a mandatory FAIL.

Note format: `Required <X>; offered <Y> – <reason>. <evidence comment>.`

### 6. Write and verify the evaluation
**6a. Values and formatting.**
- execute_office_js, one call per section (≈20 rows), values only.
- **Copy the formatting of evaluator columns already completed.** If none exist, use label fills PASS #C6EFCE/#006100, FAIL #FFC7CE/#9C0006, QUERY #FFEB9C/#9C5700, bold and centred; Note/Reference cells wrap with top alignment. Don't change row heights or column widths.

**6b. REFERENCE links (only with an evaluator `linkmap`).** For each REFERENCE cell:
1. Walk the file names in the cell text in order. Link to the first one found in `linkmap`.
2. Cross-check-only cells (`workbook: '<sheet>' row N`) get an internal link: `documentReference: "'<sheet>'!A<row>"`.
3. "File not provided – …" cells, and cells with no linkmap match, stay **plain text**. Never fall back to the bidder's URL.
```js
const c = sheet.getRange(addr);
c.hyperlink = { address: linkmap[file], textToDisplay: currentText, screenTip: "Open evaluator copy on Google Drive" };
c.format.font.color = "#0563C1"; c.format.font.underline = "Single";
```
- Keep `textToDisplay` exactly equal to the existing text.
- **Clean-up:** if a REFERENCE cell has a link whose address is a bidder URL (found in the bidder's columns) or isn't in `linkmap`, remove it: `c.clear(Excel.ClearApplyTo.hyperlinks)`, then reset the font to black with no underline. Keep internal links.
- **Optional document register** (offer it when many cells cite 2+ files): a sheet `Docs <short package> - <short bidder>` with `File | Document type | Evaluator link | Rows citing`, placed after the clarification sheet.

**6c. Verify.**
- Re-read the columns: no blank notes on evaluable rows, only profile labels, and counts that reconcile.
- Load `hyperlink` for every REFERENCE cell. Count evaluator-linked, internal and plain cells. Assert that **no address equals or contains a URL from the bidder's columns**, and that every address is in `linkmap`. Check the displayed text is unchanged, comparing values before and after.
- Render a ~15-row sample with getImage.

**Recheck mode** ("recheck the evaluation"): re-extract the documents; re-run the rule checks (labels, blank notes, Comply rows with a ticked No or a placeholder, Comply rows whose REFERENCE says "not found/not provided"); verify every cited file and page exists and contains the key values in the note; fix only clear citation errors and report the judgment points; confirm the clarification sheets still match the flagged rows. Don't change determinations without stating why.

### 7. Choose the clarification layout
- With a user template: inspect it (openpyxl) and map headers by synonyms (Row/No; Item; Requirement; Bidder Response; Supporting documents/Reference; Assessment/PC Assesment; Question/Context; reply columns). Tell the user how you mapped it.
- Otherwise use the default AMPC layout: rows 1–3 title/bidder/note; rows 4–5 headers (`Row | PROPOSED DEVICE INFORMATION | Requirements` yellow #FFFF00 merged across 4–5; `BIDDER CLARIFICATION` teal #A2C4C9 over `Bidder Response | Supporting documents | PC Assesment | Context`; `AMPC RESPONSE` over `Date | Response`); rows 6–7 brand/model; items from row 8. Use "PROPOSED ITEM INFORMATION" for non-device packages.

### 8. Build the clarification sheets (default output)
- One sheet per evaluated bidder: `Clarif <short package> - <short bidder>` (≤31 characters), right after the package sheet. Ask before replacing an existing one.
- Row 1 `="TECHNICAL CLARIFICATION – "&'<sheet>'!<title cell>`; row 2 bidder (formula) + offered model + tender no.; row 3 note "Items listed: determination = <FAIL> or <QUERY>; columns A–E linked to '<sheet>'".
- Items in row order. A/B/C = formulas to row no./item/requirement. D = a formula joining the tick label and `TRIM(details)`. E = `source & CHAR(10) & url`. **Here the bidder's own URL may be linked** with `range.hyperlink`, because the column shows what the bidder submitted. F = text label + finding (fill per label). G = text question. Reply columns blank.
- **Office.js gotchas:** `HYPERLINK()` formulas and `eval`/`new Function` are blocked; use `range.hyperlink`. Pass data as JSON literals, and use `blobs.setJSON` between calls. The Python sandbox can't call Excel tools.
- Format: Arial 10, thin borders, wrap/top; widths ≈ 8/30/33/40/30/45/50/15/45; autofit rows; freeze rows 1–5 and column A; landscape, fit to 1 page wide, print titles 4:5.
- Questions: specific, neutral, naming the document/page or value needed. Blanks: "No response was provided. Please state …". Mismatches: state both values.
**Done when:** the item count equals FAIL + QUERY per bidder, there are no #REF!/#VALUE! errors, the row numbers match the flagged rows, and a getImage of rows 1–12 looks right.

### 9. Optional: downloadable files
Only if asked: fill a copy of the template with openpyxl (static values; evaluator links only in any REFERENCE-type column; bidder links allowed only in the Supporting documents column; frozen panes, print setup). Save to `/tmp/…` and copy to `$OUTPUT_DIR` in the same reply; re-copy from /tmp if the user can't find them. Reopen to verify, and say a visual preview wasn't possible.

### 10. Report
Keep it brief:
- the profile used;
- a PASS/FAIL/QUERY table per bidder;
- the 3–6 key FAIL items per new bidder;
- the main queries;
- shared FAIL rows;
- judgment points (e.g., bidder-prepared evidence, "where applicable" rows);
- documents not provided;
- **REFERENCE link counts per bidder (evaluator-linked / internal / plain)**, any bidder links removed, and any user links that couldn't be matched;
- the clarification sheet names, with a reminder to save.

State what you re-read. If no evaluator links were given, say REFERENCE is plain text and invite the user to paste `file name → link` pairs.

## Multi-package runs
Finish Steps 1–8 for one package sheet before starting the next. Request documents and evaluator links per package. Reuse the label mapping only if the sheets share the same template.

## Examples (illustrative)
- User pastes `aScreen_TM_002.004.pdf → https://drive.google.com/file/d/<our-copy>/view`. REFERENCE `aScreen_TM_002.004.pdf – p.76 (Annex 1, Table 2)` opens our copy; text unchanged.
- REFERENCE `Brochure aScreen.pdf – p.3; OAE NIE.pdf – p.1` with a link given only for the NIE → link to the NIE (the first file with an evaluator link).
- REFERENCE `File not provided – Installation Base List` → plain text, even though the bidder's row has a Drive link.
- REFERENCE `workbook: 'Proposed Consumables & Price' row 52` → internal link to that sheet.
- The user pastes a link that also appears in the bidder's URL column → reject it: "That's the bidder's link; please send the link to your own copy."
- Patient monitor "SpO2 0–100 %" → RANGE_COVER; ventilator "Tidal volume 20–2000 mL" offered 50–2000 → FAIL; power "230 ± 10 V AC, Type F plug" → SITE_WITHIN + ENUM, plug undocumented → FAIL; OAE Screener+ licence DPOAE 2–5 kHz vs Clinical-only 1.5–12 kHz → FAIL (variant rule).
