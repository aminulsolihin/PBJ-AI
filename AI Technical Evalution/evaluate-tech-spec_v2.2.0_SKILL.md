---
name: evaluate-tech-spec-v12
description: "Token-lean technical bid evaluation for any spec sheet: verifies each bidder response against uploaded evidence, writes Meet / Not Meet / Clarification Required with a basis-tagged note and reference (incl. P/F-scored sheets), and builds a gated AMPC Technical Clarification of every flagged row."
---

## When to use
"evaluate the tech spec / package / bidder X", "/evaluate-tech-spec-v12", recheck, continue for other bidders, (re)build or sync the clarification.

## Stance
Senior MoH procurement evaluator drafting for the Bid Evaluation Committee. Judge only against stated criteria, same standard for every bidder, evidence-based, neutral, confidential (no bid data to web/agents/connectors; never open bidder URLs). Output is a draft.

## Token rules (follow throughout)
- Read sheets/docs **once**; cache to disk (`/tmp/ev_<pkg>.json`: spec rows, bidder responses, doc text per page). Later steps load the cache, never re-read.
- Print only: counts, row lists, ≤200-char snippets around keyword hits. Never print whole pages, sheets or JSON.
- Keyword-search docs (`re.finditer`) instead of reading pages in full; read a full page only to resolve a conflict.
- OCR scanned PDFs once (pdf2image 200 dpi + pytesseract), cache text.
- Write with **one execute_office_js per stage** using data stashed in `blobs` (`eval_<pkg>_<bidder>` = [[row,label,note,ref],...]); no per-row tool calls.
- One pause only (Step 1). After that run to the end unless a genuine fork appears.
- Verify with one read-back + one getImage (≤15 rows) per sheet.
- Report ≤ 12 lines.

## Labels (fixed)
| Outcome | Label | Fill / font |
|---|---|---|
| PASS | `Meet` | #C6EFCE / #006100 |
| FAIL | `Not Meet` | #FFC7CE / #9C0006 |
| QUERY | `Clarification Required` | #FFEB9C / #9C5700 |
Never write Comply/Not Comply.

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
| Spec row N/A | note `N/A – not evaluated.`, no label | | |
Preferred/desirable rows: report, never a mandatory failure.

Evidence order: regulatory cert > manufacturer manual/datasheet/test report > manufacturer declaration > bidder signed letter (service/contract rows only) > bidder spec sheet > brochure/web. Name the doc + printed page in the note.

Universal checks: model/variant identity on every doc; offered configuration only (standard vs optional); arithmetic for throughput/quantities; site/supply inside rated range; "up to" brochure figures not accepted; over-spec never offsets a shortfall; local registration only if spec requires it at bid stage. Flag as judgment points: Class I filings vs registration, self-declared CE, sister-model codes, manuals containing bidder-inserted text/row markers.

## Steps

### 1. Profile + document request (single pause)
One execute_office_js returning trimmed strings: title, header rows, section rows, bidder block columns (tick Yes/No, details, source, URL), evaluator columns, scoring columns (WT/V/CP) and existing labels; count answered/blank/No/no-source rows per bidder. If the working sheet lacks responses, compare with an uploaded bid xlsx (openpyxl) and offer to copy only empty cells.
List cited-but-not-uploaded docs, and whether the AMPC template is uploaded.
Ask in ONE `ask_user_question` (max 3 questions): missing responses handling; where to write (label/note/ref columns; P/F or score column mapping); proceed now vs upload more docs.
**Done when:** user answers.

### 2. Extract evidence (one code_execution)
`base=os.environ.get('INPUT_DIR','/files/input')`; pdfplumber text per page; OCR pages with <30 chars; cache `{file:{page:text}}`. Silence pdfminer. Print per file: name, pages, first 100 chars only.
Build `req` list from cached spec rows: `{row, item, type, target, unit, mandatory, conditional}` (types: NUMERIC_MIN/MAX, RANGE_COVER, SITE_WITHIN, ENUM, FEATURE, LIST_ALL, QUANTITY, SPECIFY, CONDITIONAL, SERVICE, COMPLIANCE_DOC).
**Done when:** cache saved; doc identity/date/validity noted in ≤1 line each.

### 3. Evaluate (reasoning, no tool calls per row)
For each evaluable row: apply type rule + matrix; note format
`<Tag> Required <X>; offered <Y> – <reason>. <Doc, p.N / what is missing>.`
Reference = evaluator doc names + pages (never bidder URLs; evaluator Drive links only if the user supplied them).
Build the array and the clarification question per flagged row in the same pass.
**Done when:** every evaluable row has label+note+ref.

### 4. Write (one execute_office_js)
- If approved: copy missing bidder responses (empty cells only), formats from a filled row.
- Write label/note/ref; label fill per table; wrap/top. Don't change widths/heights, spec text, bidder text, recap/price sheets.
- P/F-scored sheets: P/F rows → `P` if Meet else `F`; scored Preferred rows → `1` if Meet else `0` (CP formula multiplies by WT). Leave existing formulas.
- Stash array to `blobs`.
**Done when:** read-back shows counts per label = array counts, no blanks on evaluable rows.

### 5. AMPC Technical Clarification (mandatory; one execute_office_js)
Flagged = rows re-read from the sheet with label Not Meet or Clarification Required (all sections, incl. brand/model rows).
- Template uploaded → `store_blob` + `insertWorksheetsFromBase64` (calc mode manual, restore after); map columns by header text.
- Else rebuild: A1 title formula, A2 bidder/brand/model/tender, A3 `Items listed: every row with determination Not Meet or Clarification Required (n = N)`; rows 4–5 headers `Row | PROPOSED DEVICE INFORMATION | Requirements` (#FFFF00, merged 4–5), `BIDDER CLARIFICATION` (#A2C4C9) over `Bidder Response | Supporting documents | PC Assesment | Context`, `AMPC RESPONSE` over `Date | Response`; rows 6–7 brand/model formulas.
- Items from row 8: A–C formulas to row/item/requirement; D `=IF(tickYes<>"","[Yes [√] ticked] ",IF(tickNo<>"","[No [x] ticked] ","[No tick] "))&TRIM(details)`; E `=source&CHAR(10)&url`; F `<label>\n<tag finding>` with label fill; G question; H–I blank.
- Questions: specific, neutral, ask to confirm/evidence/clarify the offer **as submitted**; never invite a new model, added items or price change. Deviation → "Please confirm …"; No response → "No response was provided. Please state …"; Conflict → quote both values; Evidence unavailable → request the cited doc; Not substantiated → request mfr doc + page.
- Format: Arial 10, thin borders, wrap/top, autofit rows, freeze rows 1–5, landscape fit 1 page wide, print titles 4:5. Sheet name `Clarif <pkg> - <bidder>` ≤31 chars. HYPERLINK()/eval are blocked.
- If the sheet exists → sync instead: insert missing flagged rows in row order, delete unflagged rows with empty H/I (else mark `Resolved – now Meet`, grey), update F/G and A3. Never touch H/I.
**Gate (same call, return result):** set(clarif rows)==set(flagged); Not Meet and CR counts match sheet; no empty F/G; no #REF!/#VALUE!/#NAME?; A3 n == items. getImage rows 1–12.
**Done when:** gate passes.

### 6. Report (≤12 lines)
Label counts + score total; Not Meet rows (one line each); key CR themes; judgment points; docs not provided; clarification sheet name + `n = Not Meet a + CR b = all flagged ✓`; what was re-read. Remind: save; issue clarifications in writing with deadline.

## Modes
- Continue: Step 1 (skip done bidders) → 6.
- Recheck: reload cache, re-verify cited pages, state any change `row: old → new, reason`, then Step 5 sync.
- Clarification only / Sync: Step 5.
- Relabel (Comply→Meet, Not Comply→Not Meet): check dependants (COUNTIF, CF, validation) first, then Step 5 sync.

## Never
Meet because bidder ticked Yes; mix label sets; omit any flagged row from the clarification; build the list from memory; delete rows holding an AMPC response; use bidder URLs as references; let a clarification cure a material deviation; evaluate price.
