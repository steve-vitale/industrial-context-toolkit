# Minimal paper-layout compatibility proposals

This is an exposed development experiment for a **separate proposed source revision**.
It addresses the known missing-main-viewport dependency without resaving existing CAD records.
It does not turn the original five failed drawings into preservation passes or establish
fresh qualification, a general CAD repair service, intended typography or company acceptance.

The [plan](../LAYOUT-PREPARATION-10-PLAN.md) preceded implementation at `fecf5db`. The corrected
producer, separate verifier, 25 native inputs and native observer were [frozen](FREEZE.json)
at `4ae6607`. Two earlier wrapper failures and a native setup mistake remain retained in
their notes, Git history and evidence archive. All sources were already exposed; none is
a new holdout. No comparison exclusion or tolerance was added.

## The design

For the existing ICT_ID/TAG handoff profile, inspect text DXF R2000 or later. If a paper
layout has display viewports but no special main viewport with ID 1, propose a new main
viewport before its first existing entity, with dimensions derived from the existing
paper settings. Allocate a unique handle and advance the HEADER HANDSEED. Preserve all
other original bytes, including every original display viewport/current reference, paper
setting, geometry, model attribute, unfamiliar data value, encoding and line ending.

This method serializes only the new record. It never passes the existing drawing through
a library save. Empty layouts and existing unambiguous main viewports are exact no-ops.
Binary/malformed/ambiguous inputs, unsupported older DXF versions, duplicate handles/main
viewports, invalid paper settings and output collisions refuse. It does not reorder an
existing main viewport. The normal packet comparator requires the existing asset profile;
this prototype does not automatically profile unlabelled public CAD blocks.

The packet retains `original.dxf`, `prepared.dxf`, a revision receipt and the complete
nonzero original-to-prepared strict comparison. The new main is a deliberate source change,
not an attribute-only edit. A reviewer must choose whether to adopt that proposal as a new
source. The toolkit grants no authenticated company authority or engineering release.

A separate [verifier](../verify_layout10.py) discovers the new record from source/output,
checks ownership, fields, dimensions, unique handle allocation and insertion order, strips
it, restores the original HANDSEED body and reconstructs the exact original. It consumes
no producer edit offsets/receipt. Attribute edits on the proposed revision then use the
unchanged frozen patcher, a plan bound to the new source hash and the original strict/raw
checks. Native full-save changes are never silently imported or discarded.

These are development commands, requiring the normal ezdxf dependency:

```sh
python examples/cad-handoff/qualification/prepare_layout10.py source.dxf --out PRIVATE_NEW_FOLDER
python examples/cad-handoff/qualification/verify_layout10.py source.dxf PRIVATE_NEW_FOLDER/prepared.dxf --source-sha256 ORIGINAL_SHA256
```

Use an unused private output directory for your records. These commands propose/check bytes;
they do not prove that your source will import correctly in a particular recipient's CAD.
The [agent/local-form equipment-data route](../../data-review/README.md) remains separate
and does not require routine native CAD UI operation.

## Matched development comparison

The structural rule was applied to every existing case: five minimal proposals, 14 exact
no-ops and two explicit R12 refusals. R12 metadata exchange is a separate existing route;
this preparation method does not rewrite/upgrade it. The working public-adapted paper
example remains an exact no-op. There are no case-name exceptions in the producer.

For each of the five known authored failures, retain all five routes: exact original,
ordinary library save, library main-viewport creation with the old current reference
restored, minimal raw preparation, and the existing planned MODEL edits on that preparation.
The [input manifest](INPUTS.json) pins all 25 native inputs. Every minimally prepared file
has one added main viewport; its nonzero strict difference is retained. Prepared-to-candidate
edits must have zero unexpected strict differences and zero unplanned bytes under the
separate original source/plan reconstruction.

Native observation uses the pinned Linux QCAD Professional trial 3.33.1 Qt5 image, with
the explicit Standard-to-DejaVu Sans display profile from run 9. Read-only native import
retains the paper entities/bounds and all model attributes. Serial native bitmap exports
use the same original-derived frame within each case, 2400x1600, white background and
monochrome. No mark, license, clock, font binary or image pixel is changed. These are native
API/render observations; they add no actual UI edit/save or plant trial.

Inspect the [summary](summary.json), [all pixel comparisons](pixel-comparisons.json) and
[visual review](VISUAL-REVIEW.json) for the measured outcomes and limits. Nonblank paper
content alone does not establish complete label readability: retained trial marks overlap
some content, and the original display viewport clips some source labels. Complete native
asset views and later fresh validation remain separate obligations. Original typography
is not preserved by the display-font mapping.

## Retained failures and setup

The [first attempt](FIRST-ATTEMPT.json), source commit `7b268e6`, called the unchanged strict
comparator with an incomplete edit-plan object. The wrapper then looked for an unpublished
proposal and failed. The second attempt, retained at `2a38525`, completed the 21-case byte
checks but used an unsupported Vec3 slice while deriving render bounds. Corrected development
uses a new output directory; neither failure ran CAD or changed an original.

The [first native batch](NATIVE-SETUP-FAILURE.md) started after a failed configuration copy
because the shell continued. It is excluded from the declared-profile conclusion, despite
being allowed to finish and retaining its results. The [setup correction](NATIVE-SETUP-CORRECTION.json),
commit `0202240`, makes the normal-user driver create the destination, verify the local
configuration hash, copy it and verify the installed bytes **before any CAD process starts**.
A failure stops the driver. The second batch uses a fresh container after confirmed normal
exit of the first. The algorithm, source cohort and native input pins do not change.

Only digest receipts are published for native configuration. The settings themselves,
fonts and publisher executables stay local. `HOST-NOTES.json` explicitly transcribes host
tool observations; native stdout/stderr, exact route DXFs, images, per-command records and
terminal container state are retained separately. A quiet process or observation timeout
is never treated as terminal or a reason to restart.

## Offline replay

```sh
python examples/cad-handoff/qualification/check_layout10.py
python -m unittest discover -s scripts -p test_cad_linux_evidence.py
```

No account, Docker, native executable, network or desktop is needed. The bounded archive
reader verifies every retained member. The replay rebuilds the proposals/candidates,
re-scores all strict source-revision comparisons, verifies native fields/viewport bounds,
and decodes/recompares every paper image. Seventeen controls reject wrong/missing main
fields/owner/order, changed existing geometry/display/foreign/XDATA bytes, stale identity,
unsupported inputs and collision. Additional receiving checks reject omitted native routes
and altered native field observations. An already prepared source is an exact no-op.

The [inventory](INVENTORY.json) pins both unsuccessful development/native batches and the
verified native batch. Offline replay verifies these saved observations; it does not rerun
the native engine or create independent human approval. The full original goal remains
active: complete readable receiving checks, separately frozen fresh public/independently
authored validation and the original native full-save/revision gates must still be audited.
Every original failure and frozen method remains available.
