# Retain the first bridge UI timing failure and observe completion

The first frozen helper run eef0788 returns native observations, then its existing
typing routine refuses an immediate filename readback. The controller exits1;
the same Qt child17 remains live. A separate read-only inspection now observes
the unique Open Drawing filename field exactly `/work/source.dxf`, with no new
typing. The original mismatching text was not printed by the old error handler,
so its specific contents cannot be recovered. This supports an asynchronous
completion concern; it does not prove which key event or scheduling delay caused it.

Before cleanup, freeze cancel_failed_open.py. Require that exact later field,
original failure and same process identity; press only the observed Cancel button,
wait for dialog disappearance, then use the already frozen bridge cleanup to
stop/acknowledge/drain the observer and close normally. Retain the original failed
attempt separately from that recovery. No retry of the filename or new CAD open.

The successor UI routine will observe text completion for a bounded3seconds after
one unchanged key dispatch, without retyping or changing the expected value. It
will retain every sampled value and the full command/focus trace even on failure.
Tab/commit remains forbidden unless exact text is observed. Keep original UI19,
camera20, strict comparison, byte checks and this failed method/evidence unchanged.
Freeze that successor before any new native attempt. Existing ASCII input scope
does not become foreign-text qualification merely because text waiting improves.
