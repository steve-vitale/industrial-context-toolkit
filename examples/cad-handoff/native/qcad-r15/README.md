# Explicit R2000 export is still an unqualified exchange

This is a second actual QCAD Professional 3.33.1 Qt5 Windows trial run on the same fictional source and three-edit
plan. The only helper change is `exportFile(output, "R15")`, using the documented native export version parameter.
The output confirms AC1015 (R2000), matching the source. A fresh native document reads all six expected attributes.
The [actual command](command.json), [log](native.log), [returned DXF](returned.dxf), [native readback](readback.json)
and [comparison summary](summary.json) are retained; binaries and trial settings are not distributed.

This setting reduces changed header values from 54 to 3, but **strict differences increase from 335 to 344**:
272 added handles, 53 removed handles, 17 same-type changes and one handle reused for a different type, plus one
whole-header difference. Added/removed handles do not establish added/removed physical objects. Added records,
text-style references and the extra paper-space viewport remain unresolved. Do not rank exchanges by raw difference
count or treat matching version/attribute values as preservation acceptance. No rule was waived and no context revision
was promoted. Interactive editor, visual/geometry and company acceptance remain open.

Reproduce the complete comparison offline with the reusable tool (expected exit 1):

```sh
python scripts/cad_handoff.py review examples/cad-handoff/source/valve.dxf examples/cad-handoff/native/qcad-r15/returned.dxf --plan examples/cad-handoff/source/edit-plan.json --out out/qcad-r15-review
```

The saved summary is derived diagnostic evidence; the raw inputs suffice to reconstruct the full queue. This is a
single exposed development fixture, not a receiver comparison benchmark or a claim of engineering losses. The first
[default-format attempt](../qcad/README.md) stays unchanged. The publisher package hashes and edition limitations are
recorded there. Optional native rerun uses the retained helper and the same input/plan flags as command.json, with new
output/config paths and a separately obtained compatible trial/edition. CI never downloads or runs that trial.

Primary reference: [QCAD exportFile version parameter](https://qcad.org/api/classes/RDocumentInterface/).
