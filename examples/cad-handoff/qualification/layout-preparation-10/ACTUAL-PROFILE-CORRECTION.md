# Verify the settings file actually selected by native CAD

Post-run inspection before merging found `absConfigFile: "/work/qcad-config"` in
every second-batch native stderr. The driver had verified/copied a different file,
`/home/cad/.config/QCAD/QCAD3.conf`. Installing a file does not prove it was selected.
The second batch is therefore excluded from the intended-settings conclusion too.
Its earlier manifest/HOST-NOTES and initial published conclusion remain retained in
the first archive and Git history; this correction supersedes that conclusion.

Before a new run, change only the receiving driver to pass the installed absolute
file to `-config`. Add a wrapper that obtains `RSettings.getFileName()` inside the
native process, writes its receipt and refuses any other path before the unchanged
25-input native probe runs. Retain actual `absConfigFile` stderr and before/after
configuration digests for every native command. Do not reset settings between
commands, modify marks, licenses, clocks or installed publisher code.

The third batch uses a new container only after both previous batches are confirmed
normally exited. The original producer/verifier, 21-case cohort, 25 route byte pins,
frames, native probe and image parameters stay frozen. No original failure is erased.
Retain the first archive unchanged; package the third receiving batch separately.
Only the third batch can support the intended settings conclusion, if these checks pass.

The [QCAD API](https://qcad.org/api/classes/RSettings/) documents `getFileName()` as
the application settings filename. The version actually executed remains the pinned
3.33.1 Qt5 image; this latest documentation is used only to locate that existing API.
