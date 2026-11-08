# Public-source CAD transfer, with receiving failures retained

This adds source structures beyond the drawings used to develop the exact attribute
writer. The [plan](../PUBLIC-VALIDATION-11-PLAN.md) and six
[selected paths](SELECTION.json) were committed at `d1885d0`, before this run downloaded
or opened the selected files. The [methods](METHODS.json) were frozen at `02c8fa2`; exact derived inputs were
[bound](ADMISSION.json) at `c28959e`, before candidate execution. No original comparator,
patcher, tolerance, layout producer or earlier evidence was changed.

**Exposure correction:** the [prior-catalog/raw-hash audit](EXPOSURE-ERRATUM.json) found
that `aw10.dxf` and `pe3.dxf` were already in round-1 admission records. The pre-run claim
that all six contents were uninspected was overbroad. The fixed cohort is **four newly
inspected sources plus two exposed regression originals**, with all six results retained.
No case was replaced after observing its outcome. Newly inspected does not establish
independent plant provenance, model-training blindness or unknown outside exposure.

| Check | Observed result |
|---|---|
| Original file integrity | All six match their pinned upstream Git blob identities. |
| Untouched asset admission | All six refuse: no explicit ICT_ID/TAG profile. No identities were inferred. |
| Declared test adaptation | Existing adapter adds fictional identities and an unused test field; existing source geometry/values are not interpreted as plant information. Preservation starts from these library-reserialized derived sources. |
| Exact attribute candidates | Six of six pass unchanged strict comparison and independent raw reconstruction. |
| Matched library-save baseline | Six of six pass decoded strict comparison; all six fail exact byte preservation. |
| Native edit/save/document reopen | 72 of 72 stored-field observations match exact route files. Both default and R15 returns retained. |
| Separate-process readback | Another 72 of 72 field observations match candidate, source and both returned formats. |
| Native full-save preservation | All 12 returns fail: 346–436 strict differences. Correct field values do not waive these differences. |
| Revision/loss controls | Six cases detect unplanned geometry, changed unfamiliar attribute/XDATA payloads, stale source and stale before values; a separately bound second revision passes strict/raw reconstruction. |
| Visual and whole-workflow qualification | Incomplete. Original/corrected native images and exact commands are retained; readable receiving review and native UI gates are separate from API readback. |

The cohort covers LibreCAD air/water, power and motion library paths, and QCAD hydraulic,
mechanical and template paths. These projects have shared history. Six files are not six
independent plants. The selected template is an empty geometry/layer template; its authored
test anchor does not establish preservation of complex original geometry. The adapter's
ordinary ASCII values test transfer across source structure, not new language/font coverage.
It adds no unfamiliar field initially; the foreign/XDATA control fields are explicitly
authored in a later fictional source revision. Existing long/Unicode/layout evidence and
its failures remain separate.

## A receiving-harness failure, not a drawing fix

The first 24-image batch used min/max boxes as the native bitmap `-window` argument.
The renderer expects X/Y/width/height. The installed version's own normally completed
help command confirmed the mismatch. The [correction](WINDOW-CORRECTION.md), frozen at
`26b5372`, converts only the argument, then reruns all 24 fixed views into a separate folder.
It changes no DXF, font, canonical frame, mark or output pixel. The original failed views
remain. These files are now exposed observation-development data; the corrected observation
method is not claimed blind. The same earlier layout-10 frame claim is explicitly narrowed.

Correct framing cannot remove inherited source geometry crossing the authored labels, or
trial marks covering content. A nonblank image, native bounds or a correct stored string
does not establish that every label is readable. No engineering or company acceptance follows.

Two revision-control harness failures also remain: a complete-DXF parser correctly refused
an isolated ATTRIB fragment; then a warning-tainted control run failed to advance HANDSEED.
The [first](CONTROL-FIRST-FAILURE.json) and [second](CONTROL-SECOND-FAILURE.json) notes retain
those observations. The corrected `controls-3` run has no duplicate-handle warnings and
reproduces deliberate revisions without changing any upstream or candidate file.

## Recheck retained observations

With the normal repository requirements, from the repository root:

```sh
python examples/cad-handoff/qualification/check_public11.py
python -m unittest discover -s scripts -p test_cad_linux_evidence.py
```

No account, network, commercial executable or CAD UI is needed for replay. The bounded
archive reader checks exact original/derived/candidate/returned files and commands. The
receiver rebuilds all exact candidates, re-scores the complete retained strict comparisons,
checks every native field, source pin, selected-configuration chain, image identity and
frame command, and regenerates the revision/loss controls. A replay verifies saved software
observations; it does not rerun CAD or manufacture human review.

Originals and modified drawing records in the archive retain their upstream repository
notices, included as `source-notices/LibreCAD-*` (GPLv2) and `source-notices/QCAD-*` (GPLv3).
Their exact source URLs and original editable DXFs are retained; the toolkit's license does
not replace those notices. Added identities/annotations and returned revisions are test
modifications by this project, not upstream engineering information. Native executable,
font and configuration contents are excluded; configuration evidence is digest-only.

The original goal remains active: explain the native full-save changes, complete the actual
receiving UI/visual/editability gates and audit the whole bounded workflow. This result
establishes neither a general native-save preservation pass nor a plant-ready drawing service.
