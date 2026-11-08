# Test which dimensional store controls saving

Declared after the 26-job observation, before implementing/executing this control.
The original exact source bytes and their errors/strict reports remain unchanged.
All six sources are exposed development; no independent/held-out claim follows.

For each of the same six inputs, import explicitly with OpenDesign and export
with each writer (original source version for OpenDesign, R15 for dxflib). Cross
four predeclared operations with both writers: 48 jobs, without selection by result.

1. Unchanged.
2. Set only ordinary known variable DIMASZ to 9.875 using setKnownVariable.
3. Set only the direct dimension-style DIMASZ variant to 9.875 with its public
   setDouble method. Do not apply a generic operation that could synchronize other
   properties before the boundary is observed. This API experiment is not a UI edit.
4. Set only the unrelated ordinary USERI5 value to1234, leaving dimensional stores.

Freeze methods, sources, manifest and settings before executing. Capture the full
existing public inventory immediately before and after each operation. Verify
that the intended recorded cell is the only change (for a known-variable update,
its presence flag may become true). Preserve every other recorded value, including
the other dimensional store. If an operation has other effects, retain/refuse the
single-cell interpretation; do not normalize those changes away.

The directional hypothesis predicts the style-only value will be written by both
writers, whereas a known-only value will be overwritten by the original style.
The unrelated USERI5 should survive without changing dimensional behavior. Evaluate
that pattern from actual raw DIMASZ/USERI5 header tags, native after-export values,
reopened states and a fresh process, including every failure and strict refusal.
Do not infer full payload or geometry preservation from the single-cell observation.

No source repair, exclusion or change to the original comparator is made. Run and
receive all original strict comparisons (no planned source edits are declared to
the strict comparator for these diagnostic native returns). A successful causal
pattern remains different from CAD qualification; all original gates stay open.
