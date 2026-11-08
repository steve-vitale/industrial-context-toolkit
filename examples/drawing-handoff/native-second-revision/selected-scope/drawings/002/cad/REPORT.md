# CAD receiving review

Strict comparison: **differences**; 453 differences outside allowed edits.

Acceptance has not been performed. This packet explains differences; it does not approve a returned drawing.

Before SHA-256: 25aa6294826284917784d54ed8241a55738a4f4c3c74b4b93ff51d6add6622f2
After SHA-256: 8f67fea4ac5aa04a65a6fa13ecbd386d04ca48d935f475cdfa7b3a140ab8ded0

DXF version: AC1027 to AC1027.
Declared save metadata changed: True. These named exclusions are retained in the strict comparison.

## Asset attribute values

| Position / field | Before | Returned | Observation |
|---|---|---|---|
| validation-braces/asset-1 / ICT_ID | validation-braces/asset-1 | validation-braces/asset-1 | unchanged |
| validation-braces/asset-1 / MODEL | OTHER-CHOICE | Assembly {D} | planned edit observed |
| validation-braces/asset-1 / SERIAL | UNCHANGED-0 | UNCHANGED-0 | unchanged |
| validation-braces/asset-1 / SIZE | DN50 | DN50 | unchanged |
| validation-braces/asset-1 / TAG | FV-101 | FV-101 | unchanged |
| validation-braces/asset-1 / VENDOR_PRIVATE | retain {vendor} \P 0 | retain {vendor} \P 0 | unchanged |
| validation-braces/asset-2 / ICT_ID | validation-braces/asset-2 | validation-braces/asset-2 | unchanged |
| validation-braces/asset-2 / MODEL | Assembly {D} | Assembly {D} | unchanged |
| validation-braces/asset-2 / SERIAL | FIELD-OBSERVED | FIELD-OBSERVED | unchanged |
| validation-braces/asset-2 / SIZE | DN50 | DN50 | unchanged |
| validation-braces/asset-2 / TAG | FV-102 | FV-102 | unchanged |
| validation-braces/asset-2 / VENDOR_PRIVATE | retain {vendor} \P 1 | retain {vendor} \P 1 | unchanged |

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

9 records; see review.json and strict-comparison.json for every exact change.

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
