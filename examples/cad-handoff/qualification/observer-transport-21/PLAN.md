# Immutable native observation transport — prospective development plan

2026-11-08. N118 follows the retained camera20 template request-open failure.
This is exposed infrastructure development, not reserved CAD validation. Preserve
the old observer, exact packets, strict refusal and diagnostic result unchanged.
The old error proves a QFile open failed; it cannot establish the cause or total
error count because earlier anonymous errors could overwrite the same path.

## Requirements before implementation or execution

Use a private Linux filesystem inside the existing isolated QCAD container for
the mailbox. Keep the pinned QCAD/Qt image, user, configuration, no-network policy
and actual AT-SPI UI control. Drawings remain exact staged evidence. No native
process is restarted after an observation timeout or failed control.

1. Give each run a random identity and versioned bounded request envelope. Each
   sequence has one numbered request and one numbered reply. Publish requests
   exclusively from closed/flushed temporary files; never replace a published
   request. Require contiguous sequence, exact run identity and an admitted body.
2. The Qt observer reads the complete request and returns its exact ASCII wire
   text, not just a reconstructed object. The client and offline receiver bind
   that text to the original bytes and the intended request. Retain non-ASCII
   drawing values as UTF-8 responses; request text uses JSON ASCII escaping.
3. Publish replies only after complete write/flush/close from a new temporary
   pathname. Refuse existing destination or staging collisions. Validate the
   installed QtScript bindings; retain capability failures. This private serial
   mailbox is not a hostile-writer lock or a power-loss durability guarantee.
4. Record each native error in a unique numbered record containing run, sequence,
   operation stage, path, original wire text where available and QFile error code
   and message. Never overwrite an anonymous error. Stop the observer on the first
   error; retain partial publication. If error publication fails, emit the full
   record and publication failure on the retained native console. A console-only
   error or missing error export cannot be called a clean run.
5. The client stops dependent work on any error, request/reply mismatch, missing
   reply, changed published request or actual native exit. A timeout leaves the
   same process available for inspection. No retry converts a failed run to clean.
6. Limit the observer to status/attribute inventory and the already declared
   absolute camera procedure. No document open, selection, mutation, import,
   save, export or close is available through its protocol. Actual UI controls
   continue to do those jobs. Preserve the original strict CAD and byte criteria.
7. Retain all requests, replies, errors, staging files, console output, client
   actions, native/controller/container status and source/method/configuration
   hashes. Export the private mailbox from the same retained container, verify
   complete inventory and recheck it offline. No automatic container removal.

## Ordered exposed checks and expected outcomes

Freeze the implementation and staged inputs before its first native attempt.
First run normal status, native source fields and absolute frames on the exposed
air/water case; then the exposed template case that failed before. Match the
supplied fields and exact camera recipe, retaining original source hashes. These
are read-only transport checks, not new edit/save or native qualification runs.

Run separate fresh processes for these predeclared fault profiles, with the same
read-only workflow until injection. Each must retain a client failure and exact
evidence; a native error must retain its detailed journal or console fallback:

| Profile | Required finding |
|---|---|
| Malformed request | JSON/envelope refusal; no successful reply |
| Wrong sequence | Filename/envelope or noncontiguous sequence refusal |
| Wrong run identity | Envelope binding refusal |
| Unsupported body/action | Read-only action refusal |
| Unreadable request | Actual QFile read-open failure with code/message |
| Reply destination collision | Original bytes retained; publication refusal |
| Reply staging write failure | Actual write-open failure; no accepted reply |
| Error journal write failure | Complete native console fallback; run failed |
| Missing reply | Client deadline/liveness refusal; no dependent action |
| Changed published request | Client wire binding refusal; retained changed bytes |
| Native normal UI exit before request | Actual native exit detected; no restart |

For fault runs, record the same native PID still live after controller failure
where applicable. A separate recorded normal UI cleanup may close that process;
it does not turn the original attempt into success. Do not kill it to satisfy
the expected native-exit control.

Offline receiver controls additionally remove an error export, alter request or
reply sequence/body/identity, omit a reply, inject an extra reply, collide output
and change source/method pins. All must remain detected after recomputing an outer
archive inventory; an inventory alone is not semantic validation.

Report every attempted case and failure. If the implementation changes after a
failed attempt, retain that exact method and result, freeze its successor before
running it, and label all repeated cases development. No test key or comparator
exception may be changed to make an attempt pass.

## What still follows this repair

N118 is complete only after actual native normal/fault behavior, complete receiving
and negative controls support these requirements. Then incorporate the transport
and camera into a fully frozen edit/save/close/reopen method with multiple assets,
foreign/literal/encoding text and next-revision/conflict checks before selecting
fresh reserved cases. Existing native full-save differences remain failures.
Human readability, engineering/company acceptance and site benefit remain separate.

Primary API basis: Qt's [5.14.2 QFile source](https://raw.githubusercontent.com/qt/qtbase/v5.14.2/src/corelib/io/qfile.cpp)
and [QIODevice flags](https://raw.githubusercontent.com/qt/qtbase/v5.14.2/src/corelib/io/qiodevice.h).
Source documentation is not proof that a particular QtScript binding is present;
observe that in the installed native process before relying on it.
