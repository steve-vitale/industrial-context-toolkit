# Asynchronous helper and native UI observed together

Frozen `93cedc9` uses the full installed finished signal. While the same helper waited
for release, native UI opened Open Drawing, accepted one filename dispatch with
exact observed completion, and canceled. Only then did the controller release the
helper. The native timer advanced 1107 ticks during the helper's lifetime. Exact
UTF-8 stdout (`µ valve` plus actual PID/parent/UID) and stderr agree with the client.
The unnamed document stayed unmodified; controller/native/container all exited0.

The 96-file hashed archive retains all original inputs, native console/report,
helper identity/release, UI commands/observations, method freeze and terminal
receipts. This is exposed scheduling/API development, not a CAD transport pass or
an independent review. `recheck_async.py` checks both the predecessor's retained
failure and this result; `test_bridge_evidence.py` challenges false/coherent report
changes, replaced methods and lost failure evidence beyond outer archive hashes.
