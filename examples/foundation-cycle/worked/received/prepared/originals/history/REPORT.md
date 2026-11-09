# Maintenance history review

Which selected work records need investigation or reconciliation?

Namespace: FICTIONAL; cutoff: 2024-01-31.

3 supplied assets; 6 selected work orders; 2 recurring-work review groups; 11 review issues.

Selected administrative records and supplied meanings. Recurring work is not proven failure. No associated rows proves only none were found in supplied exports. No installed parts, net consumption, root cause, MTBF or savings established.

Authorized decision: pending. Suggested roles need named owners and source readback.

## Review actions

- missing_completion_value: Check the current work-order record and disposition; missing completion does not prove open or overdue work. Suggested role: Maintenance records owner. [FIX-work_orders, CSV record 5, ends at physical line 6](evidence/work_orders-001.html#r5)
- missing_completion_value: Check the current work-order record and disposition; missing completion does not prove open or overdue work. Suggested role: Maintenance records owner. [FIX-work_orders, CSV record 3, ends at physical line 4](evidence/work_orders-001.html#r3)
- negative_material_quantity: Review the signed movement and any return/correction; do not infer installed quantity or consumption. Suggested role: Maintenance records owner. [FIX-details, CSV record 3, ends at physical line 3](evidence/details-001.html#r3)
- unknown_flag: Obtain the exact source code definition; retain this flag as unknown. Suggested role: Maintenance records owner. [FIX-work_orders, CSV record 3, ends at physical line 4](evidence/work_orders-001.html#r3)
- unknown_flag: Obtain the exact source code definition; retain this flag as unknown. Suggested role: Maintenance records owner. [FIX-labor, CSV record 5, ends at physical line 5](evidence/labor-001.html#r5)
- unlinked_details: Transaction is missing or has no qualified work-order association. Confirm the exact scoped parent/source relationship. Suggested role: Maintenance records owner. [FIX-details, CSV record 4, ends at physical line 4](evidence/details-001.html#r4)
- unlinked_details: Detail work-order reference disagrees with its transaction target; row quarantined. Confirm the exact scoped parent/source relationship. Suggested role: Maintenance records owner. [FIX-details, CSV record 6, ends at physical line 6](evidence/details-001.html#r6)
- unlinked_labor: Labor work-order reference is unavailable. Confirm the exact scoped parent/source relationship. Suggested role: Maintenance records owner. [FIX-labor, CSV record 7, ends at physical line 7](evidence/labor-001.html#r7)
- unlinked_transactions: Transaction target entity is outside the declared work-order namespace. Confirm the exact scoped parent/source relationship. Suggested role: Maintenance records owner. [FIX-transactions, CSV record 4, ends at physical line 4](evidence/transactions-001.html#r4)
- unlinked_work_orders: Asset reference is missing or not uniquely present in supplied assets. Confirm the exact scoped parent/source relationship. Suggested role: Maintenance records owner. [FIX-work_orders, CSV record 5, ends at physical line 6](evidence/work_orders-001.html#r5)
- unparsed_date: Confirm the source date and declared format; no locale or chronology is guessed. Suggested role: Maintenance records owner. [FIX-work_orders, CSV record 5, ends at physical line 6](evidence/work_orders-001.html#r5)

## Changes since the previous packet

Changed or disappeared findings need source and receiving review. No prior disposition is inherited; changed basis and omissions remain explicit.

2 added, changed or omitted records; 0 basis changes. Inspect [revision evidence](revision.json) and [previous packet](previous/REPORT.html).

## Asset dossiers

| Scoped asset | Selected orders | Booked hours | Recurring groups |
|---|---:|---|---:|
| [R7 / P-101](assets/ae96f7ec7cdb68055dbec9ba.html) | 2 | 4.5 | 1 |
| [R7 / PARK](assets/c582404000ee9fc8e08e4c5c.html) | 2 | no_rows_supplied | 1 |
| [R8 / P-101](assets/e389fc4ab74650b3b8bcd69d.html) | 1 | 3 | 0 |

## Source coverage and unlinked records

- assets: FIX-assets rev 2; owner role Maintenance records owner; coverage: Authored selected-record excerpt; no absence or installed-state guarantee
- work_orders: FIX-work_orders rev 2; owner role Maintenance records owner; coverage: Authored selected-record excerpt; no absence or installed-state guarantee
- transactions: FIX-transactions rev 2; owner role Maintenance records owner; coverage: Authored selected-record excerpt; no absence or installed-state guarantee
- details: FIX-details rev 2; owner role Maintenance records owner; coverage: Authored selected-record excerpt; no absence or installed-state guarantee
- labor: FIX-labor rev 2; owner role Maintenance records owner; coverage: Authored selected-record excerpt; no absence or installed-state guarantee
