# Acceptance defined before the investigation implementation

This develops one maintenance review workflow. It does not evaluate repair
effectiveness or an assistant's reading accuracy. The reserved interval in
[PLAN.md](PLAN.md) remains unopened until the method freeze.

## Contract to implement

`python -S scripts/maintenance_history.py --profile JOB.json --out NEW_FOLDER`
accepts mapped CSV or JSON-record exports. Asset and work-order tables are
required; transactions, transaction details and labor are optional. Each source
declares document identity/revision, owner role, coverage, mappings and ignored
columns. Explicit scope plus exact source ID forms each primary/foreign key.
No tag normalization, fuzzy matching, inferred units or inferred boolean codes.
Date formats are explicit. Unknown optional dates, flags and numerical values
remain source-qualified review issues rather than becoming empty/zero/false.
Duplicate or blank primary identities refuse before output publication.

Source records must be retained byte-for-byte with CSV-record/end-line or JSON
array-index locators. The packet includes a portable profile, complete record
evidence, per-asset dossiers, readable HTML/Markdown and proposed actions. Each
work order accounts for its associated transaction/detail/labor rows or an
explicit unmatched/quarantined reason. Transaction entity type must permit a
work-order join; a detail's supplied work-order reference must agree with its
parent transaction. Never silently attach a conflicting detail.

Recurring-work candidates require at least two distinct work-order IDs at the
same scoped asset with equal nonempty class/type/job-type grouping values.
The report counts selected orders, preserves planned/inspection types and parent
references, and requests review. It does not count independent repairs/failures.
Ordering uses parsed creation times; unparsed times remain separately visible.

Only an explicit signed-all-entries labor-ledger policy with a documented hours
unit permits aggregation. Include positive, negative and zero entries, including
corrections. No associated rows is unavailable, not zero worked hours. Invalid
hours make that subtotal unavailable while keeping valid rows and the issue.
Report all supplied transaction statuses and signed material quantities; do not
calculate installed parts, consumption, savings or unsupported monetary totals.

## Matched baseline and authored expected result

The baseline groups every work-order row by raw asset ID and counts rows. It
does not inspect scope, joins, codes or ledger semantics. Retain its actual
output beside the proposed packet; do not turn missing baseline features into
an invented accuracy or time-saving percentage.

The initial fictional case contains three asset records and seven orders:
U1/P-101 has W1/W2 corrective-seal orders plus W3 planned inspection; U2/P-101
has W4; PARK has two planned grounds orders; W5 references an unavailable asset
and has an ambiguous creation date. Thus raw P-101 count is four, while scoped
asset counts are three and one. Exactly two recurring-work groups are review
candidates: U1/P-101 seal work and PARK planned grounds work.

W1 labor entries 2, -0.5 and 0 hours total 1.5; W2 has 1 hour with an unknown
correction flag. Under the explicit all-entry ledger, U1/P-101 totals 2.5 hours
and U2/P-101 totals 3. No labor rows for PARK yields unavailable hours. An
orphan labor entry of 4 hours must not enter any asset subtotal. Keep material
quantities 2 and -1 as separate evidence. A wrong-entity transaction must not
join W2. A detail naming W2 beneath W1's transaction must remain quarantined.

Prepare the same facts as comma CSV and differently named semicolon exports
using configuration only. Counts, relations and ledger results must agree;
source bytes and locators will differ and must remain correct for each layout.

## Revision, failure and delivery checks

1. Correct W2 completion in a new revision; preserve the earlier packet and
   separately report source, mapping/coverage/method changes. No acceptance is
   inferred from a disappeared issue.
2. Omit a prior order in a partial export; keep an explicit unresolved omission
   rather than calling it deletion or closure. Portable replay includes history.
3. Challenge duplicate IDs, unknown status/boolean encodings, ambiguous dates,
   wrong/missing parents, conflicting detail targets, negative/correction entries,
   invalid hours, zero hours, missing/empty optional exports and changed mappings.
4. Reject changed bytes under unchanged source revision, tampered prior packets,
   unsafe source/output aliases and occupied outputs without modifying originals.
5. Independently count original public rows/joins and signed ledger values, and
   trace selected dossiers to original rows. Retain discrepancies as failures.
6. Inspect the actual generated manager and asset pages at desktop/mobile sizes.
   Navigation must reach both the work-order evidence and outstanding actions.
7. Freeze code/contracts and public adapter before reserved content download.
   Evaluate the preselected interval once; retain acquisition/semantic failures
   and avoid a new cohort or method change to seek favorable results.
8. Clean-clone offline fixture replay and appropriate regressions run in CI.
   Report actual exact-final-head results and skipped checks.
