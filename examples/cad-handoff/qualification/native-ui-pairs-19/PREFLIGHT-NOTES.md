# Startup/dialog capability observations

Plan `7c1f031` and startup freeze `b915b71` precede the new native process. No drawing is opened or saved in
this preflight. The original selected settings, image and actual command are retained. Only the ordinary
trial notice is acknowledged; its restrictions remain.

The first accessibility-action bridge expected a single action and safely refused the Trial OK button,
which actually exposes Press and SetFocus. Its source and original traceback remain. A separately committed
successor selects the observed Press action; that successfully acknowledges the notice. The Open toolbar
button then opens the actual native Open Drawing dialog, but its synchronous AT-SPI doAction call times out
waiting for a reply while the modal dialog is visibly open. The same process remains live, and the read-only
observer continues answering with an empty filename/unmodified untitled document. No timeout-based restart.

The next bridge uses X11 clicks at actual enabled/showing accessibility control rectangles. Event dispatch
success is distinct from observing the intended result. The caller must inspect the resulting dialog/values.
Earlier methods, captured errors and native dialog trees remain separate; an accessibility error is not
relabelled a clean automation pass. The source discovery's guessed SelectByHandle.ui URL returned 404;
the actual public source names SelectByHandleDialog.ui, which was retrieved. Public source is a method lead,
not proof of installed script bytes. Native dialog observations establish the recipe used here.

The same preflight process subsequently completed the Save As and Selection by Handle dialog probes,
cancelled both, and exited normally via the native window close (QCAD exit 0, container exit 0, no OOM).
The discard-only filename was never created; the last native observation remained an empty, unmodified
untitled document. Exact preflight methods and receipts remain in the original scratch directory. The
drawing workflow uses separate source files, preserving this startup-only observer and its freeze.
