# evaluate-tech-spec

A Claude skill for **technical evaluation of bids** in public procurement. It runs inside **Claude in Excel**. For each bidder, it checks every response on a technical specification sheet against the documents that bidder uploaded. It then fills the evaluator columns and drafts one clarification sheet per bidder.

It works with any kind of technical specification: medical devices, lab/IVD, pharmaceuticals and consumables, IT, furniture, vehicles/machinery, and works or services.

> **The output is a draft.** The Bid Evaluation Committee makes every decision. The skill is designed so that each determination can be traced, stays neutral, and can be defended in an evaluation report, a complaint review or an audit.

---

## What it does

| Step | Output |
|---|---|
| Profiles the spec sheet | Column map, bidder blocks, label status and completeness counts. Pauses for your confirmation. |
| Checks each row against the evidence | A label and a basis-tagged note for every row that can be evaluated |
| Fills the evaluator columns | **Evaluator's Note**, **Determination** and **REFERENCE** |
| Reviews consistency across bidders | The same evidence situation gets the same label for every bidder |
| Drafts clarifications | One `Clarif <pkg> - <bidder>` sheet per bidder (AMPC layout or your own template) |
| Reports to the committee | Counts, material deviations, an indicative technical position, and judgment points |

### Labels

| Outcome | Label | Fill / font |
|---|---|---|
| Pass | `Meet` | `#C6EFCE` / `#006100` |
| Fail | `Not Meet` | `#FFC7CE` / `#9C0006` |
| Query | `Clarification Required` | `#FFEB9C` / `#9C5700` |

### Decision matrix

Every note starts with a **basis tag**:

| Basis tag | Situation | `strict` (default) | `standard` |
|---|---|---|---|
| `Verified –` | Meets or exceeds; evidence verified | Meet | Meet |
| `Deviation –` | Offered value, configuration or tier falls short | Not Meet | Not Meet |
| `Not substantiated –` | Compliance is claimed but the cited document doesn't show it | Not Meet | Clarification Required |
| `No response –` | Blank, placeholder, or not ticked | Not Meet | Clarification Required (non-material rows only) |
| `Ambiguous –` | Generic wording, or unclear unit, variant or tier | Clarification Required | Clarification Required |
| `Conflict –` | Values conflict across documents | Clarification Required | Clarification Required |
| `Evidence unavailable –` | The cited file wasn't uploaded | Clarification Required | Clarification Required |
| `Partial –` | A multi-part requirement is only partly evidenced | Not Meet if a mandatory part is missing; Clarification Required if only its documentation is missing | same |

### Evidence hierarchy

1. Regulatory or legal documents (registration, certificates, type approval)
2. Manufacturer technical documents (IFU/manual, datasheet, test reports)
3. Manufacturer signed declarations
4. Bidder signed statement letters: **service and contract commitments only**
5. Bidder-prepared spec sheets: supporting only
6. Brochures, websites, images: supporting only

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
   evaluate-tech-spec-v10/
   └── SKILL.md
   ```
3. In claude.ai, go to **Customize › Skills**, then click **+** › **Create skill** › **Upload a skill**.
4. Upload the ZIP and switch the skill on.

### Option B: from Claude in Excel

Paste the contents of `SKILL.md` into the Claude panel and ask Claude to save it as a skill. Then click **Save to claude.ai** on the review card.

## Usage

Open the package sheet in Excel and type in the Claude panel:

```
/evaluate-tech-spec-v10
```

Then:

1. Confirm the profile (columns, bidders, labels and strictness).
2. Upload each bidder's supporting documents, either in separate messages or with the bidder name in each file name.
3. *(Optional)* For clickable REFERENCE links, paste links to **your own copies** of the documents as `file name → link` pairs.
4. Review the determinations and clarification sheets, then save the workbook.

### Modes

| Mode | Example prompt |
|---|---|
| Evaluate | `/evaluate-tech-spec-v10` |
| Continue | `continue for other bidders` |
| Recheck | `recheck the evaluation` |
| Clarification only | `generate clarification` |
| Link | paste `file name → link` pairs |
| Relabel | `change labels to Meet / Not Meet` |

---

## Guardrails

- **Write scope:** the skill writes only to the evaluator columns and the clarification sheets. It never edits bidder responses, spec text, price sheets or recap sheets.
- **No price evaluation.** Accessory and BoQ sheets are read only, to cross-check items and quantities.
- **Confidentiality:** bid data is not sent to other agents, connectors, web search or external sites.
- **REFERENCE links:** these point only to the evaluator's own copies or to sheets inside the workbook. They never use bidder URLs.
- **Clarification integrity:** questions may never seek or allow a change to the price or to the substance of the offer.
- **One standard for every bidder,** on every row.

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

## Contributing

Improvements come from real evaluation work. To propose a change:

1. In Claude, run `/skillify` and describe the change you want.
2. Review the new draft that Claude writes.
3. Open a pull request with the updated `SKILL.md` in a new version folder, and add a row to the changelog.

## License

[Choose a license, e.g. MIT]
