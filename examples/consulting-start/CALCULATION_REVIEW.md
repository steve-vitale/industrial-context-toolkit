# Optional portable calculation and what-if review

Attach this manual worksheet to the agreed [scope](SCOPE.md) when a manager needs a bounded engineering
calculation or scenario review. Start with the decision and an established suitable engine. This worksheet
does not run a simulator, establish model suitability, or supply a safety/design calculation method.

## One decision and a supported calculation basis

Question / recipient / milestone / intended use: ____
Site-qualified equipment and source revisions: ____
Tool / exact engine version and patches / case format / approved execution location: ____
Property model, components, composition basis and parameter-data sources, if applicable: ____
Steady-state or dynamic basis / operating envelope / assumptions and excluded phenomena: ____
Acceptable error and independent reference or measured comparison, agreed before running: ____
Responsible domain reviewer / receiving owner: ____

| Input or parameter | Value and units/basis | Original source/revision/locator | Measured / estimated / assumed / unknown | Range or uncertainty and reviewer |
|---|---|---|---|---|
| ____ | ____ | ____ | ____ | ____ |

An unreadable or missing value remains unknown. Record pressure reference, composition basis, unit
conversions and any enthalpy reference convention explicitly. A converged model can still use unsuitable
physics, wrong inputs or an inappropriate operating envelope.

## Compare the baseline and the proposed scenario

Baseline case / exact saved file and hash / source cut-off: ____
Changed input(s), reason and permitted range: ____
Scenario case / exact saved file and hash: ____

| Result and units | Baseline | Scenario | Difference | Reference/tolerance or unresolved validation |
|---|---|---|---|---|
| ____ | ____ | ____ | ____ | ____ |

Numerical solve status / warnings / failed or out-of-envelope cases: ____
Mass/energy or other applicable consistency checks and scope: ____
Comparison against an independent reference or held-back measurement: ____
Sensitivity to uncertain inputs and alternative suitable models: ____
What this result supports / what it cannot settle / next evidence: ____

Engine-generated expected outputs can detect regressions. Independent references and conservation
checks provide different evidence; neither a matching regression nor convergence proves installed behavior.
Keep the reference source and tolerance, including failed checks, with the result.

## Make the work portable and revisit it

Original sources, input conversions, case file, report, engine/version and reviewer record location: ____
Open/recompute/readback observed in the named receiving environment: ____
Required fields lost or changed during export/import: ____
Source or assumption whose revision must reopen the finding: ____
Next revision / owner / agreed receiving check: ____
Actual preparation, calculation, review and handover effort: ____

For a browser tool, distinguish local numerical execution from the page's other network behavior, file
downloads/caching and retained storage. Use approved records/locations. Explicitly save the case and inputs;
a browser tab or cache is not the engagement archive. A document export alone may not preserve editable
model assumptions or reproducible numerical state.

Use [REVIEW_AND_NEXT_JOB.md](REVIEW_AND_NEXT_JOB.md) for receipt and commercial learning. For the
toolkit's current analysis and proposed simulator boundary, see [PROCESS_ANALYTICS.md](../../docs/PROCESS_ANALYTICS.md).
