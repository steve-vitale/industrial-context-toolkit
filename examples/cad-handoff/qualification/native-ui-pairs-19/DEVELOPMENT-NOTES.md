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

The first real baseline process opened source.dxf and the observer read the exact original parent handle
20018 and all three expected attributes. The controller then refused two showing Drawing View controls.
The full tree establishes the cause: QCAD's covered Untitled 1 MDI child remains marked showing alongside
the active source.dxf child. Their rectangles differ; this is not missing drawing geometry. No edit or save
occurred. A successor binds the canvas to the unique document frame named by the observed active filename,
then requires exactly one showing Drawing View inside that frame. It does not choose by coordinate/order.
The original controller/tree/failure stay in jobs-2; this case remains exposed development.

The jobs-3 successor's Untitled prefix rule also matched the top-level application title, so it refused
before opening any drawing. The actual ready tree contains 'Untitled 1 - QCAD Professional Trial' and
' Untitled 1'. The corrected pure selector requires a full Untitled-number name, not that prefix. Test it
against both retained ready/opened trees and ambiguity controls before the next native execution.
