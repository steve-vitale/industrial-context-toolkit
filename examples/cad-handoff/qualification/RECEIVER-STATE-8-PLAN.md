# Isolate the native paper-view state before changing the drawing

Declared before new native execution. This is development on the already exposed
`text_in_viewports` source/candidate, not fresh validation and not a new acceptance
standard. The original protocol, strict comparator, patcher and all failures remain.

The retained pair and exact-source repeat differ in the same 13,556 canvas pixels.
The two affected viewport borders and their contents alternate between black and
gray. Hypothesis: transient pointer highlighting survives the earlier capture
recipe. Alternative explanations (clipping, fonts, cache or other receiver state)
remain open if the controls do not isolate it.

Primary source lead: QCAD's matching public version tag `v3.33.1.0`, commit
`aae153a31ee8769c973722a254920ac358aa9261`,
[RGraphicsViewImage.cpp](https://github.com/qcad/qcad/blob/v3.33.1.0/src/gui/RGraphicsViewImage.cpp#L1822)
changes the color of highlighted paths when displaying, but not printing/exporting.
This makes a pointer control worth testing; source code alone does not establish
what happened in the retained screenshots. Publisher bug 2320 is fixed and concerns
another trigger; it is not evidence that this is the same defect.

## Fixed development experiment

- Use the same pinned Linux image, receiver and original source/candidate from
  `linux-native-7/INVENTORY.json`. Fresh container; no stale X lock reuse, clock,
  license, watermark or drawing changes. Capture startup and observed native state.
- Open source, source again, then candidate, serially. Use the observed native file
  dialog and the same fixed window/Block List geometry as run 7. No save.
- For each paper opening capture initial state, explicit pointer over elliptic
  viewport `(630,455)`, then blank canvas `(790,745)` and outside `(1090,900)`, then
  concave viewport `(300,630)`, then blank/outside again, then elliptic again and
  blank/outside again. Retain intermediate frames and all command receipts.
- Require two identical consecutive image-data frames for each screenshot, as in
  run 7. Stable frames do not imply correctness. Compare the previously declared
  whole canvas crop `[114,176,807,787]` in RGB, without masking drawing content,
  marks, labels or differences. Pointer is outside that crop for blank/outside
  captures. Retain raw full screenshots.
- Test observations: do explicit hovers reproduce the old alternation? Does blank
  traversal clear it? Are blank/outside views identical across exact-source opens
  and source/candidate? Report every pixel difference, even if the hypothesis fails.
  The adapted metadata anchor is outside this paper view; zero paper differences
  would not establish visibility/editability of its changed value.
- Verify exact source/candidate hashes after viewing and normal application exit.
  Keep any input/dialog/capture failure and stop the failed batch before correction.

No new general qualification follows from one exposed drawing. Font readability,
the five known missing-main-viewport source layouts, full-save preservation and fresh
reserved validation remain separate open gates. If pointer cleanup works it is a
receiver-observation method candidate requiring a separate freeze before validation.
