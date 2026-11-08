# Paper receiving must distinguish viewing from document changes

This is design evidence for the remaining paper gate, not a receiving result.
The [source receipt](PAPER-SOURCE-1.json) pins a public source version and an
exact native UI tree retained in the complete CP1251 receiving archive.

QCAD's public [PrintPreview.start source](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/scripts/File/PrintPreview/PrintPreview.js#L86)
contains a custom-paper prompt. Its affirmative branch changes dimensions and
margins; the other branch writes a paper-size acceptance variable. The
[position branch](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/scripts/File/PrintPreview/PrintPreview.js#L125)
can request automatic fitting or write a position-acceptance variable. Therefore,
entering preview and declining its prompts must not be assumed to leave document
state untouched. This public version is a design lead, not proof that the
installed binary has identical behavior.

The retained actual UI tree exposes Block List entries for `Layout1
(*Paper_Space)` and `Qualification sheet (*Paper_Space1)`, an Edit Block control
and Print Preview. That makes direct layout navigation worth testing before
adding print setup to the receiving routine. The tree does not prove that any
of those actions has succeeded. It is not a paper screenshot or a layout check.

For the next separately frozen native paper probe:

1. Inventory exact source layout/block and viewport records; distinguish absent
   source settings from reader-generated defaults. Keep the known missing-main-
   viewport and plot-storage failures from earlier studies.
2. Observe actual active file, current block and available layout controls.
   Navigate by an exact observed layout identity through native UI, then verify
   the selected block. Do not assume model-space frame coordinates describe
   the paper viewport's displayed model coordinates.
3. Capture source and candidate at common absolute paper frames, retaining every
   layout, blank/clipped result and failed action. A blank pair is evidence of
   equivalent captured pixels, not readable drawing delivery.
4. If Print Preview is tested, record all prompts/actions and complete supported
   before/after document, layout and print variables. Keep mutations explicit;
   do not silently accept auto-fit, repair paper defaults, save changed settings
   or widen image masks to get a pass. Source file bytes remain retained.
5. Derive any label regions from the actual paper viewport transformation under
   a frozen rule. Until that mapping is validated, keep paper pixel differences
   unresolved rather than applying the model-view label regions to them.

An explicitly proposed main-viewport revision remains the separate
[layout-preparation route](../layout-preparation-10/README.md), with its nonzero
original-to-prepared comparison. It cannot retroactively pass the original.
The [layout-constructor](../layout-construction-17/README.md) and
[normal-opening](../open-initialization-18/README.md) diagnoses also remain
separate from successful full native receiving. No source, mask, comparator,
paper gate or qualification result changes in this note.
