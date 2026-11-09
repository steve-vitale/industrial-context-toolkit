# Publisher definitions inspected for maintenance history

The exact original AMPS development responses remain local under the existing
[acquisition pins](../../data/corpus_pins.json). No original record values or
free-text descriptions are republished in this directory.

| Primary evidence | Identity inspected | Supported meaning / unresolved limit |
|---|---|---|
| [Publisher user guide](https://docs.google.com/document/d/1UwyGGncb6oFMiOfgz73G-iM8Yea9ubz4931hPeBO9YQ/edit), dated 2019-04-04 | TXT export, 15,524 bytes; SHA256 `3d5510cbc4a091f76cddb2e73e5a7963086cd62e4751bc2cb960177c1f7cda21` | Five administrative tables and their joins. Assets include parks/structures and equipment. Recurring planned work exists. Not equipment-failure truth. |
| [Publisher data dictionary](https://docs.google.com/spreadsheets/d/1pDr-BUe4LS7DvATfbOnd8UrV6s77krJgzqdq_gVYWqc/edit) | XLSX export, 405,071 bytes; SHA256 `b59a91a330529f003a631caf6385361a54e7b6eb520bbecea63b474d526c9825` | Read all five tab definitions; important locators below. Export is source evidence, not an authored workbook. |
| [Work-order metadata](https://data.cityofnewyork.us/api/views/8sdw-8vja.json) and the other four existing metadata pins | Exact original metadata hashes retained in the earlier acquisition | EVT_OBJECT -> OBJ_CODE; BOO_EVENT -> EVT_CODE; TRA_TOCODE -> EVT_CODE only in EVNT namespace; TRL_TRANS -> TRA_CODE. |

Dictionary `Labor!D10:M14` establishes an additive hours ledger. Corrections
are additional signed entries, not replacement rows to discard. `J14` defines
`+` as correction and `-` as not correction. `M11` warns that recorded rates
need not equal actual individual pay rates. No productive-wrench-time, payroll
or savings claim follows from recorded ledger hours.

`Transactions!D5:J8` names issue/correction/miscellaneous/receipt/stock-take
classes and approved/cancelled/unfinished status codes. These are transaction
statuses, not work-order completion states. `Transaction Details!D14:M25`
identifies quantity, unit and part-price fields; retain original quantities and
units without calling their sum physical consumption or installed BOM.

`Work Orders!D5:K5` identifies PPM as planned preventative maintenance and IN
as inspection, with several other codes left unexplained. `D29:M29` identifies
the reopened field's purpose but does not define its observed `+`/`-` encoding.
Keep those reopened codes unresolved rather than borrowing labor semantics.
The initial projection does not include the current-status field, so a missing
completion value cannot establish an open/overdue work order.

`Assets!D3:M3` distinguishes asset/system concepts and parent containment;
observed source types outside the documented examples remain explicit codes.
A park/system association does not locate an individual installed component.

All originals and extraction intermediates remain local. Retain NYC Parks/City
of New York attribution and the [publisher terms](https://www.nyc.gov/main/terms-of-use).
Public accessibility supplies no assumed open redistribution license.
