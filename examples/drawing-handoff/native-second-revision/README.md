# Receive actual native corrections without losing the original request

These two-asset drawings and engineering choices are authored fixtures. The
Property Editor edits, saved returns and reopened-field checks are actual native
executions, retained in [complete packets](../../cad-handoff/qualification/full-ui-22/SECOND-RETAINED-1.json).
This is not plant data, an image-reading trial or engineering acceptance.

Use the same reusable command for both consultant returns:

```sh
python scripts/receive_drawings.py --manifest examples/drawing-handoff/native-second-revision/initial-job.json --out YOUR_NEW_FOLDER/first
python scripts/receive_drawings.py --manifest examples/drawing-handoff/native-second-revision/resubmission-job.json --previous YOUR_NEW_FOLDER/first --out YOUR_NEW_FOLDER/next
python scripts/receive_drawings.py --manifest examples/drawing-handoff/native-second-revision/selected-scope-job.json --out YOUR_NEW_FOLDER/selected-scope
```

| Receiving question | Initial actual return | Actual second return |
|---|---|---|
| Asset 1 MODEL matches the original request? | No: `OTHER-CHOICE` | Supported by the returned field values |
| Asset 2 MODEL matches? | Supported | Supported |
| Unrequested asset 2 SERIAL? | `FIELD-OBSERVED` needs disposition | Still unrequested against the original request |
| Original-source strict drawing differences? | CP1251 322; braces 321 | CP1251 321; braces 320; still unresolved |
| Second-native-source, one-value-plan preservation? | Not this comparison | 453 differences on each native return; no-edit saves also have 453 |
| Authorized receiving decision? | Pending | Pending |

The [original-scope resubmission brief](resubmission/BRIEF.md) compares both returns
against the **same original drawing and original plan**. Its basis-change list is
empty: the consultant return changed, not the instructions. The corrected MODEL
does not close the SERIAL or preservation findings. Each of its eight review
items retains the real before/returned fields or complete strict queue.

The [selected-scope brief](selected-scope/BRIEF.md) answers a different, explicitly
identified question: did one MODEL edit preserve the actual concurrent return?
It shows the correct MODEL and 453 remaining differences. This new source/plan
does not erase the original source, original request or SERIAL finding. Drawing-
record difference counts from these baselines must not be added or treated as
counts of changed assets.

For the engineer, resolve the SERIAL's source and intended scope, and review the
complete preservation discrepancy. For the manager, arrange correction and route
the authorized receiving decision. The [paper-record audit](../../cad-handoff/qualification/full-ui-22/PAPER-RECORD-BRIEF.md)
identifies changed paper settings and a lost display viewport in the first native
round trip; matching MODELs and model views do not restore the paper sheet.

Each packet's portable `job.json` reruns from its retained sources. The latest
packet also carries the full earlier packet and source checks in `revision.json`.
[Provenance](PROVENANCE.json) binds the supplied second-return DXFs to their exact
members in the complete native archives. No native application or model is called
by these receiving commands; install only the normal pinned CAD requirements.
