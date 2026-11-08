# Explicitly retained signal-connection failure

Frozen `05628bb` used the ambiguous `QProcess.finished` connection. The installed
native error names both overloads and requires an explicit full signature. No
helper started. The controller/host failed 1; a separately frozen`3353daf` cleanup
verified the same native process, no child/helper and no dialog, then closed the
unmodified unnamed window normally. Native 0/container 1 preserve the distinction.

The 77-file hashed archive retains original sources, failure, actual UI/process
and separate cleanup receipts. The next probe is separate, not a retry or repair
of this process. Recheck both probes with `recheck_async.py` in the parent folder.
