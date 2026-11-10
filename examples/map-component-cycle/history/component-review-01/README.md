# Retained component review faults

The saved pre-fix source and independent probes identify three development faults:
browser-permitted Unicode could exceed the edit receiver's byte cap; missing
controller prerequisites disappeared from the component selector; human-readable
values could hide their text/number/boolean/null distinctions.

`actual-replay/` reconstructs the old source in a separate workspace and fails
specifically when the browser downloads a 131,615-byte request beyond the 128 KiB
receiving cap. `reproduce_review_boolean.cjs` compares whether a download occurred.
The original `reproduce_review.cjs` assertion compared the entire Playwright object;
formatting that failure consumed excessive memory. The orchestrator stopped that
owned process. `interrupted-observation/` retains the downloaded bytes and stop
observation; it is an incomplete run, not a completed expected-failure receipt.

`independent-probes/` retains the independent original-source no-controller packet,
exact generated Unicode request, type-display pairs and actual checks. Its initial
no-controller probe used the wrong column name and is not counted; the corrected
probe changed the real Type column in a separate copy of the frozen inputs.

The current source checks encoded bytes before download, retains absent-target
gaps and shows source types/literals. Current development evidence is in
`../../development/review-interface-01/` and `../../development/review-browser-01/`.
These are exposed fictional software controls, not human or product acceptance.
