# Native observer transport: failed attempts and installed capability evidence

This is exposed development for N118. **No corrected transport or CAD workflow
is qualified here.** The two normal transport attempts failed before a normal
reply. Their original methods, console, input and process evidence remain in
[development-1](development-1/NOTE.md) and [development-2](development-2/NOTE.md).
The same actual native applications were inspected and closed normally through
separate cleanup records; none was restarted or repaired in place.

The [acceptance plan](PLAN.md) was committed `ca96ca0` before implementation.
The first implementation `a720dcf` calls inherited QFile APIs that this installed
QtScript binding does not expose. Its error handler also fails. The `e395618`
successor preserves a complete console fallback and the client refuses it, but
the installed binary has no QFileDevice class. Both are failed normal attempts,
with controller1/native0/container1 exits. No drawing was opened or saved.

The separately [planned probes](PROBE-PLAN.md), frozen `a493c4f` and `01258ba`,
inventory actual capabilities. Both complete controller/native/container0, but
the first retains a codec overload refusal. The second verifies actual Python
process completion and exact UTF-8 stdout/stderr decoding through QTextStream.
Its other checks confirm missing inherited methods/classes, working QIODevice
parent size/errorString calls and NewOnly collision refusal. Probe completion is
not a normal transport pass; inspect the retained checks and failed predecessor.

The exact native reports are readable in [probe1](probes/binding-probe-1/BINDINGS.json)
and [probe2](probes/binding-probe-2/BINDINGS.json). Their adjacent hashed archives
retain all actual inputs, methods, UI actions, console, raw collision file,
controller and container receipts. Both failed-attempt archives are complete too.
Recheck all four outcomes offline, then challenge source/method changes, lost
failure evidence, promoted exits and matching but false report projections:

```sh
python -S examples/cad-handoff/qualification/observer-transport-21/recheck_evidence.py
python -S examples/cad-handoff/qualification/observer-transport-21/test_evidence.py -v
```

The five evidence regression methods pass locally without skips; they directly
challenge semantic receiving after bypassing the outer archive inventory. This
is exposed software validation, not an independent observer or engineering review.

[BRIDGE-PLAN.md](BRIDGE-PLAN.md) declares the next method before implementation:
let a pinned local Python helper own physical mailbox I/O and report its actual
OS errors, while QCAD produces read-only native observations through verified
QProcess/stream APIs. The existing strict comparator, original UI19/camera20
packets and acceptance criteria for CAD preservation are unchanged.

`mailbox.py`, `observer.js`, `workflow.py` and `receive.py` are development
prototypes. The direct-Qt observer is known to fail; `receive.py` is an unexercised
receiver prototype awaiting a complete method freeze and actual normal packet.
Do not use it as a qualification claim or replace historical evidence with it.
The eleven standard-library `test_mailbox.py` controls check software wire,
collision, history and refusal behavior, independently of native execution:

```sh
python -S examples/cad-handoff/qualification/observer-transport-21/test_mailbox.py -v
```

Those tests passed locally without skips. Native normal/fault receiving, helper
implementation, broader asset/text handling, reserved transfer, full UI/save
preservation, complete readability and revision/conflict gates remain unfinished.
Company and engineering acceptance are not inferred from these experiments.
