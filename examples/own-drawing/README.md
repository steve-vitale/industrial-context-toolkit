# Your own drawing: from one P&ID to a draft asset model

**Why it matters:** Retyping drawings into an asset list is a manual step in many historian, HMI or digital twin projects. Starting from a draft turns that typing into checking.

This is the runbook for using this repository on a drawing it has never seen. Start with the worked example below:
it runs offline from a clean clone, on a public sheet, with a real model extraction that is committed here.

What you get is the first structural part of **your plant's draft digital twin**: a sourced asset model, a
review sheet, Ignition tags and PI AF staging files. Review the assets and connections, then add your process
records, signal inventory and target-platform setup to build out the connected application. The TE screen
project is a separate case study showing one assembled result.

## On Windows, from zero

1. Install Python 3.10 or newer from python.org. In the installer, tick "Add python.exe to PATH".
2. Get the repository. With git: `git clone https://github.com/steve-vitale/industrial-context-toolkit`. Without git:
   on the repository page choose Code, then Download ZIP, and unzip it.
3. Open PowerShell in the repository folder. For the offline worked example in step 0, use the installed
   `python` directly; no environment setup or package installation is needed. For a new model extraction in
   step 2, create an environment and install the additional dependencies:

   ```powershell
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```

4. If you created that environment, use `.venv\Scripts\python` wherever the commands below say `python`. PowerShell sets environment variables on a
   line of their own: instead of `PID_SHEETS_DIR=mysheets python ...`, run `$env:PID_SHEETS_DIR = "mysheets"` once,
   then the command without the prefix.

The worked example (step 0) needs only Python. The extraction (step 2, route A) also needs a model's command-line
tool (`codex`, `claude` or `gemini`) installed and signed in, with a subscription or API key; the worked example
skips that by using a recorded extraction.

## 0. The worked example (offline, about a minute)

`manifest.json` here points at PID2Graph OPEN100 sheet 0 (a public drawing, CC BY-SA 4.0, already in the repository)
and at `extraction_sheet0.json`, the recorded GPT extraction of that sheet made with this repository's method
(2x2 tiles with `extraction/prompt_v2.md`, then the code line tracer). Sheet 0 belongs to the development set;
this is a runnable demonstration, not a new held-out accuracy result. From the repository root:

```sh
python -S scripts/import_site_drawing.py --manifest examples/own-drawing/manifest.json --out my-bundle --check-only
python -S scripts/import_site_drawing.py --manifest examples/own-drawing/manifest.json --out my-bundle
```

`my-bundle/` must not exist yet. It holds:

| File | What it is |
|---|---|
| `review_queue.csv` | 445 rows for a person to confirm, correct or reject (the `OPS_` columns) |
| `plant_model.json` | The draft model: 2 equipment, 36 instruments, 53 line items, 9 off-page connectors, 345 links |
| `svg/sheet_0.svg` | The links drawn over the sheet: logical links, not pipe routes |
| `ignition/tags.json` | An Ignition tag import with UDT types; every value is a placeholder until mapped |
| `pi/` | PI AF staging sheets and the steps a PI site would still have to run |
| `READ_ME.txt` | What the bundle has not established |

To turn the bundle into the one-page report a client reads first (the drawing with every extracted item boxed,
items and review status, the hierarchy, next steps and limits):

```sh
python scripts/deliverable_report.py my-bundle
```

[`deliverable/REPORT.html`](deliverable/REPORT.html) is that report for this example.

The `tier` column in `review_queue.csv` is empty on purpose. The risk tiers in the main results come from a model
trained on OPEN100; it isn't applied to a drawing it wasn't trained on.

### From the bundle to one useful question

The existing question engine can screen this draft model without another extraction or extra packages:

```sh
python -S scripts/question_engine.py --model my-bundle/plant_model.json --out my-questions
```

Open `my-questions/screen.md`. Each finding names its model evidence and assets, what to collect and how that
evidence could settle the question. Check those asset references against the drawing before using the collection
plan: this model is still an unreviewed extraction. A finding is an investigation prompt, not an established
opportunity, a savings estimate or permission to change equipment.
In screening decision rules, closing a question means concluding the investigation, never closing or operating equipment.

Choose one relevant question with an engineering counterpart. Copy its exact finding ID, asset references and
data requests into a private copy of the [question and pilot brief](../first-pilot/pilot-brief.md). Start with the
source investigation; define a baseline and comparison if the team chooses a measured trial. Leave missing
information unknown. The [guide](../first-pilot/README.md)
explains that first investigation and the subsequent handoff into a shared company home for context and decisions.
This step uses existing tools; it does not create a shared system or connect to plant operations.

### Carry your model and questions into shared context

To keep the represented assets, source references and questions together in a portable graph, continue from
the bundle and question output above:

```sh
python -S scripts/graph_export.py my-bundle/plant_model.json --questions my-questions/questions.json --out my-graph.json
python -S scripts/graph_export.py --check my-graph.json
```

Open `my-graph.json` to inspect asset identities, relationships, sourced claims and question references. The
[context-register guide](../../docs/CONTEXT_REGISTER.md) shows how to add your actual source manifest, retained
answers and review history. The [read-only MCP starter](../internal-mcp/README.md) can expose a selected graph or
matching graph/register pair to an approved client. Those later steps use your selected records and company
access path; the graph export itself needs no server or plant connection.

## 1. Your sheet as a PNG

Export one approved revision of one sheet to PNG. PDFs aren't read directly. Keep the drawing private: decide first
whether you're allowed to send it to a hosted model at all.

**From a PDF, or a scanned PDF:** convert each page to PNG first. PyMuPDF does it (`pip install pymupdf`; it isn't
in `requirements.txt`). Create the output folder, then:

```sh
python -c "import pymupdf,sys; d=pymupdf.open(sys.argv[1]); [p.get_pixmap(dpi=200).save(f'{sys.argv[2]}/{i}.png') for i,p in enumerate(d)]" drawing.pdf mysheets
```

That writes `mysheets/0.png`, `1.png` and so on, one per page, which is the naming step 2 expects. The same line
works in PowerShell. The drawings behind the results are about 2,600 px wide and the tracer was tuned on them; how
much a very different image size changes the result has not been tested.

**Scanned archives:** expect much more to check. On synthetic old-scan copies of the held-out sheets the review load
roughly tripled (GPT 17.8 to 51.5 differences per 100 answer-key items), mostly because the line tracer loses faded
lines ([round 4](../../README.md#results-held-out-drawings-and-how-they-were-used)). Try one clean sheet first.

## 2. An extraction of it

Pick one route. Both write a file `import_site_drawing.py` accepts.

**A. The method behind this repository's results** (tiles, then the code line tracer). Install
`requirements.txt` first (both commands need it: tiling uses Pillow, tracing uses OpenCV). Put the PNG in a folder of
its own and point the scripts at it. `--drawings` is the PNG's file name without `.png`, so `mysheets/0.png` is
`--drawings 0`; rename yours or change both commands.

```sh
PID_SHEETS_DIR=mysheets python scripts/run_extraction.py --tool codex --drawings 0 --prompt extraction/prompt_v2.md --tiles 2x2 --overlap 0.15 --label mine-tiles
PID_SHEETS_DIR=mysheets python scripts/trace_connections.py --src-label mine-tiles --tool codex --drawings 0 --label mine-trace
```

The result is `runs/mine-trace/codex/0.json` (a run record). The first command sends the image to a hosted model
through its CLI (`--tool claude` and `--tool gemini` also exist; `codex` and `claude` run on a subscription, so the
record shows token counts per tile but no cost); the second runs locally in about two seconds.

**Measured:** an agent following this route on OPEN100 sheet 8, a drawing it was handed as its own, went from PNG
to review bundle in 88 seconds of commands (extraction 36 s, tracing 4 s, intake under 1 s) plus about half a
minute of reading. Scored afterwards against that sheet's answer key, it matched the published mean for that sheet
(review load 11.0 per 100 against 10.99; journal entry 63). Reviewing the bundle is the part nobody has timed.
The tracer's settings were tuned on six OPEN100 sheets, so expect it to do worse on faded scans and very different
drafting styles ([results](../../README.md#results-held-out-drawings-and-how-they-were-used)).

### Optional: clean a scan before tracing

Keep the original PNG for source review. `scan_cleanup.py` writes a separate image at the same pixel dimensions,
so the symbols' boxes still fit. After the extraction command in route A, create `mysheets-clean/` and run:

```sh
python scripts/scan_cleanup.py mysheets/0.png --clean auto --out mysheets-clean/0.png
PID_SHEETS_DIR=mysheets-clean python scripts/trace_connections.py --src-label mine-tiles --tool codex --drawings 0 --label mine-trace-clean
```

Use `runs/mine-trace-clean/codex/0.json` for step 3, keeping the manifest's `image` pointed at the original
`mysheets/0.png`. The extraction's top-level `image_sha256`, when present, describes that original; the new
`tracer.image_sha256` describes the cleaned PNG. Keep both images and the printed clean-up detection with your
records. The intake bundles the original drawing and the traced extraction; it does not copy the separate cleaned
image automatically. Hashes can differ even when pixel dimensions agree; do not relabel one image as the other.

`auto` cleans images detected as speckled or uneven and leaves clean ones alone. `--clean on` forces the step for a
faded scan on flat paper that auto may miss. For callers importing `scripts/scan_cleanup.py`,
`prepare(gray, clean="auto", info=info)` returns `(image, cleaned)`; `trace(image_path, symbols, clean="auto",
info=info)` calls the tracer on a temporary cleaned image and records detection and clean-up details in `info`.
The underlying tracer's default remains unchanged.

The [matrix](../../docs/GENERALIZATION.md) uses auto only for its row-1 oracle-symbol diagnostic. It does not
replace the published round-2 or round-4 model extraction results. The frozen clean-up raises synthetic damaged
holdout connection F1 from 0.877 to 0.894 (L1), 0.566 to 0.818 (L2), and 0.387 to 0.753 (L3); only L1 passes
0.88 (A189/A190). Development and holdout damage come from the same generator. On the one keyed real archive scan,
the agent-keyed OMRE quadrant, it makes F1 worse: 0.561 to 0.522. Inspect your own result before using it.

### Other extraction routes

**B. The one-sheet workflow with a full audit trail** (`site_extraction_workflow.py` prepare, execute, collect).
It records hashes, the exact prompt and every attempt, but it uses a simpler recipe: the whole sheet at once, no
tiles, no tracing. It is not the method the headline numbers measure. See
[SITE_EXTRACTION_WORKFLOW.md](../../docs/SITE_EXTRACTION_WORKFLOW.md).

Or write the extraction yourself, by any means, in the contract at the top of `extraction/prompt_v2.md`
(symbols with class, tag and box; connections between symbol ids). Use `"extraction_format": "prediction"`.

## 3. The draft model

Copy `manifest.json` next to your PNG (say `mysheets/manifest.json`). Paths in it are relative to the manifest
itself, so for route A: `"image": "0.png"`, `"extraction": "../runs/mine-trace/codex/0.json"`,
`"extraction_format": "run-record"` (`"prediction"` for a file you wrote yourself). Set `drawing_id` and `revision`
to your drawing's, and `producer` to how the extraction was made (`model` is the run record's `model` field). Then
run the two commands from step 0 with `--manifest mysheets/manifest.json` and a new `--out` folder (it must not
exist yet, so don't reuse `my-bundle` from the example). The bundle always calls the sheet `0` (`svg/sheet_0.svg`,
`source/0.png`); your drawing number lives in the manifest and in `intake_manifest.json`.

### Several sheets as one drawing set

A plant is drawn across many sheets, and a line that leaves one sheet through an off-page connector continues on
another. `import_drawing_set.py` builds one bundle from a whole set and pairs those connectors. Read each sheet as in
step 2, then list them in one manifest. The committed example lists OPEN100 development sheets 0 to 5 with their
recorded extractions and runs offline:

```sh
python scripts/import_drawing_set.py --manifest examples/own-drawing/set-manifest.json --out my-set --check-only
python scripts/import_drawing_set.py --manifest examples/own-drawing/set-manifest.json --out my-set
python scripts/deliverable_report.py my-set
```

For your own set, copy [`set-manifest.json`](set-manifest.json) next to your PNGs and give each sheet its
`drawing_id`, `revision`, `page`, `image`, `extraction` and, from its title block, its `drawing_number` and `title`.
Pairing uses them in two passes, and each pair records which rule matched:

1. **References written like `PID 140-1`** are paired by `build_twin.py`'s existing rules.
2. **What that pass leaves** goes to [`offpage_pairing.py`](../../scripts/offpage_pairing.py), the shared
   cross-sheet rule (the one-map build still uses its own rule until the map-explorer method is re-frozen). It matches the supplied drawing numbers literally in any reference style
   (`REF SHT P-204`, `DWG 10-PI-003`, or `PID 140?1` where the reader lost the separator). A pair needs both
   connectors naming each other's number, or one naming the other's number while the other carries every word of the
   first sheet's title (`IRRIGATION EQUALIZATION TANK` on the sheet titled "Irrigation Equalization Tank P&ID") or,
   when the first sheet has no supplied number, its system code. Equally good candidates are never decided by order;
   they stay unpaired with the candidates named.

On sheets 0 to 5 here the first pass makes 4 pairs and the second adds 1 (`MSS PID 140?1 PEGGING STEAM` to
`EXTRACTION STEAM ES PID 180-1`): 5 of the 6 continuations the drawings print, all correct against the
[printed-reference key](offpage-key.json). The sixth is lost because the reader dropped `ACC PID 150-1` from one
end. Three of the first pass's four pairs were ties it broke by order; the key records which.

Unmatched connectors keep a reason, such as "target drawing is not in this sheet set".

The set bundle also carries the drawn line layers from [`line_layers.py`](../../scripts/line_layers.py): pipe
segments between consecutive items (`piped_to` in the graph), instrument connections, actuator stems and
junctions, re-traced from each sheet with the tracer's default options. This needs `requirements.txt`. Without it,
or for an extraction that wasn't traced, the bundle is still written and `meta.line_layers_status` says why the
layers were skipped (`--no-line-layers` turns them off). A line whose two ends the tracer placed on different
networks is dropped and listed per sheet rather than refusing the drawing. On the Pahala set that dropped one
dashed signal line and the tap it reached, leaving 42 pipe segments and 41 instrument connections. No topology key
exists for those sheets, so their accuracy is unmeasured. On OPEN100 sheets 0 to 5 the pipe layer scores 0.931 and
instrument connections 0.835 ([round-6 goal](../../docs/GOAL_ROUND6.md)). Every pair is unverified and
listed in `review_queue.csv` and in the report's "Across sheets" section. The cross-sheet links appear in the graph
export as `connects` edges, so paths can be followed from sheet to sheet. Sheet numbers in the bundle follow the
manifest order (`svg/sheet_0.svg`, `svg/sheet_1.svg`, ...).

A pipe segment gets a flow direction only where the drawing shows one: an arrowhead drawn on it, an off-page flag's
point, a pump's top discharge or side suction port, or continuity through an in-line valve from one of those (the
detectors of [`flow_direction.py`](../../scripts/flow_direction.py)). A directed segment runs `from` -> `to` in the
flow direction, with `direction: "forward"` and `direction_evidence` (basis, confidence, the kinds of evidence and
where each was found); its `piped_to` edge in the graph export is `direction: forward`. Every other segment stays
undirected. Flow through a valve with two pipe segments is continuous, so where the marks along such a run of
pipe admit no single sense of flow, every direction on the run is withdrawn; those segments get no direction but a `direction_conflict` record
saying whether the disagreement is on the segment itself or elsewhere, and which contradiction caused it.
`meta.flow_direction_status` counts all three. Nothing is guessed
from layout, and a drawn flow direction is review evidence, not isolation or lockout guidance. `--no-flow-direction`
turns it off. On the development sheets ([scores](../../out/round6/flow_direction_dev.md)) about a quarter of the
OPEN100 pipe segments and 30% of those on Pahala P-401/P-501 are directed. On the generated TE sheets every scored
direction matched the model's streams, but those sheets are drawn left to right, so a layout guess also scores high
there; it is an upper bound for clean drawings.

Control loops come next ([`loop_assembly.py`](../../scripts/loop_assembly.py), `control_loops` in `plant_model.json`).
Instruments are grouped by their ISA-5.1 loop identity (an area prefix such as `10-` and the loop number, read from
the tags; `AIC 123A` and `AT 123` share loop 123), and each gets a role from its letters, read in ISA order (first
letter, modifier, functions: `ZSC` is a closed-position switch, not a controller; `ESV` and `SV` are shut-off valves;
`PSV`, `HS` and letters that do not parse get no loop role). Membership is then confirmed or refuted by the dashed
signal lines traced from each sheet image, joined across sheets only through an off-page pair. The default is
inverted: a relation is asserted only when every condition on one positive list holds (`signal_conditions` in the
script): dashed lines only, at least two dash pieces, a stroke no thicker than the bubbles' outline pen or the sheet's
pipes, no end in reach of two bubbles, every item with a loop role, a sender and its next receiver (a measurement to
its controller, a controller to its valve or relay, or two controllers), and any ISA tag an off-page connector names
reached by the joined lines. Two dashed lines that meet a pipe from either side are one line only when the dash
pattern carries on in step through it, and such a joined line is marked `merged_through_crossing`. It is read as a
qualified reader reads it, one line crossing, but everything resting on it (`signal_to`, `controls`, `sets_point_of`,
the loop) carries its own, weakest tier, `traced_through_crossing`, with one review question attached: does the dashed
line continue across, or do two lines end here? Being in step is evidence, not proof: two lines drawn to a pipe are in
step by chance about one time in six, and then the picture is the same as one line crossing. An independent channel
promotes such a line to its ordinary tier: the reader's own connections (a model reading, not a code tracer) join the
same two items, or a blind second evaluator ([`crossing_question.py`](../../scripts/crossing_question.py)) answers a
confident "continues" for every crossing and its own scorecard has enabled it. The enabled evaluator's confident "two
lines" demotes it to review instead. The gate is recomputed at import from the runs recorded in the scorecard file the
answers name and the prompt hash; it trusts that file, which is fine for a local run on your own files (a shared
pipeline taking answers from elsewhere should pin the scorecard's hash). A shared loop number plays no part. A line drawn straight through a bubble it does
not end at is not read as a signal into it. Anything else is listed under `unresolved_signal_networks` with the
conditions it failed. A cascade (`sets_point_of`) also needs a traced measurement into the outer controller. No loop is
hidden: every loop the assembly cannot prove is listed under `candidate_loops`, either `merged_line_needs_review` or
`grouped_by_tag` (the loop number alone groups a measurement and a valve with the controller), with what it would
confirm and its question.

Every relation in `control_loops.relations` carries its tier in `confidence`, and every loop its `tier`; counts by tier
are in `control_loops.counts.relations_by_tier`, and `loops_by_tier` (in the counts, in `meta.loops_status` and in the
intake's `loops` summary) splits loops, cascades and relations into `strict` and `traced_through_crossing`. A derived
relation or loop takes the weakest tier of every input that made it possible: anything that exists in its form only
when a crossing-tier line is counted (a cascade whose direction, or a loop whose measurement or valve, needed one) is
itself `traced_through_crossing`, so a loop at tier `traced` never rests on crossing-tier support. The tiers, strongest first: `traced_and_grouped`, `traced`,
`traced_cross_sheet`, `traced_direction_inferred` (a cascade whose direction comes from graph distance) and
`traced_through_crossing`. **Default filter for consumers: keep only relations whose `confidence` is not
`traced_through_crossing`, and loops whose `tier` is `traced`** (`loop_assembly.STRICT_TIERS`). That is the strictly
traced view, and because tiers follow derivation, a loop kept by this filter contains no crossing-tier support: the
strict view is assembled from the drawing's lines with every unconfirmed merged line (and any plain line an off-page
pair joins to it) left out before networks are formed, and a cascade whose chain touches such a network is not
strict either, since another reading of that line could give its outer controller a valve. Take `traced_through_crossing` relations only into a review step that shows their `review_question`. `controls` (controller to final element) needs a confirmed loop (a traced measurement in, a
traced output out, directly or through a relay), and `sets_point_of` marks a cascade. A loop that rests on its loop
number alone stays `unconfirmed`, with the grouped tags listed for review; an item a traced line ties to another loop
is listed as refuted and as a conflict. Every relation carries its evidence and an ordinal confidence tier (a
cascade's direction, inferred from which controller is nearer a valve, has its own lower tier);
`meta.loops_status` counts them, and `--no-loops` turns it off (the bundle is then what it was before, apart from the
importer's own hash). The graph export does not carry loops yet ([N122](../../docs/TRIED.md)): it lists
`control_loops` under `not_exported`, where the item count is the number of keys in that block, not the number of
loops. Nothing is taken from layout. On the development sheets ([scores](../../out/round6/loops_dev.md)), which the
rules were tuned against, the generated TE revision D, read with its key's symbols, gives **10 of its 19 control
loops strictly traced** (the default filter: 7 of 11 valve loops, 3 of 8 cascades) with no wrong one. Counting every
tier, it asserts all 19 (11 of 11, 8 of 8), also with no wrong one, but 18 of its 57 relations are then at tier
`traced_through_crossing`, because 8 of its true signal lines cross a pipe and two cascade directions rest on one of
them: those 9 loops are for review, not use. Tag grouping alone gives 11 of 19 at 0.55 precision. Neither channel promotes the crossed lines yet: the key reader's links come from the code tracer, and
the blind evaluator failed its own scorecard (with the one model available today it supported 3 of the 60-placement
sweep's 10 chance merges and missed the obvious separate-ends control; A416). TE is drawn by this repository with
clean, consistent tags, so that is an upper bound. Precision is measured in effect on TE revision D only: the other two development
sets, TE revision A and OPEN100 0-5, draw no controllers, so they cannot show a false `controls` or cascade. TE
revision A also traces no signal lines at all, so its "0 relations" proves nothing beyond that. OPEN100's 23 to 25
traced lines per reading all stay unresolved. Grouping by loop number and then tracing follows the public pid-to-kg
skill (A409); the code here is the toolkit's own.

What the tracer does not find (recall limits measured on synthetic loops; each misses a true loop): dashes at least
0.6 of a bubble side long (read as solid lines), diagonal signal lines (only horizontal and vertical runs are traced),
lines drawn with a heavier pen than the bubbles (bubble pen 1 with line pen 2, or line pen 3 with bubble pen 2), and
sheets whose pipes are drawn thinner than their signal lines.

Known false-assertion modes (three independent reviews built drawings and models to break the assembly; each case is
a test in [`test_loop_assembly.py`](../../scripts/test_loop_assembly.py)):
A case is marked inherently ambiguous when nothing in the drawing could tell a reader, person or machine, that it is
false: its label comes from how the fixture was built, not from the picture.

| Case | Before | Now |
|---|---|---|
| A controller's input and output joined at a corner beside its bubble | false `signal_to` T to V | two lines (fixed) |
| A line end between two stacked bubbles | attached to both | attaches to neither, unresolved (fixed) |
| A branching {T, C, V} line | false T to V | unresolved (fixed) |
| One loop number in two units, no prefix | duplicate loop ids, false refuted members | scoped per sheet (fixed) |
| Two dashed lines ending at a pipe from either side, in step by chance | merged in 10 of 60 random placements (fixed seed), each a false confirmed `controls` | **inherently ambiguous**, not a defect: 2 of the 10 drawings are pixel-identical to one dashed line crossing the pipe, and the other 8 differ from it only by a uniform 1-2 px shift of the dashes below the pipe, which no drawing convention gives a meaning; a qualified reader reads all 10 as one line crossing, and so does the assembly: each asserts its loop at tier `traced_through_crossing` with the crossing question attached. 0 of 60 placements assert a loop relation at a strictly traced tier (defects: 0) |
| Two dashed lines ending on a dashed line from either side, the two ends controllers or a controller and a valve | merged across it: false `controls` and a false `sets_point_of` | kept apart, and neither end tees into the dashed line (fixed) |
| A transmitter misread as a controller (`FT` read as `FC`) beside a real controller | false outer loop, `sets_point_of` | no cascade without a traced measurement into the outer controller (fixed) |
| A dashed line drawn straight through bubbles it does not end at | false `signal_to` into and out of each bubble, false `controls` | unresolved, `not_through_a_symbol` (fixed) |
| One stroke between two stacked controllers | false cascade, `traced_direction_inferred` | unresolved (fixed) |
| A thick process line broken into dash-sized pieces | false `signal_to` | unresolved, `thin_stroke` (fixed) |
| `ZSO`/`ZSC` position switches beside an `XV` | `ZSC` read as a controller, false loop | switches, unresolved (fixed) |
| Off-page connectors whose text names other instruments | loop confirmed through them | unresolved, `connector_text_agrees` (fixed) |
| `PSV`, a plant-coded `MOV`, `TW` or `HS` on a controller line | undirected `signal_to` | unresolved, `known_roles` (fixed) |
| An I/P relay on the way to the valve | relay listed as refuted | traced (fixed) |
| Letters out of ISA order (`FCI`, `FTC`, `FIV`) | read as controllers (`FCI`, `FTC`) or a valve (`FIV`) | no role (fixed); `ESDV` is a final element |
| One controller drawn on two sheets (`FIC 101` twice) with its valve reached through an off-page pair | false `loop_identity` conflict | open: the relation is right, the conflict is not |
| A controller with its own valve fed by a second controller | cascade direction may be reversed | open: carried at the lower tier `traced_direction_inferred` |
| Redundant transmitters `FT 3A`/`FT 3B` on one branch into a controller | no loop | known partial: unresolved, accepted |
| A low-select relay (`FY`) fed by two controllers | no loop | known partial: unresolved, accepted |
| One off-page connector in two pairs | both valves controlled | open: every line at a paired connector joins |

Measured once on three public Pahala WWTP sheets (P-204, P-401, P-501, EPA docket): the reading took 183 s plus 9 s
of tracing, giving 85 instruments. The second pass paired P-401 to P-501, where P-501 names P-401 only by its
title. P-401's reference to P-204 stayed unpaired because P-204's outlet names a different destination. The
existing rules alone paired nothing on that set. No answer key exists for these sheets, so this is not an
accuracy result.

### Check the tags against the PDF's own text

Most P&IDs exported from CAD keep their text, so every printed tag is in the PDF with its position.
`pdf_tag_check.py` compares that text with what the reader extracted, sheet by sheet. It needs PyMuPDF
(`pip install pymupdf`). Pass the PDF page for each bundle sheet, in sheet order:

```sh
python scripts/pdf_tag_check.py --bundle my-bundle --pdf drawing.pdf --pages 21 --out my-tag-check
```

`my-tag-check/tag_check.md` lists, per sheet, tags printed on the drawing that no extracted item carries, and
extracted tags the drawing's text doesn't contain (possible misreads), each with its location. Instrument bubbles
are rebuilt from the letters above the loop number; tags compare on letters and digits only (`LI 401` = `LI-401`).
Descriptive labels such as `TANK` aren't compared. Tags compare as a set, so one of two identical tags being misread
goes unnoticed.

A page whose text is outlined or scanned has almost no words. It's reported as "not checked: needs OCR", and
nothing is inferred from it. On the Pahala set, P-401 and P-501 matched 14 of 14 and 13 of 13 tag-shaped labels
with nothing missed. P-204 has outlined text and was not checked. With one tag renamed and one deleted on
purpose, the check listed both.

For a page without a text layer, `--ocr auto` adds **OCR tag hints** when the Tesseract program is installed
(see [dependencies](../../docs/DEPENDENCIES.md)). The page image is read by OCR and the same tag rules run on its
words. Hints are listed separately (`ocr_hints` in the JSON, "OCR hints (not verified tags)" in the report), each
with the OCR confidence (0-100) and its box. The page stays "not checked": a hint is never reported as a matched,
missed or misread tag, and an extracted tag with no hint is not a sign of a misread. Without Tesseract every
sheet and the report are the same as without `--ocr`, and `ocr` in the JSON says what is missing.

```sh
python scripts/pdf_tag_check.py --bundle my-bundle --pdf scan.pdf --pages 1 --out my-tag-check --ocr auto
```

Measured on development drawings with their text removed ([scores](../../out/round6/ocr_tag_hints_dev.md)):
84-98% of the key tags on the generated TE sheets and 70-74% on Pahala P-401/P-501 came back as hints in the right
place, and on those clean renders every hint with confidence 80 or more was right (83 of 83). On synthetic
old-scan copies it found 30% at the lightest level (8 of 9 confident hints right) and nothing useful beyond it, so it is not shown to help poor archive scans. Text touching a
bubble or line, or much larger than the page's usual text, is dropped.

## 4. Review, then map to real signals

Keep the complete bundle and a separate filled review sheet in an approved private working folder. A qualified
reviewer fills the `OPS_` columns; preview the model corrections and supplied OPC mapping before applying them.
These illustrative sibling-folder paths keep the model, I/O list and both kinds of receipts outside the checkout:

```sh
python scripts/apply_review.py ../approved-work/unit-47/plant_model.json ../approved-work/unit-47/reviewed.csv --reviewer "Name, role" --record-dir ../approved-work/unit-47/review-records --dry-run
python scripts/map_points.py ../approved-work/unit-47/plant_model.json ../approved-work/unit-47/reviewed_io.csv --record-dir ../approved-work/unit-47/mapping-records --dry-run
```

Substitute your permitted locations and inspect the complete diffs. After review, remove only `--dry-run` to apply
each accepted plan with the same private receipt paths, then regenerate the model's exports with `generate.py`.
Keep earlier models, filled sheets, I/O originals and accepted receipts with the investigation. Mapping receipts
with the same generated name replace earlier ones in the selected folder; use a new version folder to retain them.
To carry earlier decisions into a graph, [capture review history, then associate individual records](../../docs/REVIEW_HISTORY.md).
A folder or matching item ID does not establish the source/revision relationship.

The OPC mapper uses this route's extracted-twin instrument IDs. Native process models from descriptions or DEXPI
can generate staging too, but need separately reviewed target-field authoring/configuration; this mapper does
not provide a universal Native signal adapter. Reviewed PI references have their separate `map_pi_points.py`
contract. The [review and mapping commands](../../docs/REPLICATE_AT_YOUR_PLANT.md#4-review-and-map-on-copies)
explain refusals and scope. Nothing here derives an I/O list from a drawing.

**If an item or line is missing:** the review CSV edits existing records only; it cannot add a symbol or link.
Record the omission with its sheet, crop or box, tag, both link endpoints where applicable, reviewer and date.
Keep the original extraction and bundle unchanged. Correct a separate copy of the extraction, name it in a new
manifest with the human correction stated in `producer.method`, and run the intake into a new output folder.
Compare old and new items by their source symbol IDs before carrying decisions forward: generated item IDs can
change when symbols are added. There is no automated merge of additions or old review decisions across a rebuild;
reconcile those decisions explicitly and retain both review records. Adding a CSV row with a new item ID is refused.

## 5. Into Ignition

Import the reviewed working model's regenerated `ignition/tags.json` into a tag provider in an approved **lab**
gateway: Designer, Tag Browser, Import Tags. Your model supplies the asset hierarchy; unmapped values remain
placeholders. Supplied mappings still need actual signal, unit, quality and timestamp readback in that environment.
This is the starting structure for your connected application; author and review the target connections and
screens your job needs. `scripts/ignition/build_gateway.py` assembles the separate Tennessee Eastman/OPEN100 case
with its fixed model, replay, screens and historian; it is not the own-model import command.

## What carries over to your plant, and what doesn't

The tools in this guide are intended for **your own P&IDs**. The supplied OPEN100 sheet teaches the same input,
model, review and export steps; substitute your private drawing, extraction and manifest to build the first
structural part of your plant's draft digital twin.

| Build the next part | Existing route | What you supply or review |
|---|---|---|
| Sourced asset model | One-sheet intake in steps 1–3 | Your approved PNG, supported extraction JSON, drawing identity and revision. Keep the originals with the model. |
| Corrected structure and engineering meaning | Step 4 and the [model-review guide](../../docs/REVIEW_LOOP.md) | Check assets, tags, links, parents and missing items. Apply supported corrections; additions need a corrected extraction and new bundle as described above. |
| Questions and context | [Question engine](../../docs/OPPORTUNITY_SCREEN.md), [graph export](../../docs/GRAPH_EXPORT.md) and [context register](../../docs/CONTEXT_REGISTER.md) | Add independent process/controls evidence, qualified answers and source revisions. Record missing evidence and next owners. |
| Data-connected staging | OPC/PI mapping in step 4, then reviewed lab import in step 5 | Your authoritative point inventory, exact identities/addresses and platform configuration. Verify actual values, units, quality and signal identity in the receiving environment. |
| Maintained knowledge | [Source-revision tutorial](../pump-revision/README.md) and [lifecycle guide](../../docs/CONTEXT_LIFECYCLE.md) | Preserve earlier records; refresh affected answers, reconcile model changes, regenerate selected exports and retain the receiving owner's disposition. |

Begin with one sheet and a defined unit. The OPEN100 case study also demonstrates multi-sheet structure and
off-page relationships; transferring that larger assembly requires your sheet register, reviewed continuation
matches and site conventions. Separate single-sheet bundles are not merged; build one bundle from the whole set
([several sheets as one drawing set](#several-sheets-as-one-drawing-set)).

Your process records and data supply the parts absent from the starting drawing: operating context, normal
behavior, alarm definitions and mapped values. Flow direction must be supported by the drawing or independent
process evidence; this intake's logical connections stay undirected. The TE replay and screens are a worked
case-study assembly. Your model's generated tags and PI staging are the reusable starting files for your own
approved target environment.

The reusable code and file contracts transfer; measured performance does not transfer automatically. Treat the
tracer's defaults as a starting configuration and evaluate them on your drawing style. The published OPEN100 risk
model is not applied by this intake. To measure extraction accuracy, label a small representative sample and use
[the vendor-evaluation tools](../vendor-evaluation/README.md) beside known-answer controls. Review time and site
acceptance need your own observations.
