# Retained procedure-development failures

The first job staging call after freeze 681deeb failed because the job's parent directory did not exist.
The host PowerShell command continued to docker run despite Python's failure; Docker created an empty bind
directory. Container ict-cad-ui19-air-baseline1 exited 2: python3 could not open /work/launch_case.py.
Authoritative inspect showed exited/not running, no OOM. No QCAD process or drawing run occurred.

The staging correction creates missing parents while still refusing an existing job directory. Subsequent
staging and launch are separate tool calls, with successful staging verified before starting a container.
The empty failed job is retained, not reused. Software preparation cases-1 completed before that failure:
all six source-preserving candidates pass strict comparison and independent byte reconstruction. All six
library saves pass the strict semantic comparison but fail exact byte reconstruction. Native results remain
separate; none is inferred from those software checks.
