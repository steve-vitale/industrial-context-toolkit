---
name: pid-to-context-map
description: Turns a P&ID (PDF, scanned PDF or PNG) into a sourced draft asset model, a review queue, a one-page HTML report, investigation questions and a portable context-map graph, using this repository's benchmarked reader (tiled model reading plus a code line tracer). Use when the user wants to digitize, extract or review a P&ID, build an asset list, digital-twin starter, graph or engineering context from drawings, or asks "what can this repo do with my drawing?".
---

# P&ID to context map

You run this repository's tested drawing route for the user. Many users are engineers, not programmers: handle
setup and commands yourself, explain results in plain language, and ask only what changes the next step.

Work is split between you and tested scripts:

- **The reader** (`scripts/run_extraction.py`) sends overlapping tiles of each sheet to a model with the frozen
  prompt `extraction/prompt_v2.md`. This is the method the [leaderboard](../../../benchmarks/LEADERBOARD.md) scores.
- **The line tracer** (`scripts/trace_connections.py`) finds connections in code, locally.
- **The intake, report, question and graph scripts** build the outputs the same way every time.
- **You** prepare the pages, run the steps, check the results and explain them. Do not hand-edit an extraction to
  make it look complete.

Run every command from the repository root.

## Ground rules

- **Ask before sending a drawing to a hosted model.** The reader uploads image tiles to the model provider. If the
  user has not said they may share the drawing outside the company, ask once. If they may not, offer the offline
  worked example (step 0 in `examples/own-drawing/README.md`) or a reader they already approve
  ([PLUG_IN_A_READER.md](../../../docs/PLUG_IN_A_READER.md)).
- **Keep the user's files under `work/<plant>/`.** That folder is ignored by git, so private drawings and outputs
  are never committed. Never copy a user's drawing into `examples/`, `data/` or `docs/`.
- **Only P&ID pages.** Drawings often sit inside a longer report. Use the pages the user names; otherwise look at
  each page and confirm with the user before extracting.
- **One revision per sheet.** If a PDF holds two versions of the same drawing, ask which one to use.
- **Everything is a draft.** Say so in your summary. Outputs need review by a qualified engineer before use in
  design, operations, management of change or safety studies.

## Setup (first run only)

Needs Python 3.10 or newer (`python --version`). If Python is missing, tell the user to install it from
python.org (on Windows, tick "Add python.exe to PATH") and stop.

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt pymupdf        # Windows: .venv\Scripts\pip install -r requirements.txt pymupdf
```

Use `.venv/bin/python` (Windows: `.venv\Scripts\python`) wherever the commands below say `python`. The reader
calls the `claude` command-line tool, which is already signed in when you are running inside Claude Code.

## Workflow

Copy this checklist into your notes and tick it off:

```
- [ ] 1. Pages:    render each P&ID page to work/<plant>/sheets/<n>.png, about 3,000 px wide
- [ ] 2. Read:     run_extraction.py (tiles), then trace_connections.py, per sheet
- [ ] 3. Bundle:   a manifest per sheet, then import_site_drawing.py (--check-only first)
- [ ] 4. Report:   deliverable_report.py, then open REPORT.html
- [ ] 5. Context:  question_engine.py and graph_export.py (then graph_export.py --check)
- [ ] 6. Explain:  counts, what to check first, open questions, limits
```

### 1. Pages

For a PDF, render each selected page so it is about 3,000 px wide. The line tracer was tuned on drawings of
roughly 2,600 to 3,400 px; a fixed DPI can make CAD sheets several times larger. Pass the zero-based page numbers
to keep:

```sh
mkdir -p work/<plant>/sheets
python -c "import pymupdf,sys; d=pymupdf.open(sys.argv[1]); keep=[int(x) for x in sys.argv[3].split(',')]; [(lambda p,z: p.get_pixmap(matrix=pymupdf.Matrix(z,z)).save(f'{sys.argv[2]}/{n}.png'))(d[i], 3000/d[i].rect.width) for n,i in enumerate(keep)]" drawing.pdf work/<plant>/sheets 0,1,2
```

That writes `0.png`, `1.png`, ... in page order. For a PNG the user supplies, copy it to
`work/<plant>/sheets/0.png`. Open each sheet image and check it is upright and legible; rotate it first if not.

**Scanned or faded drawings:** expect much more review. Keep the original PNG and, after step 2's reading command,
optionally trace on a cleaned copy (`scripts/scan_cleanup.py`; see "Optional: clean a scan" in
`examples/own-drawing/README.md`).

### 2. Read each sheet

`--drawings` is the PNG name without `.png`; pass several as `0,1,2`. Labels must be new for each run.

```sh
PID_SHEETS_DIR=work/<plant>/sheets python scripts/run_extraction.py --tool claude --drawings 0 --prompt extraction/prompt_v2.md --tiles 2x2 --overlap 0.15 --label <plant>-tiles
PID_SHEETS_DIR=work/<plant>/sheets python scripts/trace_connections.py --src-label <plant>-tiles --tool claude --drawings 0 --label <plant>-trace
```

On Windows PowerShell set the variable on its own line first: `$env:PID_SHEETS_DIR = "work/<plant>/sheets"`.
The reading takes a few minutes per sheet; the tracer takes seconds. The result for sheet 0 is
`runs/<plant>-trace/claude/0.json`.

### 3. Build the draft bundle

Write `work/<plant>/sheets/manifest-0.json` (paths are relative to the manifest):

```json
{
 "schema_version": "site-drawing-intake-1",
 "drawing_id": "<drawing number from the title block>",
 "revision": "<revision from the title block>",
 "page": 1,
 "image": "0.png",
 "extraction": "../../../runs/<plant>-trace/claude/0.json",
 "extraction_format": "run-record",
 "producer": {"method": "2x2 tiles with extraction/prompt_v2.md, then the code line tracer", "tool": "claude", "model": "<the run record's model field>"},
 "system_name": "<plant or unit name>"
}
```

```sh
python -S scripts/import_site_drawing.py --manifest work/<plant>/sheets/manifest-0.json --out work/<plant>/bundle-0 --check-only
python -S scripts/import_site_drawing.py --manifest work/<plant>/sheets/manifest-0.json --out work/<plant>/bundle-0
```

The `--out` folder must not exist yet. Each sheet gets its own bundle; separate bundles are not merged into one
plant automatically. For a site-wide map across sheets and records, see [docs/ONE_MAP.md](../../../docs/ONE_MAP.md).

### 4. Report

```sh
python scripts/deliverable_report.py work/<plant>/bundle-0
```

Open `work/<plant>/bundle-0/REPORT.html` for the user: the drawing with every extracted item boxed, counts, review
status and next steps. `review_queue.csv` is where a reviewer confirms, corrects or rejects items.

### 5. Questions and graph

```sh
python -S scripts/question_engine.py --model work/<plant>/bundle-0/plant_model.json --out work/<plant>/questions-0
python -S scripts/graph_export.py work/<plant>/bundle-0/plant_model.json --questions work/<plant>/questions-0/questions.json --out work/<plant>/graph-0.json
python -S scripts/graph_export.py --check work/<plant>/graph-0.json
```

`questions-0/screen.md` lists investigation questions with their evidence and what to collect. `graph-0.json` is
a portable graph of assets, relationships, sources and questions that an agent or the
[read-only MCP starter](../../../examples/internal-mcp/README.md) can use. A sheet can produce no questions;
that is a normal result, not a failure.

### 6. Explain the result

Tell the user, briefly:

- what was extracted (the counts at the top of the report) and how many items to check first;
- where the files are and which one to open;
- anything that failed or looked wrong (a blank region, unreadable text, a page you skipped);
- the limits: this is an unreviewed draft; accuracy on their drawing style is unknown until a reviewer checks it
  (the [vendor-evaluation kit](../../../examples/vendor-evaluation/README.md) measures it on their own sheets);
  flow direction and signal mappings still need engineering review.

When the user asks about the plant ("what is connected to X?"), answer from `graph-0.json` or `plant_model.json`,
name the items and the sheet they came from, and say when the answer rests on an unreviewed link. Check the
drawing image before answering anything safety-related.

Then offer one next step that fits their goal: review the queue with `apply_review.py`, map signals for
Ignition or PI (`examples/own-drawing/README.md` steps 4 and 5), connect equipment and instrument records in
[one map](../../../docs/ONE_MAP.md), or ask questions of the graph.
