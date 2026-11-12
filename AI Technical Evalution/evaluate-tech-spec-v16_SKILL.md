---
name: evaluate-tech-spec-v16
description: "Token-lean technical bid evaluation for any spec sheet: coloured requirement rows (column B fill) are evaluated; white/no-fill item rows get V = P automatically and are not assessed or clarified; writes Meet / Not Meet / Clarification Required with basis-tagged notes (incl. P/F-scored sheets) and builds a gated internal AMPC clarification plus a bidder-facing clarification sheet."
---

## When to use
"evaluate the tech spec / package / bidder X", "/evaluate-tech-spec-v16", recheck, continue for other bidders, (re)build or sync the clarification, "make the bidder clarification sheet", "apply the white-row rule".

## Stance
Senior MoH procurement evaluator drafting for the Bid Evaluation Committee. Judge only against stated criteria, same standard for every bidder, evidence-based, neutral, confidential (no bid data to web/agents/connectors). Output is a draft.

## Token rules
- Read sheets/docs **once**; cache to disk (`/tmp/ev_<pkg>.json`: spec rows, row fills, bidder responses, doc text per page). Later steps load the cache.
- Print only counts, row lists, ≤200-char snippets around keyword hits.
- Keyword-search docs (`re.finditer`); read a full page only to resolve a conflict.
- OCR scanned PDFs once (pdf2image 110–200 dpi + pytesseract); save the cache after **each file**, stop a loop at ~70 s and resume in the next call; rotate 90/270° if OCR is garbled.
- One execute_office_js per stage, data in `blobs` (`eval_<pkg>_<bidder>` = [[row,label,note,ref],...]).
- One pause only (Step 1); then run to the end unless a genuine fork appears.
- One read-back + one getImage (≤15 rows) per sheet. Report ≤ 12 lines.

## Labels (fixed)
| Outcome | Label | Fill / font |
|---|---|---|
| PASS | `Meet` | #C6EFCE / #006100 |
| FAIL | `Not Meet` | #FFC7CE / #9C0006 |
| QUERY | `Clarification Required` | #FFEB9C / #9C5700 |
Never write Comply/Not Comply.

## Row classes — decided by the fill of column B (requirement/item cell)
Read fills in Step 1 with `getRange("B<first>:B<last>").getCellProperties({format:{fill:{color:true}}})`; classify by colour, never by row number. Also read the WT column (e.g., `P/F` or a weight).

| Column B fill | Meaning | Action |
|---|---|---|
| **White (#FFFFFF) or no fill, and WT = `P/F`** (item row) | Optional / "bidder to specify" info, not assessed | **V = `P`** (centred) for every bidder; no label, note or reference; never in clarification sheets |
| White / no fill with WT header text (`WT`, `CP`), blank WT, or spec text `N/A`/`NA` | Sub-header / N/A row | Write nothing |
| Coloured, e.g. green #92D050 | Required (P/F) | Evaluate; V = `P` if Meet else `F` |
| Coloured, e.g. orange #FFC000 | Preferred (weighted) | Evaluate; V = `1`/`0`; never a mandatory failure |
| Section-header colour (e.g. #CAE0F2) or grey note | Header / note | Write nothing |
Confirm the colour legend with the user in Step 1 if the sheet uses different colours. Leave CP formulas untouched (white P/F rows then show CP = P). Brand/Model as submitted still appear in the clarification header rows (formulas), never as item rows. White rows are excluded from label counts.

## Decision matrix (note starts with the tag)
| Situation | Tag | strict (default) | standard |
|---|---|---|---|
| Meets/exceeds, evidence verified | `Verified –` | Meet | Meet |
| Offered value/config short, ticked No on required | `Deviation –` | Not Meet | Not Meet |
| Claimed but cited page lacks it | `Not substantiated –` | Not Meet | CR |
| Blank/placeholder/no tick | `No response –` | Not Meet | CR (non-material) |
| Generic wording, unit/variant/model unclear | `Ambiguous –` | CR | CR |
| Values conflict (bidder vs mfr, or two mfr docs) | `Conflict –` | CR | CR |
| Cited file not uploaded | `Evidence unavailable –` | CR | CR |
| Multi-part partly evidenced | `Partial –` | Not Meet if missing part is mandatory performance/safety/utility/qty, else CR | same |
| Conditional row, justified N/A | `Verified – (N/A justified)` | Meet | Meet |

Evidence order: regulatory cert > manufacturer manual/datasheet/test report > manufacturer declaration > bidder signed letter (service/contract rows only) > bidder spec sheet > brochure/web. Name the doc + printed page in the note.

Universal checks: model/variant identity on every doc (certificate model lists must name the offered model; flag brand-equivalence letters that don't list it); offered configuration only; arithmetic for throughput/quantities; site/supply inside rated range; "up to" figures not accepted; over-spec never offsets a shortfall; local registration only if required at bid stage; letters must cite this tender; service commitments start at ATC and cover warranty **and** service contract periods; clinical-validation rows: note whether evidence is manufacturer-sponsored vs peer-reviewed/independent and whether named criteria (e.g., Meijer, WHO TPP) are addressed. Judgment points: Class I filing vs registration, self-declared CE, sister-model codes, manuals with bidder-inserted text, unreadable accreditation marks.

## Bidder URLs
Links in the Source Data URL column can't be fetched (only links the user pastes in chat). Ask the user to upload missing files (table: document → rows); never use bidder URLs in REFERENCE.

## Steps

### 1. Profile + document request (single pause)
One execute_office_js returning trimmed strings: title, header rows, **column-B fill + WT per row → classes (white P/F → auto-P / Required / Preferred / header)**, bidder block columns (tick Yes/No, details, source, URL), evaluator columns (WT/V/CP/label/note/ref), existing labels; counts per bidder on evaluable rows. If the working sheet lacks responses, compare with an uploaded bid xlsx and offer to copy only empty cells.
List cited-but-not-uploaded docs (evaluable rows only) and whether the AMPC template is uploaded.
ONE `ask_user_question` (max 3): missing-response handling; where to write; proceed now vs upload more docs.
**Done when:** user answers.

### 2. Extract evidence (code_execution)
`base=os.environ.get('INPUT_DIR','/files/input')`; pdfplumber per page; OCR pages <30 chars; cache `{file:{page:text}}`; ignore uploads unrelated to the package. Build `req` only for coloured rows.
**Done when:** cache saved; each doc's identity/date/validity noted in ≤1 line.

### 3. Evaluate (reasoning, no per-row tool calls)
Note: `<Tag> Required <X>; offered <Y> – <reason>. <Doc, p.N / what is missing>.` Reference = evaluator doc names + pages. Draft the question for each flagged row in the same pass.
**Done when:** every coloured row has label + note + ref.

### 4. Write (one execute_office_js)
- Copy missing bidder responses only if approved (empty cells only).
- Coloured rows: label/note/ref with label fill; V per class. Wrap/top. Don't change widths/heights, spec or bidder text, recap/price sheets.
- **White P/F item rows: V = `P` (centred) only.** If earlier runs left a label/note/ref there, clear those (contents + label fill) and remove the rows from the clarification sheets in 5a/5b sync.
**Done when:** read-back: label counts = array counts; no blanks on coloured rows; every white P/F row shows V = P, CP = P and no label.

### 5a. Internal AMPC Technical Clarification (mandatory)
Flagged = rows re-read from the sheet with Not Meet or Clarification Required **and** a coloured column B.
- Template uploaded → `store_blob` + `insertWorksheetsFromBase64` (calc manual, restore); map by header text.
- Else rebuild: A1 title formula; A2 bidder/brand/model/tender; A3 `Items listed: every row with determination Not Meet or Clarification Required (n = N; Not Meet a + Clarification Required b). Rows with white/no fill in column B not assessed (V = P).`; rows 4–5 headers `Row | PROPOSED DEVICE INFORMATION | Requirements` (#FFFF00, merged 4–5), `BIDDER CLARIFICATION` (#A2C4C9) over `Bidder Response | Supporting documents | PC Assesment | Context`, `AMPC RESPONSE` over `Date | Response`; rows 6–7 brand/model formulas, F6 `Brand and model as submitted (optional information – not evaluated).`
- Items from row 8: A–C formulas; D `=IF(tickYes<>"","[Yes [√] ticked] ",IF(tickNo<>"","[No [x] ticked] ","[No tick] "))&TRIM(details)`; E `=source&CHAR(10)&url`; F `<label>\n<tag finding>` with label fill; G question; H–I blank. Set B–E to General before writing formulas.
- Questions: specific, neutral; confirm/evidence/clarify the offer **as submitted**; never invite a new model, added items or price change.
- Format: Arial 10, thin borders, wrap/top, autofit item rows, freeze rows 1–5 + col A, landscape fit 1 page wide, print titles 4:5. Name `Clarif <pkg> - <bidder>` (≤31).
- Sync: match items by the **package-sheet row number** in the A formula (`=…!A<row>`). Delete bidder-sheet rows before internal rows, bottom-up. Insert missing flagged rows in order; delete unflagged rows only if H/I (and bidder G) are empty — else mark `Resolved – now Meet / not assessed`, grey, and tell the user; update F/G and A3; autofit changed rows.
**Gate:** set(rows)==set(flagged); NM and CR counts match; no empty F/G; no error values; A3 n == items; no white row present.

### 5b. Bidder-facing clarification sheet (mandatory)
`Clarif Bidder <pkg> - <bidder>` (≤31), after the internal sheet. No PC Assesment, Context, AMPC Response/Date, labels, findings or "Items listed" note.
- Row 1 title formula (bold 12); row 2 bidder / offered brand–model / tender formula (bold).
- Rows 3–4 headers (bold, centred, wrapped; heights 18 / 52, never autofit): `Row` | `PROPOSED DEVICE INFORMATION` | `Requirements` merged 3–4 #FFFF00; `BID AS SUBMITTED` (D3:E3, #A2C4C9) over `Bidder Response (as submitted)` | `Supporting documents (as submitted)`; `CLARIFICATION` (F3:G3) over `Clarification Question` | `Bidder Response to Clarification` + newline `[Bidder to state the response and the name and page number of the supporting document(s)]`.
- Rows 5–6 brand/model (C5:C6 merged, F5:G6 merged `–` grey #F2F2F2).
- Items from row 7 = internal items in the same order: A–E copy internal A–E formulas; F `='<internal>'!G<n>`; G blank.
- Format: Arial 10, borders A3:G<last>, wrap/top, widths A 36, B 170, C 270, D 270, E 180, F 330, G 330; autofit item rows only; freeze rows 1–4 + col A; landscape fit 1 wide; print titles 3:4.
- Sync with 5a; never touch filled G cells.
**Gate:** items == internal items (same order); no empty F; G blank on creation; no error values; no label/assessment text. getImage rows 1–12 of both sheets.

### 6. Report (≤12 lines)
Label counts + score total (coloured rows); white rows set to P (count); Not Meet rows; key CR themes; judgment points; docs not provided; both sheet names + `n = Not Meet a + CR b = all flagged ✓`; what was re-read. For rechecks list `row: old → new, reason` (grouped). Remind: save; issue the bidder sheet in writing with a deadline; keep the internal sheet confidential.

## Modes
- Continue: Step 1 (skip done bidders) → 6.
- Recheck (new docs): extract only new files into the cache, re-evaluate affected coloured rows, state changes, then 5a + 5b sync.
- Apply white-row rule to an existing evaluation: Step 1 class map → Step 4 (V = P on white P/F rows, clear any labels) → 5a + 5b sync → 6.
- Clarification only / Sync: 5a + 5b. Bidder sheet only: 5b.
- Relabel (Comply→Meet, Not Comply→Not Meet): check dependants first, then 5a sync.

## Never
Assess, label or clarify rows whose column B is white or unfilled (they only get V = P); write P on header/WT/N/A rows; Meet because bidder ticked Yes; mix label sets; omit any flagged coloured row from either clarification sheet; build lists from memory; delete rows holding an AMPC or bidder response; show labels/findings on the bidder sheet; use bidder URLs as references; let a clarification cure a material deviation; evaluate price.
