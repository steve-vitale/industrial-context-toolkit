# Display diagnosis 4: imported layout names and complete label views

2026-11-07. This is diagnosis of exposed render failures, not a new preservation trial. Keep the protocol,
method-2 methods, source/plan bytes, archive and existing comparisons unchanged. Preserve all new attempts.

1. Read all imported blocks and their native layout names, entity types and bounds from each of the 12
   replacement source/candidate pairs. Use read-only native imports. Record source/candidate raw hashes before
   and after; never export or edit a drawing in this probe.
2. Compare the five blank authored paper views with their actual imported native block/layout names and
   viewport entities. Retain absent/invalid bounds and mapping failures. If a name mismatch is observed,
   test both original requested layout name and returned native block name, using the same common window
   and unchanged source/candidate. Do not change source viewports to repair a failed render.
3. For model asset labels, test a declared pair of equal-scale translated windows around each complete
   source/candidate native label union. These preserve whole planned text bounds and leave trial marks visible;
   no output masking, watermark removal, font install or license change. Paired translations let an obscured
   label be inspected in another native view. Keep Standard-to-Arial/monochrome explicitly display-only.
4. Start with the exposed cp1251/long-label cases and five failed paper layouts. Retain every diagnostic.
   Freeze any useful general recipe before applying it to all remaining model/asset/paper views. No favorable
   case omission, new independent accuracy claim, original typography fidelity or UI acceptance follows.

The native UI gate still requires actual observed open/edit/save/close/reopen and a retained returned file.
Keyboard accessibility input may be used with fresh state/focus under the Computer Use skill. API/batch edits
never substitute for interactive work. A current capture failure remains a failure, not a successful screenshot.

Primary API references: https://qcad.org/api/classes/RDocument/ (`queryAllBlocks`, `queryBlockEntities`),
https://qcad.org/api/classes/RBlock/ (`getName`, `getLayoutName`) and the native
[bitmap renderer](https://qcad.org/en/manual/scripts/pro/tools/dwg2bmp/doc/dwg2bmp/).
