# Start with maintenance records that disagree

If your question is what work keeps recurring rather than which installed fields
disagree, use [maintenance-history investigation](MAINTENANCE_HISTORY.md). Its
offline brief joins explicitly mapped assets, orders and optional parts/labor
evidence, with a chronology, unknowns and next actions.

Use this when a replacement, work order or maintenance question sends someone through several systems to work
out which equipment is installed and which records describe it. Start with one unit, one tag and a question such
as: **does the equipment register match the replacement recorded on the closed work order?**

## Try the supplied example

For a manager's review without commands, open the [brief and owner actions](../examples/manager-review/BRIEF.md)
or [download the offline packet](../examples/manager-review/manager-review.zip?raw=1).

Follow the [replacement handoff](../examples/maintenance-handoff/README.md). It reuses the existing fictional
pasteurizer and real toolkit commands; no account, model call or company data is required. It shows a closed
work order, conflicting serial numbers, a size disagreement and a field ruling with a correction still due.

## Use your own records

Your agent can do the preparation with you. The [reusable export intake](MAINTENANCE_INTAKE.md) accepts your two
CSV files and an explicit mapping, retains original-row references and produces a manager packet without drawings.
Its [three-revision example](../examples/maintenance-intake/README.md) shows a corrected export and another replacement.

1. Agree the site/unit namespace, functional position and physical equipment identity. A tag can survive a
   replacement; retain the old and new serial/model records with dates. Do not merge equipment on similar names.
2. Prepare selected equipment, work-order, datasheet and optional PM/spares CSVs using the
   [one-map contracts](ONE_MAP.md). Use exact document IDs/revisions and record what each export covers.
3. Build the map explicitly. Review disagreements and missing records with the responsible owners; silence in
   a partial export is not proof an asset or activity does not exist.
4. Use [photos and scans](../examples/photo-to-record/README.md) as attributed observations. Keep the equipment
   view, tag and nameplate association explicit; preserve unreadable fields and unconfirmed matches.
5. Return a correction proposal in the team's agreed format. Read the accepted result back from the CMMS or
   other receiving system. A generated CSV is a draft, not a completed import.
6. Repeat with a subsequent replacement or source revision. Preserve the earlier equipment identity, decisions
   and evidence; check that the new accepted state and affected records are visible.

Expected work products: an asset/evidence packet, source inventory, unresolved review queue, accepted correction
record and next-revision report. Keep the company system as the authority for accepted equipment information.

The software checks installed manufacturer/model/serial/size discrepancies in supplied records. It does not
inspect the equipment, decide whether a replacement requires MOC or validate a PM strategy. Measure actual
collection, review and correction effort using [the acceptance plan](ACCEPTANCE.md).

For help scoping a unit, [connect with me on LinkedIn and message me there](https://www.linkedin.com/in/steve-vitale/).
