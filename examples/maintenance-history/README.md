# Maintenance history: one useful investigation

An offline workflow for maintenance and engineering managers: supplied assets and
work orders, plus optional material/labor exports, become a readable brief and
source-linked asset histories. Use [the own-input contract](../../docs/MAINTENANCE_HISTORY.md)
for your records. This folder contains authored teaching fixtures and public
evaluation evidence, with different roles.

```sh
python -S examples/maintenance-history/reproduce.py --out ../ict-history-demo
```

Open `initial/REPORT.html`. No accounts, downloads, packages or model calls.
The [committed text brief](worked/initial/REPORT.md) is inspectable on GitHub;
download/clone the packet to open its HTML locally. [Full source-linked packet](worked/initial)
and [replay receipt](worked/REPLAY.json) are retained.

## What should happen

The [acceptance cases](ACCEPTANCE.md) and raw-ID [baseline](baseline.py) were
committed before implementation. U1/P-101 has three selected orders, U2/P-101
one; a raw-ID count incorrectly combines four. Two recurring groups are kept,
including planned grounds work, so recurrence cannot be called repeated failure.
W1's signed hours 2, -0.5, 0 total 1.5; U1/P-101 totals 2.5 and U2 totals 3.
No PARK labor records means unavailable, not zero. A wrong-entity transaction,
contradictory detail target and orphan labor stay outside the asset subtotals.
Parts quantities 2 and -1 remain individual movements. Completion/flag/date
ambiguities remain source-linked questions.

`reproduce.py` runs comma CSV, renamed semicolon CSV and JSON, then a corrected
W2 completion and an export omitting W2. Prior packets and unresolved omissions
survive portable replay. `scripts/test_maintenance_history.py` additionally
challenges duplicate primary keys, changed bytes under unchanged revisions,
unknown/missing/zero values, altered mapping meanings, exact foreign keys,
tampered findings/history, escaped retained paths and occupied destinations.
Seventeen unittest methods passed at freeze. An initial missing-hours action
test failed; the implementation was corrected before freezing. It is retained
as a regression, not removed or changed to accept the omission.

These are author-run software checks, with an independently specified fictional
key. No independent agent/human review or measured manager benefit is claimed.
[Desktop/mobile inspection](visual/QA.json) covers actual rendered pages, source
navigation, asset filtering and table scrolling, with screenshot hashes.

## Public development and reserved outcome

The exposed [AMPS cohort](../public-data/round-4/README.md) contains request dates
2024-01-01 inclusive to 2024-01-08 exclusive. We inspected the publisher's
[primary definitions](PRIMARY_SOURCES.md) before interpreting fields. The signed
hours ledger includes all correction entries. Parts movements are not installed
parts or net consumption; rates are not actual payroll; missing completion is
not current open status. Asset keys may identify equipment, systems or broad
locations. The selected request dates do not describe all work performed that week.

| Development observation | Result |
|---|---:|
| Assets / selected work orders | 933 / 1,612 |
| Transactions / material detail rows / labor entries | 208 / 263 / 5,268 |
| Exact recurring-work review groups | 177 |
| Review issues | 82 |
| Missing completion values | 65 |
| Negative material quantity / unavailable parent order | 1 / 1 |
| Grouped unresolved code / flag meanings | 13 / 2 |

[Original-column audit](public/development-audit.json) separately checks counts,
qualified joins, per-asset order counts, signed hours, recurrence groups and every
emitted original-record locator. All six pass. [Original-file pins](public/development-pins.json)
retain the input identity. The raw baseline has 933 ID groups here, agreeing with
the scoped asset count: this source has one administrative scope. The fictional
cross-scope control establishes the distinction; no public accuracy improvement
percentage is invented. Grouping adds inspectable questions rather than a scored
failure diagnosis.

The [plan](PLAN.md) preselected **2024-01-15 inclusive to 2024-01-22 exclusive**
before implementation. Commit `d7c5804` and [FREEZE.json](FREEZE.json) fixed the tool,
adapter, independent calculation, acquisition recipe and contract before reserved
content download. The [reserved acquisition](public/reserved-acquisition.json)
stopped at **HTTP 500 on the fourth related-asset batch**. Five metadata files,
the selected work-order response and three asset batches were retained locally.
The failing request/attempt is retained in the receipt; its HTTP error body was
not saved. No transactions/details/labor acquisition followed. No alternate
interval, post-outcome tuning, completed packet or reserved semantic pass.
**Reserved transfer remains unverified.** Another cohort from the same municipal
source would still not be independent industrial-plant validation.

## Reproduce public development when originals are available

```sh
# Explicit network opt-in; refuses changed publisher bytes against historical pins.
python -S examples/public-data/round-4/reproduce.py --fetch --max-mb 3 --out ../amps-admission
python -S examples/maintenance-history/amps.py --source data/external/nyc-amps-2024w01 --profile ../amps-profile.json
python -S scripts/maintenance_history.py --profile ../amps-profile.json --out ../amps-history
python -S examples/maintenance-history/amps.py --source data/external/nyc-amps-2024w01 --packet ../amps-history --audit-out ../amps-history-audit.json
```

Keep existing cached originals: live rows/metadata may change, so later network
fetches may refuse rather than recreate this historical result. `amps.py` is a
source-specific profile/audit, separate from the reusable tool. `acquire_reserved.py`
records the exact preselected live recipe; running it again would be a **new**
acquisition, not recovery of or a replacement for the recorded failed evaluation.
The batch/response ceilings and retry policy remain explicit in its code.

No open redistribution license was established in the inspected AMPS metadata.
Original rows, free text and full query URLs stay local. Committed public records
contain methods, aggregate counts, file hashes and sanitized acquisition attempts.
The fictional fixtures are repository-authored and redistributable for clean-clone
offline CI. No industrial plant data, authenticated company decisions, accepted
corrections, MTBF, root cause or savings are established.

## A second publisher: Nestor excavator records grouped by system

The Nestor excavator records (`nestor-excavators` in [corpus_depth.json](../../data/corpus_depth.json))
are 5,485 historical work orders on five mining excavators (A-E): a start date, the asset
letter, a short free text, an order type and a cost, with **no work-order ID**. The publisher
also distributes a cleaned file that adds a system code (`MajorSystem`) to most rows. The
question a manager asks: which systems keep coming back on each excavator, and which records
show it?

**Task (`maintenance-system-grouping`, attempt A420).** The tool reads only the raw export
(`Cost` is ignored), takes the record number as the ID (`identity: "record"`), keeps one
split's assets (`select`) and derives each record's system from its short text with the
declared [vocabulary](nestor/system_vocabulary.json) (`derive`); recurring groups are then
(asset, system) with two or more records. [`score_maintenance_systems.py`](../../scripts/score_maintenance_systems.py)
joins the packet's records to the cleaned file, which the tool never reads, and scores each
record's class against `MajorSystem` beside five controls.

**What it shows, and what it does not.** The tool's `derive` option applies a user-declared
vocabulary faithfully and groups by it. A 10-rule vocabulary written from development assets
A-C, including their publisher codes, agrees with the publisher's keyword-rule `MajorSystem`
on held-out D-E at per-record F1 0.943 (0.887 if no-system rows given a class count as
errors). Class-name words alone score 0.501. This shows that a vocabulary fitted on one part
of a fleet carries over to the rest under one publisher's coding scheme. It does not show what
a user without a key would write, and it does not measure engineering correctness. **The
vocabulary is a per-dataset profile artifact, not part of the product**: a site writes its own.

**How circular it is.** The key is a separate publisher field withheld from the tool, the
least circular choice this source offers: per-asset counts, order types, cost sums,
chronology or repeat intervals would all be our own calculation over the tool's input. But
the publisher made `MajorSystem` with keyword rules over the same short text (the cleaned
file's `Rule` column), and the vocabulary was written while reading A-C's codes, so agreement
measures how well a declared vocabulary reproduces those rules, not whether a system is right.
Some key codes are artefacts of substring matching: on development, a cab-heater fault is coded
Bucket because "GET" (ground engaging tools) matches inside "getting".

In the table, "frozen" precision leaves out the records the key gives no system (`NA`, about
42% of joined rows), as the frozen scorer does; "no-key as FP" counts every such record given
a class as a false positive. The key-free control was added at review, after the sealed run
(post hoc): the same tool run with a vocabulary of only the class names' own words ("and"
dropped), from [`maintenance_system_posthoc.py`](../../scripts/maintenance_system_posthoc.py).
Other literal choices move it: adding plural forms gives 0.546 / 0.543, and plural forms with
the shared word HYDRAULIC given only to Hydraulic System 0.615 / 0.594 (development / held out).

| Per-record system class: P / R / F1 (frozen); P / F1 with no-key as FP | Development A-C (fit) | Held out D-E (one sealed run) |
|---|---:|---:|
| Raw rows / joined to the cleaned file / with a system | 2,160 / 2,018 / 1,186 | 3,325 / 3,289 / 1,877 |
| **Tool with the A-C vocabulary** | 0.975 / 0.951 / **0.963**; 0.877 / 0.912 | 0.970 / 0.916 / **0.943**; 0.859 / **0.887** |
| Key-free control, class-name words only (post hoc) | 0.870 / 0.367 / 0.516; 0.798 / 0.503 | 0.885 / 0.350 / 0.501; 0.804 / 0.487 |
| Reference (the key itself) | 1.000 / 1.000 / 1.000; 1.000 / 1.000 | 1.000 / 1.000 / 1.000; 1.000 / 1.000 |
| Raw-asset baseline (no system) | - / 0.000 / 0.000; - / 0.000 | - / 0.000 / 0.000; - / 0.000 |
| Majority class for every record | 0.412 / 0.412 / 0.412; 0.242 / 0.305 | 0.394 / 0.394 / 0.394; 0.225 / 0.286 |
| The tool's own classes shuffled within each asset | 0.292 / 0.192 / 0.232; 0.177 / 0.184 | 0.261 / 0.159 / 0.198; 0.149 / 0.154 |
| The tool's classes against another record's key | 0.218 / 0.109 / 0.145; 0.100 / 0.104 | 0.223 / 0.104 / 0.142; 0.097 / 0.101 |
| Margin over the best wrong control, frozen F1 (bar 0.20, fixed before the held-out run) | 0.551 | 0.549 |
| Membership F1, (record, system) pairs inside recurring groups | 0.862 | 0.835 |
| (Asset, system) group F1 | 0.980 | 0.900 |
| No-system records given a class | 130 of 832 | 229 of 1,412 |

The [benchmark report](../../benchmarks/results/nestor-system-grouping.md) has every
control on every metric. The split (A-C development, D-E held out) was decided on
2026-11-12 before any result; two vocabulary passes were read on A-C only; the tool
options, vocabulary, scorer and margin were then frozen in [FREEZE.json](nestor/FREEZE.json)
and D-E scored once. Exposure: held-out key counts were surveyed on 2026-11-12 (work-order
counts per asset for all five assets, the date range and the MajorSystem distinct count over
all rows); no method was run. During development two whole-file parse counts that include D-E rows were also printed (cleaned file 5,308 rows; raw file read with a backslash escape 5,326 rows), and no D-E text, code or per-asset figure. Original-row checks pass on both splits: selected and excluded
counts, per-asset counts, every record's date, asset and text at its locator, and chronology.

**Failures on the real source, and what was done with each.**

- *Fixed in the tool (RED-first tests in `scripts/test_maintenance_history.py`):* the export
  has no ID column (now `identity: "record"`); one split could not be scored without the
  other's records becoming unlinked issues (now `select`); the tool could not group by system
  at all (now `derive`); and an export with no completion column raised a missing-completion
  issue on every record (now only a mapped, blank value does).
- *Fixed in the scorer on development, before the freeze:* the raw file is ordered so that
  neighbouring rows usually share a system, so a key shifted by one row still scored 0.775
  and was not a wrong control; it now shifts by half an asset (0.145). The reference control
  first used only a record's first system and missed multi-system rows; it now uses the full set.
- *Limits, not tuned after the held-out run:* the held-out key spells `Hydraulic Cylinder`
  (7 rows) where development has `Hydraulic Cylinders`, and codes `Slew` (7) and `Driveshaft`
  (3); the development key uses `Slew` once and `Driveshaft` never, and the vocabulary has
  neither; four held-out key groups are missed for these
  reasons. `Radiator` went to 27 held-out rows the key codes Engine or Hydraulic System
  (overheating and coolant terms). The group F1 does not separate (the shuffled and misaligned
  controls reach it too), so read per-record and membership F1. A no-system key row (`NA`,
  42% of joined rows) is outside the frozen precision; 16% of them got a class on the held-out
  assets, which the no-key-as-FP columns count.
  142 and 36 raw rows have no cleaned row and are unscored; one development raw row is
  malformed in the source (its text runs into the order-type and cost columns), and the tool
  reports its order type as an unknown code. Cost is not read: the tool has no work-order
  cost field, and the unit (AUD, per the publisher's loader) is not a confirmed ledger meaning.
- Both splits are one publisher, one fleet and one coding scheme: a held-out check, not a
  second source, and no failure diagnosis, repair effectiveness or plant acceptance.

Reproduce offline from the local pinned originals (their terms are unresolved, so none is
committed; the fetch is by hash and refuses changed bytes):

```sh
python scripts/fetch_public_group.py nestor-excavators --max-mb 2   # only if data/external/nestor-excavators is absent
python examples/maintenance-history/nestor.py --split development --out ../nestor-dev
python scripts/benchmark.py --registry benchmarks/registry.json     # UNVERIFIED without the local cache
python scripts/corpus_matrix.py --rows 9 --out-dir ../nestor-matrix
```

## Use it as a bounded starting assignment

Select one asset/system, agree the cohort and source-owner meanings, deliver the
traceable history and unknowns, and check one returned export. Scope preparation,
source clarification, field verification and failure investigation explicitly in
the [existing consulting forms](../consulting-start/README.md). This is a useful
self-service job without an engagement. For larger help,
[connect with me on LinkedIn and message me there](https://www.linkedin.com/in/steve-vitale/).
