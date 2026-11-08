# Minimal main-viewport compatibility revision — development plan

Declare before implementation/execution. This develops a general preparation method on
the five already exposed authored paper-layout failures. It does not rename the original
failures as passes or count any of these sources as fresh validation. Keep the complete
original goal, strict comparator, patcher, byte checker, frozen tests and all earlier evidence.

## Proposed design

Offer a **separate proposed source revision** for text DXF R2000 or later when a paperspace
layout contains display VIEWPORT entities but lacks the special main VIEWPORT with ID 1.
Keep the original unchanged. Insert one newly authored main viewport before that layout's
first existing entity, using the source layout's paper settings. Allocate unique handles and
advance only the existing HEADER $HANDSEED value. Preserve every other original byte,
including all original display viewport records, current-viewport references, model geometry,
attributes, layout/plot settings, encoding, line endings and unfamiliar data. Do not resave
the existing drawing through the library. Serialize only the new entity.

The prepared file is a deliberate compatibility revision, **not** an attribute-only
preservation candidate. It needs explicit review before being adopted as a new source;
the tool creates no company authority or accepted revision. Attribute edits on it use the
existing frozen patcher, a separately rebound source hash and the unchanged strict/byte checks.
Do not discard native full-save changes or import them into this proposal.

The rule must depend on DXF structure, not a case name. Empty layouts and layouts with an
existing unambiguous main viewport are untouched. Refuse binary/malformed DXF, R12/R13/R14,
duplicate handles/main viewports, nonfinite/invalid paper settings, ambiguous record ownership,
missing/ambiguous HANDSEED, newline-bearing layout names and output collisions. No automatic
source overwrite. Any additional required mutation or refusal is retained before changing
the declared method. Existing ID-1-first ordering is observed, not silently repaired.

Primary references: Autodesk's [VIEWPORT group codes](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-DXF/files/GUID-2602B0FB-02E4-4B9A-B03C-B1D904753D34.htm),
ezdxf's [layout internals](https://ezdxf.readthedocs.io/en/stable/dxfinternals/layout_management.html)
and [v1.4.5 implementation](https://github.com/mozman/ezdxf/blob/v1.4.5/src/ezdxf/layouts/layout.py).
Active paperspace entities live in ENTITIES; inactive ones live in their BLOCK. The new
record must go into the correct existing entity space. `add_new_main_viewport` moves its
new entity first; the earlier library diagnostic is not proof that arbitrary append order works.

## Fixed exposed cohort and matched routes

Use all five `validation-2/authored/validation-{braces,cp1251,foreign,long,unicode}.dxf`
sources with their existing plans. Also inspect every other case in the existing 21-case
cohort: report no-op/refusal/preparation, with no case-name exceptions. In particular retain
the working public `text_in_viewports` layout as a positive no-change control and R12 as
an explicit out-of-preparation-profile refusal. No native execution on new/reserved data yet.

For each of the five failures, produce and retain the same five routes:

1. Exact original.
2. Ordinary library save.
3. Library main-viewport creation, restoring the original current-viewport reference as
   in the earlier exposed control; retain every unrelated library serialization difference.
4. Minimal raw preparation.
5. Existing planned attribute edits on route 4, rebound to its exact source hash.

## Acceptance and independently observable checks

- Pin exact original inputs/plans and every method before executing the native comparison.
  Retain all attempted routes/results, errors and logs, not only successful cases.
- A separate verifier must discover allowed new records from source/output DXF, check their
  IDs/owner/geometry/handle allocation/order, remove them, restore the one HANDSEED value and
  recover the exact original bytes **without consuming the producer's span receipt**.
- Original-to-prepared strict differences remain a full nonzero comparison, described as
  deliberate revision. Prepared-to-attribute-candidate comparison must be strict zero and
  the original independent value reconstruction must report zero unplanned byte changes.
- In the same pinned Linux QCAD 3.33.1 Qt5 receiver, import all five routes for all five cases.
  Retain native layout/entity bounds and all model attribute values. Expect original/library
  layout failures to stay visible; compare minimal preparation with the library-main baseline
  for the original display viewport's native bounds and actual paper rendering.
- Native paper render settings/frame are identical within each five-route case, derived
  from original display viewport bounds with a declared margin. Use the explicit local
  Standard-to-DejaVu Sans display profile from run 9, retaining trial marks. No font fidelity,
  new actual UI edit/save or engineering acceptance is inferred from a renderer/API run.
- Inspect every native paper image. Preserve intended source viewport clipping/overlap as
  source behavior; do not call a nonblank image complete label acceptance. Existing native
  asset-view evidence and later fresh validation remain separate.
- Planted controls must reject wrong/missing main-viewport fields/owner/order, changed existing
  geometry/display viewport/foreign bytes, stale source identity and omitted route coverage.
  An already prepared file must be an exact no-op. Frozen originals cannot change.
- Add meaningful offline replay/tests and run required repository/CI checks. This development
  cannot finish the goal: freeze the complete chosen workflow and use new reserved public or
  independently authored drawings with matched baselines before a fresh qualification claim.
