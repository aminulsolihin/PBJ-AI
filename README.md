# PBJ-AI: AI-assisted technical bid evaluation

Tools that help a **Bid Evaluation Committee** (Indonesian public procurement, *Pengadaan Barang/Jasa*) draft a document-based technical evaluation of bids. For every requirement on a specification or criteria sheet, they check each bidder's response against the documents that bidder submitted, label it **Meet / Not Meet / Clarification Required**, write a short note with the document reference, and draft clarification questions.

The repository holds two independent tools that follow the same evaluation rules:

| | [**evaluate-tech-spec** skill](#1-evaluate-tech-spec-claude-skill) | [**Local Evaluator**](#2-local-evaluator-offline-excel-add-in) |
|---|---|---|
| Folder | [`AI Technical Evalution/`](AI%20Technical%20Evalution/) | [`LocalEvaluator/`](LocalEvaluator/) |
| What it is | A skill (prompt file) for **Claude in Excel** | An **offline Excel add-in** with a Python engine and a local model |
| Model | Claude (cloud) | `qwen3-vl:8b` through Ollama, on the evaluator's own computer |
| Internet | Needed; documents are uploaded to Claude | Only for setup. Evaluation runs fully offline |
| Strengths | Highest-quality reasoning, technical spec sheets, Drive links, clarification files | Bid data never leaves the computer; administrative and qualification forms |
| Excel | Web, Windows (Microsoft 365), Mac | Desktop Excel on Windows only |
| Current version | v26 | 1.0.0.0 |

> **Every output is a draft.** The Committee makes every decision. Both tools are designed so that each determination is traceable to a document and page, neutral across bidders, and defensible in an evaluation report, a complaint review or an audit.

---

## Contents

- [Repository layout](#repository-layout)
- [Shared evaluation rules](#shared-evaluation-rules)
- [1. evaluate-tech-spec (Claude skill)](#1-evaluate-tech-spec-claude-skill)
- [2. Local Evaluator (offline Excel add-in)](#2-local-evaluator-offline-excel-add-in)
- [Confidentiality and what not to commit](#confidentiality-and-what-not-to-commit)
- [Limitations](#limitations)
- [Contributing](#contributing)

---

## Repository layout

```
PBJ-AI/
├── README.md                                  this file
├── AI Technical Evalution/                    the Claude skill (folder name is spelled this way)
│   ├── README.md                              detailed skill guide (written for v19)
│   ├── evaluate-tech-spec-v26_SKILL.md        CURRENT skill
│   ├── evaluate-tech-spec-v19_SKILL.md        previous release (concise finding-only notes)
│   ├── eval-tech-spec-v13.md                  token-lean version with bidder-facing sheet
│   ├── eval-tech-spec-v10.md                  full reference version with category modules
│   └── Technical Evaluation with Claude.pdf   presentation / walkthrough
└── LocalEvaluator/                            the offline Excel add-in
    ├── READ ME FIRST.txt                      end-user instructions (shipped in the package)
    ├── Install.cmd / install.ps1              one-click setup
    ├── Attach to workbook.cmd                 put the pane into an evaluation workbook
    ├── uninstall.ps1                          remove from Excel and startup
    ├── build_package.ps1                      build dist\LocalEvaluator-setup.zip
    ├── Open Local Evaluator.xlsx              launcher workbook (made by setup)
    ├── app/                                   engine + task pane (see "Code map")
    ├── test/                                  unit and end-to-end tests, sample bidder folder
    ├── certs/  data/  venv/  dist/            generated per computer; never commit
```

---

## Shared evaluation rules

Both tools apply the same core rules, which came out of real evaluation work.

### Labels

| Outcome | Label | Fill / font |
|---|---|---|
| Pass | `Meet` | `#C6EFCE` / `#006100` |
| Fail | `Not Meet` | `#FFC7CE` / `#9C0006` |
| Query | `Clarification Required` | `#FFEB9C` / `#9C5700` |

The labels are fixed; "Comply / Not Comply" is never used. The Local Evaluator writes the sheet's own wording instead when the verdict column has a dropdown (for example *Qualified / Not Qualified / Clarify To Bidder*).

### Basis tags and decision matrix

Every note starts with a basis tag. Tags never contain " – ", so formulas can strip them.

| Tag (EN / ID) | Situation | Label (`strict`, the default) |
|---|---|---|
| Verified / Terverifikasi | Meets or exceeds; evidence verified | Meet |
| Deviation / Penyimpangan | Offered value falls short, or "No" ticked on a required item | Not Meet |
| Not substantiated / Tidak didukung bukti | Backed only by a declaration or self-claim, or the cited page doesn't show it | Not Meet for mandatory performance or safety parameters; otherwise Clarification Required |
| No response / Tidak ada tanggapan | Blank, placeholder, not ticked, no document | Not Meet |
| Ambiguous / Tidak jelas | Generic wording, model unclear | Clarification Required |
| Conflict / Bertentangan | Values conflict between documents | Clarification Required |
| Evidence unavailable / Bukti tidak tersedia | Cited file not uploaded or unreadable | Clarification Required |
| Partial / Sebagian | Multi-part requirement only partly evidenced | Not Meet if a missing part is mandatory; otherwise Clarification Required |

The `standard` strictness (skill only) softens *Not substantiated* and *No response* on non-material rows to Clarification Required.

### Evidence classes (internal reasoning only, never written into notes)

| Class | Examples | Use |
|---|---|---|
| A: Independent / regulatory | Registration (NIE / izin edar), notified-body certificate, accredited-lab report naming the model | Verifies a claim on its own |
| B: Manufacturer document | IFU, manual, datasheet, test report with method and data | Verifies if model-specific and consistent |
| C: Manufacturer declaration | Signed letter, self-declared DoC | Supporting only |
| D: Bidder self-claim | Bidder letter, calculation, bid-form text, brochure, website | Contractual commitments only (warranty, delivery, training…). **Never device capability** |

A genuine red flag (conflicting values, sister model only, report without data, letter citing another tender) lowers the evidence one class. Bidder navigation aids (highlights, arrows, stamps, excerpt files) are ignored silently. Rationality checks cover throughput, UPS runtime against load, kit quantities and consistency across documents.

### Universal guardrails

- One standard for every bidder, on every row. No price evaluation.
- A "Yes" tick or a bidder's own letter is never a Meet by itself.
- Over-specification never offsets a shortfall; "up to" figures are not accepted.
- No clarification may cure a material deviation or invite a new model, added items or a price change.
- **Human evaluator columns are never written.** AI output goes only into columns whose header contains `(AI Evaluation)`, added once and updated in place.
- Notes record the finding only: no methodology, evidence-class codes or adjectives about the bidder.

---

## 1. evaluate-tech-spec (Claude skill)

A skill that runs inside **Claude in Excel**. It profiles the technical specification sheet, reads each bidder's uploaded documents, fills an AI Evaluation column set per bidder, and builds clarification sheets and files. It works for any kind of specification: medical devices, lab/IVD, pharmaceuticals and consumables, IT, furniture, vehicles and machinery, works and services.

The detailed guide is [`AI Technical Evalution/README.md`](AI%20Technical%20Evalution/README.md) (written for v19). This section covers v26 and what changed.

### Requirements

- Claude **Pro, Max, Team or Enterprise** plan
- The **Claude for Microsoft 365** add-in (Microsoft AppSource)
- Excel on the web, Excel for Windows (Microsoft 365), or Excel for Mac 16.46+
- *Code execution and file creation* on in Claude (**Settings › Capabilities**)
- Optional, for v26 document links and file export: the **Google Drive** connector, with the workbook and bidder documents in Google Drive

### Install

1. Create a folder whose name matches the `name:` in the skill file, and save the file in it as `SKILL.md`:
   ```
   evaluate-tech-spec-v26/
   └── SKILL.md        (copy of evaluate-tech-spec-v26_SKILL.md)
   ```
2. ZIP the folder.
3. In claude.ai: **Customize › Skills › + › Create skill › Upload a skill**, upload the ZIP and switch it on.

Alternatively, paste the file's contents into the Claude panel in Excel, ask Claude to save it as a skill, and click **Save to claude.ai**.

### Use

Open the specification sheet (for example *Form 12 (a)*) and type in the Claude panel:

```
/evaluate-tech-spec-v26
```

1. Confirm the profile Claude shows (columns, bidder blocks, row classes, labels, strictness). This is the only pause.
2. Upload each bidder's documents (PDF, xlsx, docx), with the bidder name in the message or file names. Optionally give the bidder's Google Drive folder, e.g. `G:\My Drive\...\<bidder>\Lot 1`.
3. Review the AI Evaluation columns and the clarification sheets, then save.
4. Optionally export: `move the AMPC clarification and the bidder clarification to new Excel files`.

### Which rows are evaluated

Determined by the fill of column B and the WT column:

| Column B | Action |
|---|---|
| Green (**Required**) | Evaluate. V = `P` if Meet, else `F` |
| Orange `#FFC000` (**Preferred**) | Evaluate. V = `1` or `0`; never a mandatory failure |
| White, WT = `P/F` | V = `P` only. No label, note or clarification |
| White otherwise, headers, grey notes | Nothing written |

CP formulas are never touched. When V changes, a cell note records `Before AI Evaluation (dd Mmm yyyy): <old V>`.

### What v26 writes

**One AI Evaluation set per bidder block**, three undated columns inserted once to the right of the human columns and updated in place on reruns:

| Column | Content |
|---|---|
| `REMARKS (AI Evaluation)` | The label |
| `NOTES (AI Evaluation) – English / Bahasa Indonesia` | `<Tag> – <plain English, 2–4 sentences>` in black, then `ID: <Indonesian tag> – <translation>` in blue `#0000FF`. Jargon is explained in brackets for non-technical readers |
| `ATTACHED DOCUMENT (AI Evaluation)` | Numbered list `1. <Drive file name> (<page>) - https://drive.google.com/file/d/<id>/view`. A single-file cell is a clickable hyperlink |

On a rerun, cells that look hand-edited are listed and Claude asks once before overwriting; the changes are reported as `row: old → new, reason`.

**Clarification sheets:**

| Sheet | Audience | Content |
|---|---|---|
| `AMPC Clarif <pkg> - <bidder>` | Internal (AMPC) | Every Not Meet and Clarification Required row, with a "PC Assessment" column (no labels, tags or "AI" wording) |
| `AMPC Clarif <pkg> - Compiled` | Internal, optional | Overview across bidders |
| `Clarif Bidder <pkg> - <bidder>` | Bidder | Same rows and order; neutral questions plus a blank response column. No findings |

**Export** (optional): new Excel files in the open workbook's own Drive folder: one AMPC Clarification file with a sheet per bidder, and one clarification file per bidder. Each file is byte-verified. With `move`, the sheets are then removed from the workbook; with `export` / `save` / `copy` they stay.

**Gate before delivery:** human columns identical to the snapshot; one AI set per block; every coloured row filled with a bilingual note; V agrees with labels; no doubled numbering in references; no `#REF!`; SCORE still evaluates.

### Modes (example prompts)

| Mode | Prompt |
|---|---|
| Evaluate | `/evaluate-tech-spec-v26` or `evaluate bidder X` |
| Continue | `continue with the next bidder` |
| Recheck with new documents | `recheck the evaluation` |
| Rebuild / sync clarification | `sync the clarification sheets` |
| Export | `move / export the AMPC clarification and bidder clarification to new Excel files` |
| Drive links | `add Drive links to attached document` |
| Fix numbering | `fix the attached-document numbering` |
| Rewrite / translate notes | `rewrite the notes` |
| White-row rule | `apply the white-row rule` |

### Version history

| Version | Change |
|---|---|
| v1–v5 | Sheet-only evaluation → document checks with REFERENCE → all bidders → clarification file → clarification sheets in the workbook |
| v6–v9 | Dynamic profiling for any package; Google Drive REFERENCE links (evaluator's own copies only); materiality test, decision matrix, cross-bidder consistency |
| v10 | `Meet / Not Meet` labels, basis tags, category modules for every procurement type, Relabel mode ([file](AI%20Technical%20Evalution/eval-tech-spec-v10.md)) |
| v11–v13 | Mandatory gated AMPC clarification; token-lean workflow; P/F-scored sheets; bidder-facing clarification sheet ([file](AI%20Technical%20Evalution/eval-tech-spec-v13.md)) |
| v14–v16 | Only coloured column-B rows evaluated; white P/F rows get V = P and are never clarified |
| v17–v18 | Evidence-strict: classes A–D; self-claims never prove device capability; navigation markers are not red flags |
| v19 | Concise, finding-only notes; markers ignored silently; Tidy notes mode ([file](AI%20Technical%20Evalution/evaluate-tech-spec-v19_SKILL.md)) |
| v20–v26 | One undated AI Evaluation column set per bidder (human columns never touched); plain-language bilingual notes (English black, Indonesian blue); numbered "file name - Drive link" references; per-bidder AMPC sheets with a PC Assessment column; byte-verified export to the workbook's Drive folder, with `move` ([file](AI%20Technical%20Evalution/evaluate-tech-spec-v26_SKILL.md)) |

---

## 2. Local Evaluator (offline Excel add-in)

An Excel task-pane add-in for evaluating bids **without sending anything to the internet**. A small Python engine on the evaluator's computer serves the pane over `https://localhost:47821`, reads bidder documents (with Windows' built-in OCR for scans), asks a local model through Ollama for a structured finding, applies the decision rules in code, and writes the result into the open workbook through Excel's COM interface.

It suits administrative and qualification forms (NIB, licences, tax status, deeds, experience statements) as well as technical criteria tables.

### Requirements

- Windows 10 or 11, desktop Excel 2016 or later / Microsoft 365
- 16 GB RAM or more, about 8 GB free disk
- Internet for setup only. **No administrator rights needed**

Setup installs what is missing: Python 3.10+ (with venv and tkinter), [Ollama](https://ollama.com), the model `qwen3-vl:8b` (about 6 GB), and the Python packages `pywin32`, `pymupdf` / `pymupdf4llm`, `openpyxl`, `cryptography`, `psutil`, `pyyaml` and Office.js.

### Install

1. Put the folder at `C:\LocalEvaluator` (unzip `LocalEvaluator-setup.zip` to `C:\`).
2. Double-click **`Install.cmd`**. It lists what it will download; type `Y`.
3. When Windows asks whether to trust **"Local Evaluator (this computer only)"**, choose **Yes** (the prompt can appear behind the window).
4. Wait for **"Setup finished"**. The model download is the long part. If setup stops, run it again; finished steps are skipped.

`install.ps1` can also run single steps:

| Switch | Does |
|---|---|
| `-Prerequisites` | Check for / install Python, Ollama and the model (asks first) |
| `-Packages` | Private Python environment (`venv\`) and packages, plus Office.js |
| `-Certificate` | Create a localhost-only HTTPS certificate and trust it for this Windows user |
| `-Register` | Register the add-in in Excel (HKCU developer add-ins) and start the engine at logon |
| `-Start` | Start the engine now |
| `-Model <name>` | Use another Ollama model (default `qwen3-vl:8b`) |
| `-Yes` / `-Force` | Don't ask before installing / redo a step |

The certificate authority's private key exists only in memory during setup and is never written to disk, so it cannot sign anything else ([`make_cert.py`](LocalEvaluator/app/make_cert.py)).

### Use

1. **Attach the pane to a workbook.** Close the evaluation workbook, double-click **`Attach to workbook.cmd`** and choose it (or drag the workbook onto it). It opens with the Local Evaluator pane on the right, now and every time. A backup copy is kept the first time; only a small add-in reference is added to the file. Alternatively open `Open Local Evaluator.xlsx` and use **Attach to a workbook…**.
2. **Criteria.** Open the evaluation sheet. Two layouts are recognised automatically:
   - **One block per bidder** (stacked): the criteria table repeats down the sheet under each "Name of Bidder / Proposer" row (e.g. *Administrasi*, World Bank *Form 11A*). One AI column set serves every block.
   - **One table** (side): a single table with "No." and "Requirement" columns; each bidder gets its own AI column set. You can create one from a Word or Excel file or a pasted table.

   "Doc Required" and threshold columns are read when present.
3. **Bidders.** Block-per-bidder: click **Add AI Evaluation columns** once. One table: add each bidder by name. Give each bidder a documents folder (PDF, Word, Excel, images, text), or use **Find folders** to match bidder names to sub-folders automatically. Folders are remembered per workbook.
   - **More bidders than the form has room for:** **Add a bidder** copies the first block on every bidder sheet, empties what evaluators typed, rewires formulas to the new block and adds a summary row. A backup goes to `data\backups`.
4. **Evaluate** one bidder or all. The sheet fills in row by row while you keep working. **Stop** cancels.

**Settings** in the pane: the local model; whether the model suggests search words per requirement (better matching, slower the first time); how much document text the model sees per requirement (short / normal / long).

### What it writes

Three columns to the right of the table, each marked `(AI Evaluation)`: **REMARKS** (verdict), **NOTES** (English in black, then `ID:` and Bahasa Indonesia in blue), **ATTACHED DOCUMENT** (numbered files and pages; a single-file cell opens the file). Human Document Reference, Determination and Remark columns, and summary sheets that read them, are never touched. Previous AI columns are saved to `data\runs\` before each run.

### Checks done by code, not by the model

The model returns a structured finding (`verified`, `deviation`, `no_document`, `not_substantiated`, `partial`, `ambiguous`, `conflict`, `evidence_unreadable`, `not_applicable`). It never picks the label; [`engine.py`](LocalEvaluator/app/engine.py) maps the finding to a tag and label and then applies:

- A "met" finding must cite a page that was actually read; otherwise it becomes a clarification.
- A document whose printed validity ended before today is treated as expired.
- A document in another company's name is not accepted without clarification (unless the requirement is about the manufacturer).
- A figure below the stated minimum is flagged for a hand check.
- "Nothing found" becomes a clarification when some files could not be read.

### How it works

```
Excel task pane (taskpane.html/js, Office.js)
        │  HTTPS, 127.0.0.1:47821 only
        ▼
server.py ──► excel_io.py ──COM──► open workbook (read layout, write AI columns)
   │
   ├──► docs.py ──► PyMuPDF text  /  ocr.ps1 (Windows OCR, id-ID then en)  ──► data\cache\
   │
   └──► engine.py: search pages ─► Ollama 127.0.0.1:11434 (structured JSON) ─► fixed decision rules ─► cell texts
```

Nothing opens a connection to another machine. For a hard guarantee, use airplane mode while evaluating, or add Windows Firewall outbound rules for `ollama.exe` and Python.

### Code map

| File | Role |
|---|---|
| [`app/server.py`](LocalEvaluator/app/server.py) | Local web server: serves the pane, JSON API, job runner. `--http` serves plain HTTP on port 47822 for development |
| [`app/engine.py`](LocalEvaluator/app/engine.py) | Per-requirement pipeline: chunking and search, keyword expansion, Ollama call with a JSON schema, decision table, bilingual note building |
| [`app/excel_io.py`](LocalEvaluator/app/excel_io.py) | Excel COM: layout detection (stacked / side), AI column creation, cell writing with two-colour notes |
| [`app/docs.py`](LocalEvaluator/app/docs.py) | Bidder folder → page texts (PDF, DOCX, XLSX, TXT, images), cached by content hash; OCR up to 150 pages per file |
| [`app/criteria.py`](LocalEvaluator/app/criteria.py) | Read a criteria table from Word, Excel or pasted text (standard library only) |
| [`app/blocks.py`](LocalEvaluator/app/blocks.py) | Add a bidder block to block-per-bidder workbooks and rewire formulas by meaning |
| [`app/launcher.py`](LocalEvaluator/app/launcher.py) | Write the add-in reference into an `.xlsx`/`.xlsm` package (`new` / `add`) |
| [`app/repair_summary.py`](LocalEvaluator/app/repair_summary.py) | Repair summary-sheet result formulas on a **copy** of a workbook, with a change log and diff check |
| [`app/make_cert.py`](LocalEvaluator/app/make_cert.py) | Localhost CA + server certificate |
| [`app/ocr.ps1`](LocalEvaluator/app/ocr.ps1) | Windows.Media.Ocr wrapper |
| [`app/manifest.xml`](LocalEvaluator/app/manifest.xml) | Office add-in manifest (id `7c1f0f5e-3b7a-4d0e-9c55-2a6b8e41d9a3`, version kept at `1.0.0.0`) |
| [`app/web/`](LocalEvaluator/app/web/) | Task pane UI, ribbon commands, help page, icons; `office/` is vendored Office.js |

API endpoints (all on `https://localhost:47821`): `GET /api/status`, `GET /api/job`, and `POST` to `/api/layout`, `/api/settings`, `/api/pick`, `/api/attach`, `/api/criteria/import`, `/api/prepare`, `/api/bidder/plan-block`, `/api/bidder/add-block`, `/api/bidder/add`, `/api/bidder/folder`, `/api/bidder/automatch`, `/api/evaluate`, `/api/cancel`.

### Runtime data (`LocalEvaluator/data/`)

| Path | Holds |
|---|---|
| `cache/` | Extracted page text per document (bid content) |
| `keywords.json` | Cached search terms per requirement |
| `workbooks/` | Remembered bidder folders per workbook |
| `runs/<workbook>/` | AI columns before and after each run |
| `backups/` | Workbook copies made before adding a bidder |
| `engine.log`, `office-addin.log` | Logs (first place to look when something fails) |

### Testing

Run from `LocalEvaluator\` with the engine running:

```powershell
venv\Scripts\python.exe test\test_map_rows.py            # unit test: formula rewiring for added bidders
venv\Scripts\python.exe test\e2e_test.py real            # profile + prepare a COPY of the real-layout workbook
venv\Scripts\python.exe test\e2e_test.py evaluate        # evaluate two rows of bidder 1, check the cells
venv\Scripts\python.exe test\e2e_test.py side            # one-table sheet: import criteria, add a bidder
venv\Scripts\python.exe test\e2e_test.py close           # close the test workbooks
venv\Scripts\python.exe test\add_bidder_test.py          # add bidders on a fresh copy of the real layout
powershell -File test\ribbon_check.ps1                   # is the button / pane present in each Excel window?
```

`test\PT Contoh Alkes Nusantara\` is a fictional sample bidder folder (NIB, distribution licence, KSWP, power of attorney, deed, scanned ID) for trying the pipeline, including OCR.

### Build the distributable package

```powershell
powershell -ExecutionPolicy Bypass -File LocalEvaluator\build_package.ps1
```

Produces `LocalEvaluator\dist\LocalEvaluator-setup.zip` with `app\` and the setup scripts. It deliberately leaves out `venv\`, `certs\`, `data\`, `test\` and the launcher workbook, and fails if a required file is missing.

### Troubleshooting

| Symptom | Check |
|---|---|
| Pane is blank or "add-in error" | Is the engine running? Open `https://localhost:47821/api/status` in a browser; run `install.ps1 -Start`. See `data\engine.log` |
| Status shows model "NOT INSTALLED" | `ollama pull qwen3-vl:8b`, or `install.ps1 -Prerequisites` |
| Status shows Excel link "MISSING" | `install.ps1 -Packages -Force` (pywin32) |
| Certificate warning | `install.ps1 -Certificate -Force`, then restart Excel |
| Pane doesn't appear in a workbook | Attach that workbook (it must be closed first) |
| "is open in Excel. Close it first" | Close the workbook, then attach |
| Slow evaluation | A few minutes per requirement is normal without a GPU. Close other programs; use **Short** document text |

### Uninstall

Right-click `uninstall.ps1` › **Run with PowerShell**. It stops the engine, removes the Excel registration, the startup shortcut and the trusted certificate. Add `-RemoveFiles` to also delete `venv`, `certs`, `data` (cached bid text and run history) and the vendored Office.js. Python, Ollama and the model stay installed; remove them from **Settings › Apps** if wanted.

---

## Confidentiality and what not to commit

Bid content is confidential until award. **Never commit bid documents, evaluated workbooks or bidder names.** In `LocalEvaluator/`, the following are generated per computer or hold bid data and must stay out of git:

| Path | Why |
|---|---|
| `data/` | Cached bidder document text, folder paths, run history, logs |
| `certs/` | `server.key` is a private key |
| `venv/`, `app/__pycache__/` | Rebuilt by setup |
| `dist/` | Build output |
| `test/*.xlsx` | Copies of real evaluation workbooks |
| `Open Local Evaluator.xlsx` | Made by setup |

A matching `.gitignore`:

```gitignore
LocalEvaluator/data/
LocalEvaluator/certs/
LocalEvaluator/venv/
LocalEvaluator/dist/
LocalEvaluator/test/*.xlsx
LocalEvaluator/Open Local Evaluator.xlsx
__pycache__/
*.pyc
```

Follow your organisation's policy before uploading tender documents to any AI service. With the Claude skill, bid data is uploaded to Claude; the skill itself never sends it to the web or other agents, searches Drive by file title only, and exports only to the workbook's own Drive folder. With the Local Evaluator, nothing leaves the computer.

---

## Limitations

- AI makes mistakes. **Check every row against the documents** before the Committee relies on it.
- The Local Evaluator uses a small local model: weaker than Claude, especially at sums, averages and date arithmetic (turnover, years of experience). Verify those rows by hand.
- Evaluating with the Local Evaluator clears Excel's Undo history for the sheet (previous AI columns are saved in `data\runs`).
- Use trusted workbooks only; files from outside can contain hidden instructions (prompt injection).
- Claude in Excel does not support macros/VBA or data tables.
- Keep bid documents and workbooks on a local drive (Local Evaluator) rather than a cloud-synced folder.

---

## Contributing

Improvements come from real evaluation work.

- **Skill:** add a new `evaluate-tech-spec-vNN_SKILL.md` (don't edit released versions), with a matching `name: evaluate-tech-spec-vNN` in the front matter, and add a row to the version history above.
- **Local Evaluator:** keep the add-in version in `manifest.xml` and `launcher.py` fixed at `1.0.0.0` (attached workbooks refer to it). Run the tests, then `build_package.ps1`.
- Use only fictional bidders and documents in examples and tests.

## License

Not yet chosen. Add a `LICENSE` file before sharing outside the team.
