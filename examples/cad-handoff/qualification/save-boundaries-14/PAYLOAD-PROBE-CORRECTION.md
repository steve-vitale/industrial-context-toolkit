# Retain the incomplete payload probe and run a separate corrected successor

The preparation edit failed at PowerShell parsing, leaving native_payload.js as its three-line placeholder.
The subsequent preparation/controller was started in error without verifying that source edit. The failed
attempt is retained: no native observations or export receipt can count as a successful payload job.
The native controller's coverage/fatal guards must reject it even if the native process exits zero.

Do not modify or restart that workdir. After authoritative terminal state, copy its exact frozen authored
sources/candidates/plans into payload-3, replacing only the native probe with the complete separately named
native_payload_observed.js. Re-freeze the method and verify all other input hashes before execution. Keep
the original failed native output, controller receipt and terminal state. The source data stays exposed
diagnostic material; no fresh qualification is claimed.
