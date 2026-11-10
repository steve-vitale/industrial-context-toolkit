# Baseline and input freeze before the new implementation

The earlier-route baseline actually ran on 2026-11-09. Its corrected checker passes
16 conditions. This is existing-tool behavior and original-record/key consistency,
not completion of any of the 31 new required acceptance cases.

From the repository root, standard library only, with a new output folder:

    python -B -S examples/map-component-cycle/baseline.py --out out/my-earlier-route
    python -B -S examples/map-component-cycle/check_inputs.py
    python -B -S examples/map-component-cycle/test_input_oracle.py

The baseline runs the existing three-revision maintenance intake, drawing receiving
rehearsal, one-map build and two item queries. Complete selected outputs and actual
command/stdout/stderr records are retained in baseline/. The command record includes
software timings; those timings exclude human preparation, interpretation and review.

## What it demonstrates

- The original equipment CSV says OLD-101 for U1/P-101, while closed WO-801 records
  NEW-101. An open order's FUTURE-101 is not an installed-state observation.
- Two U1/U2 positions with the bare tag P-101 remain distinct. Across the supplied
  revisions the disagreement count is 1, 0, 1; disappearance is not accepted closure.
- The drawing rehearsal returns the recorded receiving findings and retains its
  separate native CAD preservation failure and unaccepted release state.
- A bare P-101 query in the Riverbend map yields a structured clarification, no
  selected item and no invented facts; qualified lookup runs separately.
- The plain document brief is root-agent-authored from the exposed original lines:
  FIC-101 reads FT-101 and adjusts FV-101, with fail behavior and trips not supplied.
  It requires no graph or account. It is not an automated reader or fresh-agent trial.

The first baseline checker wrongly expected ambiguous lookup to exit 2. Existing
one_map.ask correctly exits 0 with a structured cannot-answer response. The failing
checker, command outputs and diagnosis are retained in history/. The correction
checks the actual abstention and exact qualified alternatives. No legacy production
tool, engineering key, frozen CAD method or acceptance requirement was relaxed.

## What it does not demonstrate

The mapping/profile JSON and prepared drawing readings were already supplied. The
runner creates three maintenance profile versions programmatically and reuses their
mapping; it is not evidence that a human retyped the mapping on each revision.
Customer interaction counts, interpretation effort and human time remain unmeasured.
Use this honest baseline when recording the new customer journey; do not manufacture
a friction or savings advantage. Product receiving, common-basis component generation,
field dependency precision and the new customer-path requirements are still unrun.

## Input and oracle freeze

INPUT-FREEZE.json pins 22 original input/key files before candidate production code.
The new development family is explicitly fictional: one utility, a same-tag pump in
another unit, equipment and instrument exports, a datasheet, work orders, a source
register and a short narrative. It has three related revisions:

1. OLD-101 versus a closed order's NEW-101; equipment flow 40 versus datasheet flow 45.
2. Only the datasheet flow and its revision change, 45 to 50; independent records stay exact.
3. The equipment export says NEW-101, a later closed order records NEXT-101, and the
   datasheet is withdrawn. Retain its prior evidence without treating it as current.

The separate literal EXPECTED.json is agent-authored from those original records,
not generated from a future projection. check_inputs.py reads CSV/text directly and
validates raw pins and literal meanings without importing candidate tools.
The initial check passed 43 conditions; adding the explicit original typed JSON
source expands it to 45. The preceding 21-file freeze/control record stays in
history/. Five actual oracle controls include an
intact positive, tampered source bytes, altered facts with recomputed byte pins,
false changed to numeric zero in the key, and a supposedly independent changed
record. Each wrong case must fail for its specific semantic/integrity reason;
an unrelated error or blanket refusal is not accepted.

A semicolon/header dialect and the existing public DEXPI C01 conversion are
preselected for procedural transfer AFTER the tool/checker method freeze. The
public conversion/report/reference text pins normalize CRLF to LF and were checked
against committed blobs as well as the Windows checkout. Observed raw hashes remain
separate. This changes no original XML, raw input pin or engineering comparison.
The preceding raw-only public freeze stays in history/ for the portability diagnosis.
The
conversion tests downstream meaning; it is not a fresh reading of the original XML
or P&ID. The documented original-source acquisition remains a separate step before
making original-source interpretation claims. All inputs are author-known; neither
fresh fictional records nor public availability establishes blindness or plant accuracy.
