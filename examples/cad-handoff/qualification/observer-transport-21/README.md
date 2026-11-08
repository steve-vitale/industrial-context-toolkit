# Native observation transport: evidence, methods and remaining gates

This folder is exposed infrastructure development for N118. It is not an own-input
CAD tool or a qualified CAD workflow. Use [CAD data exchange](../../data-review/README.md)
or [returned-drawing review](../../receiving-review/README.md) for those jobs. The
[qualification index](../README.md) owns the overall CAD conclusion.

The [original plan](PLAN.md) preceded implementation. Preserve every failed method
and its evidence; a cleanup that exits normally never changes the failed controller.
The strict CAD comparator, value-span patcher, independent byte checks and original
UI19/camera20 packets remain unchanged.

## Follow the evidence in order

| Method | Actual outcome | Evidence and lesson |
|---|---|---|
| Direct Qt observer, two normal attempts | Both fail before a normal reply; each same process later closes normally | [First failure](development-1/NOTE.md), [second failure](development-2/NOTE.md). Installed inherited QFile methods/classes were assumed incorrectly; the first error handler fails too. |
| Installed-binary binding probes | Both close normally; probe1 retains a codec refusal | [Probe1](probes/binding-probe-1/BINDINGS.json), [probe2](probes/binding-probe-2/BINDINGS.json), [plan](PROBE-PLAN.md). QIODevice parent calls and QTextStream decoding work in this binary. Capability evidence is separate from transport acceptance. |
| Python I/O owner with synchronous QProcess waits | Two status replies, then failed typing and first Cancel timeout | [Complete failed bridge](bridge-development-1/NOTE.md), [I/O contract](BRIDGE-PROTOCOL.md), [UI failure plan](UI-FAILURE-PLAN.md). Stop/acknowledge/drain before separate cleanup; avoid blocking the GUI on helper completion. |
| Asynchronous capability probes | First refuses an ambiguous signal; second completes UI work while its helper stays live | [Retained signal failure](probes/async-probe-1/NOTE.md), [successful scheduling probe](probes/async-probe-2/NOTE.md), [prospective plan](ASYNC-PLAN.md). The full installed finished-signal signature is required. |
| Serial event-driven helper bridge | Both normal cases and all 11 intended fault refusals pass receiving | Frozen [method2](BRIDGE-METHODS-2.json), [native observer](async_bridge_observer.js), [campaign packets](bridge-2/README.md). Air/water and template each retain 14 replies, native fields and three exact camera frames. This does not qualify edit/save preservation. |

The Python helper owns physical I/O and reports its actual OS errno, stage and
path. QCAD owns the read-only status/attribute/camera observation. UI controls own
drawing actions. [BRIDGE-PLAN.md](BRIDGE-PLAN.md) documents the ownership change;
unavailable QFile error codes are never invented. A serial invocation chain binds
every exact argument, result, process identity and published reply, including idle
polls. Normal seal and separate failed-run stop are different handshakes.

## Replay the retained findings without native CAD

From the repository root, Python 3.10+ standard library only; no network/accounts:

```sh
python -S examples/cad-handoff/qualification/observer-transport-21/recheck_evidence.py
python -S examples/cad-handoff/qualification/observer-transport-21/recheck_bridge_development.py
python -S examples/cad-handoff/qualification/observer-transport-21/recheck_async.py
python -S examples/cad-handoff/qualification/observer-transport-21/recheck_bridge.py
python -S examples/cad-handoff/qualification/observer-transport-21/test_evidence.py -v
python -S examples/cad-handoff/qualification/observer-transport-21/test_bridge_evidence.py -v
python -S examples/cad-handoff/qualification/observer-transport-21/test_mailbox.py -v
python -S examples/cad-handoff/qualification/observer-transport-21/test_native_io.py -v
python -S examples/cad-handoff/qualification/observer-transport-21/test_ui_settle.py -v
python -S examples/cad-handoff/qualification/observer-transport-21/test_bridge_receiving.py -v
```

Replays check complete hashed archives and the semantic evidence inside them.
Regression controls recompute inventories after meaningful corruption, so a
missing event, lost failure, changed source or jointly false report still refuses.
These are author-run software checks, not independent engineering review.

## Reproduce the approach or extend it

1. Read PLAN, BRIDGE-PLAN/PROTOCOL and ASYNC-PLAN before changing a method. Declare
   the exposed cases and acceptance/fault criteria; retain earlier failures.
2. Check actual installed APIs separately. Freeze implementation, inputs and
   configuration before native execution. The original methods remain in archives
   and the named method manifests; today's source is not a historical source pin.
3. Keep one native process per attempt. Retain its real Qt child PID/start identity,
   controller/native/container outcomes and all partial output. An observation
   timeout does not prove termination or authorize restarting that attempt.
4. Receive the complete packet offline, then challenge its semantics after changing
   outer inventories. Only then freeze a successor or a larger qualification run.

`run_native.py --async-bridge` stages a fresh development job and uses the recorded
local image. The image is not distributed here: a new native run needs a permitted
QCAD package, compatible Linux Docker/AT-SPI lab and a declared image/configuration.
The [lab recipe](../linux-native-7/Dockerfile) explains construction; rebuilding is
a new environment, not proof of the old image hash. Offline receiving needs none
of those prerequisites. Do not describe inability to launch that optional lab as
inability to use the toolkit's own-input CAD comparison/data tools.

## What remains

N118's exposed transport checks and loss controls are complete. Integration/CI
checks remain version-specific. Next freeze the corrected complete edit/save/close/reopen method and evaluate fresh reserved
sources, multiple assets, foreign/literal/encoding fields and revision/conflict
behavior. Historical camera20's read-open cause is not retroactively proved by
new development. Native full-save losses, complete readability and engineering/
company acceptance remain separate findings. No site benefit is inferred.

`observer.js`/`receive.py` retain the known-failing direct-Qt prototype;
`bridge_observer.js` retains the failed synchronous bridge. The active successor
is explicitly named `async_bridge_observer.js`; readers should not mistake all
files in this chronological experiment for supported user-facing alternatives.
