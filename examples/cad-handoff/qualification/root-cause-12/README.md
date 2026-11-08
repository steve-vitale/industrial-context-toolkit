# CAD causes, interventions and remaining unknowns

The native-save failures are a combination of full-file reconstruction and a confirmed test-harness bug.
They are not all handle renumbering, and zero unintended text changes does not establish CAD preservation.
This investigation uses **six already exposed public-derived sources**, with **144 actual native exports**
across three matched experiments. It adds no plant, independent engineer, new holdout or native UI acceptance.
Original drawings, frozen methods, strict failures and raw byte requirements remain intact.

## What the interventions establish

| Question | Observation | Cause / consequence |
|---|---|---|
| Does an attribute edit cause the hundreds of differences? | No-edit saves reproduce the same 346–436 strict row counts as edited saves: 4,650 rows across 12 source/format pairs. | A full import/export changes the document independently of editing. Counts alone do not establish the identity of each transformation; every row is separately indexed. |
| Does our edit operation change only text? | The historical `addObject(a)` call also moves the edited ATTRIB from `ICT_QUAL_TEST_ONLY` to the drawing's current layer. | **Confirmed harness defect.** `addObject(a,false)` removes that layer difference on all six cases. Default-format no-edit versus corrected edited returns then compare exactly under the original strict rules with only planned text permitted. |
| Why does R15 still differ between those matched branches? | One `DWGPROPS COOKIE` XRECORD remains. Its groups 41/42 exactly equal the respective saved headers' `$TDUCREATE` / `$TDUPDATE`. | Embedded save-time data is inside the strict entity boundary even though those header fields were already listed as metadata. It remains a strict failure; no new exclusion is added. |
| Will saving once make the file stable? | No. Second no-edit saves produce **6,138** strict rows (482–564 per pair). Owners/resource handles change again; resources and literal formatting also differ. | Pre-saving is not a preservation fix. The writer is not a fixed point under these rules. |
| Are handle-collision warnings caused by the constructor's `beforeLoad` default? | Changing only that flag leaves all 60 comparison counts and collision warnings unchanged. Native initial state still contains 60 objects. | **Rejected hypothesis.** Public core source clears before import and initializes default resources in either mode. Do not advertise this flag as a fix. |
| Is successful process exit enough? | The first raster probe exits native code 0 while reporting a fatal unsupported constructor. Later probes emit 24 blank predictions. | Require per-job observations and known-answer output, not just exit codes, file counts or nonempty receipts. Both unsuccessful methods are retained. |
| Why were the raster predictions blank? | A known-answer device paints yellow and the camera maps correctly; inherited `QPainterPath` access on `RPainterPath` returns impossible negative element counts. | This binding route is invalid in the observed QtScript runtime. Copying every element via the native wrapper's own getters into a genuine Qt path produces nonempty renders. No fonts or CAD binaries are redistributed. |
| What causes the old 62 pixels outside text bounds? | All lie at row 537, immediately above a geometric top projecting to 538.0512493261092. All 62 are candidate yellow text pixels. None of the 16 nonempty isolated width/AA/cap profiles exactly reproduces the original GUI difference. | Stroked/raster bounds are a plausible explanation, **not established exact causation**. The original 62-pixel failure remains. The historical loaded-settings gap is not repaired retroactively. |

The strict comparisons include every exported entity and applicable header under the original
[comparison boundary](../PROTOCOL.md). [SUMMARY.json](SUMMARY.json) reports the actual counts.
The lossless [inventory](INVENTORY.json) retains all three save attempts, five raster attempts, native logs,
exact reference images, source notices and reports. There are **24 indexed full-save diagnoses covering
10,788 strict rows** in the first experiment. The unchanged conservative correspondence method verifies
370 exact closed decoded record pairs for first saves and 936 for second saves. Those are record occurrences
across comparisons, not distinct assets or waived rows. Ambiguous/unmatched records remain unresolved.
Every comparison in all three experiments is re-scored, including strict-row hashes.

Native per-stage attribute checks cover 144 fields per experiment and another 144 in each fresh process.
QSet traversal changes array order: literal arrays repeat in 16/48 jobs in attempt-1 and 32/48 in attempt-2;
all 48 complete attribute-property sets match by parent/tag in each experiment. The order difference is
reported separately; no CAD payload is normalized by the strict comparator.

## Other causes already located

| Symptom | Established cause and evidence | Status |
|---|---|---|
| Source geometry appears clipped in bitmap views | The harness passed min/max to an option expecting XYWH; installed help and separately corrected commands confirm it. [Public-11 correction](../public-validation-11/WINDOW-CORRECTION.md). | Command fixed; old images retained. Earlier viewport-clipping attribution is not supported by those wrong-frame images alone. |
| Identical paper input produces 13,556 different pixels | Two pointer-hover highlights, exactly reproduced and decomposed; nine neutral views match. [Receiver-8](../receiver-state-8/README.md). | Cause isolated; neutral traversal becomes an observation requirement. |
| Cyrillic displays question marks | Pinned Standard CXF lacks 13 required glyphs. Explicit DejaVu mapping covers supplied characters. [Font-9](../font-views-9/README.md). | Mapped display is an available profile; original typography fidelity remains unproved. |
| Some authored paper layouts are blank | Missing main paper viewport; minimal independently byte-checked additions expose the existing display viewports. [Layout-10](../layout-preparation-10/README.md). | Bounded preparation works on exposed cases; its historical bitmap framing claim was corrected. |
| Authored labels overlap original linework | `adapt_public.py` adds fixed offsets `(x+3, y-3*offset)` with fixed height, independent of occupied geometry, units or text width. Public-11 actual images show the overlap. | Fixture-authoring limitation. Do not use this qualification adapter as an asset extraction or collision-aware layout tool. Preserve old fixtures; use a sidecar or a separately reviewed annotation layout. |
| Large marks obscure labels | Actual QCAD trial output retains evaluation marks. [Public-11 visual review](../public-validation-11/VISUAL-REVIEW.json). | Real receiving limitation. No mark/license/clock removal or readability claim. A legitimately available receiver must pass its own complete readable check. |
| Copied configuration was reported as loaded | Earlier font harness selected a different path. Later receivers check RSettings, native stderr and before/after hashes. [Font-9](../font-views-9/README.md), [Public-11](../public-validation-11/README.md). | Later observation fixed; earlier reproducibility claim remains narrowed. |
| Foreign-payload control emitted duplicate handles | Its new ATTRIB used a handle without advancing HANDSEED. [Public-11 retained failures](../public-validation-11/README.md). | Control allocation fixed; warning-tainted prior control is not accepted. |
| A compressed archive changed while staging | Broad CAD text policy overrode the raw-family rule; Git converted bytes. [Staging correction](../public-validation-11/STAGING-CORRECTION.json). | Rule precedence and renormalized index fixed; exact checkout checks cover this new archive too. |
| Previously seen public drawings were called unseen | Selection did not join the earlier source catalog by original raw hash. [Exposure erratum](../public-validation-11/EXPOSURE-ERRATUM.json). | Original cohort retained and corrected to four newly inspected / two previously exposed. All six are exposed development in this investigation. |

## Reproduce and use the findings

```sh
python examples/cad-handoff/qualification/check_root12.py
python -m unittest discover -s scripts -p test_cad_linux_evidence.py
```

This offline route needs normal Python dependencies (ezdxf and Pillow), not CAD, Docker, accounts or network.
It reconstructs the original exact candidates, receives selected settings and terminal container state,
checks every native field and fresh-process property, recomputes all branch tables and the full-save row
indices, rechecks conservative pairs, and recomputes every raster mismatch. Receiving controls exercise
omitted jobs, unplanned observed properties, geometry changes and a forged zero-difference claim.

For existing asset-data corrections, use the [source-preserving data-review route](../../data-review/README.md).
It retains unknown source bytes and separates an explicit proposal from a full CAD save. For native drafting,
keep the saved revision, strict comparison and a complete readable/editable receiving check. This study does
not qualify full saves, original typography, fresh UI/revision behavior or engineering/company acceptance.

The next decisive work is to trace the actual GUI scene/pen path for the residual pixels, distinguish
import-time resource reconstruction from proprietary exporter behavior at each remaining record, and test
a legitimately available receiver on newly reserved inputs with the corrected complete method. Changing
metrics or excluding the residual rows would not answer those questions.

## Primary method references

The public QCAD source is pinned to `897079c2d11aaa0869f839a6cf5df8a937dbddbe`, the peeled
`v3.33.1.0` tag (verified with `git ls-remote`). It documents the
[operation flag](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/operations/RAddObjectsOperation.h),
[current-attribute application](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/RTransaction.cpp),
[import reset](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/RDocumentInterface.cpp),
[resource initialization](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/RDocument.cpp),
and [native path getters](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/RPainterPath.h).
Public core code is not the proprietary DXF plugin's implementation or proof of the package's build chain;
the actual native interventions supply separate evidence. Qt's
[coordinate-system documentation](https://doc.qt.io/qt-6/coordsys.html) explains geometric versus pen bounds;
it is conceptual documentation, not an exact replay of this Qt5 GUI.
