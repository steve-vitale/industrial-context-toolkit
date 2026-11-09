# What the CAD checks establish

An engineer receiving a consultant's revision needs three answers: **were the
requested changes made, what else changed, and what still needs a decision?**
Use the [drawing receiving workflow](DRAWING_HANDOFF.md) for that job. CAD
qualification determines which particular format/editor operations the evidence
supports; it does not grant the organization's drawing acceptance.

## Choose the operation

| Operation | Current evidence and limit | Engineer's next step |
|---|---|---|
| Compare supplied original/instructions/return | The reusable receiving tool retains markup readings, supported DXF field comparisons, other changes, unresolved strict findings and subsequent returns. Image readings must be supplied and checked. | Review the source-linked findings; return unmet requests, escalate unknowns and present the completed review for the authorized decision. |
| Propose single-line equipment-attribute changes | The source-preserving value-span tool changes declared values under an exact source hash and before-value plan. An independent checker reconstructs the original bytes. | Use the [equipment-data route](../examples/cad-handoff/data-review/README.md); verify native readability/editability for the receiving environment. |
| Edit and fully save in the tested native editor | Actual UI edit/save/close/reopen and fresh receiving have been exercised. Preservation **fails**: first multi-asset saves have 322/321 strict differences, and second saves have 453 each, including no-edit baselines. | Keep the actual return and original. Investigate or request correction of the full discrepancy; matching asset fields do not close preservation. |
| Deliver the required paper sheets | The [record audit](../examples/cad-handoff/qualification/full-ui-22/PAPER-RECORD-BRIEF.md) identifies changed paper settings and a missing original display viewport. The [native paper check](../examples/cad-handoff/qualification/full-ui-22/PAPER-RENDER-BRIEF.md) fails readable delivery on these two known problem sources: all twelve case views are blank; the repeated public control shows paper content. | Request usable sheets and an explicitly reviewed source/layout correction. Source-preserving bytes retain any defect already in the source; equal blank images do not pass. |
| Change geometry, piping connectivity or intelligent P&ID data | Attribute-edit preservation does not qualify these operations. Markup review checks supplied readings; graph tools check supplied represented connections. | Define the exact geometry/functional request and obtain source-bound before/after evidence. Do not infer a correct connection from matching labels. |

The native failure is a qualification result, not a requirement to keep changing
the comparison until it passes. Differences remain failures unless explained by
evidence; a new source revision must be separately identified and reviewed.

## Read an actual correction cycle

The [two-asset native-return example](../examples/drawing-handoff/native-second-revision/README.md)
uses the reusable command on actual saved files. The second return implements
both requested MODEL values, but the unrequested SERIAL and preservation findings
remain open. The original drawing and original request stay the comparison basis.
An explicitly selected newer source answers a separate question and cannot erase
the original findings.

For your own prepared records, run from the repository root:

```sh
python scripts/receive_drawings.py --manifest YOUR_JOB.json --out NEW_RECEIVING_FOLDER
python scripts/receive_drawings.py --manifest YOUR_NEXT_JOB.json --previous NEW_RECEIVING_FOLDER --out NEXT_RECEIVING_FOLDER
```

Open `BRIEF.md` for actions and `brief.json` for complete evidence. The retained
portable `job.json` lets another agent reproduce the packet. Suggested roles are
not assigned owners; software findings are not authenticated engineering decisions.

## Qualification boundary and remaining validation

The [unchanged protocol](../examples/cad-handoff/qualification/PROTOCOL.md) covers
text DXF with explicit unique ICT_ID/TAG assets, single-line supported attributes,
ezdxf 1.4.5 and the tested QCAD Professional 3.33.1 Qt5 environment. It requires
exact source/before-value binding, unchanged strict comparisons, independent byte
reconstruction, native stored fields, visual/editability checks, revision/conflict
handling, planted-loss controls and offline reproduction. It does not qualify
DWG, proprietary project databases, every editor or installed plant truth.

The [final method was frozen before ten newly reserved cases](../examples/cad-handoff/qualification/final-validation-23/README.md):
six same-author boundary fixtures and four public files selected from pinned
metadata, with authored identity annotations explicitly identified. All ten
source-preserving candidates pass strict and independent byte checks; all 42
applicable planted losses and 90 refusal controls behave as declared. Actual
native API fields match on all ten, but every one of forty native saves fails
strict preservation. Thirty native model/paper images are retained and inspected;
the five newly authored paper cases display content, with readability/font limits.
Matched native UI baseline/edit/save/reopen completes on the two predetermined
cases: both public returns have 298 strict differences and both three-asset
foreign returns have 334. All planned edits commit. Public fresh receiving and
its frozen model comparisons complete: nine comparisons have zero outside-region
pixels and six exact identities match, with six source/candidate images actually
inspected. The three-asset fresh receiver remains running. This is not whole native CAD qualification or independent
plant validation. No plant review time, customer acceptance or engineering release
has been measured.

Detailed retained runs and failures belong in the [qualification evidence](../examples/cad-handoff/qualification/README.md).
They should support the engineer's receiving decision without becoming a
prerequisite to trying the reusable comparison tools on appropriately prepared records.
