# Idle time must not consume invocation identities

This successor is exposed development prompted by the retained call-4097 failure.
Keep the 4096-invocation, 60,000-byte argument and 65,536-byte response bounds.
Do not tune those bounds or skip previously published request-byte checks.

Use one asynchronous native child for a pending poll. Inside that child, reuse
the original admission, immutable publication, exact request validation, error
journal and event chain. Repeat the original read/check operation at 50 ms while
there is no request; return only an actual request, an explicit cleanup stop or
an actual error. Do not emit successful idle invocation events. The Qt event loop
must remain free while this single helper waits. Initialization/publication keep
their original 5-second helper deadline. A waiting poll has no idle deadline; the
unchanged client owns its 5-second deadline **after publishing a request**.
Timeout/failure remains terminal for that attempt, retains the same processes and
permits no dependent request. Do not kill a waiting child merely to advance a run.

Before a full native receiving attempt, freeze the new implementation and stage
one separately identified probe on the already exposed CP1251 case. Observe the
actual waiting child PID/native parent and exact start time, wait beyond the old
5-second helper deadline, and perform a native Open dialog type/cancel with the
same helper still alive. Check no idle event burst, one child, unchanged source,
then post a real status request and receive it through that same child. Let the
next poll wait, explicitly publish cleanup stop, receive its stopped event and
observe no live helper before normal same-process close. Record terminal native,
controller and container outcomes. The original transport auditor must check the
complete probe history; separate checks bind the UI actions/observations.

Exercise malformed request, wrong run/sequence, previously changed request,
publication collision and stop while waiting with exact error/history retention.
These controls apply to the new lifecycle; old transport fault results do not
automatically transfer. A refused probe/control stays retained. Only after the
probe and controls pass may this method run full receiving on both exposed cases.
Declare/freeze new staging and native jobs once, without rewriting an earlier
JOB-FREEZE. Preserve the old sources/manifests and original strict/byte tools.

Full receiving still requires every source/baseline/edited/candidate asset and
frame, exact frozen image/camera/configuration, complete evidence, separate strict
and byte checks and the already declared pixel comparisons. Paper/layout,
readability, revision/conflict, planted CAD losses and fresh reserved validation
remain required separately. This transport repair alone qualifies no CAD route.
