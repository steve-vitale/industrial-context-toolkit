# Development evidence and retained failures

The common-basis prototype passes 37 focused software test methods on exposed
fictional records. [The run receipt](development/run.json) pins the executed
production code, tests, literal source key and runner. It records the actual
17.56-second software run on this machine; preparation/review and human time are
not measured. The [manifest](development/MANIFEST.json) binds the complete retained
run archive. It contains 991 files: actual commands, stdout/stderr and delivered
packets, including the three-revision/edit/reimport/reopen route and deliberately
corrupted controls. Repetitions and copied history are not independent examples.

`development/example-initial/` is a viewing excerpt, not a complete packet. The
archive contains its complete original sources and mappings. For a fresh run:

```sh
python -B -S examples/map-component-cycle/reproduce.py --out out/my-context-development
python -B -S examples/map-component-cycle/replay_history.py --out out/my-context-history
```

## Failures that changed the implementation

The [initial retained code and tests](history/context-core-development-01/run.json)
ran 21 methods and failed eight assertions in seven defect cases:

- Decimal underflow and excessive float precision silently changed source numbers.
- Withdrawal of an intermediate derived source did not invalidate its descendants.
- A root-source revision did not change a derived field's evidence fingerprint.
- Entity scope was not checked against the basis namespace.
- A quote could match supplied bytes that differed from the declared source hash.
- A selected-item draft exposed another item's editorial note.
- A readable outline omitted unknown relation direction.

The fixes require lossless decimal roundtrip or refusal, transitive lineage
activity/fingerprints, namespace containment and raw-byte quotation binding.
Selected derived views exclude other-item annotations; the private basis still
retains them. Readable relations carry direction and source revision. All seven
defect tests now pass. The earlier independent agent inspection found these
defects; it was an early code review, not an exact final-output acceptance.

The first 29-method passing replay is retained separately under
`history/development-29-methods/`. The next review found four additional faults:
relationship corrections used empty claim-field dependencies; correction records
could carry invented lineage/basis; open orders could imply a physical installation;
and readable outlines hid inactive relationships. The retained pre-fix run in
`history/correction-physical-lineage-01/` fails eight assertions across four cases.
Corrections now retain claim/relationship kind, content and evidence fingerprints,
an immutable proposal identity and the real historical pre-edit basis. Open item
IDs stay proposals on their maintenance record; they create no physical item or
installation. Inactive links retain source/revision and INACTIVE in the outline.

A further recheck found that a verified helper-created annotation disappeared
from the current view after an ordinary CLI edit. Its pre-fix method and failing
case are retained in `history/helper-annotation-retention-01/`. Intake, edit and
reimport now carry every verified annotation, including those hidden by selection,
into the private retained corrections. Actual CLI tests cover the API-created
packet, subsequent edit, reimport and selection/regeneration. The proposal stays
unreviewed; copying it does not add source support.

The [next retained failure](history/context-packet-order-01/run.json) exercised
the actual command in a new process. Preparation refused because the saved JSON
mapping sorted keys, while intake used mapping insertion order to emit claims.
The source and engineering facts were unchanged, but byte/semantic replay was
not stable. Intake now iterates the original CSV columns, independent of mapping
serialization. The same fresh-process test passes. Neither the source key nor
the required output was changed to accommodate the defect.
All four retained failed methods reproduce their intended assertion failures in
separate temporary fixture workspaces; the history runner leaves current code
untouched. This check does not turn those historical failures into acceptance.

An earlier unit assertion also assumed insertion order for equal quantities;
the tool sorts stable occurrence IDs. It was corrected to compare the same typed
value/unit alternatives without imposing insertion order. The original console
output was not archived separately. This is a checker correction, not a changed
engineering key or a measured production improvement.

Additional controls check tampered originals, rehashed wrong derived facts,
rehashed wrong impact reports, unaccounted artifacts, delivery path escapes,
changed delivery bytes, existing-output protection and receiving size refusal.
Each requires its intended refusal, alongside intact positive paths.

## Broader regressions

`development/legacy-full-run/` retains the actual full cached-data run: 105/105
test programs passed, zero failed, 23 individual cases skipped and three platform
notices. Public TE caches were staged from existing local files only after their
pinned hashes matched. No gateway or plant connection was made; the suite includes
a temporary loopback OPC UA replay. Skips/notices are printed in the retained log.

That broad run started before the later correction fixes; its new context tests
covered the earlier prototype. The final 37-method focused replay binds the updated
core and delivered artifacts. Treat the broad run as legacy regression evidence,
not an exact final-candidate CI or complete release pass. Final clean-clone/CI and
independent release acceptance remain required.

## Current limits

This is development, not a frozen generalization result. The public and second
CSV-dialect transfers have not run. Inputs and keys are author-known. The typed
source controls include direct helper tests; complete typed product readback is
not established. The three-revision maintenance route uses ordinary exports;
the narrative relationships are supplied interpretation checked against a quote,
not an automated document comprehension result.

The complete selected-scope delivery, native generator bridge, existing map/model
adapters, identity crosswalk/replacement route, browser path, measured workload,
clean-clone release and actual ChangePilot persistence/auth/readback/export are
unfinished. The [31-case acceptance file](ACCEPTANCE.json) remains incomplete;
these development passes do not close product or whole-goal cases. Existing CAD
preservation/paper failures and unrun human/company trials remain unchanged.
