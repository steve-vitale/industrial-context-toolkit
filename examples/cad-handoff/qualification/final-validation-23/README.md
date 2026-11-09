# Final frozen drawing-handoff validation

For an engineer's own consultant return, start with the reusable
[receiving workflow](../../../../docs/DRAWING_HANDOFF.md). This directory is its
CAD validation evidence, not a prerequisite to using it.

The [plan](PLAN.md), [method freeze](FREEZE.json) and [input admission](INPUTS.json)
precede evaluation. The frozen method was developed on two already exposed
inputs. Six newly generated same-author boundary cases and four public files
selected from pinned metadata were then evaluated without changing that method.
The public sources cover LibreCAD air/water, mechanical kinematics and power,
and an ezdxf hatch example. Exact originals, licenses and explicit authored
identity adaptations are retained under `public/`. These are not ten plants,
independently authored answer keys or installed asset identities.

## Completed results

| Check | Result | What it means for the receiving engineer |
|---|---|---|
| Source-preserving attribute proposal | All ten candidates: zero unexpected strict differences and exact independent source-plus-plan byte reconstruction. | The declared single-line attribute edit retains every other source byte on these cases. |
| Matched library-save baseline | Nine have strict zero; R12 has 82 differences. **All ten fail byte reconstruction.** | Strict equality and raw preservation are different checks; report both. |
| Deliberately wrong outputs | All 42 applicable geometry/layer/style/foreign/XDATA losses detected by both strict and raw checks. Public fixtures have no foreign/XDATA records, explicitly not applicable. | The checker rejects these known losses; this is not every possible corruption. |
| Refused proposals | All 90 stale/before-value/duplicate/identity/newline/ambiguous/collision/revision controls refuse without damaging outputs. | A stale or unsupported proposal needs correction, rather than silent application. |
| Conflicting return and selected correction | All ten retain the unrequested collateral field under the original request; both receiving packets and portable replay retained. | Correcting the requested field does not close unrelated changes. Decisions remain pending. |
| Actual native API saves and fresh reads | All ten cases match complete supplied attribute sets. Forty saved files across matched no-edit/edit and default/R15 formats all fail strict preservation. | Exact stored fields do not establish a preserved drawing. API formats are separate from the UI R27 route. |
| Native rendering | Thirty original model/paper exports finish normally; all images actually inspected. All five newly authored paper pairs display content. Small/rotated/overlapping text, trial marks and missing Chinese glyphs prevent complete readable-delivery acceptance. | Retain the actual sheets and font limitations. New valid fixtures do not repair the earlier blank-sheet failures. |

[Software results](SOFTWARE-RESULT.json), [native API results](API-RESULT.json),
[render comparisons](RENDER-RESULT.json) and [actual image observations](RENDER-VISUAL.json)
are separate. Complete bounded archives have external retained identities. An
initial render-analysis palette conversion error is retained in
[the diagnostic](RENDER-ANALYSIS-DIAGNOSTIC.json); the corrected analysis decodes
each image before comparing colors. One-pixel and palette-reindex controls cover
that error. No native drawing, source, pixel mask or frozen method was changed.

## Still running

The two predetermined native UI cases are `public-air-water` and `final-foreign`.
All four original matched baseline/edit/save/reopen executions finish normally.
The public baseline/edit each retain 298 strict differences; the three-asset
foreign baseline/edit each retain 334. All three planned foreign-case MODEL edits
commit; the complete fields and editability checks remain bound to each source.
All four complete packet inventories replay, including original runtime bytes.
The exact four returns and parent packets are committed at `e3c7899` before either
fresh receiver starts. Both original fresh four-file processes are now running;
their complete receiving and exact-frame visual checks remain unfinished.
Those checks, exact-head CI and the final objective audit prevent a
whole-workflow completion claim. Full native preservation already fails.
The [objective audit](OBJECTIVE-AUDIT.md) maps the work to the original requirements
and keeps failed and unfinished gates distinct.

The frozen `native_ui.py` has an unused packaging entry-point import omission
(`json`). Packaging uses the separate `retain.py`; the frozen receiving/pixel
functions and all 55 method identities remain unchanged. This is an evidence
packager limitation, not a new candidate method or a native qualification pass.
The first new packets also omitted runtime cache files. Exact original cache
bytes are retained separately in `ui-support/`. `receive_ui.py` restores them and
the exact configuration from its already-public, externally bound pre-final
parent packet. This avoids publishing configuration contents in new packets and
still requires **every original file, size and hash** under the unchanged full
inventory check. All four currently completed UI packets replay through it;
the initial incomplete packaging is retained rather than rewritten.
The fourth packet carries its exact runtime cache in `runtime-support/` beside
the main archive. No native configuration contents are newly published.

## Reproduce completed checks offline

With the repository's pinned requirements, from the root:

```sh
python examples/cad-handoff/qualification/final-validation-23/recheck.py
python examples/cad-handoff/qualification/final-validation-23/test_render_pixels.py -v
```

The first command rebuilds all ten software candidates, losses, refusals,
conflicts and portable receiving briefs, and re-scores the complete retained API
and render evidence. It calls no model, native editor or network service. It
does not repeat the native executions or constitute independent engineering
review. Source interpretation, site applicability and company acceptance remain
with the responsible engineering team.

To repeat native execution, use the recorded [environment and publisher package
identity](../linux-native-7/ENVIRONMENT.json), [Docker recipe](../linux-native-7/Dockerfile)
and the prepared input/launch records here. The native image is a local evaluation
artifact, not a redistributed CAD product. A rebuild with different dependencies,
editor or fonts is a new environment and needs its own results. Offline replay
reproduces the retained evidence without requiring that environment. For your
own transmittal, the reusable receiving command accepts prepared source/return
records directly; this native experiment is not an installation requirement.
