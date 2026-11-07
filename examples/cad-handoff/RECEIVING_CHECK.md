# Qualify one CAD receiver

Status: **not run in a native editor**. Complete this for the intended CAD product/version and keep its actual
files and observations. A source-compatible library round trip cannot fill these observations in.

The [2026-11-06 LibreCAD attempt](NATIVE_ATTEMPT.md) installed the application and ran its native command-line
renderer twice. Geometry appeared, but expected text/attributes were not readable in the retained render.
GUI automation failed before open/edit/save could be completed. That partial attempt does not complete this checklist.

Before testing, record the application/build, exchange version/settings, project/database, symbol library,
expected identities/classes/connectivity/attributes, units, layers and acceptable explicit losses.

1. Open a retained copy of the source DXF/project. Check appearance and that symbols/attributes are editable.
2. Find the exact ICT_ID, TAG and foreign attribute in the editor. For intelligent CAD, also check the native
   class/ports, relationship and database identities; the supplied DXF fixture does not implement those.
3. Make the declared edit in the editor, save as a new version, close and reopen it. Record any repair/import
   messages. Export the agreed format and run `cad_handoff.py compare` with the original plan.
4. Review every difference, including handle remapping and unsupported content. Do not waive differences only
   to obtain a pass. Retain a loss/mapping report and the original native source.
5. Introduce a second source revision and a concurrent manual edit. Reconcile both through the owner; preserve
   history and ensure the accepted selected version reaches the context map.

Retain: source/returned hashes, native project when permitted, editor screenshots/import messages, comparison,
declared losses, reviewer/date, acceptance scope and residual gaps. No first-party company system acceptance,
installed-state validation or human time saving follows from a DXF parse.

The [QCAD headless experiment](native/qcad/README.md) obtained a native edited/reopened return, but strict preservation failed with 335 decoded differences. It does not complete this interactive checklist.

Use [`cad_handoff.py review`](receiving-review/README.md) to retain a readable receiving packet beside the full strict queue. The [explicit R2000 run](native/qcad-r15/README.md) retains the version but still fails preservation (344 differences). These diagnostics do not waive any checklist item.
