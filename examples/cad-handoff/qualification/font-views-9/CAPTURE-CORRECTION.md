# Retain the first font capture before correcting pointer traversal

The first default-profile batch uses frozen capture method `9c64546`. Its observed
native view is 1533x1032, beginning at desktop `(113,175)`. The planned traversal
point `(1590,1220)` is below that canvas, in the lower UI. The batch remains retained
as an initial framing/font observation; it does not satisfy the declared blank-canvas
traversal step. The native input/drawing/union-camera method is unchanged.

Before a new batch, move the traversal point to `(1590,1180)`, inside the observed
canvas's padded lower-right margin, then outside `(2380,1380)`. Keep the first full
batch terminal before another begins. Use new receipt sequence numbers and a new
output directory for the corrected default batch; run the substituted profile with
the same corrected capture recipe. Retain both methods and every initial frame.
This is development on exposed cases, not a qualification-method update or waiver.
