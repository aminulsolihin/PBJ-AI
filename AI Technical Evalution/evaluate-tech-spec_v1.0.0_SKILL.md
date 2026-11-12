---
name: evaluate-tech-spec
description: Evaluate bidder responses against a technical specification / requirements matrix (e.g., medical equipment RFQ) and fill the Evaluator's Note and Determination columns with Comply / Not Comply / Clarification Required.
---

## When to use
- The user selects (or names) a technical specification range in a tender/RFQ workbook and asks to evaluate, assess or score bidder compliance.
- The sheet is a requirements matrix: Row no. | Requirement item | Requirement text, followed by one or more bidder response blocks (Yes/No tick, Device Details, Source Data, Source Data URL) and empty evaluator columns (Evaluator's Note, Evaluator's Determination, Reference).
- Example layout (OAE sheet): spec in A:C; Bidder 1 in D:H with evaluator columns I (Note), J (Determination), K (Reference); Bidder 2 in M:Q with R, S, T. Bidder names are in the header row above the blocks (e.g., row 4).

## Rules (fixed preferences)
- **Output:** write directly into each bidder's Evaluator's Note and Evaluator's Determination columns. Do not create new sheets. Do not touch the bidder response columns, the Reference column, or any columns to the right of the blocks.
- **Labels:** exactly `Comply`, `Not Comply`, `Clarification Required`.
- **Evidence standard: STRICT.** A row counts as `Comply` only if ALL of these hold:
  1. The Yes [√] box is ticked (not the No [x] box),
  2. Device Details gives a concrete answer (specific values, features or quantities, not just "Comply" or "Yes" for a requirement that has a numeric or listed condition), and that answer meets or beats the requirement,
  3. Source Data names a document and section/page (a URL alone with no document/page reference counts as weak evidence; note it).
- Placeholders such as `Enter Responses Here!`, blanks, or a ticked No mean that element is missing.
- **Language:** English for all evaluator notes.

## Steps

### 1. Map the sheet
- Read the selected range plus the full used width of the sheet (use get_range_as_csv in chunks if >100 rows; never dump it all into chat).
- Find: the spec columns (row no., item, requirement), each bidder block and its name, and the evaluator Note/Determination columns for each bidder. Check the sub-header rows (`Yes [√]`, `No [x]`, `Device Details`, `Source Data`, `Source Data URL`, `Evaluator's Note`, `Evaluator's Determination`).
- Classify every row:
  - **Section header:** column C = "REQUIREMENTS" or a group title with blank requirement (e.g., "General", "Cybersecurity Considerations"). Skip it.
  - **Sub-header:** rows with "Yes [√] / No [x]". Skip it.
  - **Note row:** e.g., the "Unless otherwise stated, all specifications constitute minimum performance requirements…" row. Read it and apply it as a rule; don't evaluate it.
  - **N/A row:** requirement is "N/A". Skip it, or write "N/A – not evaluated" with no determination.
  - **Evaluable row:** everything else.
- Done when: you can state the bidder names, their column letters, and the count of evaluable rows.

### 2. Pre-flight check of the evaluator columns
- If any target Note/Determination cell already has content, list the count and a sample and ask the user before overwriting.
- Done when: the target cells are confirmed empty, or the user has approved overwriting.

### 3. Evaluate each row per bidder
Read the requirement type and apply the matching logic:
- **"Required; <condition>"**: check that the stated value meets the condition.
  - Thresholds (≥, ≤, "minimum", "within X hours"): compare the numbers after converting units (Hz↔kHz, g↔kg, mm↔cm, hr↔min).
  - Required ranges (e.g., "1.5 – 12 kHz"): the device range must COVER the whole required range. Example: 0.5–12 kHz → Comply; 2–5 kHz → Not Comply (does not reach 1.5 or 12 kHz).
  - Single required values (e.g., "80 dB peSPL"): the device must offer that value. Watch for unit or reference mismatches (dB SPL vs dB peSPL). If the unit is different or unclear → `Clarification Required`.
  - Multi-part requirements (a/b lists, "one per unit", plug type, voltage): check each part. If any part is missing → `Not Comply`. Name the missing part.
  - Quantities ("per unit", "for 1,000 procedures"): check the quantities stated. If the total is short or not stated → `Not Comply` or `Clarification Required` (use Clarification when a cross-reference to another sheet, e.g. "Proposed Consumables", may hold the number).
- **"Bidder to specify" / "Bidder to provide"**: `Comply` if a specific answer AND a source are given. A generic "Comply" with no detail → `Clarification Required`. Placeholder or blank → `Not Comply`.
- **"If applicable" / "if offered" / "if any"**: an explicit "N/A" or "not offered" with justification is acceptable (`Comply`). A blank → `Clarification Required`.
- **Contradictions**: if the tick says Yes but the details or values contradict the requirement → `Not Comply`. Explain the contradiction.
- **Missing source under strict rules**: a requirement that is met but has no document/page cited → `Not Comply`, with the note "Claim not supported by documentary evidence".
- **Vague marketing text** that restates the requirement without device-specific facts → `Clarification Required`.
- Do not open external URLs (Drive links etc.) unless the user explicitly asks. Judge only the content in the sheet, and say so in the summary.
- Done when: every evaluable row has a determination and a note for every bidder.

### 4. Write the evaluator notes
- Note format, 1–2 sentences: `<Requirement> vs <offered value> → <reason>. Source: <doc/page or "not cited">.`
  - e.g., `Required 1.5–12 kHz; offered 2–5 kHz – does not cover 1.5–2 kHz or 5–12 kHz. Source: brochure (no page).`
  - e.g., `Required ≥500 results; offered >10,000. Source: Technical Manual Annex 1 p.76.`
- Write notes and determinations in batches by section (one set_cell_range call per section) so progress shows up.
- Colour the Determination cells: Comply = light green (#C6EFCE, font #006100); Not Comply = light red (#FFC7CE, font #9C0006); Clarification Required = light yellow (#FFEB9C, font #9C5700). Turn on wrap text for the Note cells.
- Done when: the read-back of the evaluator columns shows no blanks on evaluable rows and only the three allowed labels.

### 5. Verify and report
- Re-read the Determination columns. Count Comply / Not Comply / Clarification Required per bidder with COUNTIF (in your own check, not written to the sheet unless the user asks).
- In chat, report briefly: bidder names, counts per label, and the 3–5 most important Not Comply items (row no. + item). Say that the evaluation is based on the sheet content only and that the linked documents were not opened.
- Done when: the counts reconcile with the number of evaluable rows for each bidder.

## Example
Input row 32: "Frequency Range | Required; 1.5 – 12 kHz."
- Bidder A: ✓, "DPOAE Frequency Range 0.5 – 12 kHz", Technical manual Annex 1 p.76 → **Comply**: "Required 1.5–12 kHz; offered 0.5–12 kHz, covers the range. Source: Technical Manual Annex 1 p.76."
- Bidder B: ✓, "2000 to 5000 Hz", Drive link only → **Not Comply**: "Required 1.5–12 kHz; offered 2–5 kHz, does not cover the full range. Source: URL only, no page cited."
