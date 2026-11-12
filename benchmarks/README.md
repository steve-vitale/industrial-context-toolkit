# Corpus-driven improvement and model/task results

The contribution loop is **new case → reviewed source/key → saved model/method answers → offline scoring →
failure analysis → generalization → baseline regression check**. See [CONTRIBUTING.md](../CONTRIBUTING.md).
The corpus is a growing test bed; results describe particular tasks and methods on particular source families.
There is no universal best-model score.

## Current reproducible tasks

| Task | What is scored | Current evidence | Results |
|---|---|---|---|
| `drawing-extraction`, `pid2graph-v1` | Rough/strict six-class symbol F1 and asset-network F1 using the unchanged scorer | Existing five replicates each for Claude and Codex on six OPEN100 validation drawings. The method includes tiling and deterministic tracing. This is retrospective registration of saved runs; validation also informed method selection. | [Model comparison](results/open100-validation-tag-adapter.md), [JSON](results/open100-validation-tag-adapter.json), [suite](open100-validation.json) |
| `description-facts`, `native-facts-v1` | Literal selected equipment/type, stream endpoints, instrument/valve placement and controller relations against explicit fact atoms | Two authored synthetic cases with reference, empty and wrong-endpoint controls. Keys come from those same references. **Scorer development only: no AI interpretation benchmark.** | [Scorer controls](results/description-controls-tag-adapter.md), [JSON](results/description-controls-tag-adapter.json), [suite](description-controls-recipe-preserved.json) |
| `description-facts`, `native-facts-v1`, source review | The same selected fields against separately prepared original-source keys | [MGPI source-adapted development case](../examples/from-description/mgpi/README.md), with retained unsupported initial adaptation and an explicit source/key expansion. No held-out or original-text model trial. A planted false-shutdown claim still scores perfectly and exposes a scorer blindspot. | [Development artifacts and controls](results/mgpi-development-tag-adapter.md), [suite](mgpi-development-recipe-preserved.json) |
| `source-support`, `claim-judgments-v1` | Labels for fixed supplied claims against a bounded key; missing claims stay in the accuracy denominator | Twelve MGPI/NIST development claims using explicit project paraphrases. Synthetic scorer controls only; reasons and source validity unscored. | [Control results](results/source-support-development-tag-adapter.md), [suite](source-support-development.json) |
| Same label task, opt-in `provided-model-values-v1` admission | Exact frozen artifact values/roles/groups and approved context are admitted before the unchanged label scorer; coverage and keyed artifact contradictions are separate | Two exposed source-adapted artifacts, 82 value entries/55 provided rows/14 semantic groups each. Fourteen synthetic saved reviewer controls, not model trials or automatic claim discovery. | [Contract and contribution steps](source-support/artifact-values/README.md), [suite](source-support/artifact-values/suite.json), [publication report](results/artifact-value-review-development.md) |
| `tag-reading`, `tag-text-v1`: `geometry` | Strict tag recall over labelled scored symbols, plus accuracy on geometrically found symbols; lenient text rates are companion diagnostics. No tag precision/F1. | Saved attempts, current frozen source-derived keys and labelled-symbol projection. Exposed development evidence; offline adapter and saved-answer registration, not a new trial. | [Tag report](results/tag-reading-development.md), [JSON](results/tag-reading-development.json), [suite](tag-reading-development.json). No new model trials. |
| `batch-totals`, `logged-cumulative-v1` | `scripts/batch_analysis.py` full-window feed integrals per supplied window (whole batch and each hour) against the change in a publisher-logged running cumulative, within 0.5 kg | Ten public industrial baker's-yeast batches (figshare 33201579): development B01-B05, then one sealed held-out run on B06-B10 (A418). Deterministic tool runs with four tool-run controls and four scorer controls (perfect, empty, shuffled, recipe constant). The key is the publisher's own sum of the same feed column: an integration-semantics check (interval convention, unit, window, coverage, source consistency), not a measurement or outcome benchmark. | [Case and failures](../examples/batch-analysis/industrial-yeast/README.md), [suite](industrial-yeast-batch-totals.json), [report](results/industrial-yeast-batch-totals.md): development 5/5 batches and 84/84 hours; held out 4/5 and 82/85, kept |
| The same tag task: `taglist` | Lenient substring recall over listed identifiers. This is upper-bound partial-list coverage, with no box/location assignment or precision/F1. | Saved attempts and current frozen partial lists. Separate mode/cohort from geometry; partial-list coverage does not establish correct item assignment. | [The same report](results/tag-reading-development.md#partial-list-identifier-rates), with a separate mode/cohort. No ranking across modes. |

The third adapter, `source-support` / `claim-judgments-v1`, grades **fixed supplied claims** as supported,
contradicted or insufficient-evidence. Its [development suite](source-support-development.json) has twelve
claims, six each from MGPI and NIST, balanced four per label. A separate coding agent froze the original-source
key before candidate/scorer work. The public packets are project-authored paraphrases that explicitly scaffold
scope and absence distinctions; they are not original-document comprehension inputs or a blind evaluation.
The [prompt](source-support/prompt.md), [full review key](source-support/review_key.json),
[source inventory](source-support/source_inventory.json) and [projection receipt](source-support/KEY_PROVENANCE.json)
retain dates, locators and multi-source joins. Source hashes are declared metadata; this scorer does not fetch
or revalidate the original files.

[Results](results/source-support-development-tag-adapter.md) show synthetic controls only: reference 12/12, empty 0/12,
and each uniform-label control 4/12. These validate scorer behavior, not model capability. Primary accuracy is
correct/expected claims; missing decisions remain in the denominator. Per-label F1 is diagnostic and can differ
from accuracy on incomplete answers. Citation IDs must be admitted and reasons nonempty, but **reason quality
and whether a citation supports a claim are unscored**. Readable partial answers can have status `ok`; that means
scored, not complete or reviewed. This adds no automatic claim discovery, useful-question score, question rule,
current plant truth or human acceptance. Preserve genuine model attempts separately from these controls.

To add a public drawing case with an independently verified key, follow
[docs/CONTRIBUTE_A_PID.md](../docs/CONTRIBUTE_A_PID.md). Drawing cases pair a PNG input with a PID2Graph GraphML key; answers use `symbols`/`connections` or the existing
saved prediction envelope. Description cases pair UTF-8 source text, a JSON `facts` key and an expected native
model for the positive control. Submitted answers can be a native process model or the description workflow's
`model`/`layout`/`evidence` wrapper. Keep evaluation keys/reference models out of the inference packet.

The tag task declares `tag_key_kind` on every case. `geometry` uses the PNG, GraphML and separate tag key;
existing rough one-to-one symbol matching precedes text scoring. Strict recall is correct tags / labelled truth;
accuracy on found symbols is correct tags / found labelled symbols. An unfound symbol remains a recall miss.
`taglist` uses the PNG and a partial identifier list: a normalized identifier can match anywhere inside a predicted
tag, so one concatenated tag can satisfy several rows. Its class-agreement share is diagnostic, not precision.
Undefined rates stay null. Neither mode resolves a tag to a company asset or establishes engineering validity.

The offline fixture contains 13 exact cached adapted files, with a copied license and source/derivation
provenance. Current key bytes are frozen for development; original historical converted-key bytes and the
producing converter/version are not authenticated by those freezes. Retain that uncertainty. Five sheets from
one publisher and generated/degraded variants are not new independent source families or held-out tests.

The fact task grades identities and the fields in `benchmark.FIELDS`, plus controller output targets. It does not
grade names, narrative equivalence, source support, physical dimensions, operating limits, interlocks, drawing
layout or engineering completeness. A wrong name citing a real source can still pass. Use independent source
inventories, explicit unknowns and the [description evaluation plan](../docs/EVALUATION.md#8-description-to-pid-evaluation-gap)
before claiming interpretation accuracy. Results show fact categories separately and list missing/unexpected
facts: one wrong stream endpoint must not disappear behind a high score on unrelated equipment fields.
The [description workflow](../examples/from-description/README.md)
provides separate structure/quotation/drawing checks; those are not substituted for this task's source truth.

## Extend coverage across the toolkit

| Function family | Existing evidence | Next benchmark contribution |
|---|---|---|
| Drawing reading, tags and topology | Saved predictions, frozen geometry/tag scorers, replicate analysis and corpus matrix; the registered tag task above | Independently reviewed tag truth, real scans/handwriting/dense archives and new model/version runs; registration alone adds no reading capability |
| Description/model generation and detailed drafting | Assisted workflow fixtures; selected fact-task adapter; TE/Bayer worked examples | Independently keyed unfamiliar descriptions, missing/unsupported facts and separately reviewed rendered layouts |
| Questions and evidence/decision packets | Feature tests, sourced worked examples and independent software reviews | A reviewed question/grounding rubric with source-backed expected and unacceptable claims; keep usefulness separate from format checks |
| Graph/export/CAD/platform preservation | Corpus matrix and native-field regression checks | Semantic fidelity cases for each format, including omissions, unknowns, ownership and source/status preservation |
| Historian analysis and impact estimates | Separate public-data matrix runs and calculation tests | Labelled detection conditions, false alarms, measurement uncertainty and calculation truth; distinguish deterministic methods from AI models |
| MCP, maintenance and other integrations | Bounded protocol/feature tests and selected lab acceptance | Task-specific retrieval/coverage and compatibility tests; no performance claim about an untested company deployment |

These rows identify work to add. Five task adapters are implemented. `tag-reading` is one adapter with
two modes; each keeps its own counts, rates and comparison cohorts. Not every feature has a generalization benchmark. New tasks require a tested evaluator
contract and known-answer controls, rather than importing an arbitrary score column into a leaderboard. See the full
[feature inventory](../docs/FEATURES.md) and [eight-workflow matrix](../docs/GENERALIZATION.md).

## Reproduce or extend

```sh
python scripts/benchmark.py --registry benchmarks/registry.json
python scripts/test_benchmark.py
```

These scoring commands use no models, subscriptions, downloads or servers. Registered files and saved model
identities/prompts are checked before scoring.

**Collecting tag-reading answers with approved Copilot or manual saved JSON:** choose the declared tag mode and
exact image before collecting an answer. Give only that input image and task instructions to an approved client; keep keys and reference answers
out of that packet. Keep company documents, answers and metadata in approved private storage. No cloud model
integration is required, and this example does not establish approval of a Copilot tenant or connector. You can
save answers without installing this scorer; another approved workstation can score them offline.

**Comparing models or vendors:** freeze cases, keys and source provenance first, then retain each attempted
answer, failures included, with its model/version/interface, prompt, settings and any answer conversion. Use the
[contribution steps](../CONTRIBUTING.md#submit-model-and-method-results) for manifests and private `--root` scoring.
For tag geometry, symbol IDs must be exact unique nonempty, non-whitespace strings across all rows; invalid IDs fail the whole
answer rather than being repaired. This geometry-only policy does not apply to tag-list matching or older tasks.
Compare like-mode cohorts and counts, keeping model/method rows separate. Saved model metadata is a contributor
declaration, not provider attestation. The [tag suite](tag-reading-development.json) and [report](results/tag-reading-development.md) are registered for offline checks.

Changed source/key/prediction fingerprints fail validation; they are not counted as a
model's failure. Python scoring-code fingerprints normalize CRLF to LF, so equivalent Windows/Linux checkouts
share a cohort; actual source edits still change it. Other declared text extensions use the same normalization.
Missing/invalid attempted answers remain scored failures. New unattempted cases remain a visible
coverage gap. Comparisons group by task, scorer-code/contract, exact selected inputs/keys/protocol, family, split
and evidence type; model versions, interfaces and method settings remain separate rows. Five model replicates
on one drawing family do not establish five independent source families or a new held-out experiment.
An answer status of `ok` means it was readable and scored, not that its engineering claims were correct. Inspect
the category scores and missing/unexpected facts; execution failures and semantic mistakes are different findings.

The machine-readable [registry](registry.json) lists the current reproducible snapshots. Its drawing-reader results
are also shown per reader, family and split, beside their controls, on the generated [reader leaderboard](LEADERBOARD.md)
(`python scripts/reader_leaderboard.py --check`). The registered JSON retains exact
counts, failed answers, coverage, dates, model/configuration declarations, recipe hashes and optional reported
resources. Each replicate pools task counts before computing its metrics. Summaries average replicate metrics; tag rates also report how many repeats have a defined denominator. Range/SD describe those
repeats; they do not establish statistical significance or a winner. Unknown model builds, cost and timing stay
unknown. For a new method, retain the old answer artifacts and score both on the same baseline before expanding
the corpus. This makes improvements inspectable and keeps failures useful to the next contributor.

## Report implementation revisions

Registering the `batch-totals` adapter (2026-11-12, A418) changed `scripts/benchmark.py`, so the six earlier
registered suites were re-scored offline into `*-batch-totals` report prefixes; every count, control, status and
metric is unchanged apart from the code fingerprint and the cohort and group IDs derived from it. The earlier
reports are kept.
The development-only suite `industrial-yeast-development.json` and its report were committed before the held-out
run (dd040dad) and are no longer registered. A later wording-only change to the batch tool's report text regenerated
the case's tool reports (scores byte-identical), so that suite now refuses on its pinned report bytes in the current
tree; it reproduces at dd040dad.

The registry selects current actual report pairs; earlier tag-adapter reports remain versioned snapshots.
The opt-in artifact-value admission changes the shared benchmark implementation fingerprint, so all five prior
suites require actual successor re-scores, alongside the new saved-control suite. Registering the adapter changes the shared implementation fingerprint and derived comparison IDs. The
older tasks retain their exact typed counts, statuses, controls, model/recipe metadata and diagnostics. These are
not new model trials or measured improvements in interpretation.

Every earlier suite, run and report remains unchanged as a historical snapshot. Use the registry for current
reproduction, and inspect its selected report prefix before comparing implementations. Earlier source-preserved
and recipe-preserved reports retain their own code and provenance identities.

The current description-control and MGPI suites separately preserve their historical recipes after the live
description guide and workflow gained interpretation-review sheets. The exact guide and code bytes from
commit `bdf1b41` are retained as [recipe text](recipes/description-workflow-20261030.txt) and
[code text](recipes/description-workflow-20261030.py.txt), with the original pinned content hashes. These are
historical sources, not the current guide or executable workflow. New `*-recipe-preserved` manifests relocate
those recipe references and explain the provenance; their original run IDs, dates, predictions, model declarations,
case inputs and keys remain unchanged. The registry selects actual offline re-scores under new report prefixes.
Counts, controls, metrics and scoring cohorts are unchanged; recipe paths change submission/group identities
and may reorder the summary. This is no new model attempt, method improvement or interpretation result.

The original suites, run manifests and report pairs remain unchanged. Their references to the former live
guide/code require the corresponding historical checkout; use the current registry for reproducible checks
against the archived recipes. Keeping an old result does not authorize rewriting its original recipe or date.
