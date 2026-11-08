# Recover or update engineering drawings

Use this when the plant needs a usable drawing baseline, whether the starting point is a scan, an editable
drawing that is out of date, or equipment and field knowledge with no P&ID at all.

## Choose the starting job

Use the [manager scope form](../examples/manager-review/templates/scope.md) to agree the recipient, drawing
backlog, source cut-off, target CAD acceptance and review capacity before quoting a larger reconstruction.

| Starting point | Runnable starting route | What must be supplied |
|---|---|---|
| Existing P&ID image | [Own-drawing tutorial](../examples/own-drawing/README.md) | A supplied/approved extraction, drawing manifest and engineering review. |
| Supported structured P&ID export | [DEXPI tutorial](../examples/from-dexpi-xml/README.md) | Supported exporter/version, source records and review of conversion omissions. |
| Description and process knowledge | [Description tutorial](../examples/from-description/README.md) | Authored model, source-linked interpretation and detailed drawing layout. |
| Editable CAD with retained asset attributes | [Bounded DXF exchange](../examples/cad-handoff/README.md) | The declared profile, stable IDs, reviewed changes and a tested receiving CAD tool/version. |
| Markups sent to a consultant, with a returned drawing | [Requested markup review](PID_MARKUP_REVIEW.md) | Original/markup/returned sources and explicit page-scoped readings of each change; no complete plant graph is required. |

For a plant with no P&IDs, a drawing is reconstructed from records and field observations. Agree what is
as-designed, observed as-installed, and known as-operated. Walk down uncertain connections, valve positions,
instrument functions and off-page continuations. A photograph cannot establish a concealed connection or an
installed control function by itself. Keep those questions open until the appropriate evidence is available.

## Agree what 'CAD preserved' means

A vector picture, an editable DXF and an intelligent Plant 3D/AVEVA/COMOS project are different deliverables.
Before authoring, name the CAD product/version, project database, symbol library, required classes/attributes,
stable IDs, units, layers, connectivity and external references. Keep the original source and list unsupported
information. The public DXF exercise does not supply a proprietary P&ID project database or native DWG support.

DEXPI is an exchange route to qualify, not a promise of universal losslessness. This repo's reader documents
its supported 1.x/Proteus subset. [DEXPI 2.0.1](https://dexpi.org/specifications/) uses the newer DEXPI XML
serialization; do not send that file through the older reader and infer compatibility.

## Review the drawing and its next revision

1. Agree source scope, expected drawing content, drafting conventions, reviewer and acceptance criteria.
2. Retain a draft with source locators, missing information and authored additions clearly identified.
3. Open the result in the intended CAD application. Check editability, object identities, attributes, connections
   and appearance; inspect the native project data where applicable.
4. Make one agreed edit, save, re-export and compare the retained information and explicit losses. Reconcile a
   concurrent manual edit rather than overwriting it.
5. Publish only the reviewed selected version to the context map. Keep the earlier drawing and decisions;
   compare the affected records after another source revision.

Start with controlled exchanges and explicit refreshes. Automatic bidirectional synchronization, field accuracy
and a generic intelligent-CAD round trip are not established capabilities. Compare any speed claim against the
same accepted scope, including fieldwork, drafting, engineering review, corrections and handoff.

For help scoping a drawing package, [connect with me on LinkedIn and message me there](https://www.linkedin.com/in/steve-vitale/).
