# Receive the exposed paper sheets with the existing native bitmap exporter

This closes the remaining exposed paper observation, not a new reader or CAD UI
implementation. All sources and failures are already exposed. No result here is
a reserved validation result or an engineering acceptance.

Use the same pinned native image and selected test configuration as the current
second-revision campaign. Run QCAD's existing Dwg2Bmp exporter offscreen, serially,
at 2400 x 1600, white background, monochrome, with the existing explicit
Standard-to-DejaVu Sans display substitution. Keep trial marks and exact pixels.
Select the paper layout with the previously used `-block` option. The native
window is X/Y/width/height, using the existing corrected `window.xywh` function.

For each of the two exposed cases, render six exact files: original, its value
candidate, matched first no-edit native return, concurrent native return,
selected second value candidate and actual second native return. Use a common
frame derived only from the original display viewport extents, padded by 20% of
the larger extent (at least 2 drawing units). Do not repair sources, add main
viewports, fit native results, change print settings or save any drawing.

Render the already exposed public-adapted `text_in_viewports` paper layout twice
as a positive/repeatability control, using the same exporter/profile/frame rule.
It is a derived public teaching fixture, not an untouched plant drawing or new
independent case. Preserve its existing provenance and license references.

Before execution, retain all fourteen exact inputs, source/archive identities,
frames, manifest, driver hashes, image and configuration identities in a commit.
Retain original command stdout/stderr, every process exit, before/after source
hashes and container terminal state. No timeout-based restart. Configuration
contents and vendor binaries remain local; publish only their identity receipts.

Acceptance is established now: every input must stay byte-identical; all fourteen
native processes must terminate normally under the declared profile; both
control images must be identical and actually show paper content. Inspect every
paper image against its source/candidate scope. Blank equality fails readable
sheet delivery. Compare all source/candidate and no-edit/concurrent pixel pairs
without tolerance or masks, but do not treat an intended label change as a
preservation failure merely because its pixels change. Existing strict and raw
byte comparisons remain unchanged and authoritative for their own scopes.

If a source or return does not display its required sheet, retain that failure
and report the route as unqualified for readable paper delivery. Do not start a
new source-repair study to obtain a pass. This check does not claim original
typography, vector PDF fidelity, a complete drawing-reader evaluation, or plant
engineering approval. Final method freeze and new reserved cases remain separate.
