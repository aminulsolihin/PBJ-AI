# evaluate-tech-spec

A Claude skill for **technical evaluation of bids** in public procurement. It runs inside **Claude in Excel**. For each bidder, it checks every response on a technical specification sheet against the documents that bidder uploaded. It then fills the evaluator columns and drafts two clarification sheets per bidder: an internal one and a bidder-facing one.

It works with any kind of technical specification: medical devices, lab/IVD, pharmaceuticals and consumables, IT, furniture, vehicles/machinery, and works or services.

**Current version: v19.** Skill folder: `evaluate-tech-spec-v19/SKILL.md`.

> **The output is a draft.** The Bid Evaluation Committee makes every decision. The skill is designed so that each determination can be traced, stays neutral, and can be defended in an evaluation report, a complaint review or an audit.

---

## What it does

| Step | Output |
|---|---|
| Profiles the spec sheet | Column map, bidder blocks, row classes (by column B fill and the WT column), label status and counts. This is the only pause for your input. |
| Extracts the evidence | Each bidder document is read once and cached. Scanned pages are OCR'd. Each document is registered with its model, issuer, date, evidence class and any genuine red flags. |
| Checks each coloured row | A label and a short, finding-only note for every row that is evaluated |
| Fills the evaluator columns | **Evaluator's Note**, **Determination** and **REFERENCE** (document and page) |
| Drafts the internal clarification | `AMPC Technical Clarification` listing every Not Meet and Clarification Required row, with a completeness gate |
| Drafts the bidder-facing clarification | `Clarif Bidder <pkg> - <bidder>`: questions plus a response column. It contains no labels or findings. |
| Reports to the committee | A report of 14 lines or fewer: counts, Not Meet rows, key themes, red flags, judgment points and missing documents |

### Labels

| Outcome | Label | Fill / font |
|---|---|---|
| Pass | `Meet` | `#C6EFCE` / `#006100` |
| Fail | `Not Meet` | `#FFC7CE` / `#9C0006` |
| Query | `Clarification Required` | `#FFEB9C` / `#9C5700` |

The labels are fixed. The skill never writes "Comply" or "Not Comply".

### Which rows are evaluated

The skill reads the fill of column B and the WT column.

| Column B fill | Action |
|---|---|
| Green (any shade, **Required**) | Evaluate. V = `P` if Meet, else `F`. |
| Orange `#FFC000` (**Preferred**) | Evaluate. V = `1` or `0`. A Preferred row is never a mandatory failure. |
| White or no fill, with WT = `P/F` | V = `P` (centred). No label, note or reference. Never clarified. |
| White or no fill, with WT header text, blank WT or spec N/A | Write nothing. |
| Header colour or grey note | Write nothing. |

CP formulas are left untouched. Coloured rows without a WT or CP value are reported.

### Decision matrix

Every note starts with a **basis tag**:

| Basis tag | Situation | `strict` (default) | `standard` |
|---|---|---|---|
| `Verified –` | Meets or exceeds; evidence verified | Meet | Meet |
| `Deviation –` | Offered value falls short, or "No" is ticked on a required item | Not Meet | Not Meet |
| `Not substantiated –` | A capability is backed only by a declaration or self-claim, or the cited page doesn't show it | Not Meet for mandatory performance or safety parameters; otherwise Clarification Required | Clarification Required |
| `No response –` | Blank, placeholder, or not ticked | Not Meet | Clarification Required (non-material rows) |
| `Ambiguous –` | Generic wording, or model unclear | Clarification Required | Clarification Required |
| `Conflict –` | Values conflict | Clarification Required | Clarification Required |
| `Evidence unavailable –` | The cited file wasn't uploaded | Clarification Required | Clarification Required |
| `Partial –` | A multi-part requirement is only partly evidenced | Not Meet if a missing part is a mandatory performance, safety, utility or quantity item; otherwise Clarification Required | same |
| `Verified – (N/A justified)` | Conditional row with a justified N/A | Meet | Meet |

Universal checks: model identity; offered configuration only; no "up to" figures; over-specification never offsets a shortfall; local registration only if required at the bid stage; service commitments start at ATC.

### Evidence classes (v17 and later)

The classes guide the reasoning only. They are **never written into notes**.

| Class | Examples | Use |
|---|---|---|
| A: Independent or regulatory | Registration or filing, notified-body certificate, accredited-lab report naming the model, peer-reviewed study using the model | Verifies technical claims on its own |
| B: Manufacturer document | IFU, user or service manual, datasheet, manufacturer test or validation report with method and data | Verifies technical claims if model-specific and consistent |
| C: Manufacturer declaration | Signed letter, self-declared DoC, compatibility statement without data | Supporting only for technical claims |
| D: Bidder self-claim | Bidder letter, bidder calculation, bid-form text, brochure, website, photos | Contractual commitments only (warranty, response times, uptime, training, delivery, quantities, spare parts). **Never for device capability.** |

A **genuine red flag** lowers the evidence by one class. Examples: conflicting values, a sister model only, a report without method or data, a one-line "pass" statement, or a letter citing another tender. A bid-period date on a letter is normal and is not a red flag.

**Rationality checks:** throughput at the maximum run time, UPS runtime against the actual load, quantities as tests per kit × kits, and figures consistent across documents.

**Navigation aids are ignored silently.** Row labels, highlights, comment balloons, boxes, arrows, stamps and single-page excerpt files are pointers for the evaluator. They are never treated as tampering and never mentioned in notes or questions.

### Writing the evaluator note

The note records the finding only. Format:

```
<Tag> Required <X>; offered <Y>[ – <reason/check>].
```

- Document names and pages go in the REFERENCE column, not in the note.
- No process or methodology commentary.
- No evidence-class labels.
- No remarks about markers or highlights.
- No "previously Meet".
- An evidence remark appears only when it changes the outcome, in plain words, for example "manufacturer in-house data only" or "model not named on certificate".
- One or two sentences, neutral, with no adjectives about the bidder.

---

## Requirements

- A Claude **Pro, Max, Team or Enterprise** plan
- The **Claude for Microsoft 365** add-in, from Microsoft AppSource
- A supported Excel: Excel on the web, Excel for Windows (Microsoft 365), or Excel for Mac 16.46 or later
- *Code execution and file creation* turned on in Claude: **Settings › Capabilities**

## Installation

### Option A: upload to claude.ai

1. Download or clone this repository.
2. ZIP the skill folder. The folder name must match the `name` in `SKILL.md`:
   ```
   evaluate-tech-spec-v19/
   └── SKILL.md
   ```
3. In claude.ai, go to **Customize › Skills**, then click **+** › **Create skill** › **Upload a skill**.
4. Upload the ZIP and switch the skill on.

### Option B: from Claude in Excel

Paste the contents of `SKILL.md` into the Claude panel and ask Claude to save it as a skill. Then click **Save to claude.ai** on the review card.

## Usage

Open the package sheet in Excel and type in the Claude panel:

```
/evaluate-tech-spec-v19
```

Then:

1. Confirm the profile (columns, bidders, row classes, labels and strictness). This is the only pause.
2. Upload each bidder's supporting documents, either in separate messages or with the bidder name in each file name. Bidder URLs can't be fetched, so upload the documents instead.
3. Review the determinations and both clarification sheets, then save the workbook.
4. Issue the bidder-facing sheet in writing, with a deadline for the response.

### Clarification sheets

| Sheet | Purpose |
|---|---|
| `AMPC Technical Clarification` (internal) | Every Not Meet and Clarification Required coloured row, with the label, note and a question. It uses your template if you upload one. |
| `Clarif Bidder <pkg> - <bidder>` | Same items and order, with questions only and a blank response column for the bidder. It has no labels or findings. |

Questions are specific and neutral. They ask for the evidence needed to support the offer as submitted (document, page, model named, lab accreditation). They never invite a new model, added items or a price change.

Both sheets pass a gate before they are delivered: the rows match the flagged rows, the counts agree (`n = Not Meet a + Clarification Required b`), no cells are empty, and there are no error values. The bidder sheet's response column must be blank.

### Modes

| Mode | Example prompt |
|---|---|
| Evaluate | `/evaluate-tech-spec-v19` |
| Continue | `continue for other bidders` |
| Recheck (new documents) | `recheck the evaluation` |
| Re-verify self-claims | `re-verify self-declared claims`. It lists the proposed changes, asks once, and applies the same standard to all bidders. |
| Apply white-row rule | `apply the white-row rule` |
| Clarification only / Sync | `generate clarification` or `sync the clarification` |
| Tidy notes | `tidy notes`. It strips process commentary and evidence-class tags from existing notes without changing any label. |

---

## Guardrails

- **Evidence-strict:** a bidder's letter, calculation, brochure or self-declaration never establishes a device capability on its own. A Yes tick is never a Meet by itself.
- **Neutral and consistent:** one standard for every bidder, on every row.
- **No price evaluation.**
- **Confidentiality:** bid data is not sent to the web, other agents or connectors.
- **White rows are not assessed or clarified.** A white row with WT = `P/F` gets V = `P` only.
- **No REFERENCE links to bidder URLs.**
- **No clarification may cure a material deviation.**
- **Rows that hold responses are never deleted.** On a sync, a resolved row is marked `Resolved` and greyed.
- **Token-lean:** documents are read once and cached, output is limited to counts and short snippets, and there is a single execute step per stage.

## Limitations

- AI can make mistakes. Review every determination before it goes into an evaluation report.
- Use trusted workbooks only. Files from outside sources can contain hidden instructions (prompt injection).
- Follow your organisation's policy before uploading tender documents to an AI service. Anthropic advises against using Claude in Excel on highly sensitive or regulated data without proper controls.
- Claude in Excel does not support macros/VBA or Excel data tables.

> ⚠️ **Never commit bid documents, evaluated workbooks or bidder names to this repository.** Bid content is confidential until award.

---

## Changelog

| Version | Change |
|---|---|
| v1 | Basic evaluation from the sheet contents |
| v2 | Checks against uploaded documents; fills REFERENCE |
| v3 | All bidders; clarification list |
| v4 | Downloadable clarification file from the AMPC template |
| v5 | Clarification sheets inside the workbook |
| v6 | Dynamic profiling for any procurement package |
| v7 | Clickable REFERENCE links to Google Drive |
| v8 | REFERENCE links only to the evaluator's own copies |
| v9 | Materiality test, decision matrix, cross-bidder consistency |
| v10 | `Meet / Not Meet` labels, basis tags, category modules for every procurement type, Relabel mode |
| v11 | Always produces an AMPC Technical Clarification with every Not Meet and Clarification Required item, plus a completeness check and sync after changes |
| v12 | Token-lean workflow; handles P/F-scored sheets |
| v13 | Adds a bidder-facing clarification sheet (questions and a response column, no assessment) |
| v14 | Skips optional white rows under PROPOSED DEVICE INFORMATION |
| v15 | Evaluates only coloured requirement rows (column B fill) |
| v16 | White rows get V = P automatically and are never assessed or clarified |
| v17 | Evidence-strict: self-claims and self-declarations never suffice alone; evidence classes A to D |
| v18 | Self-claims are insufficient for device capability; bidder navigation markers are not red flags; evidence-classed notes |
| v19 | Concise, finding-only notes with no process commentary or evidence-class tags; navigation markers ignored silently; Tidy notes mode |

## Contributing

Improvements come from real evaluation work. To propose a change:

1. In Claude, run `/skillify` and describe the change you want.
2. Review the new draft that Claude writes.
3. Open a pull request with the updated `SKILL.md` in a new version folder, and add a row to the changelog.

## License

[Choose a license, e.g. MIT]
