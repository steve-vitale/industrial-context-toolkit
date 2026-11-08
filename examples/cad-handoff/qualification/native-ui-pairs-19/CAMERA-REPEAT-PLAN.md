# Exact camera repeat — development follow-up, before implementation

2026-11-08. Preserve the original 18-process cohort, its expected-metadata recording failure and every
exact-camera failure. Do not change its helper, masks, tolerances or acceptance verdict. This follow-up
uses the same six exposed sources/returns/candidates; it consumes no new validation and cannot qualify CAD.

## Hypothesis and source lead

The pinned public [RGraphicsView.cpp](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/RGraphicsView.cpp)
sets the zoom factor, then centers using the existing offset and an inverse view transform. Algebraically
the old offset cancels; floating-point arithmetic can retain dependence on it. The native motion run's
last-decimal offset differences are consistent with that source lead. The public source's identity is not
proof of the proprietary installed build's implementation; an actual native control is still required.
The [public header](https://github.com/qcad/qcad/blob/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/RGraphicsView.h)
exposes factor and offset setters, which affect the view rather than CAD entity properties.

## Frozen design for the next method

Develop a separate observer and receiver; retain both original and successor source. Use six fresh native
UI receiving processes with the unchanged image, settings, font substitution and UI file/handle/field route.
Each opens the original, no-edit native return, edited native return and exact-span candidate. No entity
edit or CAD save occurs in this camera-only follow-up. Record normal close/exit and all original input hashes.

On each open, capture all three previously frozen frames first with the old zoomTo recipe, then all three
with the proposed absolute camera. Keep both full image sets and raw view observations. Do not realign,
resize, crop differently or discard a comparison to obtain agreement. Use the same label-region recipe.
Report old/control and new results separately; a repeat need not reproduce every prior floating-point bit.

For the new camera, take actual native canvas width W and height H and the frozen world frame. Let m=24
pixels, doubled only if the native high-resolution-view setting explicitly says so. Compute
f=min((W-2m)/(xmax-xmin), (H-2m)/(ymax-ymin)). Reject nonfinite/nonpositive or clamped/out-of-range factors.
Set the native view factor to f, then set its offset directly to
(W/(2f)-(xmin+xmax)/2, H/(2f)-(ymin+ymax)/2). Keep the usual native regeneration events and repaint.
The calculation must not read the previous offset. Record requested/actual factor and offset, high-resolution
setting and canvas size. Require exact requested/actual equality and exact four-file camera equality;
there is no numerical tolerance. Unexpected installed setter behavior stops and remains a failure.

Compare complete view pixels and source-qualified native fields for all four files, not only camera numbers.
Record every outside-region pixel, including zero and failed checks. Rendering still does not establish
engineering readability, source fidelity for every font, editability outside the tested fields, or acceptance.

Before future reserved full-workflow runs, also correct the recorder to snapshot event values rather than
retain mutable references. Use the actual failed expected-value history as a regression control: the old
method must reproduce the aliasing failure, and the replacement must retain both before and after entries.
This logging repair cannot rewrite the original records or change their failed recording status. Freeze
the complete combined method before selecting new reserved inputs and running their native edit/save cycles.
