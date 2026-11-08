# Trace the actual GUI paint path before attributing the 62 pixels

Declared before new native execution on 2026-11-07. Previous goal turn made progress: PR31 merged causal
save controls and retained the exact unresolved GUI residual. Main baseline is da61cd023c2bb8da0220cfd0b351edfdaede5a8b.
This is exposed development on the existing font-9 long source/candidate, not fresh qualification.

The old GUI delta has 1,978 changed canvas pixels, 62 outside the original floor/ceil MODEL bounds at row537.
Sixteen nonempty isolated glyph width/AA/cap profiles failed exact reproduction. Do not widen the allowed
region, change the strict comparison, overwrite original frames or assume those pixels are harmless.

## Method and controls

1. Pin exact source/candidate, old reference captures/camera, native image and the settings file actually
   selected. Native RSettings, stderr and file hashes must agree. A copied file alone is insufficient.
2. Use the same native QCAD 3.33.1 Qt5 GUI and canvas geometry, no CAD edit/save. First run an ordinary
   pointer-neutral source/candidate capture. Preserve all startup/capture failures and actual terminal state.
3. Public RGraphicsSceneQt marks getDrawables/List nonscriptable. Develop a separate observation helper
   that interposes Qt's native QPainter drawPath calls and forwards each original call unchanged. Capture
   actual paths, pen/brush, transform, device and applicable clipping. Pin source, build/runtime identity and
   helper binary locally; do not distribute proprietary CAD/software, fonts or native settings contents.
4. Run a separate identically configured GUI capture with the observer. Require literal canvas equality
   between ordinary and observed captures before using the trace causally. Exit0 or trace presence is not
   observational equivalence. Do not restart any uncertain/live process after an observation timeout.
5. Re-render the actual captured native path and observed state separately. Compare every delta pixel and
   the original 62 pixels, not just a selected crop or expanded rectangle. Retain failed trace/replay designs.
   If the ordinary run does not reproduce the original GUI delta, report that and distinguish historical
   from newly observed state; do not substitute the new result as proof about the old pixels.

The helper observes public/local software for diagnosis. It does not modify source drawings, remove trial
marks, alter licensing/clock or turn diagnostic images into an accepted engineering drawing. Renderer
interposition does not itself establish the package build chain or semantic CAD equivalence.

## Receiving and next qualification

Retain commands, raw logs and exact native captures, independently re-score old/new comparisons and verify
trace completeness/forwarding controls. Register the result and any unknowns in the ledger/journal and CI.
Only after the complete receiving method is fixed/frozen can new reserved-source/native UI/revision checks
support fresh qualification. Native full-save failures and engineering/company acceptance remain separate.
