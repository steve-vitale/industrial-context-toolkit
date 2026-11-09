# CAD receiving review

Strict comparison: **differences**; 322 differences outside allowed edits.

Acceptance has not been performed. This packet explains differences; it does not approve a returned drawing.

Before SHA-256: 2044da26edd9188d07300f6b8f2abf4053956f31a7827bba488ec02c1351e158
After SHA-256: 631de0b895bb7aa331fb46ed2d30d875078f2ae8b68a24f096a28df559cc2299

DXF version: AC1015 to AC1027.
Declared save metadata changed: True. These named exclusions are retained in the strict comparison.

## Asset attribute values

| Position / field | Before | Returned | Observation |
|---|---|---|---|
| validation-cp1251/asset-1 / ICT_ID | validation-cp1251/asset-1 | validation-cp1251/asset-1 | unchanged |
| validation-cp1251/asset-1 / MODEL | Двигатель | Мотор | planned edit observed |
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
| Layout1 | {&quot;block&quot;: &quot;*Paper_Space&quot;, &quot;entities&quot;: {}} | {&quot;block&quot;: &quot;*Paper_Space1&quot;, &quot;entities&quot;: {&quot;VIEWPORT&quot;: 1}} |
| Qualification sheet | {&quot;block&quot;: &quot;*Paper_Space0&quot;, &quot;entities&quot;: {&quot;VIEWPORT&quot;: 1}} | {&quot;block&quot;: &quot;*Paper_Space&quot;, &quot;entities&quot;: {&quot;VIEWPORT&quot;: 1}} |

## Block definitions

| Record | Before | Returned |
|---|---|---|
| *Paper_Space | {&quot;base_point&quot;: [0.0, 0.0, 0.0], &quot;flags&quot;: 0, &quot;layer&quot;: &quot;0&quot;, &quot;name&quot;: &quot;*Paper_Space&quot;, &quot;xref_path&quot;: &quot;&quot;} | {&quot;base_point&quot;: [0.0, 0.0, 0.0], &quot;flags&quot;: 0, &quot;layer&quot;: &quot;0&quot;, &quot;name&quot;: &quot;*Paper_Space&quot;, &quot;paperspace&quot;: 1, &quot;xref_path&quot;: &quot;&quot;} |
| *Paper_Space0 | {&quot;base_point&quot;: [0.0, 0.0, 0.0], &quot;flags&quot;: 0, &quot;layer&quot;: &quot;0&quot;, &quot;name&quot;: &quot;*Paper_Space0&quot;, &quot;xref_path&quot;: &quot;&quot;} | (absent) |
| *Paper_Space1 | (absent) | {&quot;base_point&quot;: [0.0, 0.0, 0.0], &quot;flags&quot;: 0, &quot;layer&quot;: &quot;0&quot;, &quot;name&quot;: &quot;*Paper_Space1&quot;, &quot;xref_path&quot;: &quot;&quot;} |

## Named layers, styles and tables

67 records; see review.json and strict-comparison.json for every exact change.

## Header values

57 records; see review.json and strict-comparison.json for every exact change.

## Drawing records to inspect

| Handle / type | Scope before / returned | Observation | Fields |
|---|---|---|---|
| 132 / None to VIEWPORT | None / *Paper_Space1 | added handle | Entire record; 39 explicit fields |
| 138 / None to VIEWPORT | None / *Paper_Space | added handle | Entire record; 39 explicit fields |
| 37 / ATTDEF to ATTDEF | ASSET / ASSET | same type changed | lock_position, style |
| 38 / ATTDEF to ATTDEF | ASSET / ASSET | same type changed | lock_position, style |
| 39 / ATTDEF to ATTDEF | ASSET / ASSET | same type changed | lock_position, style |
| 3A / ATTDEF to ATTDEF | ASSET / ASSET | same type changed | lock_position, style |
| 3B / ATTDEF to None | ASSET / None | removed handle | Entire record; 7 explicit fields |
| 3C / ATTDEF to ATTDEF | ASSET / ASSET | same type changed | lock_position, style |
| 47 / INSERT to INSERT | *Model_Space / *Model_Space | same type changed | xscale |
| 53 / LWPOLYLINE to LWPOLYLINE | *Model_Space / *Model_Space | same type changed | const_width |
| 54 / HATCH to HATCH | *Model_Space / *Model_Space | same type changed | transparency |
| 5A / ELLIPSE to ELLIPSE | *Model_Space / *Model_Space | same type changed | extrusion |
| 5F / VIEWPORT to None | *Paper_Space0 / None | removed handle | Entire record; 30 explicit fields |
| 61 / None to ATTDEF | None / ASSET | added handle | Entire record; 9 explicit fields |

## All drawing record field values

138 records; see review.json and strict-comparison.json for every exact change.

## Strict entity queue summary

| Observation at handle | Count |
|---|---|
| added handle | 227 |
| removed handle | 67 |
| same type changed | 26 |

## Every strict entity difference remains open

320 records; see review.json and strict-comparison.json for every exact change.

## Boundaries and next step

Diagnostic only; the original strict comparison and its exit status remain authoritative for this software gate. Handles are not matched by geometry. Added/removed handles may be remapping, not added/removed physical objects. Drawing fields are explicit ezdxf attributes of direct block/layout records, not geometry or visual equivalence. Child ATTRIB/complex payloads, XDATA and other objects remain in the strict queue. Named table fields do not cover complete linetype patterns or style behavior. No difference is automatically waived, accepted or called harmless.

Qualify the intended receiver/settings, inspect appearance and editable data, investigate every remaining difference, then retain an owner-reviewed receiving checklist. No context update is promoted by this report.

Files: [review data](review.json), [strict comparison](strict-comparison.json), [original drawing](originals/before.dxf), [returned drawing](originals/after.dxf) and [receipt](receipt.json).
