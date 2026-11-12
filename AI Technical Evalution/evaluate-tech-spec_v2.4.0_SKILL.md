---
name: evaluate-tech-spec-v14
description: "Token-lean technical bid evaluation for any spec sheet: skips optional white rows under PROPOSED DEVICE INFORMATION, verifies each bidder response against uploaded evidence, writes Meet / Not Meet / Clarification Required with basis-tagged notes (incl. P/F-scored sheets), and builds a gated internal AMPC clarification plus a bidder-facing clarification sheet."
---

## When to use
"evaluate the tech spec / package / bidder X", "/evaluate-tech-spec-v14", recheck, continue for other bidders, (re)build or sync the clarification, "make the bidder clarification sheet".

## Stance
Senior MoH procurement evaluator drafting for the Bid Evaluation Committee. Judge only against stated criteria, same standard for every bidder, evidence-based, neutral, confidential (no bid data to web/agents/connectors). Output is a draft.

## Token rules
- Read sheets/docs **once**; cache to disk (`/tmp/ev_<pkg>.json`: spec rows, bidder responses, doc text per page). Later steps load the cache.
- Print only counts, row lists, ≤200-char snippets around keyword hits.
- Keyword-search docs (`re.finditer`); read a full page only to resolve a conflict.
- OCR scanned PDFs once (pdf2image 150–200 dpi + pytesseract), save the cache after **each file** and stop a loop at ~70 s to avoid timeouts; rotate 90/270° if OCR is garbled.
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

## Rows to skip (not evaluated, not scored, not clarified)
- Section headers, sub-headers, note rows, rows marked N/A in the spec.
- **PROPOSED DEVICE INFORMATION section: rows whose item cell (col B) has white (#FFFFFF) or no fill are optional and don't affect the score — skip them entirely**: write nothing in V/P-F, label, note or reference, and never list them in either clarification sheet (typically Brand/Manufacturer, Model, Country of Origin, Year of 1st Production, Brochure, Picture). Evaluate only the **coloured** rows in that section (e.g., Regulatory Approval, green #92D050). Detect by fill in Step 1, not by row number.
- Brand/Model as submitted still appear in the clarification header rows (formulas), never as item rows.
- Leave existing CP formulas untouched even if they show F for a blank V.

## Decision matrix (note starts with the tag)
| Situation | Tag | strict (default) | standard |
|---|---|---|---|
| Meets/exceeds, evidence verified | `Verified –` | Meet | Meet |
| Offered value/config short, ticked No on required | `Deviation –` | Not Meet | Not Meet |
| Claimed but cited page lacks it | `Not substantiated –` | Not Meet | CR |
| Blank/placeholder/no tick | `No response –` | Not Meet | CR (non-material) |
| Generic wording, unit/variant unclear | `Ambiguous –` | CR | CR |
| Values conflict (bidder vs mfr, or two mfr docs) | `Conflict –` | CR | CR |
| Cited file not uploaded | `Evidence unavailable –` | CR | CR |
| Multi-part partly evidenced | `Partial –` | Not Meet if missing part is mandatory performance/safety/utility/qty, else CR | same |
| Conditional row, justified N/A | `Verified – (N/A justified)` | Meet | Meet |
Preferred/desirable rows: report and score 0 if not met, never a mandatory failure.

Evidence order: regulatory cert > manufacturer manual/datasheet/test report > manufacturer declaration > bidder signed letter (service/contract rows only) > bidder spec sheet > brochure/web. Name the doc + printed page in the note (record printed-vs-PDF page offset).

Universal checks: model/variant identity on every doc; offered configuration only; arithmetic for throughput/quantities; site/supply inside rated range; "up to" figures not accepted; over-spec never offsets a shortfall; local registration only if required at bid stage; letters must cite this tender (flag letters naming another RFB/Pokja); service commitments must start at ATC and cover warranty **and** service contract periods. Judgment points: Class I filing vs registration, self-declared CE, sister-model codes, manuals with bidder-inserted text/row markers, placeholder responses backed by a cited folder.

## Bidder URLs
Links in the Source Data URL column can't be fetched by the assistant (only links the user pastes in chat). If cited files are missing, ask the user to upload them (table: document → rows) or paste the links; never use bidder URLs in REFERENCE.

## Steps

### 1. Profile + document request (single pause)
One execute_office_js returning trimmed strings: title, header rows, section rows, **fill colour of col B for PROPOSED DEVICE INFORMATION rows (skip list)**, bidder block columns (tick Yes/No, details, source, URL), evaluator columns, scoring columns (WT/V/CP), existing labels; count answered/blank/No/no-source rows per bidder. If the working sheet lacks responses, compare with an uploaded bid xlsx and offer to copy only empty cells.
List cited-but-not-uploaded docs and whether the AMPC template is uploaded.
ONE `ask_user_question` (max 3): missing-response handling; where to write; proceed now vs upload more docs.
**Done when:** user answers.

### 2. Extract evidence (code_execution)
`base=os.environ.get('INPUT_DIR','/files/input')`; pdfplumber per page; OCR pages <30 chars; cache `{file:{page:text}}`; ignore uploads unrelated to the package. Build `req` from cached spec rows (exclude skip list): `{row, item, type, target, unit, mandatory, conditional}`.
**Done when:** cache saved; each doc's identity/date/validity noted in ≤1 line.

### 3. Evaluate (reasoning, no per-row tool calls)
Note: `<Tag> Required <X>; offered <Y> – <reason>. <Doc, p.N / what is missing>.` Reference = evaluator doc names + pages. Draft the question for each flagged row in the same pass.
**Done when:** every evaluable (non-skipped) row has label + note + ref.

### 4. Write (one execute_office_js)
- Copy missing bidder responses only if approved (empty cells only).
- Write label/note/ref with label fill; wrap/top. Don't change widths/heights, spec or bidder text, recap/price sheets. Write nothing on skipped rows (clear any earlier evaluator entries there only if the user asks).
- P/F rows → `P` if Meet else `F`; scored Preferred rows → `1`/`0`. Keep formulas.
**Done when:** read-back label counts = array counts; no blanks on evaluable rows; skipped rows untouched.

### 5a. Internal AMPC Technical Clarification (mandatory)
Flagged = rows re-read from the sheet with Not Meet or Clarification Required, **excluding the skip list**.
- Template uploaded → `store_blob` + `insertWorksheetsFromBase64` (calc manual, restore); map by header text.
- Else rebuild: A1 title formula; A2 bidder/brand/model/tender; A3 `Items listed: every row with determination Not Meet or Clarification Required (n = N; Not Meet a + Clarification Required b)`; rows 4–5 headers `Row | PROPOSED DEVICE INFORMATION | Requirements` (#FFFF00, merged 4–5), `BIDDER CLARIFICATION` (#A2C4C9) over `Bidder Response | Supporting documents | PC Assesment | Context`, `AMPC RESPONSE` over `Date | Response`; rows 6–7 brand/model formulas.
- Items from row 8: A–C formulas; D `=IF(tickYes<>"","[Yes [√] ticked] ",IF(tickNo<>"","[No [x] ticked] ","[No tick] "))&TRIM(details)`; E `=source&CHAR(10)&url`; F `<label>\n<tag finding>` with label fill; G question; H–I blank. Set B–E number format to General before writing formulas.
- Questions: specific, neutral; confirm/evidence/clarify the offer **as submitted**; never invite a new model, added items or price change.
- Format: Arial 10, thin borders, wrap/top, autofit item rows, freeze rows 1–5 + col A, landscape fit 1 page wide, print titles 4:5. Name `Clarif <pkg> - <bidder>` (≤31).
- Sync: match items by the **package-sheet row number** (from the A formula's reference / the spec row), never by the displayed value in col A or by clarification-sheet row. Insert missing flagged rows in order; delete unflagged rows only if H/I empty (else mark `Resolved – now Meet`, grey); update F/G and A3. If H/I and bidder G are all empty, a clean rebuild is acceptable and safer than many inserts/deletes.
**Gate:** set(rows)==set(flagged); NM and CR counts match; no empty F/G; no error values; A3 n == items; no skipped row present.

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
Label counts + score total; skipped optional rows (one line); Not Meet rows; key CR themes; judgment points; docs not provided; both sheet names + `n = Not Meet a + CR b = all flagged ✓`; what was re-read. For rechecks list `row: old → new, reason` (grouped). Remind: save; issue the bidder sheet in writing with a deadline; keep the internal sheet confidential.

## Modes
- Continue: Step 1 (skip done bidders) → 6.
- Recheck (new docs uploaded): extract only new files into the cache, re-evaluate affected rows, state changes, then 5a + 5b sync.
- Clarification only / Sync: 5a + 5b. Bidder sheet only: 5b.
- Relabel (Comply→Meet, Not Comply→Not Meet): check dependants first, then 5a sync.

## Never
Evaluate or clarify optional white rows under PROPOSED DEVICE INFORMATION; Meet because bidder ticked Yes; mix label sets; omit any flagged row from either clarification sheet; build lists from memory; delete rows holding an AMPC or bidder response; show labels/findings on the bidder sheet; use bidder URLs as references; let a clarification cure a material deviation; evaluate price.
