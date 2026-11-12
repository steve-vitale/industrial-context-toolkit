# Plug in a better reader

**Why it matters:** the drawing reader is the weakest, most replaceable part of this toolkit. A better one, trained or
bought, should inherit the sources, review queue and exports around it without anyone rewriting them, and its gain
should be measured on the same keys and controls as the reader it replaces.

This is a prototype. Today's reader (a general model on drawing tiles plus a code line tracer) drafts; trained models
such as PID2Graph's and commercial readers very likely read lines better ([PRIOR_ART.md](PRIOR_ART.md)). Current
results are on the [reader leaderboard](../benchmarks/LEADERBOARD.md). One external reader has been run through the
slot so far, unregistered and on development sheets only: the public
[pid-to-kg skill](https://github.com/ScottDuncanAI/PID-to-Knowledge-Graph) (MIT, © the pid-to-kg contributors;
repository by Scott Duncan), whose graph.json
[`scripts/reader_external_kg.py`](../scripts/reader_external_kg.py) converts
([comparison](../out/ext_pidkg/comparison.md)). It is a measured comparison and a source of ideas, not a dependency.

## The slot

**A reader receives** one sheet as a PNG image and its own instructions, nothing else. Answer keys, reference
answers and scoring reports never go to the reader.

**A reader returns** one JSON file per sheet in the documented prediction format (the contract at the top of
[`extraction/prompt_v2.md`](../extraction/prompt_v2.md); stored form in [`predictions/README.md`](../predictions/README.md)):

```json
{"symbols": [{"id": "s1", "class": "valve", "tag": "HV-101",
              "bbox": {"x_min": 412.0, "y_min": 300.5, "x_max": 420.3, "y_max": 318.0}, "confidence": 0.93}],
 "connections": [{"from": "s1", "to": "s2"}]}
```

- `class` is one of six: `tank`, `pump`, `valve`, `instrumentation`, `inlet/outlet`, `general`. Map your reader's
  own classes onto these; the scorer ignores any other class and the intake refuses it.
- `bbox` is on a 0-1000 scale in both directions, origin top left, whatever the image's pixel size.
- `tag` is the text as printed, or `null`. `confidence` is 0-1 or `null` (unknown is not invented).
- `id` is unique, letters, digits, `_`, `.` and `-`. A connection joins two symbol ids along a process or instrument
  line; it is undirected, listed once, never a symbol to itself. Line bends, crossings and arrows are not symbols.

A reader with its own format needs an adapter. That adapter is the reader's part of the job, and it is checked the
same way as the reader: convert the answer key through it and expect a perfect score (the vendor-evaluation kit does
this as its "perfect" control).

## What the reader inherits

Readings in this format go through the same pipeline as the current reader's:

| Step | Tool | What it gives the new reader's output |
|---|---|---|
| Intake and review | [`import_site_drawing.py`](../examples/own-drawing/README.md) | A review queue (`review_queue.csv`) with a source for every row, a draft `plant_model.json`, the links drawn over the sheet, Ignition tags and PI staging files, all marked draft until reviewed |
| Review records | [`apply_review.py`](../examples/own-drawing/README.md#4-review-then-map-to-real-signals) | Each decision written onto its item with reviewer, date and notes; old values kept, plus a dated change record |
| Questions and exports | [`question_engine.py`, `graph_export.py`](../examples/own-drawing/README.md#from-the-bundle-to-one-useful-question) | Sourced questions and a portable graph |
| Scoring | [`evaluate_vendor.py`](../examples/vendor-evaluation/README.md), [`benchmark.py`](../benchmarks/README.md) | The frozen scorer, always beside known-answer controls, and a registered result |

Two limits carry over unchanged. The trained risk-tier model behind the risk-sorted queue in the main results was
fitted on OPEN100, so the intake leaves the `tier` column empty on any other drawing rather than guessing; and the
0.75 confidence highlighting is uncalibrated for a new reader's scores.

## Worked example: the template adapter, end to end

[`scripts/reader_template.py`](../scripts/reader_template.py) is a minimal adapter to copy. It reads a simple JSON
(`template-reader-output-1`: pixel boxes, the reader's own type names, tags, lines between symbol ids), maps types
through an editable `CLASS_MAP`, converts boxes to the 0-1000 scale, rewires lines, and runs the intake's own
validator. Whatever it drops (unknown types, collapsed boxes, unsafe ids or tags, self-links, duplicates, links to
dropped symbols) it reports instead of hiding.

[`examples/plug-in-a-reader/reader_output_sheet0.json`](../examples/plug-in-a-reader/reader_output_sheet0.json) is
its sample input: the committed GPT reading of public PID2Graph OPEN100 sheet 0 (the
[own-drawing example's](../examples/own-drawing/README.md) extraction) re-expressed in that simple format with
vendor-style names such as `gate valve` and `instrument bubble`. **It is a format exercise, not a new reader**, and
sheet 0 is a development sheet. From the repository root, standard library only, offline:

```sh
mkdir -p my-reader/run1
python -S scripts/reader_template.py examples/plug-in-a-reader/reader_output_sheet0.json \
    --image "data/external/pid2graph/PID2Graph/Complete/PID2Graph OPEN100/0.png" --out my-reader/run1/0.json
python -S scripts/import_site_drawing.py --manifest examples/plug-in-a-reader/manifest.json --out my-reader-bundle
python -S scripts/evaluate_vendor.py --keys "data/external/pid2graph/PID2Graph/Complete/PID2Graph OPEN100" \
    --sheets 0 --predictions my-reader/run1 --name "template adapter, sheet 0" --out my-reader/report
```

1. The adapter keeps 100 of 100 symbols and 345 of 345 lines, and writes exactly the committed
   [`prediction_sheet0.json`](../examples/plug-in-a-reader/prediction_sheet0.json) that the example
   [manifest](../examples/plug-in-a-reader/manifest.json) imports.
2. The intake builds the same bundle as the own-drawing example: 445 rows in `review_queue.csv` for a person to
   confirm, correct or reject, plus the draft model and exports.
3. The scorer gives review load 7.4 per 100 key items, symbol F1 0.970 (rough; 0.931 strict) and connection F1
   0.960, identical to the original reading's, beside a perfect control at 0 and deliberately wrong answers at 100
   and 121.9. The conversion lost nothing the scorer measures.

`scripts/test_reader_template.py` checks each of these. For your reader, replace `read_reader_output` with a parser
for its real output and edit `CLASS_MAP`; leave the rest. Then convert your own key through it first and expect
review load 0.

## Score it before claiming anything

Use the frozen scorer, never a new one written for the occasion, and always beside the controls. The
[vendor-evaluation kit](../examples/vendor-evaluation/README.md) does both: it scores the key itself (perfect),
every class wrong, every box moved half a sheet and an empty answer on the same keys, and exits 2 if those don't
behave. Run the reader three to five times on the same sheets and pass every run folder; the report treats them as
replicates. A missing or failed sheet scores as empty; it is never skipped.

Readers that also read tags can be scored for tag text on keys that carry it (`scripts/score_tags.py`; the
DEXPI sheets and the generated Tennessee Eastman sheets). The OPEN100 keys have no tag text.

## What counts as a claim

Every result says which of three levels it is. The [leaderboard](../benchmarks/LEADERBOARD.md) keeps them in
separate sections and ranks only inside one table.

| Level | What the sheets are | What you may say | In this repository |
|---|---|---|---|
| **Development** | Seen while the reader or its method was built, tuned or trained | It runs, here is where it fails. Not ranked | OPEN100 sheets 0-5; the DEXPI tag sheets |
| **Validation** | Used to choose between readers or settings | Which variant to carry forward. Optimistic: the winner was picked on these sheets | OPEN100 sheets 6-11 (historically "holdout A", also used for method selection) |
| **Held-out** | Sealed until a frozen reader was scored once, settings fixed in advance | A generalization claim for that source family only | None registered yet; see [EVALUATION.md](EVALUATION.md) rule 7 |

- **A sheet in a reader's training data is development for that reader**, whatever split the suite gives it. A
  model trained on PID2Graph's data must declare which sheets it saw; OPEN100 is part of that dataset.
- Compare only rows in the same table: same task, scorer, sheets, keys and split. One family, however many runs,
  is not several families. Five sheets from one publisher are not five sources.
- Run-to-run spread on fixed sheets is not a significance test, and a scorer number is not reviewer time
  ([EVALUATION.md](EVALUATION.md) section 1). Keep failed attempts; don't edit an answer toward the key.

## Submit a result

1. Save each sheet's answer under `predictions/<label>/<tool>/<sheet>.json` (the reader's actual output after the
   adapter, failures included), or keep private answers out of the repository and score them with `--root`.
2. Write a run manifest per replicate, starting from [`benchmarks/runs/codex-r5-rep1.json`](../benchmarks/runs/codex-r5-rep1.json):
   attempted `cases`, the `predictions` with their hashes, `model` (identifier, provider, version or "unknown"),
   `method`, `interface`, `configuration`, and a `recipe` that pins the files that define the reader here (your
   adapter copy, a model card or settings file).
3. Score with the unchanged scorer, register the report and regenerate the page:

   ```sh
   python scripts/benchmark.py --suite benchmarks/<your-suite>.json --out benchmarks/results/<new-prefix>
   # add {"suite": ..., "report": ...} to benchmarks/registry.json
   python scripts/benchmark.py --registry benchmarks/registry.json
   python scripts/reader_leaderboard.py
   python scripts/reader_leaderboard.py --check
   ```

4. Open a pull request with the manifests, predictions, report and regenerated leaderboard. State the level of
   every number, the training data the reader saw, and what is not established. Full rules:
   [CONTRIBUTING.md](../CONTRIBUTING.md#submit-model-and-method-results).

Licences travel with the drawings: readings of PID2Graph sheets are CC BY-SA 4.0 derived data, readings of DEXPI
sheets CC BY 4.0 ([predictions/README.md](../predictions/README.md#provenance-and-licence)).
