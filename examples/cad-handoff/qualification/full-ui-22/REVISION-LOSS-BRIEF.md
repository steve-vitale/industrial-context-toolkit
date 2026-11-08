# A return can fix one request and still need a decision

**Fictional rehearsal, not a released drawing.** Both exposed two-asset cases
complete the [frozen revision/loss exercise](REVISION-LOSS-PLAN.md). The
[result](revision-loss-1/RESULT.json) retains 32 actual CLI calls and their packets.
It demonstrates software handling of supplied values, not interpretation of
markups, a human's native CAD edit, or installed equipment information.

An engineer requested MODEL changes on FV-101 and FV-102. The simulated return
implements FV-102's request, gives FV-101 a different MODEL, and changes FV-102's
SERIAL. These are three separate observations. A supported request does not
authorize the other changes.

| Item | Returned evidence | Engineering action | Manager's decision to arrange |
|---|---|---|---|
| FV-101 MODEL | `OTHER-CHOICE`, different from the requested value | Clarify the alternative or request correction; keep both exact versions | Confirm who owns the technical selection |
| FV-102 MODEL | Matches the request in the supplied records | Retain the source-bound comparison | Keep the separate open findings visible |
| FV-102 SERIAL | `UNCHANGED-1` becomes `FIELD-OBSERVED` without an original request | Obtain the reason and authoritative evidence for the new serial | Decide who must reconcile the record before release |

`FIELD-OBSERVED` is an authored test string. No field observation has taken place.
Named owners, due dates and authorized dispositions remain **unassigned/pending**.

The explicit second plan selects the originally requested FV-101 MODEL and
preserves the concurrent SERIAL. Its exact-span candidate passes zero unexpected
strict differences and independent byte reconstruction **against that concurrent
source and second plan**. Comparison with the original plan still reports the
SERIAL as one unexpected difference. A new source hash or a clean second-plan
comparison does not erase the original scope question.

| Evidence | CP1251/Cyrillic case | UTF8/literal-brace case |
|---|---|---|
| Original requests vs simulated return: two unexpected differences | [Readable report](revision-loss-1/validation-cp1251/review-concurrent/REPORT.md) | [Readable report](revision-loss-1/validation-braces/review-concurrent/REPORT.md) |
| Explicit second plan | [Plan](revision-loss-1/validation-cp1251/second-plan.json) | [Plan](revision-loss-1/validation-braces/second-plan.json) |
| Selected drawing vs original requests: SERIAL still unexpected | [Strict comparison](revision-loss-1/validation-cp1251/original-v-selected.json) | [Strict comparison](revision-loss-1/validation-braces/original-v-selected.json) |
| Draft map revision, with both exact drawing sources retained | [Changes](revision-loss-1/validation-cp1251/map-changes/changes.md) | [Changes](revision-loss-1/validation-braces/map-changes/changes.md) |

Both cases refuse stale hashes, stale before values, identity edits, duplicate
targets, newline values, ambiguous target serialization and output collisions.
Each of twelve single planted losses produces exactly one strict difference and
an independent byte-check refusal: geometry, layer, style, foreign attribute,
foreign XDATA and block geometry, separately in each case. The unchanged first
candidate is the positive baseline. These checks detect the planted changes;
they do not determine whether a real engineering change is appropriate.

The projected map retains both assets, all supplied fields, literal foreign text
and exact source files as **draft CAD references**. It infers no piping and
updates no installed equipment register. The engineer still needs the original
instruction/baseline review, complete appearance/paper/editability checks and the
organization's receiving decision described in [drawing handoff](../../../../docs/DRAWING_HANDOFF.md).
Native full-save preservation remains failed; paper/layout, actual native
concurrent-manual-edit receiving and fresh reserved qualification remain open.

To reproduce with the repository's CAD requirements installed, use a new folder:

```sh
python examples/cad-handoff/qualification/full-ui-22/revision_losses.py --out /your/new/rehearsal-folder --expect examples/cad-handoff/qualification/full-ui-22/revision-loss-1/RESULT.json
```

Every CLI command, exit and output is retained under `commands/`. The raw drawing
mutations and both check results are under `losses/`; no CAD application, model
call, network access or plant connection is required.
