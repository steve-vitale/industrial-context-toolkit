# CAD receiving review

Strict comparison: **differences**; 453 differences outside allowed edits.

Acceptance has not been performed. This packet explains differences; it does not approve a returned drawing.

Before SHA-256: 267770b66f3cc175fa822c04e738e5cfe7e927491cfb95ff47a2db6242b9e953
After SHA-256: 62454b6839032099706f6be2d8ddeba24ec9e28742e97be9d966b3c8f438b0eb

DXF version: AC1027 to AC1027.
Declared save metadata changed: True. These named exclusions are retained in the strict comparison.

## Asset attribute values

| Position / field | Before | Returned | Observation |
|---|---|---|---|
| validation-cp1251/asset-1 / ICT_ID | validation-cp1251/asset-1 | validation-cp1251/asset-1 | unchanged |
| validation-cp1251/asset-1 / MODEL | OTHER-CHOICE | Мотор | planned edit observed |
| validation-cp1251/asset-1 / SERIAL | UNCHANGED-0 | UNCHANGED-0 | unchanged |
| validation-cp1251/asset-1 / SIZE | DN50 | DN50 | unchanged |
| validation-cp1251/asset-1 / TAG | FV-101 | FV-101 | unchanged |
| validation-cp1251/asset-1 / VENDOR_PRIVATE | retain {vendor} \P 0 | retain {vendor} \P 0 | unchanged |
| validation-cp1251/asset-2 / ICT_ID | validation-cp1251/asset-2 | validation-cp1251/asset-2 | unchanged |
| validation-cp1251/asset-2 / MODEL | Мотор | Мотор | unchanged |
| validation-cp1251/asset-2 / SERIAL | FIELD-OBSERVED | FIELD-OBSERVED | unchanged |
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

10 records; see review.json and strict-comparison.json for every exact change.

## Header values

1 records; see review.json and strict-comparison.json for every exact change.

## Drawing records to inspect

| Handle / type | Scope before / returned | Observation | Fields |
|---|---|---|---|
| 132 / VIEWPORT to None | *Paper_Space1 / None | removed handle | Entire record; 39 explicit fields |
| 138 / VIEWPORT to None | *Paper_Space / None | removed handle | Entire record; 39 explicit fields |
| 20B / None to VIEWPORT | None / *Paper_Space1 | added handle | Entire record; 39 explicit fields |
| 211 / None to VIEWPORT | None / *Paper_Space | added handle | Entire record; 39 explicit fields |

## All drawing record field values

156 records; see review.json and strict-comparison.json for every exact change.

## Strict entity queue summary

| Observation at handle | Count |
|---|---|
| added handle | 211 |
| handle reused for different type | 14 |
| removed handle | 212 |
| same type changed | 15 |

## Every strict entity difference remains open

452 records; see review.json and strict-comparison.json for every exact change.

## Boundaries and next step

Diagnostic only; the original strict comparison and its exit status remain authoritative for this software gate. Handles are not matched by geometry. Added/removed handles may be remapping, not added/removed physical objects. Drawing fields are explicit ezdxf attributes of direct block/layout records, not geometry or visual equivalence. Child ATTRIB/complex payloads, XDATA and other objects remain in the strict queue. Named table fields do not cover complete linetype patterns or style behavior. No difference is automatically waived, accepted or called harmless.

Qualify the intended receiver/settings, inspect appearance and editable data, investigate every remaining difference, then retain an owner-reviewed receiving checklist. No context update is promoted by this report.

Files: [review data](review.json), [strict comparison](strict-comparison.json), [original drawing](originals/before.dxf), [returned drawing](originals/after.dxf) and [receipt](receipt.json).
