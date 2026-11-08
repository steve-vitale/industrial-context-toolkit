# Test event-driven helper completion before another bridge run

The eef0788 bridge produced two native status replies, then its controller refused
an immediate filename readback. Later inspection found the exact filename without
retyping. A separately frozen Cancel action timed out. Only after a run-bound stop
marker was acknowledged and no helper remained did a second separately frozen
Cancel complete. The same native process exited0, original controller1/container1.
This is evidence of interference while the synchronous observer runs, not a proven
Qt-internal explanation or a passing bridge. Retain both failed actions and cleanup.

Freeze this plan before implementing the next capability probe. Test actual
QProcess asynchronous signals in the same pinned isolated image. No waitForStarted,
waitForFinished, process restart or new interpretation of CAD data is allowed.
A helper writes its actual PID/parent/UID, then waits for a release file with a
120-second bound. While it is still running, a native timer must continue ticking
and the UI controller must open the empty Open Drawing dialog, type the same
literal filename once, observe exact completion, and cancel without opening CAD.
Only after those UI observations may the controller release the helper. Native
finished must report normal exit0, exact UTF-8 JSON/stdout and stderr, multiple
timer ticks, and an unmodified unnamed document. Signal errors or timeouts retain
the same process and all partial records; they do not trigger another attempt.

Use the bounded text-observation routine already declared in UI-FAILURE-PLAN.md;
retain every observed value and action even on failure. Publish complete source,
configuration, method freeze, console, actual process identity, UI traces and
terminal receipts. Require helper-ready before UI actions, no helper-done before
release, exact native/client report agreement and source/configuration hashes.
Challenge those semantic requirements after recomputing the archive inventory.
The probe is exposed development. It tests scheduling and installed APIs only.

If it passes, freeze a separate event-driven bridge method with one outstanding
helper, no blocking native waits, exact START/END history and the same immutable
I/O protocol, error ownership, stop/seal handshake and normal/fault receiving.
Do not rewrite BRIDGE-METHODS-1.json or the failed bridge. N118 and the complete
native CAD, reserved-transfer, text/asset, readability and revision gates stay open.
