# Observe strokePath as well as drawPath

Declared after the first replay failed, before compiling/executing the extended observer. Ordinary and
observed-3 GUI canvases were literally equal, and an independent observation of the replay found zero
state/primitive discrepancies for the selected floating line calls. Nevertheless their replay reproduced
only 1,517 of the delta pixels and disagreed with the actual delta at 857 pixels, including all 62 outside.
That incomplete trace cannot establish the cause.

Reading the rest of the pinned public paintDrawable implementation shows its cubic branch calls
worker->strokePath(cubicCurve, worker->getPen()), which forwards to QPainter::strokePath. Add that distinct
entry point, retain its explicit pen, and repeat the ordinary/observed canvas equality check. Do not assume
drawPath observation captures strokePath internals. Preserve the original trace and both failed replays.
Buffer the trace within the process and flush at every observed end, retaining all events and serials;
avoid opening/closing the host-mounted file for every glyph segment. A missing end is not a complete cycle.
