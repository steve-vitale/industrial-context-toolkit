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

## Use it as a bounded starting assignment

Select one asset/system, agree the cohort and source-owner meanings, deliver the
traceable history and unknowns, and check one returned export. Scope preparation,
source clarification, field verification and failure investigation explicitly in
the [existing consulting forms](../consulting-start/README.md). This is a useful
self-service job without an engagement. For larger help,
[connect with me on LinkedIn and message me there](https://www.linkedin.com/in/steve-vitale/).
