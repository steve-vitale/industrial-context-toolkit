# Native CAD is a receiving check, not a data-entry dependency

The [local form/agent exchange](../../data-review/README.md) changes existing equipment attributes without
resaving the rest of the drawing. A native editor checks whether a recipient can read and edit that delivered
file. These are separate jobs. Native UI automation is not required to run the metadata tool.

This experiment used a separate **Linux QCAD Professional trial 3.33.1 / Qt 5.14.2** desktop after Windows capture
failed. It observed an actual native edit/save/document-close/reopen and a later complete app-process reopen
on the exposed fictional valve. It does **not** finish the broader CAD qualification goal.

| Observation | Result |
|---|---|
| Native property edits | MODEL `SRC-3`, SERIAL `AV-88412`, SIZE `DN65`; identity, tag and foreign text retained. |
| Native Save As and reopen | Default R27 [2013] DXF; returned bytes retained, document closed/reopened, app quit normally and returned file reopened in a fresh process. |
| Editability | Six native labeled fields observed enabled/editable. A temporary foreign-field edit was undone and discarded; the saved DXF hash stayed unchanged. |
| Full native save | **Fails:** 287 strict differences. Source AC1015 becomes AC1027; header, styles, records and layout changes remain in the receiving report. No waiver. |
| Exact-span candidate | Zero strict differences outside the three declared edits; independent raw reconstruction passes. Opens with readable valve labels and editable attributes in the native UI. |
| Same-session valve canvas | 425 changed pixels, all within the area of the three edited labels. Exploratory diagnostic; no general image-equivalence score. |
| Existing cohort | 21 exposed sources and their candidates: 42 native model views and 12 paper views retained with stable image-data observations and unchanged input hashes. No fresh native holdout. |
| Layout/font limits | Five authored source/candidate layout pairs are blank. Rotated Cyrillic text remains unreadable in the inspected canvas despite correct Unicode in the native field. Whole-label and original-font acceptance remain open. |
| Same-original control | The public paper view has two pixel states, differing at 13,556 canvas pixels. Reopening the **same exact original twice** reproduces both states. This receiver/view-state difference cannot be attributed to changed candidate bytes. Its underlying cause remains unresolved. |

Inspect the exact screenshots: [original valve](valve-before.png), [source-preserving candidate](valve-candidate.png),
[native returned file after fresh-process reopen](valve-native-return.png), [blank original layout](blank-source-layout.png)
and [Cyrillic zoom/property field](cyrillic-zoom.png). Trial panels remain visible. No license restrictions or printed
trial marks were removed. No proprietary CAD executable, font or settings are redistributed.

## Replay without a CAD account, desktop or network

From the repository root, with the existing pinned `ezdxf` and Pillow dependencies:

```sh
python examples/cad-handoff/qualification/check_linux7.py
```

This verifies/extracts every exact archive member, rebuilds 21 candidates, repeats the unchanged strict comparison
and receiving/correspondence reports, checks the six labeled native-field observations and 54 view records,
and recomputes the valve and same-original pixel diagnostics. Five receiving controls reject stale planned values,
changed foreign text, disabled editability, swapped field values and omitted view coverage. It **does not rerun
the GUI** or convert screenshots into engineering acceptance. The full repository suite calls this replay.

The [summary](summary.json) and [inventory](INVENTORY.json) bind the retained
[losslessly compressed evidence](evidence.tar.xz). `raw/MANUAL-ACTIONS.json` is explicitly a transcribed sequence
of tool observations, not a continuous video or automatic event recorder. Actual screenshots, native accessibility
trees, returned DXF, action receipts, package versions and stdout/stderr are retained separately inside the archive.

## Keep the failed attempts

The [plan](../LINUX-NATIVE-7-PLAN.md) preceded CAD execution. The [environment receipt](ENVIRONMENT.json) binds the
publisher package, immutable Ubuntu image, built desktop image and initial recipes. This is an optional local
evaluation environment, not a required deployment or redistributed CAD product. Use a new container after normal
app exit; restarting the same container left a stale X99 lock in this attempted recipe.

The first build failed on an existing UID 1000; a new UID was selected before any CAD run. Initial title clicks
maximized the window and invalidated matched view sizes. Two capture batches overlapped and were explicitly
excluded; their complete outputs remain. A later early filename entry left only a path suffix in a file dialog;
that run stopped on its title check. The corrected recipe waited for the actual dialog and focused its filename
field, then reran serially in new directories. All versions, frames and receipts remain in the archive and Git.

The [first replay failure](FIRST-REPLAY-FAILURE.json) also remains: its panel selector incorrectly matched an
Attributes popup menu. The fix requires the actual panel/label roles. The initial 75.7 MB ZIP is retained locally;
the public solid-compressed archive reconstructs the same 842 logical files byte for byte, including failed attempts.

All sources were previously exposed, including the public-adapted cases from one source family. These are
compatibility/development observations, not model training, independent review, plant accuracy, timed human benefit,
Windows acceptance or an approved engineering release. The original protocol, frozen comparison/patching methods
and all earlier native failures remain unchanged. Fresh native validation and complete readable visual acceptance
are still required before qualifying the full exchange workflow. The original frozen 28-test CAD module remains
unchanged; new replay/archive checks live in `scripts/test_cad_linux_evidence.py`. The
[attempted addition to the frozen module](SECOND-REPLAY-FAILURE.json) was correctly rejected by its binding check
and retained before restoring that module. No prior freeze was changed to accommodate new tests.
