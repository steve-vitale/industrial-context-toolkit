# One observed Flowstead browser calculation

On 2026-11-08, the public [Flowstead flowsheet page](https://hazemmancy.github.io/Flowstead/flowsheet.html)
was opened in a desktop Chromium browser without an account. The engine reported DWSIM 10.2.12 ready.
The supplied **Dew and bubble points** example was selected and solved. Its two stream worksheets
displayed 99.97 degrees C; their displayed mass enthalpies were 418.991 and 2675.531 kJ/kg.

[observations.json](observations.json) retains the selected public-source version, inspected files,
displayed values, limited comparisons and the UI problem encountered. The temperature and enthalpy-difference
checks agree with the project's selected reference entries after unit conversion and display rounding.
The upstream references were read before the browser solve. Their IAPWS attribution was inspected, not
independently rederived from the normative formulation. This is one observed calculation, not a rerun of
Flowstead's full benchmark suite or an independent validation of its thermodynamic engine.

The pointer click on the screen-reader object-list button was intercepted by the toolbar. Programmatic
selection of that same observed button opened the stream inspector, and its Worksheet tab was clicked
normally. This workaround is retained; it is not evidence that pointer or mobile usability passed.
Engine progress messages also appeared at console error severity even though the selected solve converged.

Source inspection was pinned to upstream commit `c2d431f67673c6dc94d4218a81ed60cd5ae9a6c3`.
The live site's exact build/commit was not established. No private records, simulator code, case files or
third-party test implementation were copied into this repository. No network/privacy audit, mobile trial,
file round trip, dynamic simulation, equipment sizing or design/safety acceptance was performed.

For lessons and an own-job review path, use [process analytics](../../../docs/PROCESS_ANALYTICS.md)
and the [manual calculation worksheet](../../consulting-start/CALCULATION_REVIEW.md).
