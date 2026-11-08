# DXF preservation evidence and unfinished qualification

For a supplied, explicitly identified DXF asset, `scripts/cad_value_patch.py` proposes single-line attribute
changes while preserving all other source bytes. In the frozen software cohort, **all 21 candidates have zero
unexpected strict differences and reproduce exactly from source plus plan**. This is a useful bounded handoff
route. Full native CAD qualification is **not established**: native full saves still differ and complete readable
visual acceptance remains open. A later [Linux native UI experiment](linux-native-7/README.md) observes an actual
edit/save/close/reopen on the exposed valve, with a retained returned DXF and fresh-process reopen.

Use the [handoff guide](../README.md) for your own inputs. It explains the supported record-framed DXF profile,
explicit `ICT_ID`/`TAG`, hash-bound before/after plan, permitted fields and refusal conditions. This does not
infer installed identity, pipe connectivity or a proprietary intelligent-P&ID database. Native returns with
other edits require review; the value patcher does not silently discard or merge those edits.

The later [full-application initialization comparison](open-initialization-18/README.md) rejects ordinary
MDI opening and print-getter calls as a repair for the diagnosed plot-storage gap. It retains 84 development
jobs, complete public-inventory comparisons and actual cleanup failures. It does not close any native-save,
reserved edit/save/reopen or engineering acceptance gate.

The [matched native UI cohort](native-ui-pairs-19/README.md) now retains 18 completed exposed-development
processes in seven portable packets with offline replay. All twelve native full saves still fail strict
preservation (298–377 differences); matched pairs retain 50–53. The receiver preserves twelve recording
metadata failures and exact-camera failures on two cases. Nine of 54 pixel comparisons are diagnostic only;
zero outside-region changes does not waive the camera gate. Original failures/recovery remain separate.
New reserved validation and whole qualification remain unfinished.

The separate [camera repeat](camera-repeat-20/README.md) now has one fully received
original air/water run: both camera recipes repeat exactly, with 18 pixel
comparisons and zero outside-region changes. It reproduces neither prior camera
failure; the other five cases are unfinished. The repeat edits/saves no CAD file
and changes no original qualification verdict.

## Reproduce the evidence offline

**A different operation is available without a CAD UI:** the [equipment-data sidecar route](../data-review/README.md)
keeps the DXF intact, reviews existing attributes in a local form or agent-readable catalog and applies a returned
JSON proposal through the unchanged byte-preserving writer. Its [separate six-case qualification](exchange-6/README.md)
includes actual browser downloads and revision checks. It does not retroactively pass the original native UI,
rendering or full-save requirements. Those requirements matter when promising behavior in the receiving CAD editor.

From the repository root, with Python 3.10+ and the pinned `ezdxf==1.4.5` in `requirements.txt`:

```sh
python examples/cad-handoff/qualification/recheck.py --out out/cad-qualification-local
python examples/cad-handoff/qualification/check_controls.py
python scripts/test_cad_handoff.py
```

Choose a new `--out` directory each time. No network, model, commercial CAD download or native application is
called. The replay verifies the frozen methods and inputs, checks/extracts the exact retained archive, rebuilds
21 candidates beside matched library-save baselines, re-scores 63 saved native-file comparisons, checks 45
retained fresh-process stored-value readbacks, and runs three context revision commands. A replay pass means
these software results reproduce; it does not rerun the native engine or establish visual/UI acceptance.
The negative controls require altered/omitted evidence and changed native stored values to fail.

The [round-2 report](round-2/README.md), [replay receipt](round-2/offline-recheck.json) and
[raw-file inventory](round-2/INVENTORY.json) retain successes and failures. The 11.4 MB ZIP contains 1,189 exact
records (76.1 MB uncompressed), including original native DXF returns, commands, logs, render images and failed
diagnostics. It contains no native executable, font or native application settings. Windows paths in original
receipts describe the actual runs; the offline replay maps them to the retained files without running drivers.

## What passed, and what did not

| Gate | Current evidence and limit |
|---|---|
| Source binding and exact preservation | 21/21 candidates: unchanged strict comparison passes and separate offset-free source/plan byte reconstruction passes. Nine exposed development/regression cases; six replacement authored and six public-adapted cases. Same-author software checks, not independent human review. |
| Matched library save | The same 21 inputs/plans were run. R12 and nested-dimension differences remain visible; every library save fails exact raw-byte preservation, including those that pass decoded strict comparison. |
| Native engine | QCAD Professional trial 3.33.1 Qt5 read all 21 candidates; stored planned and foreign attributes match. All 42 native full-save returns (default and R15) retain strict differences. Original valve baselines of 335/344 differences are not waived. |
| Fresh process | 45 retained new-process readbacks match stored attributes: nine development candidates and 36 replacement candidate/default/R15 returns. This is API readback, not a UI edit. |
| Native rendering | 82 images cover 12 full-model, 23 asset-label and six paper-layout pairs. All command exits are zero and inputs remain unchanged. Review of all seven contact sheets finds watermark overlap and five blank drawing-layout views; the sixth paper pair contains viewports. All six paper pairs have identical RGB pixels. No complete readable visual pass or original-font fidelity is claimed. |
| Revision/conflicts | Two stale proposals refuse without output; one concurrent MODEL disagreement remains explicit; an explicit second plan produces an exact candidate and sourced draft context. Three graph/revision commands pass. Fictional branches, not a human edit or authenticated company decision. |
| Actual native UI | Windows capture/interaction remains unproved ([original observation](UI-OBSERVATION-20261107.json)). A later [Linux experiment](linux-native-7/README.md) observes one exposed valve's three UI edits, native Save As, document close/reopen and fresh-process reopen; its returned file still fails with 287 strict differences. No fresh native holdout or whole-workflow qualification. |
| Engineering/plant acceptance | Not established. No plant data, operator review, timing, live platform import or company authority is inferred. |

The later [layout diagnosis](diagnosis-4/README.md) confirms that the five blank authored layouts contain
viewports in the sources, but the native importer exposes empty layout blocks and native returns lose the original
viewport settings. Six predeclared working-copy controls isolate a main-viewport compatibility dependency on one
exposed source. Adding one makes the drawing visible; that deliberate source revision is not a byte-preserving
candidate or a new qualification pass. Translated long-label renders still suffer trial-mark overlap. A fresh
UI restart still fails capture/indexed input. All original failures and frozen sources/methods remain unchanged.

The later [record-correspondence audit](correspondence-5/README.md) retains every strict index while testing
exact ordered decoded bodies and complete pointer correspondence. It finds 583 corresponding record occurrences
across the 42 native returns, chiefly limited table records in the original example; all 16,209 strict rows stay
visible. Even exact source-preserving controls leave ambiguous records unpaired, so unpaired does not mean lost.
This exposed-data diagnostic does not establish whole-drawing equivalence or change any qualification verdict.

## How the method was kept separate from validation

The [original protocol](PROTOCOL.md) defines acceptance before development. [Round 1](round-1/README.md) keeps
the original R12 inspection failure, literal-brace harness failure, public-input refusals/parser failure and
unreadable renders. Those cases became exposed development data. Their exact methods remain in
`history/method-1/`; the strict comparator, value patcher and byte checker remain unchanged.

Six replacement authored cases and six public originals were committed at `d79e437` before correcting the R12
inspection projection. [Method 2](METHOD-FREEZE-2.json) was committed at `8fdc775` before replacement execution.
All six unmodified public originals refuse the asset profile. The frozen [adaptation plan](ROUND-2-PLAN.md)
adds explicitly authored test identities/annotations and an unused field without overwriting existing values.
Its exact derived sources were bound by [a separate receipt](PUBLIC-ADAPTATION-2.json), committed at `07fd3d3`
before candidate runs. The six originals are from one ezdxf source family, not six independent plants. Adaptation
is a library save; preservation is measured from each derived source, not from the untouched public original.

Display diagnosis used already exposed results. The first 60 native images had clipped/low-contrast labels and
missing Cyrillic glyphs. A recorded `txt -> Arial` trial had no pixel effect; native font probes found `Standard`.
The later frozen display recipe uses native union bounds, monochrome and process-local `Standard -> Arial`.
It makes the inspected Cyrillic labels readable without changing DXF input bytes. It does not preserve original
typography. Trial marks were retained. [The visual review](round-2/VISUAL-REVIEW.json) names observations and limits;
these post-exposure diagnostics are not a new blinded preservation trial.

The later [Linux native experiment](linux-native-7/README.md) fills the single-valve UI observation gap on a separate
receiver: three actual native property edits, default Save As, document close/reopen and fresh-process reopen.
Its full save still fails with 287 strict differences. The exact-span candidate opens with readable valve labels;
425 native canvas pixels differ in the three changed label area. Fifty-four model/paper views cover the existing
21 exposed sources/candidates; five authored paper pairs remain blank and a same-original repeat control reproduces
the public paper view's two different pixel states. No whole-cohort readable/font pass or fresh native holdout.
The earlier Windows/native-engine/rendering failures remain independent of the Linux observations.

The subsequent [pointer-state controls](receiver-state-8/README.md) explain the 13,556-pixel public-paper difference:
deliberate hover reproduces the old states exactly; nine pointer-neutral source/repeat/candidate views have zero
canvas differences. This is development on one exposed drawing, not fresh validation or a whole-layout readable pass.

The subsequent [font/frame controls](font-views-9/README.md) test a process-local Standard-to-DejaVu Sans
display profile on three exposed authored pairs. Native bounds measured after mapping provide common complete
asset frames. All 36 accepted native views and 144 unique native field values are retained; mapped Cyrillic,
mixed Unicode and long target labels are readable in the inspected asset views. All nine mapped pairs have zero
changed canvas pixels outside exact planned MODEL bounds. The default font lacks 13 required Cyrillic characters;
its long overview still has 62 pixels outside the native label bounds. Existing linework/label overlaps remain.
This is display development, not original typography fidelity or fresh qualification. Two failed/interrupted
batches remain alongside the completed matched batches; no strict/raw-byte rule was relaxed.

The [minimal layout proposal](layout-preparation-10/README.md) is a new structure-based development design:
serialize only a missing main viewport and HANDSEED, preserving every other original byte. Across all 21 exposed
cases it proposes five revisions, leaves 14 exact no-ops and refuses two R12 inputs. Twenty-five matched native
paper views retain 330 exact field observations; each minimally prepared image matches its library add-main
baseline exactly. Original/library-only layouts stay blank. This requires explicit adoption of a new source;
it never turns the original failed file into a preservation pass. Trial marks and original top-edge label clipping
remain. Seventeen input/semantic controls and three receiving controls reject the declared corruptions.

Next acceptance work remains complete readable layout/label/font review and fresh native validation with a
separately frozen observation method, alongside the original native full-save/editability/revision gates.
Retain every original full-save/layout/font failure before claiming a qualification gain.

The subsequent [six-source public transfer](public-validation-11/README.md) adds six exact
candidates and 144 native/fresh-process field observations, while all twelve new native
full saves still fail strict preservation. It also discovers the bitmap window contract
error: min/max coordinates were passed to an X/Y/width/height option. All original images
remain, and a corrected receiving batch uses unchanged canonical frames. The earlier
layout-10 frame claim is narrowed explicitly. New source structure does not by itself
establish readable layouts, unknown-payload transfer, native UI acceptance or qualification.

The [root-cause investigation](root-cause-12/README.md) separates no-edit saving from attribute operations:
144 matched native exports confirm an unintended current-layer change in the historical API harness;
an explicit preserve-attributes call fixes that defect on the six exposed cases. Full saves still rebuild
records without an edit, second saves remain unstable, and R15 retains embedded timestamp differences.
The before-load constructor hypothesis is rejected. The 62-pixel GUI residual is localized but not exactly
reproduced by isolated glyph renders; it remains a failure. Every original comparison and acceptance gate stays.
