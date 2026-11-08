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

The corrected jobs-4 baseline completed its native no-edit save/close/reopen/attribute checks and normal
application exit (controller 0, native 0). Its full-save strict comparison retains 300 unexpected differences.
The separate edited process failed after keyboard entry: its attribute panel disappeared. A fresh read-only
observation establishes that MANUFACTURER stayed QUAL-BEFORE, the drawing stayed unmodified and all 14
entities became selected. Accessibility grabFocus alone did not activate the floating Property Editor;
Ctrl+A went to the drawing. Event-dispatch success was not an edit. No return was saved by that attempt.

Freeze a corrected input bridge before further input: click the observed editable field bounds, require
native focused state, retain the active X11 window, verify actual field text before Tab, then independently
verify UI and stored native values. A separately labelled recovery may continue the same unmodified process
after explicitly clearing selection. It retains both failures and never becomes a fresh procedure pass.

The first offline receiver rejected a fresh edited run with `Field expectation changed`. The original
receiver source, actual failed command/stdout/stderr and exit 1 are retained in receiver-1. Four native_fields
events in the original actions file all declare QUAL-AFTER, while the first two observed field snapshots
correctly show QUAL-BEFORE. The producer stored the same mutable expected dictionary in earlier events;
the later field change retroactively changed their declared metadata when the action list was serialized.
The independently captured UI trees, native observation replies and actual DXF values retain the real states.

The receiver now derives before/after expectations from the frozen source and workflow phase. It still
reports each producer expectation mismatch as a FAILED recording check, with both exact values, rather than
calling the original metadata correct. All observed UI/native/DXF values must independently match. The
producer remains frozen while the cohort runs; fix its snapshot semantics before new reserved evaluation.
This diagnostic receiving repair does not remove original failures, change strict CAD checks or establish
authenticated run records. The clean-controller cohort can still have a recording-quality failure.

The original motion pixel analyzer then refused `Native camera/canvas changed`. Its frozen source,
receiver source, actual command/stdout/stderr and exit 1 remain in receiver-2. Equal requested frames and
canvas sizes/factors did not produce bit-identical offsets: source overview Y offset 47.862565912624135
versus 47.86256591262412 after reopening; the asset offsets also differ in their last decimal places.
This remains a failed exact-camera repeat, not an accepted tolerance. An additional diagnostic reports
all exact camera values and every pixel comparison under the original two-pixel label-region recipe.
Its results are explicitly diagnostic when camera equality fails. No image is aligned, resized, dropped,
or masked differently. A future native camera correction needs its own frozen method and actual repeat.
