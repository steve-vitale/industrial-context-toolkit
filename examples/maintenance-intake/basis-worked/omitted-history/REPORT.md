# Maintenance record review

Scope: SIM/P1; units U1, U2; as of 2026-11-06.

0 detected disagreements; 1 total review queue entries. Equipment rows: 2; work-order rows: 1.

Draft comparison of the supplied exports. Absence of a finding does not establish complete coverage, installed state or accepted corrections.

## Comparison basis needs review

- Recorded basis and export changes, not acceptance, physical change or proof of complete source coverage. Review disappeared findings against this basis.
- Changed method files: maintenance_intake.py. A changed result can reflect changed software; inspect before treating it as a source correction.
- equipment (EQ-EXPORT): revision 1 to 1; 2 to 2 rows; 0 added, 0 removed, 0 changed normalized records.
- work_orders (WO-EXPORT): revision 1 to 2-omitted-history; 2 to 1 rows; 0 added, 1 removed, 0 changed normalized records.
- Missing from the supplied export: P1/U1/P-101/WO-801, prior original CSV record 2. Omission is not physical removal or an accepted correction.

See comparison-basis.json for exact before/after values, source rows and mappings.

## Review boundaries and next steps

- Review queue includes scope ambiguities and other checks: map/queues/review_queue.csv.
- No field inspection, engineering approval, MOC determination, PM validation or company-system write/readback has occurred.
- Open work orders (blank closed_on) supply history only, not evidence of installation. Latest dated closed order per attribute is the comparison basis; owners must confirm its meaning.
- Only mapped fields are interpreted; ignored columns remain in originals. Text is trimmed in prepared CSVs; exact original bytes and CSV-record/physical-line locators remain.
- Proposed actions need a named person, due date and accepted source readback. No action has been assigned or completed by this tool.
- Compared with verified previous packet: 0 new, 0 still detected, 1 no longer detected. See changes.md and findings.json; disappearance is not acceptance.
- equipment: EQ-EXPORT rev 1; owner Maintenance; declared coverage: Selected U1/U2 fictional equipment positions
- equipment attributes absent in some/all rows (not compared where unavailable): manufacturer, size.
- work_orders: WO-EXPORT rev 2-omitted-history; owner Maintenance; declared coverage: Selected U1/U2 fictional replacement history; open orders retained
- Coverage gap: work_orders has no rows for declared units U2. No conclusions there.
- work_orders attributes absent in some/all rows (not compared where unavailable): manufacturer, size.

Open REPORT.html offline; proposed-actions.csv is a draft review form. Retain this whole folder and receipt.json for the next revision.
