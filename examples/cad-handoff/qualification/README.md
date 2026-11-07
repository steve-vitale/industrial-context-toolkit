# DXF preservation evidence and unfinished qualification

For a supplied, explicitly identified DXF asset, `scripts/cad_value_patch.py` proposes single-line attribute
changes while preserving all other source bytes. In the frozen software cohort, **all 21 candidates have zero
unexpected strict differences and reproduce exactly from source plus plan**. This is a useful bounded handoff
route. Full native CAD qualification is **not established**: native full saves still differ, some visual checks
remain unreadable, and the interactive edit/save/close/reopen gate is unproved.

Use the [handoff guide](../README.md) for your own inputs. It explains the supported record-framed DXF profile,
explicit `ICT_ID`/`TAG`, hash-bound before/after plan, permitted fields and refusal conditions. This does not
infer installed identity, pipe connectivity or a proprietary intelligent-P&ID database. Native returns with
other edits require review; the value patcher does not silently discard or merge those edits.

## Reproduce the evidence offline

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
| Actual native UI | **Unproved.** Accessibility text shows startup/trial-expiry dialogs; two fresh window-capture attempts time out. No successful drawing edit/save/close/reopen was observed. See [the observation](UI-OBSERVATION-20261107.json). |
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

Next acceptance work is readable complete layout/label review and a recorded actual native UI edit/save/reopen
with retained return. If that reveals a preservation-method defect, retain the failure and freeze a new method
and fresh cases before claiming a qualification gain. More files alone cannot fill those gates.
