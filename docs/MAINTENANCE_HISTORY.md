# Investigate selected maintenance histories

Use this when a manager asks “what keeps coming back on these assets, what work
was recorded, and which records should we investigate next?” Supply permitted
asset/work-order exports and, if available, related material and labor exports.
The tool builds a local HTML brief, searchable asset index, per-asset chronology,
recurring-work candidates and proposed source-linked actions. It runs offline
with Python 3.10+ and the standard library. No account, model, CAD or MCP is needed.

For conflicting installed equipment values after replacement, use
[maintenance reconciliation](MAINTENANCE_INTAKE.md). This history workflow does
not infer an installed model/serial from a part movement or work description.

## Try one useful job

```sh
python -S examples/maintenance-history/reproduce.py --out ../ict-history-demo
```

Open `initial/REPORT.html`, find U1/P-101, then follow W1 to its original CSV
record. Its 2, -0.5 and 0 booked-hour entries total 1.5 hours under the declared
signed-ledger policy. U1/P-101 has three selected orders and 2.5 booked hours;
U2/P-101 remains separate with one order and 3 hours. A planned grounds group
also recurs; neither group proves repeated equipment failure. The runner checks
two CSV layouts, JSON, corrected/omitted exports and portable history replay.
[Authored acceptance](../examples/maintenance-history/ACCEPTANCE.md) predates implementation.

## Substitute your exports

Copy one [example profile](../examples/maintenance-history/inputs/comma/profile.json)
to a private working folder. Inspect source headers, primary keys, scope, dates,
coverage and exact code definitions before editing its mappings. Run:

```sh
python -S scripts/maintenance_history.py --profile /path/to/profile.json --out /path/to/new-packet
```

Paths in the profile are relative to its directory, or absolute. Destination must
be new. Inputs stay intact and exact copies are retained in `originals/`.
Do not put private records or packets in this public repository. The report has
no external assets or network calls; serving it is optional. Open it locally.

The profile uses `schema: maintenance-history-1`. Declare `namespace`, the
manager's `question`, and an ISO calendar `as_of` date. The date flags later
event values; it does **not** filter records into a historical snapshot.

For each source in `sources` declare:

| Setting | Contract |
|---|---|
| `assets`, `work_orders` | Required tables. `transactions`, `details`, `labor` are optional; details requires transactions. |
| `id`, `revision`, `owner`, `coverage` | Distinct source document ID, honest export revision, suggested owner role and selection/omission limitations. Changed bytes under the same source ID/revision are refused when comparing a prior packet. |
| `files` | One or more `{ "path": "...", "sha256": "optional expected hash" }` entries. No repeated file roles. JSON can span ordered API batches. |
| `columns` | Source-header to canonical-field mapping. See fields below. Every CSV header is mapped or explicitly in `ignored_columns`; JSON keys must be mapped/ignored, absent keys remain missing. |
| `constants` | Optional explicit `scope` or `entity` only; never invent an asset ID, status, hours or date. A scope constant identifies an administrative namespace, not necessarily a physical plant. |
| Format | `format: csv` (default) or `json` array of objects. Encoding `utf-8-sig` (default), `utf-8` or `cp1252`; delimiter comma (default), semicolon, tab or pipe. JSON numbers preserve lexical values, booleans/nested mapped values require explicit preparation. |
| `date_formats` | Declare every mapped date: `iso_date`, floating `iso_datetime`, offset-bearing `iso_utc`, `dmy_date`, `mdy_date` or `english_datetime` (`Jan  9 2024 12:50PM`). Declare `time_basis`, including unknown timezone/within-day limits. No locale guessing. |
| `flags` | Optional `reopened`/`correction` dictionaries with disjoint exact `true`/`false` lists. Unmapped codes stay unknown, including blank flags. Nonempty unknowns generate actions. |
| `labels` | Field → exact raw code → meaning, grounded in the source owner/dictionary. Empty dictionary deliberately exposes all observed nonempty codes as unresolved. |
| `work_order_entities` | Required on transactions: exact entity codes allowed to reference work orders. Equal-looking IDs in another entity cannot join. |

All tables require exact nonempty `id` and `scope`; duplicate `(scope,id)` keys
are refused before publication. References join only within the same scope.
Whitespace and spelling are not silently normalized. Supply an explicit reviewed
crosswalk/prepared export if systems use different keys; keep that crosswalk as
source evidence. The tool does not guess identity from descriptions.

| Table | Canonical fields |
|---|---|
| assets | `id`, `scope`; optional `description`, `kind`, `type`, `manufacturer`, `model`, `serial` |
| work_orders | `id`, `scope`, `asset_id`, `created`; optional `description`, `work_class`, `order_type`, `job_type`, `completed`, `reopened`, `parent_id`, `status` |
| transactions | `id`, `scope`, `work_order_id`, `entity`; optional `status`, `type`, `date`, `from_id` |
| details | `id`, `scope`, `transaction_id`; optional `work_order_id`, `part_id`, `catalog_part_id`, `description`, `unit`, `quantity`, `price`, `date`, `type` |
| labor | `id`, `scope`, `work_order_id`; optional `date`, `hours`, `rate`, `cost`, `correction`, `trade` |

Required mappings can contain missing values except primary identity; missing
relationships/dates remain explicit. A detail must have a qualified transaction;
if it also names a work order, both must agree. Contradictions are quarantined.
Cancelled/unapproved transactions remain associated evidence with their raw
status; association is not approval, installation or consumption. Parts quantities
and units remain individual source entries, with negative quantities flagged.

To authorize hours aggregation, supply `labor_ledger` with
`mode: signed_all_entries`, `unit: h`, and a source-grounded `basis`. It sums all
linked entries, including signed corrections and zero, rather than filtering by
the correction flag. Use this only if your source uses that ledger convention.
If not confirmed, omit this policy: rows remain visible and totals are unavailable.
Blank/invalid hours block the associated subtotal; zero remains a known zero.
Missing rows/exports are distinct from zero. Rates/costs are retained without
currency, payroll or savings calculations. The report labels totals **booked hours**.

`recurring_fields` selects a nonempty subset of `work_class`, `order_type`,
`job_type` (default all three). Within each scoped asset, at least two distinct
orders with identical nonempty values form a review candidate. Missing values
are listed as unclassified. Descriptions, parent orders and planned work remain
visible; this is transparent grouping, not a classifier, failure episode counter,
root-cause diagnosis or priority based on safety/criticality. The asset index is
sorted by selected-order count. Confirm whether each asset is equipment, a system
or a broad location before acting on recurrence.

## Read the result and act

`REPORT.html` is the manager brief; `assets/*.html` gives individual histories.
`evidence/*.html#rN` leads to mapped fields/declared constants and exact originals.
CSV locators identify logical record number (header is record 1) **and** physical
end line, so multiline descriptions do not shift the claimed row. JSON locators
are one-based array records. Ignored fields remain in original bytes.

`result.json` retains all records, joins, unknowns and grouping evidence.
`actions.csv` proposes roles and follow-ups; people and dispositions remain
pending. Start with an actionable ambiguity: identify the exact work/asset,
obtain the code meaning or missing source, ask the record owner to resolve it,
then read the accepted company record back. There is no writeback or assignment.
Record any reasoning that combines sources in the existing
[context register](CONTEXT_REGISTER.md); this workflow does not automatically
register a company decision or keep a live graph synchronized.

## Receive corrected or partial exports

Increment the changed source revision and write a new packet:

```sh
python -S scripts/maintenance_history.py --profile /path/to/new-profile.json --previous /path/to/previous-packet --out /path/to/new-packet
python -S scripts/maintenance_history.py --check-packet /path/to/new-packet
python -S scripts/maintenance_history.py --profile /path/to/new-packet/job.json --out /path/to/portable-replay
```

The new packet copies prior evidence, compares exact added/changed/omitted
records, retains earlier issues and exposes source/mapping/coverage/method basis
changes. A disappeared issue needs reconciliation; omission is not deletion,
closure or accepted correction. History is bounded at 20 nested revisions; archive
and verify older evidence separately. Packet hashes detect changed bytes relative
to the receipt; they are not authenticated signatures. With current method hashes,
checking also recomputes findings and revision comparisons. A different method
is reported as not reproduced; its retained evidence is not retroactively approved.

Budget: 64 MB original source bytes and 200,000 combined records per run. History
and rendered views add storage. For larger scopes, split deliberately with explicit
coverage rather than silently sampling. This is a batch investigation, not live
monitoring, full maintenance performance measurement or plant acceptance.

The [public evaluation](../examples/maintenance-history/README.md) states what was
checked and what remains unknown. No manager's time/benefit or industrial plant
performance has been measured.
