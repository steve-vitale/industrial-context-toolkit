# Retained second attempt: preservation passes, CAD qualification unfinished

`evidence.zip` preserves 1,189 raw records with individual pins in `INVENTORY.json`. The archive is exact bytes;
do not normalize its logs or rewrite the DXFs. It includes earlier failed display attempts and the first native
development driver's reporting failure. `summary-checked.json` corrects that reporting key using already retained
files/receipts; it does not replace the failed `summary.json` or pretend a successful original driver exit.

`offline-recheck.json` records an actual local replay: 21 exact candidate rebuilds, 63 re-scored native comparisons,
45 saved fresh-process stored-value checks, two stale refusals, one retained concurrent conflict and three draft
context commands. Forty-two native full saves remain strict failures. Read the [qualification guide](../README.md)
for the predeclared gates and exposure limits. None of these API/software checks fills native interactive editing.

The first packaging attempt stopped because a native help settings subdirectory contained an INI file; the
incomplete archive remains locally at `data/external/cad-qualification/packaging-failed-1/`. The original failed
offline replay remains in `data/external/cad-qualification/offline-recheck-1/`. The corrected packager excludes
declared settings/software before packaging. No qualification method or comparison rule changed for this fix.

The first negative-control run also exposed an unstable *informational* `save_metadata_changed` flag: ezdxf
replaces a zero creation date with the current time when reading. A deliberately delayed read of the same pinned
source/candidate changes that flag without changing strict status, unexpected differences or raw bytes
(`recheck-metadata-diagnostic.json`). The initial successful replay and exact pre-diagnostic replay code remain
in `offline-recheck-initial.json` and `../history/recheck-before-metadata-diagnostic.py`. The replay now compares
every strict field exactly and reports both retained and observed informational flags. The frozen inspector,
strict comparator, exclusions, patcher and byte checker are unchanged; all native full-save failures remain failures.

The archive contains all 82 final native PNGs and seven labelled contact sheets under
`raw/render-review-3/`. `qa/pairs.json` binds both images of every pair and reports exact RGB differences without
an acceptance threshold. All 35 model/asset pairs change pixels; all six paper pairs do not. Direct contact-sheet
inspection found five paper views blank apart from the retained trial mark; `text_in_viewports/paper-2` contains
the rectangular, elliptical and general viewport examples. An identical pair is not proof of useful content.

`VISUAL-REVIEW.json` is the agent's review record, not an independent engineer's approval. Font substitution,
watermark overlap, long labels and provisional passive paper bounds prevent a complete readable visual pass.
The original full-resolution DXFs/PNGs remain available for further inspection. No engineering truth or
original typography fidelity is inferred from the contact sheets.
