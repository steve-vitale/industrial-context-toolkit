# Select the exact general CAD importer after the ambiguity refusal

Attempt-1 is terminal exit1. Its native process exits0, but emits one error
row and fatal because OpenDesign registers two DXF filters: general CAD and
JWW Shift-JIS. The controller refuses incomplete job coverage. No source was
imported/exported; retain that run and its exact frozen method/registry list.

Before attempt-2 execution, copy every original frozen input byte into a new
workdir, replace only the probe with native_records_explicit.js, and re-freeze.
The successor selects these exact importer strings:

- All CAD Files [OpenDesign] (*.dxf *.dwg *.dwt *.dxb *.dgn *.dwf)
- DXF Files [dxflib] (*.dxf)

Keep exact source-version exporter matching and require unique membership in
the actual registry. No fallback, source replacement or format reinterpretation.
The unrelated Shift-JIS importer is not a method variant on these ASCII fixtures.
