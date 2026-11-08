# Find the record interpretation boundary

The existing source-preserving attribute route still works on these twelve
authored sources: exact byte reconstruction and the unchanged strict comparison
pass under their plans. This experiment investigates the **separate general native
save**, whose earlier failures remain. It does not qualify a CAD exchange or
replace the [original protocol](../PROTOCOL.md).

The central finding is that these readers build document variables from XRECORDs;
their writers reconstruct those variables rather than round-tripping arbitrary
record paths, group codes and payloads. The matched controls locate distinct losses:

| Boundary | Actual observation | Consequence |
|---|---|---|
| dxflib import, private namespace | The three mixed values become only the final real value in the public native document. | Loss is already observed at import. The public importer calls setVariable for each item, overwriting the same key. |
| dxflib import, foreign namespace | Changing only QCAD_OBJECTS to ICT15_FOREIGN_OBJECTS removes all five test variables from the public model and from both returned formats. | Namespace selection matters. The public importer recognizes its own dictionary; this is not general dictionary preservation. |
| OpenDesign import | Both nested namespaces expose the scalars and complete ordered array in the public native document. | The tested nested array is represented before saving. This differs from the earlier direct-root XRECORD omission; it is not proof of arbitrary opaque-data support. |
| OpenDesign import, either writer | Native array values remain observable after export, but the returned record is empty with OpenDesign or a dangling dictionary link with dxflib. | The represented mixed payload is lost at the export-to-file boundary. All 12 OpenDesign-to-dxflib returns have the dangling link; no repair or waiver is applied. |
| Record identity and wire format | Foreign records move into QCAD_OBJECTS; group1 strings become group1000. Tested integer/real/private-string payloads can survive these changes. | Scalar readback is not complete record/path preservation. The group1000 fixture is labelled native-private format, not generic standard-XRECORD support. |
| Attached attributes | Every dxflib-imported test attribute points to the native model-space block (72 observations), matching the public constructor's current-block parent. dxflib-written raw sequences omit the INSERT's attribute-follow flag and sequence terminator; decoded INSERTs have no attached attributes. | The existing asset-profile guard refuses these returns even when a native reader still displays their text. No flattening or profile exclusion is added to obtain a comparison. |
| Hydraulic cross-route export | dxflib import followed by OpenDesign export fails for both namespaces with Invalid Symbol Table name. | Both attempted routes stay failed. The exact offending symbol remains unresolved; neither source is removed or rewritten. |

The last batch observes all **48 declared jobs**: **46 exports**, **46 fresh-process
public-inventory repeats**, **12 strict comparisons with differences**, **34 asset-profile
refusals** and **two native export failures**. The controller exits1 and records
cohort_status=differences. It has complete diagnostic coverage, not a successful cohort.
An earlier stopped batch retains another **26 exports** and their receiving reports;
it never reached fresh import. A refused comparison is not a zero-difference report.

## Matched sources and reproducibility

Six already exposed public-adapted originals each receive five authored XRECORDs:
string, integer, real, ordered mixed data and a separately labelled native-private
string. A paired source differs only at the literal root dictionary key. Original
handles, owners, payloads and all other bytes in each pair are equal. Mechanical and
template originals already contained private records; those entries are retained and
relocated by the same namespace intervention, with their original contents reported.
These are authored development revisions, not untouched public CAD or new holdouts.

The crossed experiment explicitly selects OpenDesign/dxflib importers and both
exporters. OpenDesign writes each source's original ACADVER; dxflib writes AC1015.
The pinned QCAD 3.33.1 / Qt5.14.2 image, selected settings hash, registry filters,
full public properties, raw returns, source provenance, commands and terminal states
are retained. Native software, fonts and settings contents are excluded.

```sh
python examples/cad-handoff/qualification/check_records15.py
python scripts/test_cad_linux_evidence.py
python scripts/test_checkout_contracts.py
```

The offline receiver does not execute CAD. It verifies all frozen inputs/methods,
the exact namespace substitution, candidates, native profile and phase selection,
the complete 48-job cohort, the successful fresh subset and all saved reports. It
retains dangling paths instead of skipping them. [SUMMARY.json](SUMMARY.json) and
[INVENTORY.json](INVENTORY.json) bind the received summary and exact raw archive.

Failed preparations remain: an ambiguous OpenDesign filter was refused; a file-only
copy omitted empty output directories; a pre-execution name collision was corrected
before any native run. The separately frozen final controller records per-job errors
and still exits1. The first offline analysis failed on a dangling link; its successor
keeps the unresolved handle. A shadowed local variable miscounted exports as5; the
first report remains and the count-corrected successor differs only at5->46.
See [filter](FILTER-CORRECTION.md), [directory](DIRECTORY-CORRECTION.md),
[complete-cohort](COMPLETE-COHORT.md) and [analysis](ANALYSIS-CORRECTIONS.md) records.

## Scope of the cause claims

The public [dxflib importer](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/io/dxf/RDxfImporter.cpp)
documents dictionary selection, per-item variable assignment and attribute parents.
The [exporter](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/io/dxf/RDxfExporter.cpp)
and [wire writer](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/3rdparty/dxflib/src/dl_dxf.cpp)
rebuild variable records and write INSERT/ATTRIB data. URL/byte hashes are retained.
This source-visible method is distinct from the proprietary OpenDesign implementation;
the actual native observations establish the latter's bounded public-model/file boundary.
No closed-source code identity or complete internal loss stage is inferred.

Other header/resource payload differences and the exact hydraulic symbol-table cause
remain unresolved. Full readable receiving, newly reserved source/native UI/editability
and revision qualification remain open. No company, plant or engineering acceptance
is established. These failures support retaining the original drawing and explicit
source-preserving proposals; they do not establish general native-save preservation.
