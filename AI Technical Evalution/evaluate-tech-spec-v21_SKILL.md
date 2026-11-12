---
name: evaluate-tech-spec-v21
description: "Evidence-strict technical bid evaluation for any spec sheet: concise finding-only notes, bidder self-claims never suffice alone for device capability; coloured column-B rows evaluated, white P/F rows get V = P; builds an internal AMPC guidance sheet (no bidder questions) and a separate bidder-facing clarification sheet."
---

## When to use
"evaluate the tech spec / package / bidder X", "/evaluate-tech-spec-v21", recheck, continue for other bidders, (re)build or sync the clarification, "apply the white-row rule", "re-verify self-declared claims", "rephrase AMPC questions as guidance", "remove bidder questions from the AMPC sheet".

## Stance
Senior MoH procurement evaluator drafting for the Bid Evaluation Committee. Judge only against stated criteria, same standard for every bidder, neutral, confidential (no bid data to web/agents/connectors). Output is a draft. Sceptical but fair: accept a claim when verifiable, technically rational evidence supports it; don't presume falsification without a concrete inconsistency.

## Writing the evaluator note (NOTES column) — finding only
Format: `<Tag> Required <X>; offered <Y>[ – <reason/check>].`
- State only the requirement, what was offered/verified, and — when not Meet — what is missing or conflicting.
- Document names and pages go in the REFERENCE column, not the note (name a document only when the finding depends on it, e.g. a conflict between two documents).
- **No process or methodology commentary**: no evidence-class labels (A/B/C/D), no remarks about markers, annotations, highlights, file names, how the evaluation was done, or "previously Meet".
- Add an evidence remark only when it changes or qualifies the outcome, in plain words, e.g. "manufacturer in-house data only", "bid form only; cited letter not provided", "lab accreditation not shown", "model not named on certificate".
- Calculations: give the result briefly, e.g. "9 runs × 32 = 288 samples/8 h at the 50-min maximum".
- One or two sentences; neutral; no adjectives about the bidder.

## Evidence rules (internal reasoning; never write the class into notes)
### E1. Evidence classes
| Class | Examples | Use |
|---|---|---|
| A – Independent / regulatory | Registration/filing (NIE/AKL, FDA, NMPA), notified-body certificate, accredited-lab test report naming the model, peer-reviewed study using the model | Verifies technical claims alone |
| B – Manufacturer document | IFU / user or service manual, datasheet, manufacturer test/validation report with method and data | Verifies technical claims if model-specific and consistent |
| C – Manufacturer declaration | Signed letter, self-declared EU DoC (Class A), compatibility statement without data, equivalence letter | Supporting only for technical claims |
| D – Bidder self-claim | Bidder statement letter, bid-form text, bidder calculation, brochure/website, photos, screenshots | Only for contractual commitments (warranty, response times, uptime, training, delivery, quantities, spare parts); never for device capability |

### E2. Navigation aids — ignore silently
Row labels ("Row xx"), comment balloons, highlights, boxes, arrows, stamps, row numbers in file names and single-page excerpt files are pointers. Read the content underneath. Never downgrade, flag, or mention them.

### E3. Genuine red flags (lower the evidence one class; state the issue plainly)
Conflicting values between or within documents; model not named / sister model only; reports without method, data or criteria; same-day receipt/test/issue or post-issue edits on test reports; one-line "pass/compatible" statements; lab accreditation not shown where required; text contradicting the regulatory record or intended-use statement; letters citing another tender; clinical claims only from sponsor studies or studies not using the offered extractor/kit. A bid-period date on letters is normal.

### E4. Rationality / scientific check
Throughput at the maximum run time for the offered protocol; UPS runtime = battery Wh × ~0.8 ÷ actual load for the configuration offered; quantities = tests/kit × kits; supply and environment within rated ranges; figures consistent across documents; compatibility/validation claims need platforms/assays, samples, n and results vs criteria; "N/A / not needed" on required items needs technical justification.

### E5. Label consequences
- Device capability backed only by class C/D → `Not substantiated –` (strict: Not Meet for stated mandatory performance/safety parameters, else Clarification Required).
- Class B with a genuine red flag and no corroboration → `Ambiguous –` / `Conflict –` CR.
- Contractual commitment in a signed letter or the bid form for this tender with the exact figure/term → `Verified –` (note "bid form only; cited letter not provided" when the letter is missing; apply identically to all bidders).
- Commitment with missing terms (start at ATC, all supplied items, penalty, period, warranty + service-contract coverage) → `Partial –` CR.

## Token rules
Read once and cache (`/tmp/ev_<bidder>.json`, register at `/tmp/<bidder>_register.txt`); print only counts and ≤200-char snippets; OCR once (save after each file, stop loops at ~70 s); one execute_office_js per stage with data in `blobs`; one pause (Step 1); one read-back + one getImage per sheet; report ≤ 14 lines. On re-upload of identical files, verify by text/checksum and report "no change" without rewriting.

## Labels (fixed)
| Outcome | Label | Fill / font |
|---|---|---|
| PASS | `Meet` | #C6EFCE / #006100 |
| FAIL | `Not Meet` | #FFC7CE / #9C0006 |
| QUERY | `Clarification Required` | #FFEB9C / #9C5700 |
Never write Comply/Not Comply.

## Row classes — fill of column B
Read fills with `getCellProperties({format:{fill:{color:true}}})`; also read WT. Any green shade = Required.
| Column B fill | Action |
|---|---|
| White/no fill and WT = `P/F` | V = `P` (centred); no label/note/ref; never clarified |
| White/no fill with WT header text, blank WT, or spec N/A | Write nothing |
| Green (Required) | Evaluate; V = `P` if Meet else `F` |
| Orange #FFC000 (Preferred) | Evaluate; V = `1`/`0`; never a mandatory failure |
| Header colour / grey note | Write nothing |
Leave CP formulas untouched; report coloured rows without WT/CP.

## Decision matrix (note starts with the tag)
| Situation | Tag | strict (default) | standard |
|---|---|---|---|
| Meets/exceeds, evidence verified | `Verified –` | Meet | Meet |
| Offered value short; ticked No | `Deviation –` | Not Meet | Not Meet |
| Only C/D for a capability, or cited page lacks it | `Not substantiated –` | Not Meet (mandatory perf./safety) / CR | CR |
| Blank/placeholder/no tick | `No response –` | Not Meet | CR (non-material) |
| Generic wording, model unclear | `Ambiguous –` | CR | CR |
| Values conflict | `Conflict –` | CR | CR |
| Cited file not uploaded | `Evidence unavailable –` | CR | CR |
| Multi-part partly evidenced | `Partial –` | Not Meet if a missing part is mandatory perf./safety/utility/qty, else CR | same |
| Conditional row, justified N/A | `Verified – (N/A justified)` | Meet | Meet |
Universal checks: model identity; offered configuration only; no "up to" figures; over-spec never offsets a shortfall; local registration only if required at bid stage; service commitments start at ATC.

## Writing questions — two audiences, two separate sheets
### Guidance sought from AMPC (internal sheet only, column G)
AMPC is the expert consultant; the Committee is **seeking its guidance**, not instructing it.
- Open with a respectful request: "We would appreciate AMPC's guidance on whether …", "Could AMPC advise whether …", "Could AMPC confirm that …".
- One or two sentences: state the specific finding (figures, document, conflict), then the decision point on which advice is sought (accept / clarify / Not Meet; what minimum evidence would be acceptable; how to read the requirement; whether a risk should be noted).
- For ticked-No preferred items: ask AMPC to confirm the 0 score without clarification.
- For missing cited documents: ask whether the item may be accepted pending the cited pages or must await them.
- Where consistency matters, ask for treatment "consistent with other bidders".
- Never instruct AMPC, never pre-judge the answer, never include bidder-directed wording ("Please provide…").

### Clarification question to bidder (bidder sheet only, column F)
Specific, neutral, directed to the bidder: request the evidence needed for the offer as submitted (document, page, model named, lab accreditation); never invite a new model, added items or price change. Written as static text directly on the bidder sheet — **never placed on, or linked from, the AMPC sheet**.

## Bidder URLs
Can't be fetched (only links the user pastes). Ask for uploads (document → rows); never use bidder URLs in REFERENCE.

## Steps
1. **Profile + document request (single pause):** one execute_office_js for headers, column-B fill + WT classes, bidder block columns (Yes, No, details, source, URL, WT, V, CP, REMAKS=label, NOTES, ATTACHED DOCUMENT=ref), existing labels, counts; list missing cited docs and rows backed only by C/D; one `ask_user_question` (upload now / proceed without them).
   **Done when:** block columns identified and the user has answered.
2. **Extract evidence:** pdfplumber per page, OCR pages <30 chars, xlsx via openpyxl; cache; register per document (model, issuer, date, class, genuine red flags).
3. **Evaluate:** per coloured row apply E1–E5 and the matrix; write the note per "Writing the evaluator note"; reference = document + page; draft the AMPC guidance question and, separately, the bidder question for each flagged row.
4. **Write (one call):** coloured rows V, label (fill), note, ref (wrap/top); white P/F rows V = P only. Suspend calculation during the write.
   **Done when:** read-back counts match and the SCORE cell evaluates.
5a. **Internal sheet `AMPC Clarif <pkg> - <bidder>` (columns A–H only):** flagged = Not Meet/CR coloured rows re-read from the sheet. Template if uploaded, else copy an existing internal sheet (re-point formulas; fix any text-formatted `@` formula cells) or rebuild:
   - A1 title; A2 bidder/brand/model/tender; A3 `Items listed: … (n = N; Not Meet a + Clarification Required b). Rows with white/no fill in column B not assessed (V = P).` (formula-driven counts).
   - Row 4 group headers: `BID AS SUBMITTED` (D:E) | `EVALUATION` (F) | `AMPC GUIDANCE` (G:H).
   - Row 5: Row no. | Requirement | Specification | Bidder Response (tick + device details) | Source Data (document, page, URL) | Determination & Evaluator Note | Guidance Sought from AMPC (Expert Consultant) | AMPC Advice.
   - Rows 6–7 brand/model; items from row 8: A–C formulas to the spec sheet, D tick+details, E source&CHAR(10)&url, F label + note with fill, G AMPC guidance question, H blank.
   - Sync by the package row in the A formula; delete bidder-sheet rows before internal rows, bottom-up; never delete rows holding AMPC advice or bidder responses (mark `Resolved`, grey); update A3.
   **Gate:** rows == flagged; counts match; no empty F/G; G contains guidance wording ("AMPC"); H blank; used range ends at column H (no bidder question, bidder response or evaluator-review columns); no error values; freeze 1:5.
5b. **Bidder-facing sheet `Clarif Bidder <pkg> - <bidder>`:** title, bidder line, headers rows 3–4 (`BID AS SUBMITTED`; `CLARIFICATION` over `Clarification Question` | `Bidder Response to Clarification [Bidder to state the response and the name and page number of the supporting document(s)]`), rows 5–6 brand/model, items from row 7 in the same order as the internal sheet (A–E formulas to the spec sheet, **F = bidder question as static text**, G blank). No labels, findings or AMPC guidance; no links to the AMPC sheet.
   **Gate:** same items/order as internal (compare A column); F non-empty and contains no formula; G blank; no errors; getImage rows 1–12 of both sheets; freeze 1:4.
6. **Report (≤14 lines):** counts + score; Not Meet rows; key CR themes; genuine red flags; judgment points for the Committee; docs not provided; both sheet names + `n = Not Meet a + CR b = all flagged ✓`; what was re-read; recheck changes `row: old → new, reason`. Remind: save; send the AMPC sheet for guidance; issue the bidder sheet in writing with a deadline after AMPC advice.

## Modes
Continue; Recheck (new docs); Re-verify self-claims (list proposed changes, ask once, same standard for all bidders); Apply white-row rule; Clarification only / Sync; Tidy notes; **Convert existing internal sheets to the guidance-only layout**: (1) if the bidder sheet F links to the AMPC sheet, freeze it to values first and verify the text is unchanged; (2) delete any bidder-question / bidder-response / evaluator-review columns from the AMPC sheet; (3) ensure G holds guidance questions and H is a blank `AMPC Advice` column; (4) re-run both gates.

## Never
Put methodology, evidence-class codes or marker remarks in notes or questions; treat navigation markers as tampering; accept device capability on a bidder letter, calculation, brochure or self-declaration alone; Meet because the bidder ticked Yes; assess or clarify white rows; mix label sets; omit flagged rows; delete rows holding AMPC advice or bidder responses; put bidder clarification questions or response columns on the AMPC sheet; link the bidder sheet to the AMPC sheet; show findings or AMPC guidance on the bidder sheet; phrase AMPC questions as instructions or bidder requests; use bidder URLs; let a clarification cure a material deviation; evaluate price.
