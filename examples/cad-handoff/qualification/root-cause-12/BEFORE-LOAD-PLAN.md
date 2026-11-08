# Separate prepopulated document state from file loading

Declared after attempts 1/2 and before attempt-3. Their native stderr reports original-handle collisions,
including resource type 2 and block type 3. Those warnings are not a clean preservation result.
The frozen historical harness and first probes use RDocument(storage,index) with the default beforeLoad=false.
Public RDocument.h exposes beforeLoad as an explicit third constructor argument. The hypothesis is that a
new-drawing initialization populates resources before import, contributing collisions and record inflation.
That does not explain every proprietary reader/writer transformation without a matched intervention.

Use the explicit preserve-attributes probe from attempt-2 and change only constructor initialization to true,
plus read-only logging of native object handles/types before and after each import. Run the same 48 exports
and 48 fresh-process reads on the same sources, selected configuration and image. Preserve all warnings,
outputs and differences. Report whether collision warnings, added linetypes and strict rows change; do not
assume zero or classify remaining unknown payload as harmless. This remains exposed API method development,
separate from the earlier actual native UI case and from a fresh engineering receiving qualification.
