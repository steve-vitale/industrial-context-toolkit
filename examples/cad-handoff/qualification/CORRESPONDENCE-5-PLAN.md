# Audit native-return record correspondence without waiving differences

2026-11-07. Diagnostic only, on exposed retained round-2 evidence. This is not a new preservation method or
fresh validation. The original protocol, strict comparator, patcher, sources, native returns and failed verdicts
stay unchanged. No native save is accepted by this audit. No new model/CAD call or commercial download.

## Question and fixed cohort

How many decoded records can be shown to correspond exactly under an explicit one-to-one renaming of their
own handles and declared pointer fields? Is “only handles changed” supported? Audit all 42 native default/R15
returns of the 21 previously measured cases, with the same source and hash-bound edit plan. Also retain all 21
source-preserving candidates as matched controls. Inputs come from the verified round-2 archive, not a new
selection of convenient working files. This plan precedes implementation and cohort execution.

## Conservative correspondence rule

1. Start from the unchanged `cad_handoff.snapshot` decoded surface, including its already declared metadata
   boundary. Apply only `validate_plan` edits to an expected-before copy, using the same single group-1 check as
   the strict comparator. Do not alter actual source bytes or compare with a different plan.
2. A record needs exactly one own-handle tag: code 105 for DIMSTYLE, code 5 otherwise, equal to its database key
   and a nonzero 1–16 digit hexadecimal string. Malformed/duplicate own handles stay unpaired. Finite JSON
   values and exact types/order are required. Literal serialization is conservative, not a geometry canonicalizer.
3. Replace only that own handle and the values of pointer codes 330–369, 390–399 and 480–481 with structural
   markers in a candidate fingerprint. Preserve record type, every tag code/position and every other literal
   value exactly. In particular, preserve codes 320–329, XDATA 1005, unknown/custom data, geometry, layer/style
   names, and missing versus explicitly present defaults. No numeric tolerance, default expansion, tag sorting,
   nearest-geometry match or iterative refinement of ambiguous bodies.
4. Seed a pair only if the literal-body fingerprint occurs exactly once on each side. Duplicate bodies on
   either side remain ambiguous even if same handles or geometry suggest a match. Do not infer physical identity.
5. Validate all pointer edges at their original ordered positions. The exact string `0` is a null only when
   paired with `0`. Every nonzero reference must target an existing seeded pair with the corresponding target
   handle. Repeatedly remove pairs with invalid/unpaired targets until a fixed point. Identical dangling
   references are unproved, not equivalent. Cycles can survive only when their complete pairs/edges survive.
6. Report seeds and the final closed subset separately. A failed reference dependency must remain inspectable;
   zero final pairs is a valid negative result, not reason to relax the rule. Every unpaired before/after record
   retains a reason. This is decoded tuple/reference correspondence, not whole-drawing, visual, raw-byte or
   engineering equivalence. Application-specific semantics remain unverified even for matching tuples.
7. Retain every original strict difference index. Attach correspondence evidence separately to its before and
   after sides: handle reuse can put two distinct records in one strict row. Never mark a strict row resolved,
   suppress it, change its status or subtract pairs from the strict failure count. Report exact header/version
   changes and unexpected kinds too. No new metadata exclusions.

Pointer-code roles are taken from the primary
[Autodesk DXF group-code reference](https://help.autodesk.com/cloudhelp/2025/ENU/AutoCAD-DXF/files/GUID-3F0380A5-1C15-464D-BC66-2C5F094BCFB9.htm).
Application payloads and literal XDATA handles are deliberately not translated by this diagnostic.

## Controls and freeze order

Commit authored decoded-graph controls and expected pair sets before matcher implementation. These are software
controls, not valid CAD files or independent plant drawings. Include complete renaming, cycles, null/dangling,
wrong reference/owner, geometry/layer/style/foreign/XDATA/unknown-value loss, arbitrary/XDATA handle changes,
duplicate bodies on either side, missing/duplicate own handles, DIMSTYLE code 105, code order/type changes,
planned versus wrong/missing edits, and a reused outer handle. Strict status must stay unchanged in every case.

Freeze matcher, controls, runner and plan hashes before running the whole exposed native cohort. Publish the
first full result, including empty/failed correspondence. A separate checker will inspect every reported pair
directly, including ordered literal values, one-to-one coverage, all pointer targets and every strict side/index;
it will replay the retained cohort offline and reject an omitted report or an invalid pair. No new qualification
claim follows from a passing diagnostic/checker. Full readable native visuals and an actual observed native UI
edit/save/close/reopen remain required by the original protocol.
