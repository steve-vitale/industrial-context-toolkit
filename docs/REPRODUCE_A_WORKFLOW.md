# Reproduce one useful workflow, then adapt it

For an assistant: read [AGENT_START_HERE.md](AGENT_START_HERE.md) when helping a person with their records.
Use this page when the task is to reproduce the toolkit or learn its approach. Choose a single workflow,
run its real commands, inspect its sources and result, and state exactly what was demonstrated.
These exercises use exposed public/fictional examples, not the user's plant or a blind accuracy evaluation.

To check all seven current fixture routes and five targeted regression suites in
one run, use the [cross-workflow runner](../examples/agent-first-use/workflow-check/README.md):
`python -S examples/agent-first-use/workflow-check/reproduce.py --out ../ict-repro-check`.
It retains the actual commands, logs, reports and known-answer checks. Choose a single
row below when you only need one job; this whole check is not a prerequisite for using a tool.

## 1. Record the version and choose a clean destination

Clone the [public repository](https://github.com/steve-vitale/industrial-context-toolkit), enter its root and
record `git rev-parse HEAD` and `python --version`. The commands below use Python 3.10+ and the standard
library; `-S` disables installed site packages. They require no accounts, network, model calls or native CAD.
Each output directory must be new. Substitute your own private working location for the example `../ict-repro-*`
paths, and retain failed command output. The same one-line commands work in PowerShell and bash.

| Exercise | Command from the repository root | Inspect and check |
|---|---|---|
| Explore an engineering context map and compare a supplied revision | `python -B -S examples/map-explorer/reproduce.py --phase development --out ../ict-repro-map-explorer` then `--phase transfer --out ../ict-repro-map-transfer` | Complete snapshot/source receiving, qualified identity selection, sourced questions, retained disagreements and previous/current views. The second phase uses preselected known fictional/public fixtures. [Inputs, exact checks and limits](../examples/map-explorer/README.md). |
| Equipment/work-order reconciliation across revisions | `python -S examples/maintenance-intake/reproduce.py --out ../ict-repro-maintenance` | `initial/REPORT.html`, `corrected/REPORT.md`, `next-replacement/REPORT.md` and replay receipt. U1 OLD-101/NEW-101 conflicts, U2 stays separate, an open order is not installation evidence; the next replacement is retained. [Inputs and limits](../examples/maintenance-intake/README.md). |
| Asset history with associated material/labor evidence | `python -S examples/maintenance-history/reproduce.py --out ../ict-repro-history` | `initial/REPORT.html`, asset dossiers and `REPLAY.json`: U1/P-101 has three selected orders and 2.5 booked hours; U2 stays separate. Wrong entity/contradictory details are quarantined; a planned group also recurs. Both CSV layouts, JSON, corrected/omitted sources and portable replay are checked. [Contract](MAINTENANCE_HISTORY.md). |
| Consultant markup return | `python -S scripts/check_pid_markups.py --manifest examples/pid-markup-review/inputs/manifest.json --out ../ict-repro-markups` | `REPORT.html`, `result.json`, `review_queue.csv`. Retain supported, missing/partial and unverifiable requests, the unrequested fail-action change and the coverage gap. Read all three original documents. [Prepared-reading boundary](../examples/pid-markup-review/README.md). |
| Exact endpoint review | `python -S examples/pid-port-review/replay.py --out ../ict-repro-ports` | Initial/corrected reports and the separately frozen [acceptance key](../examples/pid-port-review/ACCEPTANCE.json). The tag-only baseline misses the wrong-input distinction; the exact-port check retains it. R4 remains unknown. |
| Cross-sheet routes and a revised answer | `python -S examples/pid-path-review/reproduce.py --out ../ict-repro-paths` | Policy reports/registers and replay receipt. The naive baseline follows a reversed edge; the reviewed/exploratory checks refuse that route. A remote revision reopens its answer while local/unrelated dependencies remain unchanged. [Coverage](../examples/pid-path-review/README.md). |
| P&ID reading to a draft bundle | `python -S scripts/import_site_drawing.py --manifest examples/own-drawing/manifest.json --out ../ict-repro-drawing` followed by `python -S scripts/deliverable_report.py ../ict-repro-drawing` | `REPORT.html`, model, review queue and draft exports. The committed public drawing reading is supplied; these commands do not run a model or independently verify its interpretation. [Substitute your drawing](../examples/own-drawing/README.md). |
| Retain an engineering contribution and its next source revision | `python -B -S examples/engineering-onboarding/contribution-loop/reproduce.py --out ../ict-repro-knowledge` | Source-qualified handoffs and contribution/refresh receipts. Retain earlier claims and reopen combined-source reasoning when a source changes. [Own-input contract](../examples/engineering-onboarding/contribution-loop/README.md). |
| Connect selected history, drawing findings and notes through receiving and the next change | `python -B -S examples/foundation-cycle/reproduce.py --out ../ict-repro-foundation` | Explicit scoped projections, exact originals, actual toolkit graph/context readback, conflicts, source-only and combined revisions, omissions and full export/reopen. [Own-input contract and limits](FOUNDATION_HANDOFF.md). |
| Recorded batch calculations | `python -B -S scripts/batch_analysis.py --csv examples/batch-analysis/observations.csv --plan examples/batch-analysis/plan.json --graph examples/batch-analysis/graph.json --out ../ict-repro-batches` | `batch_analysis.json` and `batch_analysis.md`: units, declared phase windows, observed coverage and mapped asset IDs. [Expected outputs and limits](../examples/batch-analysis/README.md). Calculations do not establish causation or a valid site recipe. |

Read each exercise's actual receipt and known-answer checks. Exit zero alone does not establish that the result
means what the user needs. A fixed replay with its own authored key is software evidence, not independent
engineering validation, model-reading accuracy or measured human saving.

## 2. Try a failure and retain the next revision

The maintenance, port, path and knowledge runners above already include subsequent revisions or deliberately
wrong comparisons. Inspect those outcomes rather than keeping only the final successful report. To challenge
the comparison and source contracts further, run the existing targeted suites:

```sh
python -S scripts/test_maintenance_intake.py
python -S scripts/test_pid_markups.py
python -S scripts/test_pid_connections.py
python -S scripts/test_pid_path_review.py
python -S scripts/test_knowledge_capture.py
```

Use a copied packet in a fresh destination for your own planted fault. Specify the expected refusal or finding
first, change one meaningful condition (source revision, endpoint, identity, field or coverage), and keep the
original, changed input, command, actual result and explanation. An unknown or failed acquisition is not an
all-clear. Never modify a frozen key to make the result agree.

## 3. Choose the additional evidence your claim needs

| Claim or task | Reproduce this | What it does not establish |
|---|---|---|
| Source-preserving CAD metadata proposal | Follow [DXF equipment-data exchange](../examples/cad-handoff/data-review/README.md) with the pinned requirements. Use the [qualification index](../examples/cad-handoff/qualification/README.md) for byte checks and retained native returns. | General CAD equivalence, DWG/intelligent-P&ID preservation or an accepted native full save. |
| Repeat retained native observations/images offline | Run [UI19 receiving](../examples/cad-handoff/qualification/native-ui-pairs-19/README.md) and the [separate camera repeat](../examples/cad-handoff/qualification/camera-repeat-20/README.md). | A new native UI session, corrected old failures, reserved transfer or engineering readability/acceptance. |
| Inspect how a failed native observation method was repaired | Follow the [observer transport evidence](../examples/cad-handoff/qualification/observer-transport-21/README.md): installed-API probes, failed synchronous bridge, event-driven successor and retained fault controls. Offline replay uses the standard library. | Availability of the original local CAD image, a general CAD adapter or completed edit/save qualification. |
| Reproduce a saved drawing/model score | Use [benchmark registry scoring](../benchmarks/README.md), [prediction rescoring](../predictions/README.md) and [reviewer checks](../AGENTS.md#ten-minutes-no-accounts-no-network). | A new model run, unseen-data performance or a plant guarantee. Claim matching and actual rescoring are different checks. |
| New image/scan/photo interpretation | Supply the permitted original, declared model/OCR/version/prompt and preprocessing, a source/key basis, uncertainty and saved failures. Follow [drawing contribution](CONTRIBUTE_A_PID.md), [reader slot](PLUG_IN_A_READER.md) or [photo example](../examples/photo-to-record/README.md). | Installed identity, unreadable values or connections absent from the evidence. |
| Native receiving-system acceptance | Follow the selected editor/gateway/version's exact import/edit/save/close/reopen/readback and next-revision checks. [CAD protocol](../examples/cad-handoff/qualification/PROTOCOL.md) and [Ignition record](IGNITION_ACCEPTANCE.md) define separate scopes. | Company release, operating authorization, PI acceptance or acceptance in another version. |
| Calculation or automation consulting scope | Use [calculation review](../examples/consulting-start/CALCULATION_REVIEW.md) or [automation handoff](../examples/consulting-start/AUTOMATION_HANDOFF.md). Retain the client's existing tool, inputs, reference and receiving basis. | A toolkit simulator, MTP adapter, generated PLC logic, verified thermodynamics or a funded client requirement. |

For the larger historical TE/OPEN100 assemblies, use the [advanced reproduction guide](REPLICATE_AT_YOUR_PLANT.md).
For all repository checks, use [run_tests.py](../scripts/run_tests.py) with the pinned requirements and inspect
reported skips. A green CI job can contain skipped checks; local replay is not runtime/site acceptance.

## 4. Transfer the method to your records

1. Define the selected question, scope, source authority and exact source revisions. Freeze expected behavior
   before evaluating a method change; retain source/key provenance and actual prior exposure.
2. Inspect original rows/pages, then prepare only the input contract in [WORKFLOWS.md](WORKFLOWS.md).
   Identity, units, endpoint meanings, layout and interpretation remain supplied/reviewed work where stated.
3. Run the documented tool in a new directory. Keep original source bytes, transformations, method/version,
   complete results and failures. Trace each material finding back to its original source location.
4. Reopen or relocate the retained package through its documented route. Compare a predeclared next revision
   and a meaningful wrong control beside the same baseline. Reproduction checks must match the claimed scope.
5. Return the finding, unknowns, correction/evidence request and proposed owner. Company receipt/readback
   establishes an accepted correction; a disappeared finding alone does not. Measure complete preparation,
   interpretation, rework and receiving effort before claiming a saving.

The assistant and numerical/drawing reader are replaceable. The useful retained work is the source, interpretation,
review and receiving basis. Check [existing/free tools](COMPETITIVE_WORKFLOWS.md) before adding a platform or
format; a self-service outcome is valid without contacting the author. Larger scopes can use the
[consulting forms](../examples/consulting-start/README.md). No human participant, plant access or paid engagement
is fabricated by these exercises; those remaining [acceptance gaps](SELF_SERVICE_GAPS.md) stay explicit.
