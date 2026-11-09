# Goal: ordinary records to reusable engineering context and ChangePilot receiving

Set 2026-11-09, before implementation (original plan: a89a1b2). Status: implementation
in progress; development evidence is recorded separately. No full-goal case is complete.
Toolkit baseline: a26a0e0a4e8588081e16a1a63b2f26d045a75cb4.

## Outcome and customer journey

An engineering or maintenance manager starts with permitted records they already have,
gets one source-supported finding, keeps an editable engineering context foundation,
reuses it for component drafts and the next revision, and optionally carries that
same foundation into ChangePilot for continuing managed use. Value must precede
product signup. Each stage leaves a useful portable result even if the customer stops.

1. Start from the existing job selector: document clarification, maintenance records,
   or a drawing-return question. Inventory the supplied files and explain unsupported
   inputs. Extraction and engineering interpretation remain supplied/reviewed work
   where the current tools require them; count that effort.
2. Obtain one useful finding with exact sources/revisions, conflicting accounts and
   missing evidence. No graph completion requirement, account or paid service is
   needed to reach this first result.
3. Retain scoped identities, claims, typed relations, original evidence, authority/
   applicability declarations and review history. Build drafts from that selected
   context rather than asking the customer to enter the same facts repeatedly.
4. Review a contribution and handle later records. Preserve earlier versions and
   manual edits. Explain changed facts and their dependent answers/draft fields.
5. Offer a plain-language handoff preview: included scope, retained information,
   exclusions, unresolved questions, source authority and access requirements.
   Authentication and explicit sharing occur through the destination's normal path.
6. Receive in actual ChangePilot, inspect/query the same evidence and uncertainty,
   handle another revision and export the complete declared scope again.

This work improves the toolkit's context foundation and the bounded product receiving
route. It does not add work assignment, reminders, approval orchestration or execution
tracking to this repository.

## Scope and implementation choices

Implement a bounded common projection basis over the existing documented model/graph
contracts, with explicit adapters and preservation/omission reports. Do not require a
wholesale implementation of the context-map-1 draft or retire existing formats first.
Preserve complete originals. Scope identities by site/unit; distinguish a functional
position from the installed physical item, and design/installed/operating applicability.

Provide versioned, inspectable local functions/CLI JSON for capability discovery,
entity lookup, typed relationship traversal, claims/evidence/conflicts, context gaps,
draft requests and revision impact. Reuse existing lookup/question/generator tools
where their semantics fit. MCP is an optional interface, not a prerequisite.

Required draft targets from the SAME selected context:
- Equipment/instrument list (CSV plus typed machine-readable basis).
- An item datasheet scaffold (readable plus typed basis).
- Loop/control-narrative outline (readable plus typed basis, explicit missing behavior).

Also exercise a bounded projection into one existing generator model contract through
its real validator/consumer. Supply no invented topology, signals, setpoints or detailed
layout to make it pass. Partial/unsupported results are legitimate and explicit.
This does not qualify native CAD or plant platform imports.

Inspect ChangePilot's current code/contracts and governed context before declaring gaps.
Reuse canonical import, evidence, context and agent/UI surfaces; implement missing
bounded receiving pieces in an isolated product worktree when necessary. Follow that
repository's instructions, exact-candidate independent review and governed landing.
Product readiness requires an actual approved isolated non-production receiving flow
using normal application authorization, persistence and readback. A mock, archive-only
upload, service-role-only bypass or local toolkit Snapshot pass is insufficient.
Private product implementation and credentials must remain private; publish only
permitted interoperability specifications and sanitized evidence. Production promotion
and real customer uploads are not part of this goal.

## Definition of done

Every criterion in ACCEPTANCE.json must have a retained pass with its actual evidence,
or the goal remains incomplete. Do not silently shrink required scope to make it pass.

1. All three starting-job fixtures reach their predeclared sourced finding with known
   unsupported preparation visible. The documented default needs no hand-written
   JSON or account. Header mapping is guided, retained once and reused on the next
   export. Source interpretation and ambiguity confirmation are not hidden.
2. Intake, query, draft, revision and handoff consume the same scoped identities and
   source-linked facts. No known fact must be retyped for a new component or migration.
   Exact original data and explicitly unsupported information remain reconstructable.
3. The three drafts agree on shared facts, carry field-level source/derivation links
   and preserve unknown/conflicting states. Required minimum context is per target.
4. A selected fact revision identifies all and only its declared dependent answer/
   output fields in the bounded fixtures. Preserve conservative whole-asset handling
   outside proven dependency coverage. No revision-only change silently inherits a
   current engineering review; document the actual applicability/refresh policy.
5. An engineer's declared edit is read back after reopen and either preserved or
   explicitly reported on regeneration. Reimporting a generated document cannot
   multiply independent evidence support.
6. A scoped package carries complete declared content, external references, history,
   source locations/bytes where permitted, access requirements and omissions. A fresh
   process reopens it away from the original workspace and checks semantic equality,
   not just counts or self-consistent hashes.
7. Actual ChangePilot acceptance covers authenticated scope, persisted readback,
   useful existing UI/agent access, conflicting proposals, retry without duplicates,
   interrupted delivery, stale base refusal, source/access withdrawal, next revision
   and a complete export/reopen. Any unsupported meaning is previewed and retained;
   loss of required context fails. No manufactured authenticated approval or automatic
   sharing of personal/company records.
8. The same predeclared engineering questions retain their supported answer, citation,
   uncertainty and conflict semantics before and after receiving. Show the customer
   where each source lives and what continuing managed responsibility adds.
9. Retain the entire customer journey: actual commands/actions, prerequisites,
   navigation, mapping/clarification steps, failures, retries, software time, manual
   interventions and bytes/records preserved. Measure against the same starting
   records and task using the earlier tool/manual-folder route. No human-time saving,
   adoption or willingness-to-pay claim follows from agent simulation.
10. Report actual runtime/memory/artifact size at 100, 1,000 and 10,000 synthetic
    assets, plus an over-limit refusal. Publish environment and admitted workload;
    retain failure/limit observations instead of asserting plant/global capacity.
    Product workload/load testing must use its approved isolated environment and
    predeclared limits; no production stress test.
11. A clean clone reproduces the offline journey, outputs, controls and relocation
    checks from documented commands. The product integration has its own real
    authorized receiving replay and exact product revision/runtime identity.
12. Required focused regressions, affected legacy workflows, existing registry/claim
    checks, full CI and governed product gates pass with every skip reported.
    Review the frozen exact implementation with an oracle/checker independent of
    the production projection, and satisfy the product's independent Judge requirement.
13. README, agent guide, workflow contracts and existing script/feature/attempt
    registries describe actual capability, preparation, evidence and limits. Preserve
    all historical CAD/model failures and frozen prior methods. Land the authorized
    changes using each repository's normal path and verify final trees/checks.

## Validation protocol and protection against tuning to the test

Before production-code changes, retain the old-route baseline, input/key provenance,
literal expected facts and unacceptable outputs, interaction counts and failure cases.
The checker must derive its oracle from those sources/keys, not the candidate's own
rendered output. Mutation controls must cause the SPECIFIC intended refusal or mismatch;
a crash, unrelated error or blanket refusal does not pass. Include intact positives.

Development reuses the exposed Riverbend, existing maintenance and drawing-return
fixtures where applicable. Fix a second synthetic unit/record dialect and at least one
permitted public structured/drawing-derived source route before method freeze. Retain
license, source bytes/hashes, versions, input preparation and actual prior exposure.
Check raw public source facts when available; a saved reading tests downstream transfer,
not original-image interpretation accuracy.

After development, commit hashes of tools, adapters, renderer, evaluator, inputs/keys,
acceptance and replay BEFORE running the preselected transfer cases. Existing public
fixtures are author-known procedural transfers, not blind data. A case that informs
a fix becomes development; preserve the failed run and use a newly fixed transfer set
for a later generalization claim. Neither more examples nor test count alone proves
engineering correctness.

Use actual separate-process CLI/API calls and actual delivered files. Bind receipts
to exact source/adapter/template/specification versions. Query the real receiving
store and UI, not its own "success" response. Independently retain expected hashes
where substitution detection is claimed. Keep tests of meaning, access, preservation,
interface usability and runtime performance separate.

Desktop and 390px browser checks cover navigation, sources, conflicts, revision,
handoff preview and product readback. Check rendering and actual interactions, not
screenshots alone. These are browser/agent checks, not a physical phone or human trial.

## Customer value and friction

For each starting job, the receiving brief must answer:
- What useful question did this resolve, with what source-supported finding?
- What remains unknown, disputed or outside the supplied records?
- What reusable context did the work leave, and what can be drafted next?
- Why would ongoing use benefit from a managed service, and what can stay local?
- Exactly what will transfer and what responsibility stays with company source owners?

Freeze a recorded baseline interaction count before candidate work. Report required
decisions, file/field re-entry, prerequisite/setup steps, context-switches, retries and
recovery. The supported fixture path requires zero hand-edited JSON, zero repeated
entry of already retained facts for component generation/product migration, and zero
repeated mapping entry for the next export of the same admitted dialect. Genuine
identity/access/engineering ambiguities must still be surfaced. Explain installation
and unsupported extraction honestly. Do not replace the own-record route with a
prepared demo and report that the customer's route succeeded.

A consultancy-assisted route can supply preparation and engineering review, but it
must leave the same portable package. The self-service route must not require the
author's hidden knowledge, a call with the author or product purchase.

## Boundaries and completion reporting

No human engineer trial, real-plant acceptance, measured human saving or production
service capacity is available merely because these software gates pass. N052/N062/
N063 keep their separate human/company scope. Accountable source systems keep released
records and engineering authority. ChangePilot receives a declared context scope; it
does not become owner of every CAD object, CMMS event or design calculation.

Produce a final per-criterion report with baseline/candidate results, every failed
attempt and correction, skips, exposed inputs, exact toolkit/product revisions, actual
environment, known limits and a runnable replay. Distinguish implemented, tested,
unsupported and human/company-unrun claims. Do not call the product ready for this
handoff until its actual receiving acceptance passes; repository text is insufficient.

