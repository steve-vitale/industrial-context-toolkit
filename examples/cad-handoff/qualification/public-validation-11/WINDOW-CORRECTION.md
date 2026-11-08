# Native bitmap window contract correction

The first frozen public transfer render batch passes `[min_x,min_y,max_x,max_y]` directly
to Dwg2Bmp's `-window`. Inspection of its first asset image found right-edge clipping.
The installed QCAD 3.33.1 Qt5 command's actual `-help` output confirms that the argument is
`X,Y,W,H`, matching the [publisher documentation](https://qcad.org/en/command-line-tools/).
The local help command completed normally in its own network-disabled container; it did
not access or edit a drawing. Its output and terminal state are retained with this run.

This was a test-harness error. The canonical native boxes and declared common-frame rule
remain unchanged. A separately frozen receiving driver converts only the command argument
to `[min_x,min_y,max_x-min_x,max_y-min_y]`. It reruns all 24 views into a new folder after
the first batch is confirmed terminal. Every original image, command and failure stays.
No per-case frame selection, font change, image editing, trial-mark removal or drawing
mutation is permitted. Correct framing cannot remove inherited label/geometry overlaps.
These sources have now been inspected during observation development; the corrected visual
run is not an independent blinded observation-method validation.

The earlier layout-10 bitmap driver uses the same mistaken min/max serialization. Its
saved images and numerical matched-pixel comparisons remain actual observations under
identical commands, but the claim that those arguments implemented the declared canonical
frame is incorrect. Do not use those images as proof of complete layout framing/readability.
No old driver, source, image, strict comparison, score or archive is changed. Native stored
values, exact candidate byte checks and measured main-viewport bounds are separate evidence.
