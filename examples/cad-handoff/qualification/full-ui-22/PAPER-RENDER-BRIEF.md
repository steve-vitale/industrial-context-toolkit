# Paper delivery fails even where images match

The [predeclared check](PAPER-RENDER-PLAN.md) completed all fourteen native bitmap
exports normally, with the selected profile and unchanged source bytes. The
existing offscreen native exporter needed no CAD UI session. Exact inputs,
commands, stdout/stderr, images and normal host/container exits are retained in
[the complete inventory](PAPER-RETAINED-1.json).

Actual agent inspection of [all fourteen images](PAPER-VISUAL-1.json) found:

| Inputs | Observed paper result | Receiving consequence |
|---|---|---|
| Two originals and their original value candidates | Blank except the retained native trial mark | Exact byte preservation retains the source's existing paper dependency; readable sheet delivery fails. |
| Both matched no-edit native returns, both concurrent native returns, both selected second value candidates and both actual second native returns | Blank except the retained native trial mark | Correct MODEL values and matching model images do not supply usable paper sheets. |
| Exposed public-adapted text/viewport control, rendered twice | Six visible viewport/text examples; both full images identical | The exporter can display paper content under this profile. The control is not an untouched plant or typography acceptance case. |

All ten declared full-image comparisons have zero different pixels. **These are
matching blank case images, not a paper-preservation or readability pass.** The
public control differs from a case image at 122,616 pixels. No pixels, trial
marks, fonts, paper settings or source drawings were repaired or removed. The
control retains viewport clipping and a trial mark over part of the text.

The [record audit](PAPER-RECORD-BRIEF.md) independently distinguishes what the
blank images cannot: originals have a display viewport without a special main
viewport; first native returns lose the original display viewport and change
paper settings. A second value candidate preserves its already changed native
source, including that loss. This run establishes failed paper delivery on
these known problem sources; it does not isolate the precise importer/writer
function or claim that arbitrary CAD drawings have the same problem.

For the engineer, request a usable sheet and an explicitly reviewed correction
to its CAD/layout source. Keep the original request, original drawing and actual
return. For the manager, retain the paper requirement as unresolved and route
correction with the drawing custodian. Do not release the drawing on the basis
of a supported attribute row or equal blank images.

Reproduce the complete source/provenance, command and pixel check offline:

```sh
python examples/cad-handoff/qualification/full-ui-22/check_paper.py examples/cad-handoff/qualification/full-ui-22/paper-render-1 --expect examples/cad-handoff/qualification/full-ui-22/PAPER-COMPARISON-1.json
```

This performs no native/model/network call. It checks saved execution evidence,
not a fresh CAD execution or independent engineering review. Source and method
identities were committed before native execution at `a7c386b`; the receiving
code is a separately identified exposed analysis. Final freeze and newly
reserved validation remain required. No new source-repair study is part of this
failed paper result.
