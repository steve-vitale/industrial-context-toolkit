# CAD receiving review

Strict comparison: **differences**; 335 differences outside allowed edits.

Acceptance has not been performed. This packet explains differences; it does not approve a returned drawing.

Before SHA-256: c64f5ac8f53f7f35ed0f119abdc28c1e11eb5c7cc28011ddaf079940cfee2b7d
After SHA-256: cebdc13aabd4a9049c941d08c03834bd6f9852cef3177489f9ffdbd3067cc36e

DXF version: AC1015 to AC1024.
Declared save metadata changed: True. These named exclusions are retained in the strict comparison.

## Asset attribute values

| Position / field | Before | Returned | Observation |
|---|---|---|---|
| S1/P1/PAST1/FDV-2210 / ICT_ID | S1/P1/PAST1/FDV-2210 | S1/P1/PAST1/FDV-2210 | unchanged |
| S1/P1/PAST1/FDV-2210 / MODEL | SRC-2 | SRC-3 | planned edit observed |
| S1/P1/PAST1/FDV-2210 / SERIAL | UNKNOWN | AV-88412 | planned edit observed |
| S1/P1/PAST1/FDV-2210 / SIZE | DN50 | DN65 | planned edit observed |
| S1/P1/PAST1/FDV-2210 / TAG | FDV-2210 | FDV-2210 | unchanged |
| S1/P1/PAST1/FDV-2210 / VENDOR_NOTE | retain this unfamiliar attribute | retain this unfamiliar attribute | unchanged |

## Identity and block changes

| Position | Observation | Before | Returned |
|---|---|---|---|

## Layouts

| Record | Before | Returned |
|---|---|---|
| Layout1 | {&quot;block&quot;: &quot;*Paper_Space&quot;, &quot;entities&quot;: {}} | {&quot;block&quot;: &quot;*Paper_Space&quot;, &quot;entities&quot;: {&quot;VIEWPORT&quot;: 1}} |

## Block definitions

| Record | Before | Returned |
|---|---|---|
| *Paper_Space | {&quot;base_point&quot;: [0.0, 0.0, 0.0], &quot;flags&quot;: 0, &quot;layer&quot;: &quot;0&quot;, &quot;name&quot;: &quot;*Paper_Space&quot;, &quot;xref_path&quot;: &quot;&quot;} | {&quot;base_point&quot;: [0.0, 0.0, 0.0], &quot;flags&quot;: 0, &quot;layer&quot;: &quot;0&quot;, &quot;name&quot;: &quot;*Paper_Space&quot;, &quot;paperspace&quot;: 1, &quot;xref_path&quot;: &quot;&quot;} |

## Named layers, styles and tables

64 records; see review.json and strict-comparison.json for every exact change.

## Header values

54 records; see review.json and strict-comparison.json for every exact change.

## Drawing records to inspect

| Handle / type | Scope before / returned | Observation | Fields |
|---|---|---|---|
| 114 / None to VIEWPORT | None / *Paper_Space | added handle | Entire record; 39 explicit fields |
| 33 / LWPOLYLINE to LWPOLYLINE | DRAFT_VALVE / DRAFT_VALVE | same type changed | const_width |
| 34 / ATTDEF to ATTDEF | DRAFT_VALVE / DRAFT_VALVE | same type changed | lock_position, style |
| 35 / ATTDEF to ATTDEF | DRAFT_VALVE / DRAFT_VALVE | same type changed | lock_position, style |
| 36 / ATTDEF to ATTDEF | DRAFT_VALVE / DRAFT_VALVE | same type changed | lock_position, style |
| 37 / ATTDEF to ATTDEF | DRAFT_VALVE / DRAFT_VALVE | same type changed | lock_position, style |
| 38 / ATTDEF to ATTDEF | DRAFT_VALVE / DRAFT_VALVE | same type changed | lock_position, style |
| 39 / ATTDEF to ATTDEF | DRAFT_VALVE / DRAFT_VALVE | same type changed | lock_position, style |
| 44 / TEXT to TEXT | *Model_Space / *Model_Space | same type changed | style |

## All drawing record field values

53 records; see review.json and strict-comparison.json for every exact change.

## Strict entity queue summary

| Observation at handle | Count |
|---|---|
| added handle | 262 |
| handle reused for different type | 1 |
| removed handle | 53 |
| same type changed | 17 |

## Every strict entity difference remains open

333 records; see review.json and strict-comparison.json for every exact change.

## Boundaries and next step

Diagnostic only; the original strict comparison and its exit status remain authoritative for this software gate. Handles are not matched by geometry. Added/removed handles may be remapping, not added/removed physical objects. Drawing fields are explicit ezdxf attributes of direct block/layout records, not geometry or visual equivalence. Child ATTRIB/complex payloads, XDATA and other objects remain in the strict queue. Named table fields do not cover complete linetype patterns or style behavior. No difference is automatically waived, accepted or called harmless.

Qualify the intended receiver/settings, inspect appearance and editable data, investigate every remaining difference, then retain an owner-reviewed receiving checklist. No context update is promoted by this report.

Files: [review data](review.json), [strict comparison](strict-comparison.json), [original drawing](originals/before.dxf), [returned drawing](originals/after.dxf) and [receipt](receipt.json).
