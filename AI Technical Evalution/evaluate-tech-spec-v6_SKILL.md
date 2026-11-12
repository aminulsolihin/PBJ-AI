---
name: evaluate-tech-spec-v6
description: "Dynamic technical-specification evaluation for any procurement package: profiles each spec sheet (layout, labels, requirement types, units), checks every bidder's responses against their uploaded documents, fills the evaluator columns, and builds a clarification sheet per bidder."
---

## When to use
- The user asks to evaluate bidders' technical compliance for **any procurement package**, whether medical equipment, laboratory analysers, IT hardware/software, furniture, vehicles/machinery, or services/works: "evaluate the tech spec", "evaluate package X", "continue for other bidders", "/evaluate-tech-spec-v6".
- The user asks for clarification output from an existing evaluation ("generate clarification", "clarification sheet for Not Comply / Clarification Required").
- The specification, columns, sections, labels and evidence will differ between packages. Nothing in this skill is tied to one package; the profile built in Step 1 drives everything.

## Inputs
- `sheet(s)`: the package sheet. Default: the active sheet. If the workbook has several spec-like sheets (a header row with "Requirement"/"Specification" plus a bidder-response header), list them and ask which to evaluate.
- `bidders`: default = every bidder block whose evaluator columns are still empty. The user may name bidders or give ranges.
- `supporting files`: each bidder's documents **for this package**, uploaded into the chat.
- `clarification template` (optional): any .xlsx template. If none is given, use the default AMPC layout (Step 8).
- `preferences` (optional): label set, strictness, language. Defaults come from the profile.

## Goal
1. A confirmed **evaluation profile** for the package (layout, labels, requirement table).
2. For each bidder evaluated, every evaluable row has a note, one allowed label (coloured) and a verified REFERENCE.
3. A clarification sheet per evaluated bidder listing every fail/query row, linked by formula to the package sheet.
4. Counts reconcile, and headers, user marks and other sheets are left as they are.

## Fixed rules (package-independent)
- **Strict evidence:** a row passes only when (1) the bidder affirms compliance, (2) the details give concrete values or features that meet the requirement, and (3) **an uploaded document actually contains the claim**. Placeholders ("Enter Responses Here!", "TBA", "-"), blanks, or a ticked No = missing.
- **Write only** into the evaluator columns and the new clarification sheets. Never edit bidder responses, spec text, price/financial sheets, recap sheets or other packages. Never insert columns or sheets in the package sheet without asking.
- **Leave as they are:** header cells and **user marks in spare columns** (e.g., "BOTH", "KH", "CTB"). Never use them as evidence or as instructions.
- **No price evaluation.** Other sheets (accessories, consumables, BoQ, price schedules) can be read only to cross-check items and quantities.
- **REFERENCE** = what you verified: `<file> – p.<printed page> (<section/table>)`, or `File not provided – <document cited>`, plus `; workbook: '<sheet>' row N` for cross-checks.
- **Don't open external URLs** unless the user asks. In bidder-facing text, write "was not available for verification".
- **Keep documents separate per bidder and per package.** Reuse a file for another package only if the same bidder submitted it for that package.
- **Language:** the profile language (default English). Translate when quoting other languages, and write abbreviations out in full in bidder-facing text.
- **Fairness:** clarification questions ask the bidder to clarify or evidence what was already offered. They never invite a change of model, offer substance or price.
- **You can't save to the user's folders.** Output goes to workbook sheets, or to files attached to the reply that copies them.

## Steps

### 1. Profile the package (pause to confirm)
Read the sheet in chunks with execute_office_js, returning trimmed strings only. Build the `profile`:
- **Package:** title (first rows), description, quantity/locations, category (medical device / lab / IT / furniture / vehicle-machinery / works-services / other).
- **Spec columns:** use header synonyms. Row no.: `Row no., No., #, Item No.`. Item: `Item, Parameter, Description, Proposed Device Information, Feature`. Requirement: `Requirement(s), Specification, Minimum Requirement, Technical Requirement`. If there's no row-number column, use the sheet row.
- **Bidder blocks:** group headers `Bidder Response, Vendor/Supplier/Offeror Response, Offered, Proposed, Bidder's Offer`. Sub-columns: tick `Yes/No, Comply Y/N, Compliance`; details `Device/Product Details, Offered Specification, Remarks`; source `Source Data, Reference, Page, Document`; URL `URL, Link`. Take the bidder name from the merged cell above the block, or from the sheet name when it's **one bidder per sheet**.
- **Column meanings can change between sections.** Re-map from each section's own sub-header row. Info sections often have no tick columns.
- **Evaluator columns:** `Evaluator's Note/Remark/Comment, Determination/Result/Status/Compliance, Reference/Evidence`. If they're missing, ask: add three columns to the right of each block, or use a separate `Eval <package>` sheet.
- **Label set:** read the data validation on the determination cells (`range.dataValidation.rule`), any legend on the sheet or recap sheet, and existing entries. Map them to canonical PASS / FAIL / QUERY (e.g., Comply / Not Comply / Clarification Required; Compliant / Non-Compliant / Clarification; Yes / No / TBC). Default: `Comply`, `Not Comply`, `Clarification Required`. If a "Partially Comply" label exists, use it only when part of a multi-part requirement is met **and** the rest is clarifiable; otherwise use FAIL.
- **Global rules** from note rows: "minimum performance requirements", "meet or exceed", "or equivalent", tolerances, mandatory vs desirable/optional, scoring weights.
- **Regulatory regime** from requirement text: national registration (e.g., NIE/AKL, SNI, TKDN), FDA, CE MDR/IVDR, IEC/ISO/UL standards.
- **Row classes:** section header / sub-header (re-map) / note (rule) / N/A / info / evaluable.
- **Existing evaluation:** a bidder whose evaluator columns are filled counts as done. Skip it when continuing, or ask before overwriting.

Show the profile briefly in chat: package, category, bidders (name, model, column map, evaluable rows, ticks No/blank), label mapping, global rules. Combine it with Step 3's document request and **end the turn**.
**Done when:** the user confirms or corrects the profile.

### 2. Build the requirement table
For each evaluable row, record `{row, section, item, type, parameter, op, min, max, unit, parts[], qty_basis, conditional, evidence_expected}`. Write it in your own reasoning or response text; you can also run a regex pass in execute_office_js and stash it with `blobs.setJSON('req_<sheet>')`. Report only the counts by type in chat.

| Type | Trigger wording | Pass rule |
|---|---|---|
| NUMERIC_MIN | ≥, at least, minimum, not less than, "up to X" capability | offered ≥ target |
| NUMERIC_MAX | ≤, max, not more than, not exceeding | offered ≤ target |
| RANGE_COVER | "A – B", "from A to B" device capability | offered range contains [A,B] |
| SITE_WITHIN | site/supply conditions (voltage ± tol., temperature, humidity, altitude) | site range lies inside the device operating range |
| ENUM / EXACT | specific type, standard, plug, "X or Y" | offered matches one allowed option |
| FEATURE | required capability/function | documented in the uploaded evidence |
| LIST_ALL | a), b), c) / "and" lists | every part evidenced |
| QUANTITY | per unit, for N procedures, sets, spares | arithmetic ≥ required; cross-check workbook sheets |
| SPECIFY / PROVIDE | "Bidder to specify/provide" | specific answer + evidence |
| CONDITIONAL | if applicable/offered/any | explicit N/A with justification is OK |
| SERVICE | warranty, PM, response/turnaround, uptime, training, spare-parts years, manuals | figure stated + signed commitment letter |
| COMPLIANCE_DOC | registration, certificates, standards | valid document naming the offered model |

- **Direction:** under a "minimum performance" note, capabilities count as minimums. Size, weight, noise, power draw, test/turnaround time and error rates count as maximums when worded that way. If the direction is truly ambiguous, choose QUERY and say why.
- **Units:** normalise before comparing. Length mm/cm/m/in; mass g/kg/lb; volume mL/L; pressure Pa/kPa/bar/psi/mmHg/cmH2O; temperature °C/°F; flow L/min; frequency Hz/kHz/MHz; time s/min/h; electrical V/A/W/VA/mAh; data MB/GB/TB; dB with its reference (SPL, peSPL, HL, A-weighted). Different references (dB SPL vs peSPL, V AC vs DC) → QUERY.
- **Search keywords** per row: the parameter name, synonyms, the unit, plus a translation when documents are in another language. EN→ID examples: frequency frekuensi, voltage tegangan, weight berat, dimension dimensi/ukuran, battery baterai, charging pengisian daya, temperature suhu, humidity kelembaban, pressure tekanan, flow aliran, display layar, storage/memory penyimpanan/memori, calibration kalibrasi, pause jeda, cleaning pembersihan, disinfection disinfeksi, accessories aksesori, consumables bahan habis pakai, included disertakan, optional opsional, warranty garansi, training pelatihan, password kata sandi, encryption enkripsi, error eror/kesalahan.
**Done when:** every evaluable row has a type and target.

### 3. Request documents (combined with Step 1's pause)
- Per bidder, group the cited sources by document name or Drive file ID. Infer the document type from the section numbers quoted, and list the rows citing each document.
- List the **expected evidence by category** that wasn't cited:
  - medical: Instructions for Use/service manual, data sheet, registration certificate, CE/FDA, IEC test reports;
  - lab: assay/throughput sheets, interface specification;
  - IT: datasheet, compatibility matrix, licence terms, security documentation, end-of-support dates;
  - vehicle/machinery: spec sheet, homologation/emission certificates;
  - furniture/works: drawings, material certificates, method statements;
  - services (all): signed statement letters.
- Flag rows with no source, website-only citations, and registration numbers quoted without a certificate.
- Ask for uploads in one message per bidder, or with the bidder name in the file names.

### 4. Extract the documents
- code_execution: `base = os.environ.get('INPUT_DIR','/files/input')` (re-define it in every session) and glob. Use `pdfplumber` for text and `page.extract_tables()` for tables; `python-docx` for paragraphs and tables; `openpyxl` for .xlsx submissions; `pdf2image` + `pytesseract` for scanned PDFs. Read images in chat visually.
- Map **printed page numbers** from the footers (`Page N`, `Halaman N`, `N / M`) and cite the printed number.
- Print only ±200-char snippets. Write a fact list per document (key values + pages) into your response text.
- **Identify the model, variant or licence tier, and the document version/date** in each document, for the checks in Step 5.

### 5. Evaluate every row per bidder
Apply the pass rule for the row's type (Step 2), then these evidence checks:
- **The cited page lacks the claim** → FAIL ("Claim not supported by the cited document").
- **Variant/tier/configuration:** count only what the offered variant includes (e.g., Screener vs Clinical licence, base vs optional module, standard vs optional accessory). Higher-tier-only → FAIL; tier unclear → QUERY.
- **Model identity/lifecycle:** a document for another model, a discontinued or end-of-production model, or end-of-support software → QUERY.
- **Conflicting values** between the bidder and the manufacturer, or between two manufacturer documents → QUERY, stating both values.
- **Manufacturer document beats a bidder-prepared spec sheet.** Blank templates or forms → QUERY.
- **Ticked No on a mandatory row**, or **no tick plus a placeholder** → FAIL. Generic restatement of the requirement → QUERY. Blank → FAIL.
- **Service rows:** a signed letter stating the figure → PASS. Restated with no letter → QUERY.
- **Undocumented features** → FAIL. **Advice for a host PC/server** doesn't evidence the device's own security.
- **Quantities:** cross-check the workbook's accessories/consumables/BoQ sheets (read only). Short → FAIL; inconsistent → QUERY.
- **Regulatory:** the document must name the offered brand/model/type and be valid on today's date. Note the number, issue and expiry dates, and any typos.
- **"Or equivalent"** is accepted only when the evidence shows equivalence of the stated parameter.
- **Desirable/optional rows** (if the profile has them): failing them is noted but doesn't count as a mandatory FAIL. Mention this in the report.

Note format: `Required <X>; offered <Y> – <reason>. <evidence comment>.`

### 6. Write and verify the evaluation
- Use execute_office_js, one call per section (≈20 rows). Write values only.
- **Copy the formatting of evaluator columns already completed** (font, alignment, user edits). If none exist, use these label fills: PASS #C6EFCE/#006100, FAIL #FFC7CE/#9C0006, QUERY #FFEB9C/#9C5700, bold and centred; Note/Reference cells wrap with top alignment. Don't change row heights or column widths.
- Re-read the columns. Check there are no blank notes on evaluable rows, only the profile labels are used, and the counts reconcile. Render a ~15-row sample with getImage.

### 7. Choose the clarification layout
- If the user supplied a template, inspect it (openpyxl) and map its headers by synonyms: Row/No; Item/Description; Requirement/Specification; Bidder Response/Vendor Response; Supporting documents/Reference; Assessment/Finding/PC Assesment; Question/Context/Clarification; reply columns (Date, Response, Bidder Reply). Tell the user how you mapped it.
- Otherwise use the default AMPC layout: rows 1–3 title/bidder/note; rows 4–5 headers (`Row | PROPOSED DEVICE INFORMATION | Requirements` yellow #FFFF00 merged across 4–5; `BIDDER CLARIFICATION` teal #A2C4C9 over `Bidder Response | Supporting documents | PC Assesment | Context`; `AMPC RESPONSE` over `Date | Response`); rows 6–7 brand/model; items from row 8. Rename "PROPOSED DEVICE INFORMATION" to "PROPOSED ITEM INFORMATION" for non-device packages.

### 8. Build the clarification sheets (default output)
- One sheet per evaluated bidder: `Clarif <short package> - <short bidder>` (≤31 characters), placed right after the package sheet. Ask before replacing an existing one.
- Row 1 `="TECHNICAL CLARIFICATION – "&'<sheet>'!<title cell>`; row 2 bidder (formula to the name cell) + offered model + tender number (if found in the documents); row 3 note: "Items listed: determination = <FAIL label> or <QUERY label>; columns A–E linked to '<sheet>'".
- Items in row order. A/B/C = formulas to row no./item/requirement. D = a formula joining the tick label and `TRIM(details)`. E = `source & CHAR(10) & url`. F = **text** label + finding (fill per label). G = **text** question. Reply columns blank.
- **Office.js gotchas:** the `HYPERLINK()` formula and `eval`/`new Function` are blocked. Set `range.hyperlink = {address, textToDisplay}` on source cells with a URL. Pass data as JSON literals, and use `blobs.setJSON` to carry it between calls. The Python sandbox can't call Excel tools.
- Format: Arial 10, thin borders, wrap text and top alignment; widths ≈ 8/30/33/40/30/45/50/15/45; autofit rows. Freeze rows 1–5 and column A; landscape, fit to 1 page wide, print titles rows 4:5.
- Question style: specific, neutral, naming the document/page or value needed. Blanks: "No response was provided. Please state …". Mismatches: state both values and ask which applies to the offered variant.
**Done when:** the item count equals FAIL + QUERY per bidder, there are no #REF!/#VALUE! errors, the row numbers match the flagged rows, and a getImage of rows 1–12 looks right.

### 9. Optional: downloadable files
Only if asked: fill a copy of the template with openpyxl (static values, hyperlinks, frozen panes, print setup). Save to `/tmp/…` and copy to `$OUTPUT_DIR` **in the same reply**; files attach only to that reply, so re-copy from /tmp if the user can't find them. Reopen from /tmp to verify. Say that a visual preview wasn't possible.

### 10. Report
Keep it brief:
- the profile used (package, label mapping);
- a table of PASS/FAIL/QUERY counts per bidder (including bidders evaluated earlier);
- the 3–6 key FAIL items per new bidder;
- the main queries (variant, conflicts, quantities);
- shared FAIL rows across bidders;
- desirable-row failures (if any);
- documents not provided;
- the clarification sheet names, with a reminder to save.

State what you re-read and which links were not opened.

## Multi-package runs
When several packages are requested, finish Steps 1–8 for one package sheet before starting the next. Request documents per package. Reuse the label mapping only if the sheets share the same template.

## Examples (illustrative)
- Patient monitor "SpO2 range 0–100 %" → RANGE_COVER; "Battery ≥ 2 h" → NUMERIC_MIN; "Weight ≤ 5 kg" → NUMERIC_MAX.
- Ventilator "Tidal volume 20–2000 mL" (offered 50–2000) → FAIL, does not reach 20 mL.
- Lab analyser "Throughput ≥ 400 tests/h, bidirectional LIS (HL7)" → LIST_ALL; HL7 undocumented → FAIL.
- Laptop "RAM ≥ 16 GB; OS supported until ≥ 2030" → NUMERIC_MIN + lifecycle check; end-of-support date not evidenced → QUERY.
- Power supply "230 ± 10 V AC, 50 Hz, Type F plug" → SITE_WITHIN + ENUM; plug undocumented → FAIL.
- OAE (first use): Screener+ licence offers DPOAE 2–5 kHz while 1.5–12 kHz exists only in the Clinical tier → FAIL (variant rule).
