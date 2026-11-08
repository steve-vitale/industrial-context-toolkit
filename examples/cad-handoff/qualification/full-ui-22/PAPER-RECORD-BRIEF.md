# The native round trip loses paper information

The [record audit](paper-records-1/REPORT.md) checks both exposed originals, their
matched no-edit native returns, the actual concurrent native returns and both
source-preserving attribute candidates. It retains complete decoded layouts and
raw LAYOUT/VIEWPORT tags, independently checking raw viewport IDs and ownership.

Both original `Qualification sheet` layouts have one display viewport, ID 3, and
no main viewport, ID 1. That missing main is a known dependency in the earlier
[layout preparation study](../layout-preparation-10/README.md). These are known
problem cases, not a representative accuracy sample or evidence that every CAD
application behaves this way on correctly prepared paper layouts.

For **both** the no-edit and concurrent native returns:

- A3 / 420 x 297 settings become A4 / 210 x 297 with changed rotation.
- The original display viewport is absent. A generated ID 1 main viewport is
  present; it does not retain the original ID 3 display record.
- The complete recorded paper layouts are identical between the no-edit and
  concurrent returns. The requested MODEL/SERIAL actions do not explain this
  difference between the original and native return.

There are four observed losses: two cases, each on two native routes. These are
not four independent drawings. `Layout1` originally has no display viewport and
is not counted as losing one. Model plotting records and every other layout
record remain in the JSON even though this short table emphasizes paper sheets.

The original-source value candidate retains the original paper records exactly.
The selected second-revision candidate retains its native source's paper records
exactly, including those earlier losses. A successful attribute-only patch does
not repair its source or retroactively pass the original native round trip.

For an engineer, keep the original sheet and its viewport, paper-size and rotation
requirements in the receiving scope. For a drawing custodian, return the paper
preservation discrepancy for correction or explicitly review a separate proposed
source revision. A manager should keep the receiving decision pending until the
required readable sheets and editable CAD agree under the agreed delivery scope.
Do not close this finding because asset fields match or model screenshots agree.

This locates a failure in the tested native import/save round trip. It does not
identify the precise installed importer/writer function, render either current
paper sheet or explain all 322/321 strict differences. Source originals and strict
comparisons remain unchanged. Reproduce offline, without native CAD or models:

```sh
python examples/cad-handoff/qualification/full-ui-22/native_paper_records.py PRIVATE_NEW_FOLDER/paper-record-audit
```

The producer and inputs are [frozen](PAPER-RECORD-FREEZE-1.json) as a
post-observation diagnosis; no blind validation result is claimed.
