# Trace dictionary interpretation through matched importer/exporter paths

Declared from clean main 808d9d798f1bfb3be759fd9b54f3f897688ff2d0 before
preparation or native execution. Previous goal turn made progress (PR34);
there is no carried blocker/no-progress streak. Original protocol and strict
comparator remain unchanged. All six source families are exposed development.

The pinned public dxflib importer maps QCAD_OBJECTS XRECORDs to document
variables, with one setVariable call per payload item; its exporter rebuilds
these variables as individual XRECORDs. This is a source-visible lead, not
proof of the installed proprietary OpenDesign implementation.

1. From the six exact public-11 adapted originals used in save-boundaries-14,
   author a QCAD_OBJECTS dictionary with string (group1), integer (90), real
   (40), and ordered mixed (1,90,40) XRECORDs. Include a separate native-private
   string control (1000), which is what the public writer uses; do not call
   that private wire format generic standard XRECORD support.
2. Make the paired foreign source by changing only the literal dictionary key
   QCAD_OBJECTS to ICT15_FOREIGN_OBJECTS in those exact bytes. All record handles,
   values, owner links, metadata and line endings stay identical. Retain both
   authored revisions, source pins and exact source-preserving attribute proposals.
3. Freeze all inputs, plans, native method and controller before execution.
   Run each source through the 2x2 cross of explicitly selected OpenDesign and
   dxflib import/export routes (48 exports), plus close/reopen and fresh-process
   import through that job's selected importer. Verify actual written ACADVER:
   source version for OpenDesign; AC1015 for dxflib. Record selected registry
   filters and actual native imported version; ambiguity must fail, not fallback.
4. Observe all public object/custom/attribute properties and every document
   variable with typed values before import, after import/export and after reopen.
   Native absence is absence in this public model, not proof about opaque storage.
   Use the existing pinned image/settings, no network, normal CAD user. No Qt seed
   intervention or UI edit is added. Retain any failure and stop on incomplete jobs.
5. Offline, verify the one raw namespace substitution, source-preserving candidates,
   exact per-path ordered tags/dictionary links, native variable observations and
   every strict row. Scalar survival cannot stand in for complete record preservation.
   Cross-route evidence may locate a public interpretation boundary; never claim
   source identity with the closed implementation or waive lost foreign records.

QCAD public source pinned to 897079c2d11aaa0869f839a6cf5df8a937dbddbe:
src/io/dxf/RDxfImporter.cpp (addXRecord*, addDictionaryEntry), RDxfExporter.cpp
(exportFile document variables), src/3rdparty/dxflib/src/dl_dxf.cpp (writeXRecord),
src/core/RDocument.h (getVariables/getVariable), RDocumentInterface.cpp and
RFileImporterRegistry.h (explicit filter selection). Retain URL/hash provenance.

Full native-save payload differences, complete readable receiving, newly reserved
source/UI/editability/revision qualification and company/engineering acceptance
remain open. This diagnostic cannot fill those gates or change the frozen target.
