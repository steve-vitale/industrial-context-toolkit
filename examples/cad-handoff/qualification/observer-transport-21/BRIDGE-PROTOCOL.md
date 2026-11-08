# Helper implementation contract before native execution

Refines the frozen BRIDGE-PLAN without waiving any original result. Request/reply
wire remains `ict-native-mailbox/1`; local helper invocations use `ict-native-io/1`.
Every attempt has the same frozen random run identity. Helper CLI accepts one
structured ASCII JSON argument; no shell or arbitrary path/command parameter.

Operations are initialize, poll and publish. Publish admits exactly one native
observation or native observation error, bound to the already admitted request.
Initialization reads the frozen configuration. Poll checks every completed request
hash, contiguous inventory and the next request. Publish rechecks its exact bytes.
Request/envelope/response bounds are65536bytes; the Qt helper argument is capped
at60000ASCII characters before launch. Refuse rather than truncate. Limit a run
to4096helper invocations; this is a bounded serial lab protocol, not unlimited
streaming or an adversarial filesystem/concurrent-writer service.

Each closed/fsynced staging file is exclusively linked into its permanent path.
Requests, replies, errors, invocation events and cleanup controls have separate
directories and staging directories. Every helper call has a contiguous call ID,
its exact input and output, OS owner/parent PID/UID, previous-event hash and
operation context. Each Qt start/end is printed on the retained native console.
Normal receiving must bind the complete event chain to all native starts/ends,
all client requests/replies and exact method/source/configuration pins. A launch,
timeout, decode, history/error publication or sequence failure never becomes
clean because another file exists or a process eventually exits zero.

## Transport shutdown and deliberate fault ordering

The protocol-only `seal` request obtains a final read-only status observation,
publishes it and stops the observer timer after the helper has actually completed.
The client waits for the matching native sealed acknowledgement before normal UI
close. `seal` cannot open/edit/save/close any CAD document. This avoids destroying
an active helper while closing a normal application.

After a retained controller failure, separate cleanup can exclusively publish a
run-bound cleanup-only stop marker. Polling acknowledges it, journals that call
and stops the observer. An already fatal observer needs no new request. For a
deliberately paused Qt child, publish this marker before resuming the same child,
so cleanup cannot consume the abandoned pending request. Require a native stopped
or fatal acknowledgement and no live helper before the actual normal UI close.
This is cleanup evidence; it never converts the controller attempt to success.

Before publishing faults that pause the actual Qt child, drain any already
running helper without restarting it; record process identities/states. No pending
request may race that drain. Skip an accessibility failure snapshot while Qt is
deliberately paused, retaining that explicit unavailability. Then use the separate
same-PID cleanup above. Actual native normal UI exit is a different control and
needs no second cleanup after that process is terminal.

All eleven original fault profiles remain. OS read/write errors must retain their
actual errno and owner; observation errors retain the native cause with errno
absent. Error-publication failure must preserve the complete primary and secondary
errors on console and in any obtainable invocation event. The original direct-Qt
attempts, probe refusal, historical camera20 failure and all CAD gates remain.
