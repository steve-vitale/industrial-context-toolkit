# Complete native procedure: exposed development

This is development toward the [original CAD exchange protocol](../PROTOCOL.md),
with its [plan](PLAN.md), declared [exposed inputs](DEVELOPMENT-INPUTS.json),
[first method](METHODS-1.json) and [prepared cases/configuration](PREPARATION-1.json)
frozen before native execution. No fresh reserved cases have been admitted.

The first complete edited run on the already exposed CP1251 fixture opens two
identified assets, verifies every attribute, changes both Cyrillic MODEL values
through actual native Property Editor controls, saves, closes/reopens, checks both
assets again, captures fixed model frames, seals the observation history and
closes the application normally. Both edits commit; foreign literal fields remain
editable and retain their values. Native/controller/container/host exits are zero.

The [retained packet](development-1/cp1251-edited-1/INVENTORY.json) has 5,952 files,
including 2,470 helper calls, 73 native observations, eight editable-field checks
and 40 images across ten views. The returned DXF still has **322 unexpected strict
differences** (version, header and 320 entity rows). They remain a failed native
preservation route; successful UI operation does not qualify the whole exchange.
The source-preserving candidate separately passes zero unexpected decoded
differences and the independent byte-span check for both declared cases.

The matched CP1251 no-edit run has 61 observations, four editable-field checks,
ten views/40 images and the same 322 source-to-return strict count. The separate
UTF8/literal-brace edited run completes both edits, 73 observations, eight field
checks and ten views/40 images, retaining 321 strict differences. Its matched
no-edit run also completes, with 61 observations, four field checks and ten
views/40 images; 321 strict differences remain. All four
original attempts are listed in [the retained identities](RETAINED-ATTEMPTS-1.json)
and recheck offline. The no-edit receiver's first empty-plan call is retained as
a refusal; its successor uses the original comparator's existing no-plan API.

The matched native returns have 53 strict entity differences between them. The
[reference-aware diagnosis](analysis/correspondence-analysis-1/SUMMARY.json),
checked independently by the existing pair checker, establishes closed exact
decoded correspondences for all 53: 50 linetype and three style records are
allocated different handles. This does not waive any strict row. Only 14 records
close in the original-to-return comparison; 79 original and 239 returned records
remain unpaired, with version/header differences also unresolved.

The same unchanged diagnostic and independent pair checker applied to the
[literal-brace returns](analysis/braces-pair-1/reports/SUMMARY.json) close all 52
paired strict rows: 49 linetypes and three styles have different handle allocation.
The original-to-return diagnosis closes only 18 record pairs, leaving 75 original
and 235 returned records unpaired; all 321 strict differences remain failures.
`check_braces_pair.py` reconstructs this diagnosis from the committed original and
complete native archives, without relying on the original scratch paths.

The first offline receiver refused semantic JSON object insertion order. Its
original source, exit and trace remain in the packet. The correction compares
semantic maps with sorted keys; exact transport wire bytes and ordered arrays
remain exact. An initial loss-control invocation also refused due to a local
module-name collision; its retained log is separate from the passing successor.

## Recheck without CAD

With the pinned requirements installed, from the repository root:

```sh
python examples/cad-handoff/qualification/full-ui-22/recheck.py
python examples/cad-handoff/qualification/full-ui-22/test_contract.py -v
python examples/cad-handoff/qualification/full-ui-22/test_receiving.py -v
python examples/cad-handoff/qualification/full-ui-22/test_pixels.py -v
python examples/cad-handoff/qualification/full-ui-22/test_evidence.py -v
python examples/cad-handoff/qualification/full-ui-22/check_failed.py
python examples/cad-handoff/qualification/full-ui-22/test_waiting.py -v
python examples/cad-handoff/qualification/full-ui-22/waiting_probe_evidence.py check
python examples/cad-handoff/qualification/full-ui-22/check_braces_pair.py
python examples/cad-handoff/qualification/full-ui-22/recheck_waiting.py
```

The actual-packet controls change evidence and recompute its inventory before
checking semantic refusal: wrong asset, incomplete Unicode entry, absent commit,
foreign-field editability, extra selection, missing observations/captures/images,
unbound camera, replaced return, repinned source/method and hidden failed history.
Twelve methods pass; six inventory/selection and four semantic/input methods
are separate scopes. Three pixel controls reject no-edit pixel loss, a change
between separate asset-label regions and a change on an exclusive mask edge.
No new native launch, model call or download is used.

The initial visual inspection shows the expected Cyrillic change in the rotated
asset-1 label view with the nearby other labels present. The completed waiting
receiver below now adds full model receiving, exact pixel comparisons and bound
same-agent model-view observations. Paper/layout, revisions/conflicts, planted
CAD losses and final-method reserved validation remain unfinished. The historical
authored paper-layout issue is not waived. No operator, independent engineering
reviewer or plant data is involved.

For the engineering job this evidence supports, use [drawing receiving](../../../../docs/DRAWING_HANDOFF.md).
That workflow makes requested changes and unresolved preservation findings useful
to a reviewer while the separate software qualification remains open.

## Fresh receiving exposed an idle-call limit

Both original fresh-process receivers failed on helper invocation 4097. The
frozen helper admits 4096 invocations; idle polls consumed 3,883 calls for CP1251
and 3,871 for literal braces. CP1251 captured 18 of 20 views; the brace case
captured 20 but failed before completion. Neither has a normal receiving receipt
or completed pixel verdict. These are observed transport refusals, not evidence
of a CAD-file defect or a completed drawing check.

The complete [CP1251](failed-development-1/cp1251-receiving-1/RESULT.json) and
[brace](failed-development-1/braces-receiving-1/RESULT.json) failure packets retain
every invocation, original error, client refusal, host outcome and separate
same-process cleanup. The original last error has null run/call IDs and no
predecessor hash because admission refused before those fields were initialized;
those records are preserved. The checker audits the successful 4096-call prefix
with the original transport auditor and checks the final rejection separately.
Four altered-evidence controls per packet reject invented completion, hidden
controller failure and changed final call/error records. The first archive
packager's file-count refusal is retained too; its successor retains both complete
mailbox snapshots under the separately declared failure format.

The [waiting-helper plan](WAITING-HELPER-PLAN.md) addresses idle polling without
raising the original invocation or wire bounds. One asynchronous child waits for
the next request or cleanup stop. Six subprocess controls pass, including a wait
beyond five seconds, malformed/run/sequence errors, changed prior request bytes
and a reply-publication collision. The first test's event-count arithmetic error
is retained separately from its passing successor.

The [first native probe](waiting-probes/probe-1/RESULT.json) retains a recorder
field-name collision and its cleanup. The [corrected probe](waiting-probes/probe-2/RESULT.json)
completes: the same child remains live during native filename typing/cancellation
for 43.986 seconds, then serves the request; the next poll acknowledges stop.
Both complete transport histories recheck with six invocations, two requests and
zero idle events. This establishes this observed waiting lifecycle, not full
receiving, paper/layout preservation or CAD qualification. The complete waiting
receiving method is frozen in [WAITING-METHODS-3.json](WAITING-METHODS-3.json);
fresh reserved cases remain unadmitted.

## Complete waiting-method model receiving

Both [CP1251](waiting-development-1/cp1251-receiving-wait-1/RESULT.json) and
[literal-brace](waiting-development-1/braces-receiving-wait-1/RESULT.json) runs
complete with native/controller/container/host exits zero. Each opens the source,
matched no-edit return, edited return and source-preserving candidate; retains
115 observations, eight editable-field checks and 20 views/80 images; seals its
complete history and closes normally. There are 231 helper calls, with idle time
no longer spending invocation identities. Original strict/byte gates remain.

The first offline receipt exposes another recorder bug: `0*.json` omits host
commands after 0999. Its source/trace stay in the CP1251 packet. The
[separately planned correction](HOST-HISTORY-PLAN.md) receives canonical contiguous
numeric history beyond 999 and 9999, rejecting gaps, aliases and extra records.
Both complete original attempts then receive without a native restart. The
[second analysis freeze](WAITING-ANALYSIS-2.json) changes host enumeration only;
the native method and original exact camera/mask recipe remain intact.

All 30 [model-frame comparisons](analysis/waiting-pixels-1) have zero changed pixels
outside their predeclared regions. Source/no-edit has no allowed region. The
candidate and native edited view are also pixel-identical for every fixed frame;
20 exact identities bind the corresponding versions. The
[visual record](analysis/waiting-visual-1/OBSERVATIONS.json) records actual agent
inspection of all 20 source/candidate overview, asset and label views. Detail
labels show the intended Cyrillic and brace changes with other values retained;
existing rotation/line intersections remain, and overview labels are too small
for value verification. Pixel identity supports equivalence of these captured
views, not correctness of the original drafting or engineering function.

`recheck_waiting.py` reopens the complete archives, binds their returns to the
original native packets, re-runs receiving and all pixel comparisons, and checks
the retained difference images and inspected-view hashes. No CAD application,
network or model call is needed. These are exposed model-view development results.
Paper/layout receiving, complete revision/conflict and planted-loss work, final
method freezing and fresh reserved transfer remain open. Native full-save
preservation still fails at 322/321 differences; visual equality does not waive it.

## Multi-asset revision and planted losses

The [revision decision brief](REVISION-LOSS-BRIEF.md) adds a complete exposed
software rehearsal on both sources: original proposal, simulated concurrent
return, stale refusals, explicit second plan and draft map revision. Thirty-two
actual CLI calls reproduce; each return retains two separate findings, and the
selected result still reports the unrequested SERIAL against the original plan.
Twelve single raw planted losses are detected by both unchanged strict and
independent byte checks. Seven admission/refusal conditions per case include
output collision and ambiguous target serialization. Full commands, returned
files and exact control mutations are retained in [revision-loss-1](revision-loss-1/RESULT.json).

This fills the exposed software branch/loss exercise. The concurrent branch was
authored by the patcher, so actual native manual-edit/revision receiving remains
open, alongside paper/layout, final-method freezing and fresh reserved transfer.
It supplies no installed-state or engineering acceptance.

The [paper-receiving design notes](PAPER-RECEIVING-NOTES.md) bind the next paper
investigation to a retained native layout-control tree and pinned public source.
Print Preview may mutate document settings; its entry cannot silently fill a
read-only paper-view gate. No new paper probe is claimed by those notes.
