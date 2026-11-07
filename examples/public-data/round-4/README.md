# Linked public maintenance records

This pass adds a useful missing category: **asset records, dated work orders, parts movements and labor from
the same source system**. NYC Parks' public AMPS tables yielded 1,612 work orders, 933 referenced assets,
208 transactions, 263 transaction lines and 5,268 labor entries. The 53 original projected API responses and
metadata files total **2,366,010 bytes**. They are local, acquired and structurally checked, without model scoring.

The four acquisition passes now retain **183 files, 423,771,529 bytes in 40 download groups**, plus the four
separately frozen DXF originals. A query batch is a file, not another independent plant. AMPS is one municipal
maintenance system; these records do not establish performance on manufacturing plants.

## Fetch or check

From the repository root, Python 3.10+ and the standard library:

```sh
# Explicit opt-in download of the selected, checksum-pinned responses.
python examples/public-data/round-4/reproduce.py --fetch --max-mb 3 --out data/external/amps-admission-1

# Offline after acquisition; hashes, schema and all four relationships checked again.
python examples/public-data/round-4/reproduce.py --out data/external/amps-admission-2

# Cached replay with the network replaced by a refusal, plus changed-byte and fictional relationship controls.
python examples/public-data/round-4/verify.py --out data/external/amps-verification-1

# Tiny fictional controls need no original records, packages or network; CI runs these too.
python -S examples/public-data/round-4/check_controls.py
```

Each output directory must be new. Originals go to ignored `data/external/nyc-amps-2024w01/`.
Live metadata and records can change: a later hash mismatch is a refusal, not permission to silently replace
the cohort. Keep an acquired copy for exact offline reproduction. `verify.py --fresh` additionally re-fetches
one work-order query; it does not re-fetch or establish snapshot consistency for the whole linked cohort.
Use a Python environment with working system HTTPS trust; certificate verification is never disabled.

## What was selected and linked

The [selection](SELECTION.md) and [original recipe](history/acquire-initial.py) were committed before row download.
All work orders with request date `2024-01-01 <= evt_date < 2024-01-08` were included regardless of outcome.
The corresponding assets, EVNT transactions, transaction lines and labor were requested with deterministic
100-identifier batches and explicit field projections. This is a one-week **request-date cohort**, not all work
performed that week, historical backlog, or a frozen database as it stood in 2024. Related rows are the source's
current public records when fetched. Labor excludes worker identity; the separate comments collection was omitted.

| Publisher table | Key / documented relationship | Rows and actual coverage |
|---|---|---|
| [Work orders](https://data.cityofnewyork.us/d/8sdw-8vja) | `evt_code`; `evt_object -> obj_code` | 1,612; all have one selected parent asset |
| [Assets](https://data.cityofnewyork.us/d/e25p-jzfy) | `obj_code` | 933; no missing or duplicate primary keys in this snapshot |
| [Transactions](https://data.cityofnewyork.us/d/gcys-vvnq) | `tra_code`; `tra_tocode -> evt_code` **only when `tra_toentity = EVNT`** | 208; all have one selected work order; 114 work orders have transactions |
| [Transaction details](https://data.cityofnewyork.us/d/ub9z-gccp) | Checked row identifier `trl_sqlidentity`; `trl_trans -> tra_code` | 263; all have one selected transaction |
| [Labor](https://data.cityofnewyork.us/d/xzj8-i3jk) | `boo_code`; `boo_event -> evt_code` | 5,268; all have one selected work order |

All five checked row identifiers are unique and nonempty, with no uncontracted projected columns in the acquired cohort.
The detail-row identifier is an observed surrogate, not an inferred publisher guarantee of global uniqueness.
The [admission](admission.json) retains counts and diagnostics. These links establish administrative association;
they do not establish installed equipment identity, a compatible BOM, physical pipe connectivity or causation.

## A useful starting job

Ask your agent:

> Fetch or inspect the pinned AMPS cohort using this guide. Show me the relationship-coverage report first.
> Then propose a source-bound maintenance review: repeated work against the same asset, orders without a
> completion value, and orders with parts/labor records. Keep source IDs and raw-file hashes in a local
> evidence table. Explain the fields using the publisher's linked User Guide and Data Dictionary before
> interpreting codes, dates, quantities, costs or correction flags. Keep unknown meanings visible.

This pass prepares those records and checks their joins. It does **not** perform that semantic analysis or
provide a ready CMMS adapter. There are 1,547 nonempty completion values; the other 65 are missing completion
values at acquisition, not automatically overdue, still open or failed repairs. Reopened/correction columns
are populated, but a nonempty value is not a true flag. Parts movements may include returns/corrections;
no net consumption or cost/hour totals have been calculated. Verify units, signs, status codes and timestamps
against source definitions before using them. Repeated work is a review candidate, not proof of repeat failure.

## Evidence and remaining limits

[Pins](../../../data/corpus_pins.json), the [source registry](../../../data/public_sources_20261107_round4.json),
[selected publisher schemas](../../../data/public-source-evidence/2026-11-07-round-4/amps-schema.json),
[acquisition receipt](acquisition.json) and [verification](verification.json) are retained. The latter checks
all 53 responses offline with zero network calls, refuses truncation/same-size mutation, and exercises ten
fictional relationship controls. A separate fresh HTTPS request reproduced the 653,046-byte work-order pin.
All 50 preexisting source pin groups and their metadata remain unchanged.

Two incomplete attempts stopped at HTTP 503; their receipts remain in [history](history/). Recovery reused only
hash-matching bytes from exact successful queries and bounded retries for missing queries. It changed no dates,
predicates, ordering, fields or ceilings. Sequential reads cannot guarantee a transactionally consistent snapshot.
API response projection, ordering, source updates or metadata changes may prevent a future exact network replay.

No dataset `licenseId` was supplied in the five inspected metadata documents. Originals/full metadata remain
local; no open redistribution license or public-domain status is inferred from public access. Retain attribution
to NYC Parks/City of New York and review the [publisher terms](https://www.nyc.gov/main/terms-of-use) for your use.
No source record values or free-text descriptions are committed here. No package was installed and no downloaded
code was executed.

The previous [category-wide](../README.md), [second](../round-2/README.md) and [third](../round-3/README.md) passes
cover drawings/CAD, photos, scans/documents, process models, batch/quality, historian/condition and alarm data.
This pass supplies linked administrative records but leaves **verified repair effectiveness, a linked industrial
plant history, engineering-reviewed drawing revisions, CAD qualification and customer-system acceptance** open.
It changes no frozen CAD cohort, model method, reader score, generalization cell or independent review status.
