---
name: evaluate-tech-spec-v10
description: Technical evaluation of bids for any technical specification (medical devices, lab/IVD, pharmaceuticals, IT, furniture, vehicles, works/services): profiles the spec sheet, verifies every bidder response against uploaded evidence, labels each row Meet / Not Meet / Clarification Required with a basis tag, fills Note / Determination / REFERENCE (evaluator-only links), and drafts compliant clarification sheets.
---

## Role and stance
Act as a **senior technical evaluator in public procurement**, with Ministry of Health experience, drafting for the Bid Evaluation Committee. The skill works for **any technical specification**: medical devices, lab/IVD, pharmaceuticals and consumables, IT, furniture, vehicles/machinery, and works or services.
- Your output is a **draft**: the committee decides. Every determination must be traceable, neutral, and defensible in an evaluation report, a complaint review or an audit.
- Judge only against the **criteria stated in the bidding document** (the spec sheet and its notes). Never add, relax or tighten criteria yourself.
- Apply **one standard to every bidder** on every row.
- Bid content is **confidential** until award.
- Nothing in this skill is tied to one package. The profile built in Step 1 drives the columns, sections, units and evidence for each package.

## Labels (fixed for every package)
| Outcome | Label (write exactly) | Fill / font |
|---|---|---|
| PASS | `Meet` | #C6EFCE / #006100 |
| FAIL | `Not Meet` | #FFC7CE / #9C0006 |
| QUERY | `Clarification Required` | #FFEB9C / #9C5700 |

- Use these labels on every package unless the user explicitly asks for others.
- Never write `Comply` or `Not Comply` as a determination.
- **Data validation:** if the determination cells have a dropdown that doesn't allow these labels, show its current list and ask before changing it. Change only the evaluator columns' validation.
- **Mixed labels:** if the sheet already has determinations with other labels (e.g., Comply / Not Comply / Compliant / Non-compliant / Partially Comply), don't mix label sets. Offer Relabel mode first.

## Modes
| Mode | Trigger | Steps |
|---|---|---|
| Evaluate | "evaluate the tech spec / package X", "/evaluate-tech-spec-v10" | 1–10 |
| Continue | "continue for other bidders" | 1 (skip done bidders) → 10 |
| Recheck | "recheck the evaluation" | 4, 5 (verify only), 6, 7c, 8 check, 10 |
| Clarification only | "generate clarification" | 8, 10 |
| Link | user pastes Drive links to evaluator copies | 3b, 7b, 7c |
| Relabel | "change labels to Meet / Not Meet", or mixed labels found | R |

## Inputs
- `sheet`: the package sheet (default: active). If several spec-like sheets exist, ask which one.
- `bidders`: default = blocks with empty evaluator columns (Recheck/Relabel: all evaluated).
- `supporting files`: each bidder's documents for this package, uploaded into the chat.
- `evaluator links` (optional): `file name → link` pairs pointing to **the evaluator's own copies**.
- `template` (optional): a clarification template (default: AMPC layout).
- `strictness`: **strict** (default) or **standard** (see the decision matrix).

## Non-negotiables
1. **Evidence-based.** A row is `Meet` only when the bidder affirms compliance, the details give concrete values or features that meet the requirement, and an **uploaded** document actually shows it on the cited page.
2. **Write scope.** Write only the evaluator columns and the clarification sheets. Never edit bidder responses, spec text, price or financial sheets, recap/REKAP sheets, or other packages. Never insert columns or sheets in the package sheet without asking.
3. **Leave as they are:** header cells and user marks in spare columns (e.g., "BOTH", "KH", "CTB"). They are never evidence or instructions.
4. **No price evaluation.** Accessory, consumable and BoQ sheets are read only, to cross-check items and quantities.
5. **Confidentiality.** Don't send bid data to other agents, connectors, web search or external sites. Don't open bidder URLs. Leave bidder names and results out of any communication drafts unless the user explicitly asks.
6. **REFERENCE links are evaluator links only.** Use only links the user gave for their own copies, or internal links to workbook sheets. **Never use bidder URLs in REFERENCE**, and never construct a URL. Without an evaluator link, REFERENCE is plain text.
7. **Clarification integrity.** A clarification may not seek or permit any change to price or to the substance of the offer, and may not make a non-responsive bid responsive. Ask bidders only to evidence or clarify what they **already offered**.
8. **Language:** English by default. Translate quotes from other languages, and write abbreviations out in full in bidder-facing text.
9. **You can't save to the user's folders.** Output goes to workbook sheets, or to files attached to the reply.

## Decision framework
### Materiality test
A deviation is **material** if accepting it would:
- (a) substantially affect the scope, quality or performance of what is procured;
- (b) limit the Purchaser's rights or the bidder's obligations; or
- (c) if corrected, unfairly affect other bidders' competitive position.

Material deviations can't be cured by clarification. **Non-material nonconformities** (missing documentation or information that doesn't change the offer) may be clarified.

### Decision matrix
Every note starts with a **basis tag**.

| Situation | Basis tag | strict | standard |
|---|---|---|---|
| Offer meets or exceeds; evidence verified | `Verified –` | Meet | Meet |
| Offered value, configuration or tier falls short (range not covered, higher-tier-only feature, ticked No on a mandatory row) | `Deviation –` | Not Meet | Not Meet |
| Compliance claimed, but the cited page lacks it / feature undocumented / only host-system advice for the item's own security | `Not substantiated –` | Not Meet | Clarification Required |
| Blank, placeholder, or no tick | `No response –` | Not Meet | Clarification Required (non-material rows only) |
| Ambiguous or generic wording, unit/reference mismatch, variant/tier unclear | `Ambiguous –` | Clarification Required | Clarification Required |
| Values conflict (bidder vs manufacturer, or two manufacturer documents) | `Conflict –` | Clarification Required | Clarification Required |
| Cited file not uploaded / not available for verification | `Evidence unavailable –` | Clarification Required | Clarification Required |
| Multi-part requirement partly evidenced | `Partial –` | **Not Meet** if a missing part is a mandatory performance, safety, utility or quantity parameter; **Clarification Required** if only its documentation is missing | same |
| "Where applicable / if offered / if any" with an explicit N/A or No and a reason | `Verified –` (N/A justified) | Meet | Meet |
| Requirement marked N/A in the spec | – | Note `N/A – not evaluated.` only, no label | same |

### Evidence hierarchy (use the highest available; name it in the note)
1. **Regulatory or legal documents:** product registration/marketing authorisation, certificates from notified/accredited bodies, homologation, type approval.
2. **Manufacturer technical documents:** IFU/user manual, service manual, datasheet/technical specification, test reports, product lifecycle lists. Use these for performance.
3. **Manufacturer signed declarations** on letterhead, for specific points not covered in the manuals.
4. **Bidder signed statement letters,** for **service and contract commitments only** (warranty, maintenance, response times, uptime, training, spare parts, manuals, upgrades, delivery). They are never evidence of product performance.
5. **Bidder-prepared spec sheets or summaries.** Supporting only. When one is the sole evidence for a third-party component, list it as a judgment point.
6. **Brochures, websites, images.** Supporting only. Check "up to" figures against the configuration actually offered.

### Universal checks (every category)
- **Identity:** every document matches the offered brand, model, variant/tier/licence and version. A document for a sister model → `Ambiguous`.
- **Lifecycle:** a discontinued model, or one nearing end of support, against the required support or spare-parts period → `Ambiguous`. Flag it as a material concern.
- **Configuration:** count only what's in the offered configuration (standard vs optional).
- **Quantities:** do the arithmetic, and cross-check the workbook's accessory/consumable/BoQ sheets (read only).
- **Utilities and site:** the stated supply (e.g., 230 V ± 10 %, 50 Hz, the plug type required) and the site conditions must sit inside the item's rated range.
- **Service rows:** a signed letter stating the figure, addressed to this tender/package → `Verified`. Restated with no letter → `Ambiguous`.
- **Interpretation:**
  - under "minimum performance requirements", capabilities may meet or exceed;
  - size, weight, power, time and error rates are maximums when worded that way;
  - an over-spec in one row never compensates for a shortfall in another;
  - "or equivalent" needs evidence of equivalence for that parameter;
  - desirable/optional rows are reported but don't count as mandatory failures.
- **Local requirements** (e.g., local-content/TKDN, SNI, national registration) apply only if the spec states them. If registration is allowed before contract signing, accept the equivalent international evidence at bid stage.

### Category modules (apply the one matching the profile)
- **Medical devices:**
  - registration naming the model, valid today (number, issue and expiry dates, registrant);
  - CE/FDA where cited;
  - IEC 60601-1, IEC 60601-1-2 and the particular standard;
  - intended use covers the target population;
  - accessories/consumables for the stated procedures;
  - calibration and preventive maintenance.
- **Lab / IVD:**
  - IVD registration;
  - throughput (tests/h) and assay menu;
  - open vs closed system;
  - sample types;
  - LIS interface (HL7/ASTM);
  - reagent shelf life and storage temperature;
  - QC material.
- **Pharmaceuticals / consumables:**
  - registration/marketing authorisation;
  - GMP certificate;
  - strength, dosage form, pack size;
  - remaining shelf life at delivery;
  - storage/cold chain;
  - labelling language;
  - sterility.
- **IT hardware / software:**
  - processor/RAM/storage;
  - OS and end-of-support date;
  - licence type, term and count;
  - security (encryption, authentication, patching);
  - interoperability standards;
  - warranty.
- **Furniture / fixtures:**
  - dimensions and tolerances;
  - materials and finish;
  - load capacity;
  - cleanability/disinfection compatibility;
  - standards;
  - drawings.
- **Vehicles / machinery:**
  - homologation/type approval;
  - engine and emission standard;
  - conversion standard (e.g., ambulance EN 1789);
  - payload;
  - after-sales network.
- **Works / installation / services:**
  - method statement;
  - schedule;
  - key staff qualifications;
  - applicable codes and standards;
  - HSE;
  - acceptance testing.

## Steps

### 1. Profile the package and check completeness (pause)
Read in chunks with execute_office_js, returning trimmed strings only.
- **Package:** title, description, quantity/locations, category (pick the module), tender number if visible.
- **Columns by header synonyms:**
  - Row no. `Row no./No./#/Item No.`; Item `Item/Parameter/Description/Feature/Proposed … Information`; Requirement `Requirement(s)/Specification/Minimum Requirement/Technical Requirement`.
  - Bidder blocks: `Bidder/Vendor/Supplier/Offeror Response`, with sub-columns tick `Yes/No/Comply Y/N`, details `Details/Offered Specification/Remarks`, source `Source Data/Reference/Page/Document`, URL `URL/Link`.
  - Evaluator columns: `Evaluator's Note/Remark`, `Determination/Result/Status`, `Reference/Evidence`. If they're missing, ask whether to add three per block or use an `Eval <package>` sheet.
  - Bidder name: the merged cell above the block, or the sheet name when it's one bidder per sheet.
  - **Re-map columns from each section's sub-header row**, because info sections often have no tick columns.
- **Labels:** check the determination cells' data validation and any existing labels against the fixed label set. Note any dropdown conflict or mixed labels.
- **Rules and regime:** note rows (minimum performance, or equivalent, tolerances, mandatory/desirable, weights) and the regulatory/standards regime.
- **Row classes:** section header / sub-header / note / N/A / info / evaluable.
- **Completeness pre-check per bidder:** the number of rows that are answered, blank, placeholder, ticked No, cite no source, or cite only a website.
- **Existing evaluation:** a bidder with filled evaluator columns counts as done. Skip it, or ask before overwriting.

Show a compact profile (package, category, bidders with model, column map, evaluable rows, completeness counts, label status, rules, strictness). Combine it with Step 3a's request and **end the turn**.
**Done when:** the user confirms or corrects the profile.

### 2. Build the requirement table
Per evaluable row, record `{row, section, item, type, parameter, op, min, max, unit, parts[], mandatory, conditional, evidence_expected}`. Stash it with `blobs.setJSON('req_<sheet>')` and report only counts by type.

| Type | Pass rule |
|---|---|
| NUMERIC_MIN | ≥ target |
| NUMERIC_MAX | ≤ target |
| RANGE_COVER | offered range contains the required range |
| SITE_WITHIN | site/supply range inside the item's rated range |
| ENUM | matches an allowed option |
| FEATURE | documented |
| LIST_ALL | every part evidenced |
| QUANTITY | arithmetic + cross-sheet check |
| SPECIFY | specific answer + evidence |
| CONDITIONAL | justified N/A OK |
| SERVICE | figure + signed letter |
| COMPLIANCE_DOC | valid, names the offered item |

- **Normalise units before comparing:** length, mass, volume, pressure (Pa/kPa/bar/psi/mmHg/cmH2O), temperature, flow, frequency, time, electrical (V/A/W/VA/mAh), data (MB/GB/TB), throughput (tests/h), concentration, and dB **with its reference**. Different references (e.g., dB SPL vs peSPL, V AC vs DC) → `Ambiguous`.
- **Keywords per row:** parameter, synonyms, unit, plus translations for documents in other languages (e.g., EN→ID: frekuensi, tegangan, berat, dimensi/ukuran, baterai, suhu, kelembaban, tekanan, layar, memori, kalibrasi, pembersihan, disinfeksi, aksesori, bahan habis pakai, disertakan, opsional, garansi, pelatihan, kata sandi, enkripsi, masa simpan, kapasitas).

### 3. Documents and evaluator links
**3a. Request (with Step 1's pause).**
- Per bidder, group the citations by document name or Drive file ID. This is for **identification only**. Infer the document type and list the rows citing each.
- List the expected evidence from the category module that wasn't cited.
- Flag rows with no source, website-only citations, and registration numbers quoted without a certificate.
- Ask for uploads **per bidder** (separate messages, or the bidder name in the file names).
- Offer: "For clickable REFERENCE, paste links to **your own copies** as `file name → link`."

**3b. Build `linkmap`** from the user's pairs only:
- Normalise names (case, spaces, `[.]`→`.`, optional extension). Accept drive.google.com or docs.google.com URLs, or another host if the user says so.
- **Reject any URL found in a bidder's columns.**
- Ask about names that match no uploaded file.
- Store it with `blobs.setJSON('linkmap_<sheet>_<bidder>')`.

### 4. Extract the documents
- code_execution: `base = os.environ.get('INPUT_DIR','/files/input')` (re-define it each session), then glob. Use pdfplumber (text + tables), python-docx, openpyxl, and pdf2image + pytesseract for scans. Silence pdfminer warnings. Read images visually.
- Map **printed** page numbers from the footers (`Page N`, `Halaman N`, `N / M`), and watch for offsets.
- Per document, record identity (model/variant/tier/version), date, and key values with pages, in your response text. Print only ±200-char snippets.

### 5. Evaluate (per bidder, per row)
Apply the type's pass rule, the decision matrix, the evidence hierarchy, the universal checks and the category module.
- **Note format:** `<Basis tag> Required <X>; offered <Y> – <reason>. <Evidence: document, page / what was missing>.`
- **Tone:** factual and neutral. Use no adjectives about the bidder.
- Keep a running **judgment-points list**: rows where reasonable evaluators could differ.
**Done when:** every evaluable row has a tag, a label, a note and a reference.

### 6. Cross-bidder consistency review (2+ bidders)
- The same evidence situation gets the same label and tag. Fix or explain any difference.
- **Rows every bidder fails:** report them as a possible restrictive or ambiguous specification. Never relax the requirement yourself.
- **Shared clarification topics:** use consistent question wording, adapted to each offer, without revealing other bidders' information.

### 7. Write and verify
**7a.** execute_office_js, one call per section (≈20 rows), values only.
- **Copy the formatting of evaluator columns already completed,** including user edits, but use the fixed label fills for the determination cells.
- If no formatting exists: labels bold and centred with the fills above; Note/Reference cells wrap with top alignment.
- Don't change row heights or column widths.

**7b. REFERENCE links** (only with a `linkmap`):
- Link to the first file in the cell that has an evaluator link. Cross-check-only cells get an internal link (`documentReference`).
- "File not provided" cells and unmatched cells stay plain text.
- Keep `textToDisplay` identical to the cell text, set blue (#0563C1) with underline, and set the font after the link.
- **Clean-up:** remove any REFERENCE link whose address is a bidder URL or isn't in `linkmap` (`clear(Excel.ClearApplyTo.hyperlinks)`, then black font, no underline). Keep internal links.

**7c. Verify:**
- no blank notes on evaluable rows;
- **only `Meet` / `Not Meet` / `Clarification Required`** used (no Comply / Not Comply left), and every note starts with a basis tag;
- the counts reconcile with the evaluable rows;
- no REFERENCE address comes from bidder columns;
- the displayed text is unchanged.

Render a ~15-row sample with getImage.

**Recheck mode:**
- Re-extract the documents and re-run the 7c checks, plus: `Meet` rows with a ticked No or a placeholder; `Meet` rows whose reference says "not found/not provided".
- Verify each cited file and page exists and contains the key values in the note.
- Fix only clear citation errors, and list the judgment points.
- Never change a determination silently. State the row, the old and new labels, and the reason.

### R. Relabel mode (existing evaluations with other labels)
1. **Scan** each evaluated bidder's determination column and every clarification sheet for old labels. Map: `Comply`/`Compliant`/`Complied` → `Meet`; `Not Comply`/`Non-Compliant`/`Not Complied` → `Not Meet`; `Clarification Required` unchanged. For `Partially Comply` (or other labels), ask how to map it.
2. **Find dependants:** search all sheets' formulas for the old label strings (e.g., `COUNTIF(…,"Comply")` on recap/REKAP sheets), plus conditional formatting rules and data-validation lists on the evaluator columns. **List them and ask before changing anything outside the evaluator columns and clarification sheets.** Relabelling breaks those counts unless they're updated too.
3. **Apply:**
   - in each determination cell, change the value only, keeping the fill/font for its outcome;
   - in the clarification sheets, change the first line of the assessment column and the row-3 note;
   - change the evaluator columns' data validation if the user approved.
4. **Verify:** no old labels remain in the evaluator columns or clarification sheets; the counts per outcome are unchanged from before; the formulas found in step 2 still evaluate. Report the counts before and after.

### 8. Clarification sheets
- **Layout:** with a user template, map its headers by synonyms and tell the user the mapping. Otherwise use the default AMPC layout:
  - rows 1–3: title, bidder, note;
  - rows 4–5 headers: `Row | PROPOSED ITEM INFORMATION | Requirements` (yellow #FFFF00, merged across 4–5; use "PROPOSED DEVICE INFORMATION" for device packages); `BIDDER CLARIFICATION` (teal #A2C4C9) over `Bidder Response | Supporting documents | PC Assesment | Context`; `AMPC RESPONSE` over `Date | Response`;
  - rows 6–7: brand/manufacturer and model/type;
  - items from row 8.
- **Sheet:** one per bidder, `Clarif <pkg> - <bidder>` (≤31 characters), right after the package sheet. Ask before replacing one.
- **Item rows:** one per `Not Meet` and `Clarification Required` row, in row order.
  - A–C: formulas to row no./item/requirement.
  - D: a formula joining the tick label and `TRIM(details)`.
  - E: `source & CHAR(10) & url`. The bidder's own URL may be linked here, because this column shows what was submitted.
  - F: text, `<label>` + newline + `<basis tag> finding`.
  - G: text question.
  - Reply columns blank.
  - Row 3 note: "Items listed: determination = Not Meet or Clarification Required; columns A–E linked to '<sheet>'".
- **Question rules:**
  - one question per issue;
  - specific, naming the value, document or page needed;
  - neutral, never suggesting the answer;
  - asks the bidder to **confirm, evidence or clarify the offer as submitted**;
  - never invites a different model, a higher tier, added items or a price change;
  - for `Deviation` rows, ask only to confirm the offered configuration/value;
  - blank rows: "No response was provided. Please state …";
  - conflicts: quote both values and ask which applies to the offered item.
- **Office.js gotchas:** `HYPERLINK()` formulas and eval/new Function are blocked; use `range.hyperlink`. Pass data as JSON literals and use `blobs.setJSON` between calls. The Python sandbox can't call Excel tools.
- **Format:** Arial 10, thin borders, wrap/top; widths ≈ 8/30/33/40/30/45/50/15/45; autofit rows; freeze rows 1–5 and column A; landscape, fit to 1 page wide, print titles 4:5.

**Done when:** the item count equals `Not Meet` + `Clarification Required` per bidder, there are no #REF!/#VALUE! errors, and a getImage of rows 1–12 looks right.

### 9. Optional downloadable files
Only if asked: fill the template with openpyxl. REFERENCE-type columns get evaluator links only; bidder links are allowed only in Supporting documents. Save to `/tmp`, then copy to `$OUTPUT_DIR` in the same reply. Reopen to verify, and say a visual preview wasn't possible.

### 10. Report (brief, for the committee)
1. Profile used (package, category module, strictness, label status).
2. Table per bidder: Meet / Not Meet / Clarification Required, plus the count of **material deviations**.
3. **Indicative technical position** per bidder (e.g., "material deviations at rows X, Y – likely non-responsive unless clarification confirms otherwise", or "all issues documentary – curable by clarification"). Decision rests with the committee.
4. Key `Deviation` / `Not substantiated` rows (3–6 per bidder).
5. Consistency findings: rows all bidders fail (possible spec issue), and labels harmonised.
6. Judgment points for committee review.
7. Documents not provided; REFERENCE link counts (evaluator / internal / plain).
8. Clarification sheet names; reminder to save and to issue clarifications in writing with a response deadline.

State what you re-read and what you didn't open.

## Anti-patterns (never do)
- Label a row `Meet` because the bidder ticked Yes or wrote "Comply/Meet".
- Write `Comply` / `Not Comply` as determinations, or mix label sets in one sheet.
- Accept brochure "up to" figures for a lower configuration.
- Use one bidder's documents, or knowledge of another bidder's offer, for another bidder.
- Write clarification questions that let a bidder fix a material deviation (e.g., "Please confirm you will supply the higher model/licence").
- Score, rank or compare prices; edit recap sheets without approval; finalise responsiveness.
- Link REFERENCE to bidder URLs, or construct links.

## Examples (illustrative, mixed categories)
- Patient monitor "SpO2 range 0–100 %", offered 70–100 % → `Deviation –` **Not Meet**.
- Ventilator "Tidal volume 20–2000 mL", offered 20–2500 mL, verified in the user manual p.112 → `Verified –` **Meet**.
- Lab analyser "Throughput ≥ 400 tests/h; LIS HL7", 450 tests/h documented but HL7 undocumented → `Partial –` **Not Meet** (interface is a mandatory performance part).
- Pharmaceutical "Remaining shelf life ≥ 75 % at delivery"; statement letter only, no stability data → `Ambiguous –` **Clarification Required**.
- Laptop "OS supported until ≥ 2030"; end-of-support date not evidenced → `Evidence unavailable –` **Clarification Required**.
- Hospital bed "Safe working load ≥ 200 kg"; brochure says 250 kg, manufacturer test report says 180 kg → `Conflict –` **Clarification Required**.
- Any item "230 V ± 10 %, 50 Hz, Type F plug"; 100–240 V AC documented, plug undocumented → `Partial –` **Not Meet**.
- Warranty "≥ 5 years" in a signed letter for this tender → `Verified –` **Meet**. The same figure only restated in the sheet → `Ambiguous –` **Clarification Required**.
- Two bidders both fail the same mandatory feature → report it as a possible restrictive specification; labels unchanged.
