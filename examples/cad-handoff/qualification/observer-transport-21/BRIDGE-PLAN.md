# Prospective successor: give file I/O an observed, accountable owner

The first two direct-Qt normal attempts failed. The two retained installed-binary
probes establish which APIs are actually present: QFile lacks inherited size,
error, errorString and flush; QFileDevice is absent. QIODevice parent size and
errorString work, and the NewOnly numeric flag refuses a collision. The first
probe's codec name call refused; the second verifies QProcess completion and
exact UTF-8 stdout/stderr decoding through QTextStream, including `µ valve` and
the helper's actual UID1001. Both probes close normally. None qualifies transport.

Freeze this prospective design before implementing or running the successor.
Keep PLAN.md's identity, sequencing, immutability, complete history, fail-stop,
source/method binding, actual native process and all normal/fault requirements.
The original requirement to record a QFile numeric error cannot be implemented
through this installed binding. The replacement gives the file operation to a
pinned Python helper and requires its actual OS errno, message, path and stage,
with that ownership explicit. Do not substitute a guessed Qt error code or treat
the two failed direct-Qt attempts as passing this revised procedure.

## Ownership and protocol

- QCAD continues to produce every status/attribute/camera observation through the
  same read-only payload. Actual UI controls open/select/edit/save/close drawings.
  No helper command interprets a drawing, edits an entity or resaves geometry.
- A literal `/usr/bin/python3 /work/native_io.py` command, with structured argument
  data and no shell, owns mailbox file operations. QProcess and QTextStream are
  the actual observed APIs. This is local to the pinned isolated container; no
  new network service, plant connection or credential is introduced.
- The helper admits only initialization, next-request polling and reply
  publication at the fixed private mailbox. No arbitrary path/read/write/command
  operation comes from a request. It returns one bounded ASCII-escaped JSON
  envelope; Qt decoding reconstructs the exact original Unicode values.
- Initialization reads/validates the frozen run configuration. Polling checks
  the exact prior published request hashes, inventory and next contiguous wire
  message. Publishing binds the exact same wire text and native observation to
  one numbered reply. Closed/fsynced exclusive staging plus Linux no-replace
  hard-link publication prevents replacement; staging originals stay retained.
- Every helper invocation has a unique monotonic call ID. Keep exact operation
  input/result, hash bindings, owner PID and actual Qt parent PID. Record a
  complete append-only invocation history, including idle polls. Missing/changed
  events or native call records refuse receiving; do not rely on a latest-state
  file to prove coverage. Requests, replies, errors and invocation records have
  separate staging areas so a reply-write fault does not suppress its error.
- A helper operation failure records actual exception type, errno/message,
  stage/path, sequence and request wire when available. If error/history writing
  also fails, return and print the complete original and publication errors on
  the retained native console. Every such run remains failed. No recursive error
  retry, anonymous overwrite or successful reply is allowed after a fatal error.
- A process launch/exit/decode failure belongs to QProcess; retain its actual
  status/error, output and native console. An observation timeout does not prove
  termination. Retain the same QCAD and any still-live helper handle for inspection;
  do not restart either solely because an observation deadline expired.
- Bound request, helper argument and response sizes explicitly, before launching
  or publishing. Refuse oversized data; never truncate an observation or quietly
  omit attributes. This is serial development infrastructure, not a hostile-writer
  lock, power-loss durability guarantee or accepted company transport.

## Execution and receiving gates

Freeze complete successor source/method/configuration and the exact exposed inputs
before execution. Start with normal air/water and template source fields/frames,
then the same eleven PLAN.md fault profiles. Missing-reply injection may pause
the actual Qt child, retaining PID/start identity; the client must stop on its
deadline. Do not ask the paused native UI for a failure screenshot: record that
controlled unavailability, then separately resume/close the same process normally.
Target the actual Qt child, not the `/opt/qcad/qcad` shell wrapper.

Keep each original attempt/controller failure separate from its subsequent UI
cleanup. Receive complete exported mailbox, helper history, native/client call
bindings, console, staged methods, sources and actual terminal records. Delete
an error/history record, remove or add a reply, change source/method/identity/wire,
or recompute an outer archive inventory after a semantic fault: receiving must
still refuse. Native error controls need their detailed original error or the
explicitly expected publication fallback; a green process exit is insufficient.

Only after those actual native and offline checks can N118 be completed. Then
freeze the corrected complete CAD UI method and evaluate fresh reserved sources,
multiple assets, foreign/literal/encoding fields and revision/conflict behavior.
The historical camera20 read failure, native full-save strict losses, clipping,
human readability and engineering/company acceptance remain distinct findings.
