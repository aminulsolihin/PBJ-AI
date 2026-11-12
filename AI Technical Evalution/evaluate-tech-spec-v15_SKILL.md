---
name: evaluate-tech-spec-v15
description: "Token-lean technical bid evaluation for any spec sheet: evaluates only coloured requirement rows (column B fill; white/no-fill rows skipped), verifies each bidder response against uploaded evidence, writes Meet / Not Meet / Clarification Required with basis-tagged notes (incl. P/F-scored sheets), and builds a gated internal AMPC clarification plus a bidder-facing clarification sheet."
---

## When to use
"evaluate the tech spec / package / bidder X", "/evaluate-tech-spec-v15", recheck, continue for other bidders, (re)build or sync the clarification, "make the bidder clarification sheet", "apply the white-row skip".

## Stance
Senior MoH procurement evaluator drafting for the Bid Evaluation Committee. Judge only against stated criteria, same standard for every bidder, evidence-based, neutral, confidential (no bid data to web/agents/connectors). Output is a draft.

## Token rules
- Read sheets/docs **once**; cache to disk (`/tmp/ev_<pkg>.json`: spec rows, row fills, bidder responses, doc text per page). Later steps load the cache.
- Print only counts, row lists, ≤200-char snippets around keyword hits.
- Keyword-search docs (`re.finditer`); read a full page only to resolve a conflict.
- OCR scanned PDFs once (pdf2image 150–200 dpi + pytesseract); save the cache after **each file**, stop a loop at ~70 s; rotate 90/270° if OCR is garbled.
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

## Which rows to evaluate — decided by the fill of column B (the requirement/item cell)
Read fills in Step 1 with `getRange("B<first>:B<last>").getCellProperties({format:{fill:{color:true}}})` and build the row classes from colour, never from row numbers.

| Column B fill | Meaning | Action |
|---|---|---|
| **White (#FFFFFF) or no fill** | Optional / "bidder to specify" information, not scored | **Skip entirely** |
| Coloured, e.g. green #92D050 | Required (P/F) | Evaluate; V = `P`/`F` |
| Coloured, e.g. orange #FFC000 | Preferred (weighted) | Evaluate; V = `1`/`0`; never a mandatory failure |
| Section-header colour, e.g. light blue #CAE0F2; grey note rows | Header / note | Skip |
Confirm the colour legend with the user in Step 1 if the sheet uses different colours.

**Skipping means:** write nothing in V, label, note or reference; leave existing CP formulas as they are (report that CP shows F for a blank V); never list the row in either clarification sheet; leave out of counts and scores. Brand/Model as submitted still appear in the clarification header rows (formulas), never as item rows. Rows marked N/A in the spec are skipped too.

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

Evidence order: regulatory cert > manufacturer manual/datasheet/test report > manufacturer declaration > bidder signed letter (service/contract rows only) > bidder spec sheet > brochure/web. Name the doc + printed page in the note (record printed-vs-PDF page offset).

Universal checks: model/variant identity on every doc; offered configuration only; arithmetic for throughput/quantities; site/supply inside rated range; "up to" figures not accepted; over-spec never offsets a shortfall; local registration only if required at bid stage; letters must cite this tender (flag letters naming another RFB/Pokja); service commitments must start at ATC and cover warranty **and** service contract periods. Judgment points: Class I filing vs registration, self-declared CE, sister-model codes, manuals with bidder-inserted text/row markers, placeholder responses backed by a cited folder.

## Bidder URLs
Links in the Source Data URL column can't be fetched (only links the user pastes in chat). If cited files are missing, ask the user to upload them (table: document → rows) or paste the links; never use bidder URLs in REFERENCE.

## Steps

### 1. Profile + document request (single pause)
One execute_office_js returning trimmed strings: title, header rows, **column-B fill per row → classes (evaluate Required / evaluate Preferred / skip)**, bidder block columns (tick Yes/No, details, source, URL), evaluator columns, scoring columns (WT/V/CP), existing labels; counts per bidder on evaluable rows only. If the working sheet lacks responses, compare with an uploaded bid xlsx and offer to copy only empty cells.
List cited-but-not-uploaded docs (evaluable rows only) and whether the AMPC template is uploaded.
ONE `ask_user_question` (max 3): missing-response handling; where to write; proceed now vs upload more docs.
**Done when:** user answers.

### 2. Extract evidence (code_execution)
`base=os.environ.get('INPUT_DIR','/files/input')`; pdfplumber per page; OCR pages <30 chars; cache `{file:{page:text}}`; ignore uploads unrelated to the package. Build `req` only for evaluable rows: `{row, item, type, target, unit, mandatory, conditional}`.
**Done when:** cache saved; each doc's identity/date/validity noted in ≤1 line.

### 3. Evaluate (reasoning, no per-row tool calls)
Note: `<Tag> Required <X>; offered <Y> – <reason>. <Doc, p.N / what is missing>.` Reference = evaluator doc names + pages. Draft the question for each flagged row in the same pass.
**Done when:** every evaluable row has label + note + ref; skipped rows have none.

### 4. Write (one execute_office_js)
- Copy missing bidder responses only if approved (empty cells only).
- Write label/note/ref with label fill; wrap/top. Don't change widths/heights, spec or bidder text, recap/price sheets.
- Required rows → `P` if Meet else `F`; Preferred rows → `1`/`0`. Keep formulas.
- **Skipped rows:** write nothing; if earlier runs left evaluator entries there, clear contents and the label fill (V, label, note, ref only) and remove them from the clarification sheets in 5a/5b sync.
**Done when:** read-back label counts = array counts; no blanks on evaluable rows; skipped rows blank.

### 5a. Internal AMPC Technical Clarification (mandatory)
Flagged = rows re-read from the sheet with Not Meet or Clarification Required **and** an evaluable column-B colour.
- Template uploaded → `store_blob` + `insertWorksheetsFromBase64` (calc manual, restore); map by header text.
- Else rebuild: A1 title formula; A2 bidder/brand/model/tender; A3 `Items listed: every row with determination Not Meet or Clarification Required (n = N; Not Meet a + Clarification Required b). Rows with white/no fill in column B not evaluated.`; rows 4–5 headers `Row | PROPOSED DEVICE INFORMATION | Requirements` (#FFFF00, merged 4–5), `BIDDER CLARIFICATION` (#A2C4C9) over `Bidder Response | Supporting documents | PC Assesment | Context`, `AMPC RESPONSE` over `Date | Response`; rows 6–7 brand/model formulas, F6 `Brand and model as submitted (optional information – not evaluated).`
- Items from row 8: A–C formulas; D `=IF(tickYes<>"","[Yes [√] ticked] ",IF(tickNo<>"","[No [x] ticked] ","[No tick] "))&TRIM(details)`; E `=source&CHAR(10)&url`; F `<label>\n<tag finding>` with label fill; G question; H–I blank. Set B–E to General before writing formulas.
- Questions: specific, neutral; confirm/evidence/clarify the offer **as submitted**; never invite a new model, added items or price change.
- Format: Arial 10, thin borders, wrap/top, autofit item rows, freeze rows 1–5 + col A, landscape fit 1 page wide, print titles 4:5. Name `Clarif <pkg> - <bidder>` (≤31).
- Sync: match items by the **package-sheet row number** in the A formula (`=…!A<row>`), never by displayed col-A value or clarification-sheet row. Delete bidder-sheet rows before internal rows. Insert missing flagged rows in order; delete unflagged/skipped rows only if H/I (and bidder G) are empty — else mark `Resolved – not evaluated / now Meet`, grey, and tell the user; update F/G and A3. If all H/I and bidder G are empty, a clean rebuild is acceptable.
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
Label counts + score total (evaluable rows only); skipped rows by colour (one line); Not Meet rows; key CR themes; judgment points; docs not provided; both sheet names + `n = Not Meet a + CR b = all flagged ✓`; what was re-read. For rechecks list `row: old → new, reason` (grouped). Remind: save; issue the bidder sheet in writing with a deadline; keep the internal sheet confidential.

## Modes
- Continue: Step 1 (skip done bidders) → 6.
- Recheck (new docs): extract only new files into the cache, re-evaluate affected evaluable rows, state changes, then 5a + 5b sync.
- Apply skip rule to an existing evaluation: Step 1 fill map → Step 4 clear skipped rows → 5a + 5b sync → 6.
- Clarification only / Sync: 5a + 5b. Bidder sheet only: 5b.
- Relabel (Comply→Meet, Not Comply→Not Meet): check dependants first, then 5a sync.

## Never
Evaluate, score or clarify rows whose column B is white or unfilled; Meet because bidder ticked Yes; mix label sets; omit any flagged evaluable row from either clarification sheet; build lists from memory; delete rows holding an AMPC or bidder response; show labels/findings on the bidder sheet; use bidder URLs as references; let a clarification cure a material deviation; evaluate price.
