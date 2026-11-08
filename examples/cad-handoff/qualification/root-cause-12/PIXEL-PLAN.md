# Diagnose the retained 62 pixels, without a tolerance waiver

After the two serial save experiments, the exact font-9 default overview frames 106/107 were decomposed.
All 62 changed pixels outside the floor/ceil MODEL rectangles occur at canvas row 537, x 411..956.
Both native geometric top bounds project to y=538.0512493261092 (floor 538). The source is 81 A glyphs,
the candidate 107 B glyphs. Source row 537 is black; 62 candidate pixels there are solid yellow.
The rectangles describe centerline geometry; a stroked renderer can paint beyond geometry (Qt coordinate
system documentation and QCAD RTextBasedData / graphics-view source). This is a hypothesis, not yet an
exact cause or permission to expand the acceptance rectangle.

Before execution, test isolated native glyph paths from the exact retained source/candidate, with the exact
retained camera and pinned Standard.cxf, no drawing modification/save, no GUI input. Retain native path
bounds, settings selection, output and errors. Render all combinations of width 1/2/3 screen pixels,
antialiasing off/on and round/square caps (12 profiles, two drawings each). No profile is selected as an
accepted display method from this diagnostic. Compare each prediction to the original images at every
changed pixel and at the 62 outside pixels; report mismatches, not just whether a larger rectangle fits.
An exact reproduction would locate these pixels in rasterized intended text, without proving whole-canvas
equivalence or recovering the historical loaded settings. If no profile reproduces them, keep cause unresolved.
