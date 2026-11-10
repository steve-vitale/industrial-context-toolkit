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
2. **Any other style** (`REF SHT P-204`, `DWG 10-PI-003`) is matched literally against the supplied drawing numbers.
   A pair needs either both connectors naming each other's number, or one naming the other's number while the other
   carries every word of the first sheet's title (`IRRIGATION EQUALIZATION TANK` on the sheet titled "Irrigation
   Equalization Tank P&ID").

Unmatched connectors keep a reason, such as "target drawing is not in this sheet set".

The set bundle also carries the drawn line layers from [`line_layers.py`](../../scripts/line_layers.py): pipe
segments between consecutive items (`piped_to` in the graph), instrument connections, actuator stems and
junctions, re-traced from each sheet with the tracer's default options. This needs `requirements.txt`. Without it,
or for an extraction that wasn't traced, the bundle is still written and `meta.line_layers_status` says why the
layers were skipped (`--no-line-layers` turns them off). A line whose two ends the tracer placed on different
networks is dropped and listed per sheet rather than refusing the drawing. On the Pahala set that dropped one
dashed signal line and the tap it reached, leaving 42 pipe segments and 41 instrument connections. No topology key
exists for those sheets, so their accuracy is unmeasured. On OPEN100 sheets 0 to 5 the pipe layer scores 0.931 and
instrument connections 0.835 ([GOAL.md, round 6](../../docs/GOAL.md)). Every pair is unverified and
listed in `review_queue.csv` and in the report's "Across sheets" section. The cross-sheet links appear in the graph
export as `connects` edges, so paths can be followed from sheet to sheet. Sheet numbers in the bundle follow the
manifest order (`svg/sheet_0.svg`, `svg/sheet_1.svg`, ...).

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
