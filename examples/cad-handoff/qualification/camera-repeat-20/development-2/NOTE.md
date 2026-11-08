# Finalizer refused an expected not-yet-created job

The first finalizer (frozen at `1ee1fac`) successfully received the original air
packet, then exited1 when Docker reported `error: no such object:` for the queued
mechanical job. Its missing-handle check expected capitalized `No such object:`.
This note transcribes the observed terminal outcome; it is not a saved stderr
stream. The actual original source and runtime freeze are retained here, and the
air replay remains in the first output destination. The batch/native processes
were not changed, stopped or restarted.

The revised missing-handle classification compares the same explicit Docker
diagnostic case-insensitively, only for the five known remaining jobs. It does
not treat another inspection error as a pending job and cannot launch CAD.
A new receiving destination preserves the original finalizer output.
