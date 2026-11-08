# First native batch did not receive the declared configuration

The stopped-container `docker cp` failed: `/home/cad/.config/QCAD` did not exist.
PowerShell continued to `docker start --attach`, so native batch `native-1` started
without the intended copied terminal run-7 profile. It is retained and excluded from
the declared matched-profile conclusion. All original frozen methods and inputs remain.

The process was inspected and confirmed live, executing the native probe and serial
renders. It is allowed to finish; no observation timeout is treated as terminal and
no live process is restarted. Its eventual state/logs/results must remain retained.

Before the next native batch, correct setup only: the driver creates the native profile
directory as the normal `cad` user, verifies the locally supplied configuration SHA-256,
copies it, verifies the installed file, and writes a digest-only receipt **before any
CAD process starts**. A failed check stops execution. The local configuration is not
published. Use a fresh container after the original batch is confirmed terminal.
The DXF producer, separate verifier, source cohort, 25 routes, native probe and rendering
settings do not change. This correction is declared before the repeated native batch.
