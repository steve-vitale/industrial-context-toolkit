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
asset-1 label view with the nearby other labels present. Complete visual review,
matched no-edit/edited/fresh-process receiving, paper/layout checks, exact pixel
comparisons, revisions/conflicts, planted CAD losses and final-method reserved
validation remain unfinished. The historical authored paper-layout issue is not
waived. No operator, independent engineering reviewer or plant data is involved.

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
