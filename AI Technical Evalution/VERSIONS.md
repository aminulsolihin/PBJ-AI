# evaluate-tech-spec: version history

Skill files in this folder are named `evaluate-tech-spec_v<MAJOR>.<MINOR>.<PATCH>_SKILL.md`. The version number was assigned from what each file actually does, compared with the file before it.

The `name:` inside each file is unchanged, for example `evaluate-tech-spec-v27`. That is the name the skill has in claude.ai and the slash command you type (`/evaluate-tech-spec-v27`). Skill names can't contain dots, so the semantic version lives in the file name only.

## How the numbers are assigned

| Part | Raised when | Example |
|---|---|---|
| **MAJOR** | The evaluation contract changes: the determination labels, or the evaluator columns written into each bidder block. Workbooks evaluated with the previous version are not compatible. | `Comply` → `Meet` labels; a new AI Evaluation column set |
| **MINOR** | A new capability, rule or stricter standard is added, and the outputs stay compatible. The clarification sheets count here, because they are rebuilt as drafts on every run. | Bidder-facing clarification sheet; export to Google Drive |
| **PATCH** | A fix or narrowing of the previous version, with no new capability. | Navigation markers no longer treated as red flags |

## Versions

| Version | Former name | Type | What changed |
|---|---|---|---|
| [1.0.0](evaluate-tech-spec_v1.0.0_SKILL.md) | v1 (`evaluate-tech-spec`) | first release | Fills Evaluator's Note and Determination with `Comply` / `Not Comply` / `Clarification Required` from the sheet alone. |
| [1.1.0](evaluate-tech-spec_v1.1.0_SKILL.md) | v2 | minor | Checks each response against the bidder's uploaded documents; adds the REFERENCE column. |
| [1.2.0](evaluate-tech-spec_v1.2.0_SKILL.md) | v3 | minor | Detects every bidder block automatically; generates a clarification-questions sheet. |
| [1.3.0](evaluate-tech-spec_v1.3.0_SKILL.md) | v4 | minor | One downloadable AMPC Technical Clarification file per bidder, from the user's template. |
| [1.4.0](evaluate-tech-spec_v1.4.0_SKILL.md) | v5 | minor | Clarification sheets built in the workbook by default; downloadable files optional. |
| [1.5.0](evaluate-tech-spec_v1.5.0_SKILL.md) | v6 | minor | Profiles any procurement package (layout, requirement types, units), not just equipment sheets. |
| [1.6.0](evaluate-tech-spec_v1.6.0_SKILL.md) | v7 | minor | REFERENCE links to the source file on Google Drive. |
| [1.6.1](evaluate-tech-spec_v1.6.1_SKILL.md) | v8 | patch | Links only to the evaluator's own Drive copies; never to bidder URLs. |
| [1.7.0](evaluate-tech-spec_v1.7.0_SKILL.md) | v9 | minor | MoH evaluator stance, materiality test, decision matrix, evidence hierarchy, basis tags, cross-bidder consistency. |
| [2.0.0](evaluate-tech-spec_v2.0.0_SKILL.md) | v10 | **major** | Labels change to `Meet` / `Not Meet` / `Clarification Required` (`Comply` no longer written); category modules for every procurement type; Relabel mode. |
| [2.1.0](evaluate-tech-spec_v2.1.0_SKILL.md) | v11 | minor | AMPC Technical Clarification always produced, with a completeness check and sync. |
| [2.2.0](evaluate-tech-spec_v2.2.0_SKILL.md) | v12 | minor | Token-lean rewrite; supports P/F-scored sheets; gated AMPC clarification. |
| [2.3.0](evaluate-tech-spec_v2.3.0_SKILL.md) | v13 | minor | Adds the bidder-facing clarification sheet next to the internal AMPC sheet. |
| [2.4.0](evaluate-tech-spec_v2.4.0_SKILL.md) | v14 | minor | Skips optional white rows under PROPOSED DEVICE INFORMATION. |
| [2.5.0](evaluate-tech-spec_v2.5.0_SKILL.md) | v15 | minor | Rows to evaluate chosen by the column-B fill across the whole sheet. |
| [2.6.0](evaluate-tech-spec_v2.6.0_SKILL.md) | v16 | minor | White P/F rows get V = P automatically and are never clarified. |
| [2.7.0](evaluate-tech-spec_v2.7.0_SKILL.md) | v17 | minor | Evidence-strict: evidence classes A–D; bidder self-claims never prove device capability. |
| [2.7.1](evaluate-tech-spec_v2.7.1_SKILL.md) | v18 | patch | Bidder navigation markers and highlights are not treated as red flags. |
| [2.8.0](evaluate-tech-spec_v2.8.0_SKILL.md) | v19 | minor | Concise, finding-only notes; markers ignored silently; Tidy notes mode. |
| [2.9.0](evaluate-tech-spec_v2.9.0_SKILL.md) | v20 | minor | AMPC sheet questions seek the expert consultant's guidance; separate bidder-facing questions. |
| [2.9.1](evaluate-tech-spec_v2.9.1_SKILL.md) | v21 | patch | Bidder questions removed from the AMPC sheet (A–H only). |
| [3.0.0](evaluate-tech-spec_v3.0.0_SKILL.md) | v22 | **major** | A rerun never overwrites: each round inserts a new dated REMAKS / NOTES / ATTACHED DOCUMENT column set. |
| [4.0.0](evaluate-tech-spec_v4.0.0_SKILL.md) | v23 | **major** | Rounds replaced by one AI Evaluation column set per bidder, updated in place; human columns never touched; plain-language notes with Indonesian translation. |
| [4.1.0](evaluate-tech-spec_v4.1.0_SKILL.md) | v24 | minor | Undated AI headers; Indonesian in blue; numbered "file name - Google Drive link" attached-document list. |
| [4.2.0](evaluate-tech-spec_v4.2.0_SKILL.md) | v25 | minor | Per-bidder AMPC sheets without title rows and with a PC Assessment column; compiled AMPC sheet. |
| [4.3.0](evaluate-tech-spec_v4.3.0_SKILL.md) | v26 | minor | Exports the AMPC and bidder clarification files to the workbook's Drive folder, byte-verified; `move` removes the sheets. |
| [4.4.0](evaluate-tech-spec_v4.4.0_SKILL.md) | v27 | minor | Formatting rebuilt and checked before upload; AMPC sheets follow the AMPC Technical Clarification template (A–I). **Current.** |

## Adding a new version

1. Compare the new skill with the current one and pick the part to raise using the table above.
2. Save it as `evaluate-tech-spec_v<new version>_SKILL.md`. Keep the `name:` inside the file as the claude.ai skill name.
3. Add a row to the table above.
