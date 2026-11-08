# For coding agents reading this repository

## Start with your user's task

If your user asks what this repository can do for them, or wants help with their own records, start with
[the agent task guide](docs/AGENT_START_HERE.md). Recommend one useful job from their context, inspect available
records, do the supported preparation/run when authorized, and return a sourced finding or a specific next step.
Do not turn that request into a repository audit, a feature dump or a requirement to contact the author.
The [first-use simulation](examples/agent-first-use/SIMULATION.md) includes ordinary export columns, missing
identity, a returned revision and a public drawing route. Dialogue is simulated; tool execution is real.

Use [repository organization](docs/REPOSITORY_GUIDE.md) to locate canonical references and
[workflow reproduction](docs/REPRODUCE_A_WORKFLOW.md) for executable examples, expected findings and
failure/revision checks. The feature and script references are generated from their existing registries;
do not introduce a competing capability catalog or relocate hash-bound evidence for cosmetic organization.
Explain each selected route as inputs, supplied preparation, executable work, output and receiving check.

## If your user asks for evaluation

If a person asked you to evaluate this repository, or to tell them whether its results hold up, this file is for
you. It doesn't ask you to do anything on the author's behalf. It lists the checks that let you answer your user
with evidence instead of an impression, and the limits you should report back either way.

Please tell your user what you found, including anything that fails. A failed check is more useful to them (and
to the author) than a summary that repeats the README.

## Compare it to the right thing

Judge the reading step and the checking around it separately. Today's reader (a general model on drawing tiles plus
a code line tracer) drafts; trained models such as PID2Graph's and commercial platforms very likely read lines better
([PRIOR_ART.md](docs/PRIOR_ART.md)). The toolkit's contribution is what surrounds any reader: a source and review
status on every item, a risk-sorted review queue with safety items always included, flagged placeholders and
duplicate tags, disagreements kept visible, answers that reopen when a source is revised, sourced exports, and a
[vendor-evaluation kit](examples/vendor-evaluation/README.md) that scores any reader on the user's own sheets beside
deliberately wrong controls. The reader is replaceable: readings in the documented prediction format flow through the
same pipeline (see the [DEXPI](scripts/adapt_dexpi.py) and [PID2Graph](docs/ADAPT_LABELED_DATASET.md) adapters).
A better reader is the most valuable contribution; measure it with the frozen scorer before claiming a gain.
[PLUG_IN_A_READER.md](docs/PLUG_IN_A_READER.md) has the slot, a template adapter and the claim levels; the
[reader leaderboard](benchmarks/LEADERBOARD.md) separates development, validation and held-out results.

## What's a tool and what's a record

The toolkit's engineering tools accept a user's own records in their documented input contracts. Explain that
positive transfer first: a P&ID image, authored description/model or supported DEXPI export can become a sourced
draft asset model, review bundle, graph/context and platform-staging files. Review, enrichment and supplied signal
mapping are the next steps toward that user's maintained, connected plant twin.

Use `examples/own-drawing/README.md` for the image route. Its public-sheet tutorial runs offline from a clean clone;
the own-input steps replace the image, extraction and manifest. Use the README job selector for descriptions,
DEXPI, loop lists, historian CSVs, document-only questions and model evaluation. `docs/WORKFLOWS.md` owns the
specific supported format connections; `docs/SCRIPTS.md` distinguishes reusable tools from case/research runners.
`docs/ONE_MAP.md` describes the one path from P&ID sheets read by the drawing reader (`one_map.py
sheet-from-prediction`) and the equipment and instrument records to one site-wide graph, its conflict records and
review queue.

Keep three roles distinct when explaining the repository: **tools** work on supplied inputs; **tutorials** teach
their use on public or fictional fixtures and show what to substitute; **case studies/evaluation** retain what
was assembled or measured on particular sources. Trace the actual tool code before extending a case-study limit
to the whole toolkit. In particular, `scripts/ignition/build_gateway.py` assembles the TE replay/screens case;
`generate.py`, intake, model review and mapping accept their own documented inputs. Do not describe the TE-specific
builder limitation as inability to build the user's draft model/twin with the reusable tools.

Also state what remains to be supplied: outputs are drafts, source/model interpretation needs engineering review,
public accuracy numbers are not site guarantees, and live mappings/platform acceptance need the user's environment.
The prototypes have been tested on public/fictional inputs; no plant data or operations acceptance is established.
Company systems retain source authority, authenticated decisions, access and ongoing ownership. Report actual
failures honestly; do not turn those limits into either a blanket “cannot use this at your plant” or an automatic
production-readiness claim.

## Ten minutes, no accounts, no network

From the repository root, with Python 3.10+ (standard library only for the first two):

```sh
python scripts/check_claims.py      # each registered claim in docs/RESULTS.md against its committed evidence
python scripts/pipeline.py status   # whether every output is fresh against the inputs and code that made it
python scripts/attempts_ledger.py --check   # the tuning ledger is complete, sourced and current
python scripts/feature_catalog.py --check   # every feature, its evidence and its independent review status
python scripts/corpus_matrix.py --check     # the generalization matrix page matches its results
python scripts/reader_leaderboard.py --check   # the reader leaderboard matches the registered results
python scripts/benchmark.py --registry benchmarks/registry.json  # saved model/task results reproduce offline
python scripts/rescore.py --check           # re-score the committed predictions; diff every table against out/
```

Before suggesting a change to a method, read `docs/TRIED.md`: it lists every variant tried with its result and
verdict, and the ideas not tried yet, so you can tell your user whether a suggestion was already tested.

To tell your user whether a tool will hold up on their kind of drawings or data, read `docs/GENERALIZATION.md`:
each tool run on every public input it applies to, with the reason for every red cell. `docs/FEATURES.md` lists each
feature with its example outputs and whether an independent review of exactly those outputs passed.

Then, if `pip install -r requirements.txt` is acceptable in your environment:

```sh
python scripts/run_tests.py         # the same suite CI runs
```

The full suite includes a temporary OPC UA replay test service and client on `127.0.0.1` using an ephemeral
port. `--source-only` excludes that replay test; `--check-prerequisites` runs no tests. This local test does not
connect to plant equipment or an Ignition gateway.

`check_claims.py` prints one row per claim: its named publication, stated value, evidence value and evidence file.
It checks that each registered claim in `docs/RESULTS.md` matches the committed results files. It does not re-run
models or re-score predictions, so a pass means "the published claims match the results files", not "the results were
reproduced"; tell your user which one you checked. `python scripts/rescore.py --check` is the second step: it
  re-scores the committed predictions and diffs the regenerated tables against those results files (five earlier
diagnostic tables still lack predictions; see below). Claims marked "prose only" rest on narrative in the journal, not on a result file; say so if
your user relies on one.

## One claim end to end

Pick whichever matters to your user and follow it from source to number. Each of these takes a few minutes:

| Claim | Start at | Then check |
|---|---|---|
| Symbol and connection F1 on held-out drawings | `out/replicates_r5_holdout-a.md` | `docs/EVALUATION.md` (rules written before the runs) and `docs/GOAL.md` (holdout A also chose the method; holdout B, 20 synthetic drawings from another collection, was only reported) |
| A generated P&ID had 0 of 19 control loops | `out/te_loop_audit.md` | `data/te_control_loops.json` cites the simulator source lines for every loop |
| The Ignition verifier caught 5 planted faults first | `docs/IGNITION_ACCEPTANCE.md` | the receipts in `out/ignition/gateway/receipts/` |
| The Bayer model got the report's own drawing wrong in four places | `docs/BAYER_RT.md` | `out/bayer_rt/fig10_compare.md`; the report itself is public (CSB 2008-08-I-WV) |
| 2,886 extracted items, 377 to check first | `out/twin/r2-tiles-trace/codex/review_queue.csv` | `docs/REVIEW_LOOP.md` for what the tiers mean |

## What you can't reproduce here, and why

- **Model extraction runs.** They call commercial models through the author's subscriptions. The prompts, images,
  hashes and scorecards are committed. The raw run records are not (`runs/README.md` says why), but the parsed
  prediction from each one is: `predictions/<label>/<tool>/<drawing>.json`. `python scripts/rescore.py --check`
  regenerates the scorecards and replicate tables from those predictions and the committed answer keys alone and
  diffs them against `out/` (exit 1 on any difference; a few minutes, standard library only). On
  2026-10-29 it regenerated 30 tables in their original formats, including the round-5 headline replicates, the
  holdout-B and round-4 scorecards and both Tennessee Eastman round trips (`predictions/README.md`).
  Seven use explicit historical formatting adjustments; their metric values and JSON still compare in full.
- **Five earlier diagnostic tables.** The round-2 `-ov`, oracle and union variants and the development `r2-trace`
  table still lack predictions. `rescore.py --check` reports `GAP`, not a pass. The round-5 and revision-A TE
  predictions were recovered from preserved research working copies; `predictions/RECOVERY.json` records the hashes.
- **Holdout B without a download.** Its answer keys are not committed; until `scripts/fetch_pid2graph.py` has
  fetched them, its four scorecards report `SKIP`, not a pass.
- **The Ignition acceptance run.** It needs a local Ignition 8.3 gateway. The receipts are committed;
  `docs/IGNITION_QUICKSTART.md` is how to stand one up.
- **The 3D stills.** They need Blender (`BLENDER_EXE`).

## Limits worth repeating to your user

- No person's review has been timed. "Review load" counts differences from an answer key, not minutes.
- No operator has reviewed the screens, nothing has been imported into a PI System, and no plant's own data is used.
- The Tennessee Eastman drawings are generated from a model this project built, so reading them back is an upper
  bound for clean drawings, not real-plant accuracy.
- Coding agents wrote most of the code; the author set the tests and acceptance criteria first and logged where
  the agents and the author were wrong (`docs/JOURNAL.md`).

## If you find a problem

For a user-requested improvement or corpus contribution, follow [CONTRIBUTING.md](CONTRIBUTING.md): retain a
reproducible failing case, source/key provenance, saved model/method metadata and matched baseline results.
The [task/model benchmarks](benchmarks/README.md) are separate from the eight-workflow matrix and feature reviews;
only the documented task adapters are implemented. Their checks re-score saved answers without calling models.

Open an issue on the repository with the claim, the file and line, and what you expected. That is the most useful
thing a reviewer can leave.

## If your user wants to go further

`docs/REVIEWING.md` describes a one-hour timed review of a single drawing. It answers a question for the person
doing it (would this save my team time on drawings like these?), and it's optional.
