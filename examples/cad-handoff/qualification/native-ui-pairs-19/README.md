# Matched native UI saves and fresh receiving: exposed development

2026-11-08. All 18 processes frozen at `5f27559` completed: a no-edit save, an edited save and a
fresh receiving process for each of six previously exposed public adaptations. Actual native UI
actions opened the drawings, selected the asset, inspected fields, changed MANUFACTURER where
planned, saved through the file dialog, closed/reopened and exited normally. The receiver opened
the source, both native returns and the source-preserving candidate. **Native full saves still
fail preservation; this does not qualify CAD.**

[PLAN.md](PLAN.md) and [METHOD.md](METHOD.md) preceded comparisons. The original
[qualification protocol](../PROTOCOL.md), strict comparator and byte checks are unchanged.
The [public source/exposure record](../public-validation-11/README.md) explains the adapted inputs.
These are six development files, not six independent plants or new reserved cases. Each has one
authored qualification asset with ICT_ID, TAG and MANUFACTURER; no foreign attribute is tested here.

## What the complete records show

| Exposed case | Source → no-edit return: strict differences | Source → edited return: strict differences | No-edit → edited return: unexpected differences | Exact camera in all three receiving frames |
|---|---:|---:|---:|---|
| libre-air-water | 300 | 300 | 53 | pass |
| libre-motion | 302 | 302 | 53 | FAIL |
| libre-power | 298 | 298 | 53 | FAIL |
| qcad-hydraulic | 374 | 374 | 50 | pass |
| qcad-mechanical | 356 | 356 | 52 | pass |
| qcad-template | 377 | 377 | 53 | pass |

All twelve native source-to-return comparisons fail. Save As selected R27/AC1027; source versions
differ. Complete strict reports retain every difference, including table/entity changes. Matched
no-edit saves help diagnose serialization but do not authorize ignoring it. All six exact-span
candidates pass strict comparison and independent exact-byte reconstruction; matched library saves
pass semantic comparison but fail byte reconstruction.

Offline receiving checks 798 retained native observations, 60 property-panel observations and 144
view captures, with 576 full/canvas PNG files. Actual UI, native stored values and returned DXFs
retain the intended MANUFACTURER change and unchanged ICT_ID/TAG. It also reports **12 failed
expectation-metadata checks**, two per edited process. The recorder retained a mutable dictionary;
later serialization rewrote earlier expected values. Independent UI trees/replies retain the real
before/after states. These failures remain even though every cohort controller exited zero.

All 54 fixed-region pixel comparisons have zero outside-region changes (no-edit comparisons permit
no region). Nine are explicitly **diagnostic only**: motion/power have last-decimal camera-offset
changes under the original zoom method. Their exact-camera gate fails. No tolerance, registration
or enlarged mask was introduced. Rendering with the recorded font substitution does not establish
engineering readability.

The development packet retains startup, staging, document-selection and wrong-window keyboard failures.
A same-process recovery completed but retains its failed original controller/container and 57 paired
strict differences. It is outside the clean cohort. See [DEVELOPMENT-NOTES.md](DEVELOPMENT-NOTES.md).

## Recompute offline

With the repository's installed requirements, from its root:

```sh
python examples/cad-handoff/qualification/check_ui19.py
```

This checks seven lossless [evidence packets](evidence/), inventories, frozen inputs/methods, native
execution records, actual controls/fields, source/return readback, crops and comparisons. It regenerates
strict reports and pixel-difference images in a temporary directory, then compares the complete result
with [SUMMARY.json](SUMMARY.json). No CAD process, network or model is called.
[REPLAY-METHODS.json](REPLAY-METHODS.json) binds replay Python text with CRLF normalized to LF;
native methods, drawings, observations and images retain exact byte hashes. The bounded archive reader
alone runs under `python -S`; complete receiving needs ezdxf and Pillow.

Each packet has a complete file/size/SHA-256 inventory, archive hash and explicit exclusions. Members
are at most 4 MiB; raw packets at most 256 MiB. Settings contents and publisher/compiled binaries are
excluded; recorded identities remain. The seven archives total 27,058,032 bytes. Packet names:
development, libre-air-water, libre-motion, libre-power, qcad-hydraulic, qcad-mechanical, qcad-template.

Packager identities resolve to their retained source versions, not automatically to the latest file.
The first full local suite exposed that mistaken assumption (94/95 programs passed, one failed).
Its [actual failure, command and source](validation/full-suite-1/) remain. The first two case packets
used the source retained under receiver-2 in the development archive; its only difference from today's
packager is adding receiver-2 history to the historical packet, not case packing. Today's packager
reproduced both case archives byte-for-byte. [Original inventories stay unchanged](validation/PACKAGER-REPRODUCTION.json),
and the receiver rejects packager identities without retained, frozen source evidence.

A subsequent replay exposed a separate load-clock diagnostic: ezdxf 1.4.5's
[_finalize_setup/_setup_metadata](https://github.com/mozman/ezdxf/blob/v1.4.5/src/ezdxf/document.py)
replaces the loaded $TDCREATE with the inspection time. The unchanged comparator's ancillary
save_metadata_changed flag can therefore differ for identical file headers. The
[original summary and actual replay difference](validation/INITIAL-SUMMARY.json) are retained.
The stable presentation now separates that flag from strict content results and checks the complete
raw candidate HEADER byte-for-byte. Actual unmodified comparator flags are returned in
live_parser_diagnostics on every check; they are explicitly non-reproducible diagnostics. A controlled
two-clock test reproduces the effect and a changed raw header refuses. This reporting correction changes
no comparator, CAD acceptance rule or native return. All original strict failures remain.

Regression controls remove observations, trees, close actions and fields; alter source/return data;
plant an unrelated pixel with updated capture hashes; challenge archive traversal, duplicates, links,
omissions and invalid sizes; and reproduce the recorder bug beside snapshot semantics. Run through
`python scripts/test_cad_linux_evidence.py` or the full repository runner. A passing replay reproduces
the retained failures and observations; it does not make native saves pass.

## What remains

[CAMERA-REPEAT-PLAN.md](CAMERA-REPEAT-PLAN.md) separately freezes an absolute-view control and immutable
event recorder before execution. It reuses exposed inputs, makes no CAD edit/save and cannot substitute
for a complete newly frozen native workflow on reserved cases. See [PROGRESS.md](PROGRESS.md) for status.

Full-save preservation, reserved transfer, foreign/other-text and multi-asset coverage, complete
revision/conflict gates and independent engineering/company acceptance remain open. Keep the narrower
source-bound metadata route distinct from acceptance of an arbitrary native-editor save.
