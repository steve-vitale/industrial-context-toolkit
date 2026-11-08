# Locate CAD failures before changing acceptance

Declared on 2026-11-07, before the new native experiment. This is development diagnosis on the six
already exposed public-validation-11 adapted sources, not a new holdout or plant qualification.
Original sources, failed saves, comparisons, strict comparator, byte verifier and acceptance remain unchanged.

## Causal questions and controls

For every selected source, in the same pinned QCAD 3.33.1 Qt5 Docker image and explicitly selected settings:

1. Import and save without an operation (default and R15).
2. Import the exact patched candidate and save without an operation (default and R15).
3. Import the original, apply only the declared attribute operation, and save (default and R15).
4. Import each no-operation return and save again in its format.

These are 48 exports (eight per case). Each export starts from a newly imported document; branches do not
reuse a modified document. Capture imported / after-operation attribute positions, alignment, font, native
handle and exact stored text; close and re-import every output. A separate fresh process reads all 48 outputs.
Retain all actual commands, stderr, per-case exceptions, output bytes and configuration digest chains.
No timeout/restart, settings/license change, removed trial mark, tolerance, metadata waiver or row suppression.

Score all branches with the original strict comparator:

- Source -> no-operation return: differences that do not require an edit.
- No-operation return -> edited return: bind the existing plan to that exact no-operation source hash and
  require the same original before-values; no other plan field or comparator change.
- Patched-no-operation return -> edited return: identical intended text; compare with no plan.
- First no-operation return -> second no-operation return: test repeat-save stability, not assumed equivalence.
- Source -> edited return: retain the ordinary strict failures beside those controls.

Exact zero in a branch comparison establishes only that decoded comparison boundary. Nonzero differences
remain failures; inspect concrete headers/tags and native before/after states rather than calling them churn.
Do not infer import versus exporter internals from an output alone. The proprietary DXF importer/exporter is
not available as source; public core code documents API behavior, not that hidden implementation.

## Other failures and breadth of explanation

Maintain a source-linked cause register for prior confirmed issues (frame convention, pointer state, missing
font glyphs, missing main paper viewport, authored label placement, selected-config provenance, handles in
controls, Git archive conversion, source exposure). Separate causes established by intervention from direct
code defects, visible symptoms and unresolved hypotheses. In particular the font-9 62-pixel outside-bounds
result, complete readable receiving, and general native full-save preservation must remain open unless
new evidence actually explains them. Do not declare all issues solved because a list covers their names.

## Independent receiving

Freeze scripts and exact selected inputs before execution. Offline receiving must hash-check every output,
recompute every strict table, require every route / case / native field / fresh-process observation, and
reject omitted controls, changed geometry or native text and an incorrect zero-difference assertion.
The offline receiver is separate from the native producer; it does not rerun QCAD or establish human approval.
Commit failures and corrections, causal findings, limits, journal and attempts ledger. Run focused checks
and full exact-head CI; preserve chronological plan/method commits in the merge.
