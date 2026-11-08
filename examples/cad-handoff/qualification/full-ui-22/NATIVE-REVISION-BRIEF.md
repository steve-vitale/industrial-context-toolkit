# Keep the original scope when a native CAD return becomes a new source

These are **authored development drawings with actual automated native UI
actions and saved returns**. They are not plant records, a human review or an
engineering release. Both cases complete three Property Editor edits, Save As,
close/reopen, all-field checks and normal native/controller/host exits.

| Receiving observation | CP1251/Cyrillic case | UTF8/literal-brace case |
|---|---|---|
| Requested FV-101 MODEL | `Мотор` | `Assembly {D}` |
| Actual returned FV-101 MODEL | `OTHER-CHOICE` | `OTHER-CHOICE` |
| FV-102 MODEL | Requested value retained | Requested value retained |
| Unrequested FV-102 SERIAL | `UNCHANGED-1` becomes `FIELD-OBSERVED` | Same authored test change |
| Original-to-native strict preservation | **322 differences; failed** | **321 differences; failed** |
| Selected second proposal vs that native return | One MODEL edit; strict pass and independent byte pass | Same |

`FIELD-OBSERVED` is a test string, not an actual field observation. The explicit
second plan selects the originally requested FV-101 MODEL and keeps that SERIAL.
Its preservation pass means **this returned file** is retained except for one
declared value. It does not restore the original drawing's other records or
approve the SERIAL. Against the original request, 322/321 strict differences
still remain. Those counts are drawing-record differences, not changed assets.

| Evidence for the engineer | CP1251 | Literal braces |
|---|---|---|
| Actual return vs original request | [Review](concurrent-review-1/validation-cp1251/original-review/REPORT.md) | [Review](concurrent-review-1/validation-braces/original-review/REPORT.md) |
| Explicit second plan | [Plan](concurrent-review-1/validation-cp1251/second-plan.json) | [Plan](concurrent-review-1/validation-braces/second-plan.json) |
| Selected proposal vs original request | [Review](concurrent-review-1/validation-cp1251/original-v-selected/REPORT.md) | [Review](concurrent-review-1/validation-braces/original-v-selected/REPORT.md) |
| Draft map changes, with exact original/selected sources | [Changes](concurrent-review-1/validation-cp1251/map-changes/changes.md) | [Changes](concurrent-review-1/validation-braces/map-changes/changes.md) |
| Complete original native packet identity and receipt | [Inventory](concurrent-development-1/cp1251-concurrent-edited-1/INVENTORY.json) | [Inventory](concurrent-development-1/braces-concurrent-edited-1/INVENTORY.json) |

The responsible engineer needs to resolve the alternative MODEL and establish
the SERIAL's source and intended scope. The drawing custodian needs to investigate
the native-save preservation findings and confirm the required delivery route.
The manager can coordinate correction/clarification and route the receiving
decision. Named owners, due dates and authorized dispositions remain pending.
No installed register is overwritten; map attributes remain draft CAD references.

Each complete native packet retains 159 helper calls, 79 observations, ten
editable-field checks and ten views/40 images. Twenty actual CLI calls produce
the two original-scope reviews, stale refusals, second proposals and map changes;
their stable results reproduce from the native archives. Six control methods
challenge both real packets after recomputing local inventories, including source/
plan repinning, changed identity, omitted SERIAL commit, foreign editability loss
and hidden controller failure.

The first offline replay and control failures are retained in
`concurrent-validation-1`. The archive stores files; its first replayer omitted
empty protocol directories. The [separately frozen restoration](NATIVE-REVISION-RESTORE-PLAN.md)
reuses the original recheck's directory rule. Original native attempts, files,
freezes and strict criteria remain unchanged. Use the corrected public commands:

```sh
python examples/cad-handoff/qualification/full-ui-22/recheck_native_revisions.py
python examples/cad-handoff/qualification/full-ui-22/test_native_revisions.py -v
python examples/cad-handoff/qualification/full-ui-22/recheck_native_reviews.py --out PRIVATE_NEW_FOLDER/native-review-replay
```

Install the repository's pinned CAD requirements first. These commands launch
no CAD application, models or network requests. The original experimental
`native_revisions.py check` branch retains the empty-directory failure; it is
not the current replay command.

Fresh four-file concurrent receiving has been launched separately; no completion
or pixel result is claimed here. Actual second-revision native receiving,
paper/layout, final-method freezing and fresh reserved transfer remain open.
The [receiving workflow](../../../../docs/DRAWING_HANDOFF.md) describes how to
prepare an accept/return/escalate brief from your own drawing records.
