# The 62 pixels came from native cubic strokes

The [retained diagnosis](SUMMARY.json) explains the old long-label GUI failure exactly. QCAD renders this
Standard CAD-font text as separate lines and cubic `strokePath` calls. Replaying the actual primitives and
their actual painter state reproduces all **1,978** changed canvas pixels, including the **62** above the
MODEL geometric bounds. Removing the curve calls removes all 62; curve-only replay reproduces every one
of their original source/candidate colors. No drawing byte, geometric acceptance region or strict comparator
was changed. The original failed acceptance result remains a failed historical result.

This is exposed diagnosis of one authored source/candidate, not whole CAD qualification or a new accuracy
benchmark. Native full-save preservation, unresolved record payloads, complete readable receiving and fresh
native UI/editability/revision qualification remain open. No engineering/company acceptance is established.

## Evidence and causal controls

The [plan](PLAN.md) was committed at `f3cd1ca` before execution. The observation method was expanded before
each new run: [line/fill capture](PAINT-EXTENSION.md), [separate cubic strokes](CURVE-EXTENSION.md) and
[curve-removal controls](ABLATION.md). Earlier [isolated joined-path profiles](../root-cause-12/README.md)
had not reproduced the GUI. The pinned public [paintDrawable implementation](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/gui/RGraphicsViewImage.cpp)
supplied a method lead: its non-draft branch splits line segments and cubic strokes. The
[worker implementation](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/gui/RGraphicsViewWorkerPainter.cpp)
forwards them to distinct Qt methods. Actual native observation and counterfactual replays establish the
measured cause; public source alone is not proof of the proprietary package's build chain.

The ordinary GUI uses the original exact source/candidate, frozen native image and a verified selected
settings profile. Its 1533 x 1032 canvas, camera and both rendered canvases equal the historical captures
literally. Two successful instrumented GUI runs also equal the ordinary canvases literally. The observer
forwards the original Qt call with the original arguments; it does not edit/import/export a replacement
CAD model or remove trial marks. Full desktop frames, stabilization frames, native receipts, inputs,
settings hashes, terminal states and logs are retained. Native drawing bytes remain unchanged.

The complete trace has **1,193 source / 4,909 candidate yellow-stroke calls** at the target camera, across
four complete worker cycles per role. Those include other unchanged labels. Each primitive retains pen,
brush, transform, clipping, device, composition and render hints. A separate observer on the standalone
replayer finds **zero state/primitive discrepancies**. The comparison scores the entire canvas delta, and
also checks both colors at every original outside pixel; it does not score an expanded mask.

| Retained control | Whole-canvas delta mismatches | Original 62 outside colors |
|---|---:|---:|
| Incomplete line-only trace/replay | 857 | 62 wrong |
| Complete actual line + cubic-stroke replay | 0 | 0 wrong |
| Remove all cubic calls | 857 | All 62 removed |
| Keep only cubic calls | 1,367 | 0 wrong |

The curve-only run reproduces 1,285 changed pixels overall. It is a counterfactual, not the accepted complete
image. Stroked ink and a geometric entity bounding box are different quantities. This diagnosis explains
why the earlier geometric-bound check failed; it does not retroactively waive it or claim every changed
pixel in another drawing is legitimate.

## Failures and provenance limits retained

- First observer compilation failed because unqualified `brush` resolved to a QPainter member. Its source
  and compiler error remain. The corrected successor uses explicit global lookup.
- The first traced launch exited 127 before QCAD because its shell could not resolve Qt. The next exited
  127 on a Qt JSON initializer-list symbol absent from the package runtime. Separate successors correct
  library resolution and use a small standard C++ JSON writer. The frozen native image remains unchanged.
- A separate known line/path/fill/stroke fixture has identical ordinary/observed pixels in actual Qt 5.14.2.
  This checks the used observation route, not all ABI compatibility between the builder's Qt 5.15 headers
  and every runtime API. Source, exact build commands/dependencies and local binary hashes remain.
- The first successful GUI trace omitted `strokePath`; both failed replays remain. Restricting dash setters
  did not change its 857 mismatches. Re-observation showed its captured line state was already correct:
  missing cubic calls, rather than a pen-width guess, explained its incompleteness.
- The historical `/work/qcad-config` still cannot be recovered; the failed recovery remains. New runs
  self-report the actual default settings filename and bind its startup hash. The default launcher does
  not emit the old explicit `absConfigFile` stderr line; this is a documented deviation from that part of
  the initial plan. Literal old/new canvas equality is measured separately and is not a claim to recover
  all historical settings. Native property collections are compared by unique tag, retaining every field;
  their process-dependent array order is not a change to strict CAD comparison.

## Check without native CAD

From the repository root, with the documented Python requirements installed:

```sh
python examples/cad-handoff/qualification/check_scene13.py
python scripts/test_cad_linux_evidence.py
```

The receiver safely unpacks the [inventory](INVENTORY.json), reassembles exact hashed trace parts, checks
input/plan reconstruction and native profile/state coverage, independently checks replay state/primitive
identity, regenerates numeric replay streams and re-scores every saved image/control. It does **not** run
the native renderer. All original CAD comparison/patch methods and historical tests remain unchanged.
Publisher software, fonts, settings contents and author helper binaries are excluded. Traces are split
into bounded parts so the existing safe archive receiver's 4 MiB/member limit remains unchanged.
