# Full-application opening and print-getter boundary — development plan

2026-11-08. Declared before implementation/execution. Follow the original
[qualification protocol](../PROTOCOL.md); no acceptance criterion or strict comparator changes.
The six exact header16/layout17 drawings are exposed development data. No reserved case is used.

## Question and controls

Does the normal application document-open/new path, including native view/default-action/listener setup,
initialize the twelve primitive plot locations whose installed constructors retained typed presets in
layout17? Does merely reading the application's print settings initialize them? Public source at QCAD
commit `897079c2d11aaa0869f839a6cf5df8a937dbddbe` suggests distinct paths; it is a lead, not installed-build provenance.

Run the same full GUI startup in six fresh processes: bare API and normal MDI routes, each with the
existing observation-only, preset-a and preset-b helper modes. Reuse the exact already compiled forwarding
helper/library/image from layout17; retain their hashes and source reference. These presets are diagnostic
values, never a proposed drawing repair or accepted print profile. No helper changes or new compilation.

Each process runs six sources through both exact OpenDesign/dxflib filters and two empty controls: 14 jobs.
Bare API uses the same default RDocument construction/import path as layout17, within a fully initialized
GUI runtime. MDI uses the installed `NewFile.createMdiChild` with the same explicit filter (silent import-error
handling); a null input uses its new-document path. Retain the loaded filename, native errors, view presence,
modified state and open-window counts. Close each MDI document without saving after explicitly clearing its
modified flag; that cleanup is not a successful save or an editability check. Bare interfaces are destroyed.

For each job collect the complete header16 public inventory after opening, after a no-operation event-loop
pass, and after these installed Print getters: paper width, height, unit, size in mm, paper-size name,
page orientation, drawing scale and drawing offset (record exact supported names in the method freeze).
No setter, print-preview action, auto-fit, entity edit, export or save is performed. Full preview may prompt
and change values and is a separate possible future stage, not silently simulated here.

## Freeze and execution

Commit this plan first. Then freeze staged drawing/settings/method/job/helper hashes and the exact runtime
image before native execution. Start Xvfb/openbox and normal QCAD startup with `-exec`, not a custom no-GUI
autostart. Reset the selected settings from the identical pinned input before each process, record actual
selection and before/after hashes; normal application changes to its working settings are retained, not
misreported as immutable. No network, host display, plant data or external service. Retain every process
exit, stdout/stderr and failure. A live observation timeout does not authorize restarting a process.

## Analysis and limits

Keep all typed values, IDs, handles and custom properties. Compare complete inventories with only documented
set-traversal sorting, never omit an inconvenient field. Report every difference within stages, across modes
and between routes; separate the twelve targeted plot fields from all other recorded leaves. Count per-getter
preset retention/overwriting, not independent plant accuracy. Both presets must lose influence to support
initialization at a boundary; one apparently sane value in an observation-only process is insufficient.
Record print getter returns separately from native layout getters: defaults returned by Print do not prove
native layout storage was initialized. Check all source and frozen method bytes after execution.

Retain a bounded lossless evidence packet and a standard-library offline receiver that recomputes the tables
from actual native records, checks inputs/settings/commands/coverage and rejects altered results or unsupported
qualification claims. Preserve unrelated changes and failures rather than relabeling them as successful
initialization. This does not enumerate complete geometry/opaque native payloads, re-run the strict CAD comparator,
establish interactive UI edit/save/close/reopen, consume a holdout, or qualify the full CAD workflow. Those gates
and original native-save failures remain open; no engineering/company acceptance follows.
