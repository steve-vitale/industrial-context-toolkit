# Preserve the original receiving failures and inspect the call boundary

The CP1251 fresh receiver stopped with host/controller exit 1 while the same
native QCAD process remained live. Its private error record is invocation 4097,
sequence 107, `Invalid invocation identity`, stage `admission`. The frozen helper
admits at most 4096 invocations; idle polls consume those identities. The native
call argument is retained even though its rejected result has null call/run IDs
and its final event has no previous-event hash. Do not repair that original record.

Before any successor, preserve the complete failed input/method freeze, client
actions, console, every helper request/reply/event/error and the failed host
outcome. Check the first 4096 complete chained invocations independently from the
last admission refusal, and bind that last exact input/error/console result to
the original native process and the controller's refusal. Missing views remain
missing. No normal receipt or completed full-view comparison may be issued.

For cleanup only, reuse the existing frozen `bridge_cleanup.py` in a separately
frozen action: require the same Qt PID/start identity, publish a cleanup stop,
observe native fatal/stop acknowledgement and no live child helper, refuse any
unexpected dialog, then request one normal window close. Preserve the original
failed host/controller status. No CAD file edit, save, restart or new normal
attempt is part of this cleanup. A refused cleanup is retained separately.

The literal-brace receiver was independently launched before this failure. Keep
its original live handle and record its own outcome; launch no dependent normal
successor until the new method is declared. Do not restart either process because
an observation takes time. No reserved cases have been admitted.

The successor must address unnecessary idle invocations rather than tune a larger
call allowance to these runs. Retain the original bounds and evidence; declare
the waiting-helper lifecycle, request/cleanup response, timeout ownership and
actual GUI responsiveness tests before implementation and execution.
