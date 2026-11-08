# Port-aware P&ID revision checks: declared development plan

2026-11-08. This is an exposed, fictional development exercise, not a held-out model evaluation.
Freeze this plan, the source records and the acceptance key before implementing the new checker.

## Problem and evidence

A tag-to-tag signal check can miss a connection to the wrong input on the right controller.
A syntactically valid JSON record can contain an incompatible signal or reversed endpoint.
The existing markup tool remains the baseline; retain its tag-level behavior and old packets.
Keep CAD preservation, structured consistency and drawing interpretation as separate checks.

Sources are separately authored, fixed CSV connection schedules, a markup instruction text and a
small public-domain fictional symbol/port catalog. Prepared observations will be authored from those
records, not emitted by a drawing generator. The key is written separately before checker implementation.
The same assistant authors the key, inputs and implementation and can see all of them. No independent
person has reviewed them; no blind inference or drawing-reading accuracy claim is permitted.

## Contract and acceptance before execution

Add an opt-in standard-library checker for supplied assets, typed ports, connection observations,
explicit coverage and exact expected connections. Bind every observation and requirement to a retained
document hash, page and region. Unknown data stays unknown. Exact ports, direction, relation and signal
type matter. Missing observations only establish absence when the user explicitly declares complete
coverage for that endpoint and evidence. Extra observed connections enter the report. Never edit inputs.

Use a versioned catalog separating illustrative glyph references from endpoint meaning; this catalog
is not an ISA symbol standard or a DEXPI interchange implementation. Record library revision/hash.
Report incompatible ports/directions/types and duplicate/ambiguous identities, and retain sources in a
portable packet. Malformed or stale input refuses before output. No automatic engineering corrections.

Expected development outcomes (ACCEPTANCE.json): one correct change, one absent requested signal,
one wrong input on the correct controller, one unrequested signal and one unknown/uncovered request.
Compare the old tag-level fact with a new exact port-level fact on the same wrong-input case.
Then run a separately retained corrected return: all represented explicit requests except the unknown
one should be supported. An old observation rebound to the new revision must refuse.

Adversarial tests include wrong direction, process/signal mismatch, incompatible medium, duplicate tags,
missing ports, null types, incomplete coverage, false absence, conflicting readings, stale source hashes,
unsafe paths, output collision, portable replay and source preservation. Never derive acceptance from
the checker's result. Save actual failures and matched baseline/candidate results, not just a summary.

## Public methods review

Review DEXPI/pyDEXPI and the five published example rule graphs in arXiv:2502.18493v2.
Record what can be reused, required inputs and why source-specific heuristics are not universal requirements.
Use public references and original paraphrases; do not copy unlicensed code, symbol libraries or full papers.
No dependency on pyDEXPI is required for this bounded tool. An adapter or broader rule set needs its own
documented mapping, loss report and independent tests before claiming interoperability.

## Receiving boundary

Run targeted and registered repository checks. Preserve all prior CAD results and comparators.
Expose the route from the agent/manager and markup guides. Supply a concise manager handoff template:
scope, correction/evidence needed, owner, disposition and receiving checks. Contact Steve through his
LinkedIn only. No claim of complete drawing equivalence, safe design, plant acceptance or time saving.
