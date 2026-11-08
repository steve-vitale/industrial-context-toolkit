# Locate header changes at the native boundary

The imported header and the native dimension style are separate stores in this
API route. Both tested writers use the style when saving, replacing several
imported header values. **48 matched controls on all six exposed sources** establish
that direction: a style-only DIMASZ=9.875 is written; a known-header-only change to
9.875 is overwritten by the original style. An unrelated USERI5=1234 survives.
Every recorded before/after-operation inventory differs only in its intended cell.
The controls use public setters, not a native UI edit or an engineering acceptance.

These findings concern the exact low-level import/export method below, not every
interactive CAD application's file-open workflow. A different caller may synchronize
the stores. No claim about the proprietary implementation's source identity follows.

| Evidence | Result | What remains |
|---|---|---|
| Original observation cohort | 26 declared jobs, 25 exports and 25 fresh imports; one retained hydraulic symbol-name failure | 6 strict differences, 17 original asset-profile refusals and 2 predeclared empty/unprofiled controls; no strict pass |
| Expanded fresh inventories | 17 of 25 repeat exactly; 8 differ in 46 plot/layout value leaves | These are failed repeats, not waived fields. Earlier inventories did not include these getters. |
| Dimensional intervention | 48 exports, 48 fresh inventory repeats, 48 exact single-cell operations and the predicted direction in all 48 raw headers | 24 strict differences and 24 asset-profile refusals; neither writer preserves the full source |
| Paper/header recording | Every source/returned HEADER byte and every changed non-save-metadata decoded header value is retained | Other paper limits, default additions, resources and unassigned payload causes remain open |

The frozen observer records all **157 public known variables**, **22 dimension
variants**, **24 layout getters**, ordinary document variables, object IDs/handles,
names, custom properties and attribute parents. It distinguishes undefined values,
numbers, booleans, vectors and colors. This is a defined public inventory, not a
complete geometry or opaque-payload model. Only set traversal order is sorted for
inventory receiving; the original strict comparator and raw bytes are unchanged.

The eight failed repeats all use dxflib for receiving, including its empty control.
Differences include margins, paper units and plot/scale types. Their exact paths
and before/after values are in [SUMMARY.json](SUMMARY.json), not collapsed to a
count. The pinned public [RLayout constructors](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/RLayout.cpp)
initialize the tab order but leave primitive plot members without initializers;
the [header](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/RLayout.h)
declares those members. This is a concrete source lead consistent with the observed
unreliable fields. It does not prove the installed build's internal cause; a direct
initialization/receiving control remains to be run. The failures stay unresolved.

The separate dimensional values and settings-derived defaults are visible in
[RDimStyleData](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/RDimStyleData.cpp),
[RDimStyle](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/RDimStyle.cpp)
and [RDocumentVariables](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/RDocumentVariables.cpp).
Primary URLs, byte lengths and hashes are retained. Actual native interventions,
rather than source inference alone, establish the tested direction of control.

## Reproduce the evidence offline

```sh
python examples/cad-handoff/qualification/check_headers16.py
python scripts/test_cad_linux_evidence.py
python scripts/test_checkout_contracts.py
```

The receiver launches no CAD, model, account or network request. It verifies every
frozen input, selected settings, image, resource limits, terminal status, manifest,
raw header, complete job/failure coverage and all 74 reports. Large raw logs are
bounded chunks reassembled only after byte/hash/path checks. Native software,
fonts and settings contents are excluded; settings hashes and source notices stay.
The six source bytes match save-boundaries-14 exactly. These are exposed adapted
public drawings, not a new holdout or plant data.

Failures remain. Docker was stopped before the first launch; its failure is
retained and no native run was restarted on a timeout. The first analysis had a
syntax error. Its corrected form then refused fresh inventory differences. Both
exact sources and actual failures remain. The descriptive successor reports all
eight failed repeats and their 46 leaves; it does not turn them into passes.
Raw zero creation-time values are retained, avoiding an inspection-library current
time substitution. The dimension batch's successful coverage is labelled
diagnostic_coverage_only, not CAD preservation.

Full readable receiving, reserved-source native UI/editability/revision qualification,
remaining payload causes and company/engineering acceptance are still open. The
source-preserving value-edit route and all prior native-save failures remain intact.
