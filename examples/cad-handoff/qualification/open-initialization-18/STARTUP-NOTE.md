# Observed startup acknowledgement, before document observations

The first declared native process remained live before the observation script. Its X11 tree and retained
`attempt-1/native/startup.png` show the ordinary QCAD Professional Trial information dialog with one **OK**
button. No diagnostic job has run yet. This is an observed startup wait, not a native crash or completed run.

A separate controller may activate that exact observed `Trial` window and press Return to acknowledge OK,
retaining the command, screenshot and timestamp for each process. No trial feature, license state or CAD
method is modified. The six frozen process/method/input settings remain unchanged. The controller must stop
on container termination or command failure, not restart a timed-out application. Future unknown dialogs
require inspection. This acknowledgement is not evidence for the interactive edit/save gate.

The read-only source-discovery container `ict-cad-open18-source` preceded the plan and exited zero. Its
Python probe found no loose installed NewFile/OpenFile/Print/PrintPreview/autostart script files at the
candidate `/opt/qcad/scripts/...` paths; the installed application can resource-load scripts. It did not
open drawings, call CAD or establish that these scripts are absent from the application. Public pinned
source supplied the method lead; installed functions are exercised by the native script itself.
