# What the native save changes, and where

These are **exposed diagnostic controls, not CAD qualification**. They follow
the [original protocol](../PROTOCOL.md), [full-save diagnosis](../root-cause-12/README.md)
and [resolved GUI pixel cause](../gui-scene-13/README.md). The original strict
comparator, source-preserving patcher and historical evidence remain intact.

The practical distinction matters: a selected attribute proposal can preserve
every other source byte, while a general native save reconstructs the drawing.
Reading back the desired attributes is insufficient evidence that the rest of
the drawing survived. The new controls demonstrate actual unfamiliar-data loss.

| Question | Observation | Conclusion / remaining boundary |
|---|---|---|
| Does an unspecified export preserve source version? | Default saves write AC1024 on all six sources. Explicit R15/R21/R24 writes each source's actual ACADVER. | Select and verify the version explicitly. It does not solve preservation: original-version saves still have 351, 349, 353, 432, 403 and 424 strict rows. |
| Where do added line types come from? | All 32/33 added literal names already exist in the native document before import. Empty exports contain 252–262 records and 53 line types. | Public document initialization supplies default resources. Named-path associations retain full payload differences; they are not an equivalence proof or permission to remove records. Opaque exporter reconstruction remains only partly explained. |
| Why do otherwise matched processes disagree on 53 resource records? | Two independent processes with testing-only QT_HASH_SEED=0 produce zero strict differences on all six cases. Each differs from the unseeded return in 53 records. | Controlled Qt hash ordering explains this repeatability component in this cohort. Qt documents the fixed seed for testing/debugging; this is not a production setting recommendation or whole-file preservation result. |
| Does used foreign XDATA survive? | Ordered string/double/integer XDATA survives all used cases, through native custom properties, export and fresh import. Asset attributes also survive. | Positive transfer for exactly these tested payloads, not arbitrary vendor data. |
| Does other foreign metadata survive? | The named root-dictionary XRECORD disappears on all 17 valid-integer controls. The unused APPID disappears on all 17; an APPID registered without XDATA is also omitted. | These are real returned-file omissions. Public RObjects do not enumerate all opaque importer state, so absence there does not locate the proprietary implementation's exact loss stage. Do not accept these returns as preserved originals. |
| Was USERI5 lost? | The first authored values 60000..60005 become -5536..-5531 already on import. The 17 corrected controls preserve 6000..6005 and -32768, -1, 0, 1, 32767. | The first probe exceeded the signed 16-bit domain. Retain it as an invalid-input diagnostic, not evidence of loss of valid integers. |

The source-version repeat saves still fail, and every old/new strict report is
retained. Neither stable serialization nor matching selected fields closes the
unresolved header/record payloads, full visual/readability, native UI editability,
fresh reserved-source validation or revision gates. No plant, company or engineering
acceptance is established.

The six source families are public LibreCAD/QCAD adaptations already exposed in
[public validation 11](../public-validation-11/README.md). The payload additions
are authored revisions, not untouched upstream drawings or a new holdout. Their
12 paired and 17 corrected candidates use the existing byte-preserving operation;
the independent byte reconstruction verifies them. Native controls do not edit:
they import/export/close/reopen and then import in a separate process. There are
**63 complete native exports and 63 fresh public-inventory repeats**, plus one
retained incomplete-probe failure; **65 strict reports** re-score offline.

## Reproduce the saved evidence

From the repository root with its ordinary Python requirements installed:

```sh
python examples/cad-handoff/qualification/check_boundaries14.py
python scripts/test_cad_linux_evidence.py
python scripts/test_checkout_contracts.py
```

This receiver checks the bounded archive, every input/method hash, original source
provenance, exact candidate bytes, native selected configuration and terminal states,
complete manifests, actual versions, every captured public property and every saved
strict report. It **does not rerun QCAD**. Frozen methods and pre-execution plans
remain chronological commits; the archive includes raw returns and observations.
Native software, fonts and settings contents are excluded; the selected settings
hash is retained. [INVENTORY.json](INVENTORY.json) binds all raw members;
[SUMMARY.json](SUMMARY.json) is the exact received summary.

Failures are part of the record. The original payload helper was a placeholder
after a PowerShell edit failed, and its controller correctly refused missing jobs
despite native exit zero. A separately frozen successor used the same source data.
The first empty-document analysis improperly required an asset profile; the
generic diagnostic replaced that call without changing the comparator. The first
generic report then included an inspection-library synthesized creation time;
the successor retains original raw header bytes. All first reports and failed
observations remain. See [probe correction](PAYLOAD-PROBE-CORRECTION.md),
[integer correction](INTEGER-PLAN.md) and [receiver correction](RECEIVER-CORRECTION.md).

## Primary method sources

QCAD's pinned [RDocument initialization](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/RDocument.cpp)
creates default document resources. Its [public object API](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/RObject.h)
exposes custom properties, not a complete opaque DXF store. Public core code is
not the proprietary OpenDesign importer/exporter implementation or proof of its build.
Qt 5.14.2's [qhash.cpp](https://github.com/qt/qtbase/blob/v5.14.2/src/corelib/tools/qhash.cpp)
documents the environment seed and testing-only intent. Autodesk's
[header reference](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-DXF/files/GUID-A85E8E67-27CD-4C59-BE61-4DC9FADBE74A.htm)
assigns USERI1..5 group 70; the [value-type reference](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-DXF/files/GUID-2553CF98-44F6-4828-82DD-FE3BC7448113.htm)
identifies its 16-bit domain. Native controls, rather than source inference alone,
establish the bounded observed results above.
