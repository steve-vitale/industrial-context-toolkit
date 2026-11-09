# CAD receiving review

Strict comparison: **differences**; 2 differences outside allowed edits.

Acceptance has not been performed. This packet explains differences; it does not approve a returned drawing.

Before SHA-256: 2044da26edd9188d07300f6b8f2abf4053956f31a7827bba488ec02c1351e158
After SHA-256: 3d3dab97cf7aaa1a8dc68b6cf9ecf5cb913adea5d527242e89d8647d46ad402f

DXF version: AC1015 to AC1015.
Declared save metadata changed: True. These named exclusions are retained in the strict comparison.

## Asset attribute values

| Position / field | Before | Returned | Observation |
|---|---|---|---|
| validation-cp1251/asset-1 / ICT_ID | validation-cp1251/asset-1 | validation-cp1251/asset-1 | unchanged |
| validation-cp1251/asset-1 / MODEL | Двигатель | OTHER-CHOICE | planned edit missing or different |
| validation-cp1251/asset-1 / SERIAL | UNCHANGED-0 | UNCHANGED-0 | unchanged |
| validation-cp1251/asset-1 / SIZE | DN50 | DN50 | unchanged |
| validation-cp1251/asset-1 / TAG | FV-101 | FV-101 | unchanged |
| validation-cp1251/asset-1 / VENDOR_PRIVATE | retain {vendor} \P 0 | retain {vendor} \P 0 | unchanged |
| validation-cp1251/asset-2 / ICT_ID | validation-cp1251/asset-2 | validation-cp1251/asset-2 | unchanged |
| validation-cp1251/asset-2 / MODEL | Двигатель | Мотор | planned edit observed |
| validation-cp1251/asset-2 / SERIAL | UNCHANGED-1 | FIELD-OBSERVED | unexpected |
| validation-cp1251/asset-2 / SIZE | DN50 | DN50 | unchanged |
| validation-cp1251/asset-2 / TAG | FV-102 | FV-102 | unchanged |
| validation-cp1251/asset-2 / VENDOR_PRIVATE | retain {vendor} \P 1 | retain {vendor} \P 1 | unchanged |

## Identity and block changes

| Position | Observation | Before | Returned |
|---|---|---|---|

## Layouts

| Record | Before | Returned |
|---|---|---|

## Block definitions

| Record | Before | Returned |
|---|---|---|

## Named layers, styles and tables

0 records; see review.json and strict-comparison.json for every exact change.

## Header values

0 records; see review.json and strict-comparison.json for every exact change.

## Drawing records to inspect

| Handle / type | Scope before / returned | Observation | Fields |
|---|---|---|---|

## All drawing record field values

0 records; see review.json and strict-comparison.json for every exact change.

## Strict entity queue summary

| Observation at handle | Count |
|---|---|
| same type changed | 2 |

## Every strict entity difference remains open

2 records; see review.json and strict-comparison.json for every exact change.

## Boundaries and next step

Diagnostic only; the original strict comparison and its exit status remain authoritative for this software gate. Handles are not matched by geometry. Added/removed handles may be remapping, not added/removed physical objects. Drawing fields are explicit ezdxf attributes of direct block/layout records, not geometry or visual equivalence. Child ATTRIB/complex payloads, XDATA and other objects remain in the strict queue. Named table fields do not cover complete linetype patterns or style behavior. No difference is automatically waived, accepted or called harmless.

Qualify the intended receiver/settings, inspect appearance and editable data, investigate every remaining difference, then retain an owner-reviewed receiving checklist. No context update is promoted by this report.

Files: [review data](review.json), [strict comparison](strict-comparison.json), [original drawing](originals/before.dxf), [returned drawing](originals/after.dxf) and [receipt](receipt.json).
