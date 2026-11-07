# Clear transient pointer state before comparing native views

The earlier 13,556-pixel paper mismatch is explained on these exact exposed inputs.
QCAD highlights the viewport or text under the pointer. Its display can keep that
highlight after the pointer leaves the canvas. The original capture recipe did not
explicitly clear it. This is an observation-method defect, not evidence of DXF loss.

The [plan](../RECEIVER-STATE-8-PLAN.md) and [frozen method/input identities](FREEZE.json)
were committed before this new native experiment. In the same pinned Linux receiver,
the experiment opened the exact source twice and candidate once, without saving.
It deliberately moved the pointer over the elliptic viewport, through blank canvas,
over concave-viewport text, and through blank canvas again, then repeated the ellipse
and blank control. All 21 native paper views and 42 stable-frame observations remain.

| Compared native canvas states | Different RGB pixels |
|---|---:|
| Earlier two exact-source repeats | 13,556 |
| New initial state versus earlier first repeat | 0 |
| Explicit ellipse hover versus earlier second repeat | 0 |
| Initial state versus pointer-neutral view | 6,788, in the concave viewport |
| Ellipse hover versus pointer-neutral view | 6,768, in the elliptic viewport |
| All nine neutral source/repeat/candidate views | 0 |
| Explicit concave text hover versus neutral | 1,076; different target within the viewport |

The two old highlighted regions are disjoint and account for all 13,556 pixels.
Both old full canvas states reproduce exactly. The neutral recipe moves through
empty canvas `(790,745)` before moving outside `(1090,900)` in the observed
1600×1000 desktop with fixed CAD window geometry. Merely moving outside is not the
same control. Coordinates require observing another desktop before reuse.

Inspect the untouched native screenshots: [ellipse hover](ellipse-hover.png) and
[pointer neutral](pointer-neutral.png). The comparison uses the same previously
declared whole canvas crop, without masks or altered output pixels. Trial panels and
all drawing content remain. Nine neutral views are nine repeated observations of
one source family, not nine independent drawings or a readability assessment.

The adapted equipment-data anchor is outside this paper view. Zero paper differences
therefore do not prove that its changed value is visibly rendered. Geometry/text
already clipped by viewports is not made complete by clearing a highlight. The five
missing-main-viewport layouts, Cyrillic/font readability, native full-save differences
and fresh native validation remain open. This does not finish CAD qualification.

## Replay the result offline

From the repository root with the existing Pillow/ezdxf dependencies:

```sh
python examples/cad-handoff/qualification/check_receiver8.py
```

This verifies both evidence archives and all declared source/method identities,
recomputes full-frame stability and canvas pixel comparisons, and rejects five
planted receiving errors: an altered canvas pixel, a hover image substituted for
neutral, an abnormal receiver exit, an omitted case and a changed input identity.
It replays retained native observations; it does not rerun CAD or establish an
independent engineer's review. The complete evidence is 73 exact records in
`evidence.tar.xz`, pinned by [INVENTORY.json](INVENTORY.json).

[ENVIRONMENT.json](ENVIRONMENT.json) records the actual image/container, copied local
configuration digest, startup acknowledgement and normal native application exit.
The configuration and licensed CAD/font binaries are not redistributed. A copied
run-7 configuration was used before starting the fresh container; this is not an
independent receiving environment. No new native input/capture failure occurred in
this batch. Earlier failures and all frozen methods are retained unchanged.

This supports a successor observation method: use pointer-neutral native views when
checking recipients, while keeping equipment-data editing independent of a CAD UI.
It needs a separate method freeze and fresh validation before a broader claim.

Source-reference correction: the precommitted plan calls `aae153a…` a commit. It is
the annotated `v3.33.1.0` **tag object**; GitHub's tag API resolves it to source commit
`897079c2d11aaa0869f839a6cf5df8a937dbddbe`. The version-tag source link used for the
hypothesis is unchanged. This bibliographic correction does not alter the planned
method, executed binary, evidence or original pre-execution plan.
