# State of the toolkit

Implementation snapshot: **2026-11-06**. The public package is **Industrial Context Toolkit** (renamed from Engineering Context Toolkit on 2026-11-05; old links redirect).
Use the [job selector](../README.md#start-wherever-you-are) to choose a tool or the
[first-question guide](../examples/first-pilot/README.md) for a no-install contribution.
The [workflow map](WORKFLOWS.md) owns supported inputs and outputs; this page owns current readiness and gaps.

Maintenance and engineering managers can use the [decision-first guide](MANAGERS_START_HERE.md) and
[offline review packet](../examples/manager-review/README.md) without installing software. The packet is an
authored fictional handoff with reproduced source findings; human usefulness and company acceptance remain unrun.

For agent-assisted self-service, use the [task guide](AGENT_START_HERE.md) and [reusable export intake](MAINTENANCE_INTAKE.md).
It accepts mapped equipment/work-order CSVs and produces an offline manager packet. The [three-revision replay](../examples/maintenance-intake/README.md)
retains corrected and subsequent replacement evidence. Two [actual fresh-agent sessions](../examples/agent-rehearsal/README.md)
reached the same substantive answer on a frozen fictional case; their author-scored rubric and exact retained artifacts
are distinct from the earlier authored dialogue. No human benefit, company acceptance or completed N062/N063 exercise.

**Reusable local tools build draft plant structure and engineering context from your supported records.**
A P&ID image plus extraction, an authored description/model, or supported DEXPI XML can become a sourced draft
model and review material. Review and enrich it, then choose graph/context, analysis or platform staging.
The tutorials teach what to substitute at your plant; case studies retain their own evidence.
Company review, accepted identities and receiving-system checks determine what can be relied on.

## Current verification

The earlier full-suite release baseline was **`a439f14`**:
[main CI run 41590240463](https://github.com/steve-vitale/industrial-context-toolkit/actions/runs/41590240463).
It passed **77/77 test programs**, with **18 individual unittest cases skipped**, plus six saved task/model
benchmark suites and the optional MCP/protocol job. This is software evidence, not human usefulness,
company-client acceptance or plant validation. Check [committed-version CI](https://github.com/steve-vitale/industrial-context-toolkit/actions/workflows/tests.yml)
for later revisions; the dated development records below apply only to their stated inputs and versions.

The current runner registers **72 source-only and 93 full-suite programs**. The earlier 2026-11-06 local Windows run
passed **89/89 programs**, with **seven individual unittest cases skipped** and three platform notices explaining
skips. It is not a complete run of every optional check. The drawing-to-map fixture now pins LF source bytes to
fix [Linux CI regression #7](https://github.com/steve-vitale/industrial-context-toolkit/issues/7); use
[committed-version CI](https://github.com/steve-vitale/industrial-context-toolkit/actions/workflows/tests.yml)
for the result on a particular published revision.

Offline publication checks match
41 numerical claims and identify one prose-only claim. The 95-cell workflow matrix records
**64 pass / 23 fail / 8 n/a**; its failures are retained research results, not failing unit tests.
Pipeline freshness remains **50/52**: manual `te.pid_live` and `te.replay` receipts are stale.
Saved predictions regenerate 23 matching tables and seven with documented historical formatting adjustments;
five earlier diagnostic tables still lack predictions. The feature catalog has **31 features**, of which
**22 have current independently reviewed example outputs**; the generalization-matrix review is stale after
the selected intake receipt refresh. Its numerical results are unchanged. The new CAD and photo examples still
need independent review.
Neither a passing software test nor a matching source hash establishes an accepted engineering conclusion.

The coherence audit corrected [core graph reduction](GRAPH_EXPORT.md#two-profiles-the-full-record-and-the-part-a-change-system-needs): connections stay
whole when retained memberships cannot explicitly represent them, or when they carry substantive claims or
additional qualifications. The complete graph is checked before reduction. The original reduction remains
historical evidence beside its conservative successor; this is not proof of complete physical impact analysis.

## What exists, and what remains manual

Select the tools needed for the job. The [workflow map](WORKFLOWS.md) owns the supported format contracts;
the [feature reference](FEATURES.md) owns individual example evidence. Company systems retain authority,
access, accepted decisions and continuing ownership. Local hashes, role labels and read-only transport do not
create those controls.

| Piece | Contribution | Boundary |
|---|---|---|
| Consultant P&ID markup return review | [Original/markups/returned review](PID_MARKUP_REVIEW.md) with explicit per-change checks, other observed changes and a portable packet; imperfect and corrected fictional returns reproduce offline. | Supplied source-bound interpretation and annotation inventory; no automatic PDF/handwriting reading, model accuracy, full-sheet equivalence, engineering release or map update. |
| Maintenance record handoff | [One fictional replacement](../examples/maintenance-handoff/README.md) links the existing before/after model, changes and closeout tools into a reproducible job. | Supplied identities and records; no CMMS acceptance, real recipient observation or measured review-time result. |
| Bounded editable CAD exchange | [Source-retaining DXF edits and mapped draft context](../examples/cad-handoff/README.md), plus a [local form/agent equipment-data exchange](../examples/cad-handoff/data-review/README.md) that avoids CAD resaving. Six fresh authored cases preserve all unplanned bytes; real browser downloads/reopen are retained. A [Linux native UI experiment](../examples/cad-handoff/qualification/linux-native-7/README.md) observes actual edit/save/close/reopen on the exposed valve and readable native candidate labels. | Profiled existing attributes only; this metadata operation requires no CAD UI. Full native save still fails: 287 new Linux strict differences, original Windows 335/344 unchanged. Complete layout/font acceptance, fresh native validation and company acceptance remain open; no inferred connectivity or automatic synchronization. |
| Public photo-to-record exercise | [Two attributed nameplate photographs](../examples/photo-to-record/README.md), candidate fields, six retained OCR attempts and explicit unknown asset identities. | Empty and incorrect OCR results remain visible. Candidate readings need independent review and site identity evidence; neither OCR confidence nor a legible plate establishes installed state. |
| Drawing intake and review report | A supplied extraction becomes a draft model, review queue, staging and readable HTML. | Approved extraction, engineering review and receiving-company acceptance. |
| DEXPI routes | Read supported XML or the separate adapted-key/sheet contract; report omissions. | Exporter coverage and downstream eligibility vary; supported unplaced roles can feed source-qualified questions while equipment placement remains unknown. This does not extend platform-generator eligibility. |
| Description/model drawing | Authored model and detailed layout produce draft sheets and platform outputs; the bundle retains the exact question catalog it consumed. | Interpretation and geometry remain authored; matching quotations and catalog hashes cannot establish correct meaning or company approval. |
| Portable graph and statement review | Typed relationships, sourced claims and supplied appearances can be inspected and reviewed. | One-way export; statement verdicts do not edit generator facts. |
| Model correction and point mapping | Apply supported local corrections and stage supplied signal addresses with history. | Identity/signal review, external companion reconciliation and regeneration remain explicit. |
| Loop audit and vendor evaluation | Compare supplied loop truth or saved drawing answers with bounded scorers. | No installed safeguard/wiring acceptance or measured review-time result. |
| Historian CSV and impact tools | Analyze supplied observations and calculate from supplied measurements/constants. | Qualified baseline, quality/time metadata, causal evidence and live connectors remain separate. |
| Saved batch calculation basis check | Explicitly compare selected CSV/plan/graph and current code pins, then reproduce the complete typed report when they match. | No automatic dependency monitoring, source authority, method validation or context refresh. |
| Selected batch-record joins | [Explicit batch/event/executed-recipe/lab/outcome selections](../examples/batch-analysis/record-joins/README.md), availability/quality gaps, reproduced calculation inputs, raw originals and descriptive differences. | Normalized local contracts; supplied metadata needs review. No record discovery, live connector, causal/yield model, actual historical-access proof or accepted investigation outcome. |
| Question engine | Catalog screens produce investigations and collection requests; source-scoped recipes retain known answers. | No arbitrary natural-language diagnosis or broad usefulness/coverage benchmark. |
| Model-bound context and graph snapshot | Retain supplied answers, source dependencies and decision/ownership history; explicitly refresh and read back the selected graph/context pair. | Supported model/question contracts and manual refresh/restart; no source fetching or shared company access service. |
| Knowledge/workflow starter packet | [Author and read](../examples/engineering-onboarding/own-packet/README.md) a selected landing map, source references, roles and workflow/practice records without an asset model. | Reference data; the reader/MCP remains read-only. No workflow execution or authenticated assignment. |
| Local knowledge contribution capture | [Capture selected text and authored findings](../examples/engineering-onboarding/contribution-loop/README.md) into a new packet with exact prior state, source pins, combined-source dependencies and readable handoff. | Complete UTF-8 text and authored links only; no semantic answer verification, automatic source watching, accepted-answer selection, concurrent shared writes or bound graph/context reconciliation. Fictional revision/readback controls do not measure human benefit. |
| Checks, matrix and task/model benchmarks | Reproduce claims/results and exercise selected workflows with failures visible. | Four task adapters, including `tag-reading` / `tag-text-v1` with separate geometry and partial-list modes, raw fixture checks and offline saved-answer reports. Selected facts, fixed labels and tag coverage do not grade arbitrary engineering meaning or company asset identity. See the [task scope](../benchmarks/README.md#current-reproducible-tasks); these are not a whole-toolkit completion percentage or general model ranking. |

## Demonstrations are a separate track

The [TE/OPEN100 comparison](DELIVERABLES.md) includes screens, recorded replay, tours and isolation mockups.
The gateway builder is TE-specific; PI staging has never been imported here. Proposed 3D geometry, keyword
hazards and isolation views are not installed geometry, hazard analysis or operating procedures. Replay does not
make commands drive a physical process simulation. The Docker package remains a historical demonstration.
Anatomy's optional vendored drawing kit belongs only to the [interactive TE case study](../drafts/interactive-tour/README.md),
with browser-only viewing and separate rebuild/verifier requirements. It is no core architecture or toolkit dependency.

<a id="company-handoff-external-responsibilities-and-missing-adapters"></a>

## Open work and company handoff

The [self-service gap record](SELF_SERVICE_GAPS.md) states which of the four current improvements have evidence
and which remain open. In particular, [native CAD diagnosis](../examples/cad-handoff/native/diagnostic/README.md)
does not establish a successful native edit/save/reopen; this LibreCAD route remains unqualified for the attributed profile.
The subsequent QCAD native API returns are actual edit/document-reopen observations, with complete offline receiving
reviews, but unresolved strict differences and no interactive, visual or company acceptance.
The later [Linux native UI observation](../examples/cad-handoff/qualification/linux-native-7/README.md) records a
single exposed valve's real edit/save/close/reopen and fresh-process reopen, beside its 287 strict full-save
differences. Existing-cohort model/paper views and same-original rendering controls retain layout/font failures;
they do not establish whole-workflow native or company acceptance.
The subsequent [pointer-state experiment](../examples/cad-handoff/qualification/receiver-state-8/README.md)
explains that public-paper mismatch: deliberate highlighting reproduces both old states; nine neutral repeated
source/candidate views have zero canvas differences. One exposed drawing does not close font/layout or fresh-validation gates.
The [font/frame experiment](../examples/cad-handoff/qualification/font-views-9/README.md) retains 36 matched native
views of three exposed authored pairs. A declared Standard-to-DejaVu Sans display mapping and bounds measured
after mapping make the inspected Cyrillic, mixed Unicode and long asset labels readable without changing DXF bytes.
Existing linework overlaps, default-font glyph failures and a 62-pixel default overview discrepancy remain; no original
typography fidelity, repaired paper layouts, full-save equivalence or fresh qualification is inferred.

The [minimal layout experiment](../examples/cad-handoff/qualification/layout-preparation-10/README.md) adds a
structure-based proposal while retaining every original non-seed byte: five proposals, 14 exact no-ops and two
R12 refusals across all 21 exposed cases. Each prepared paper image matches its library add-main baseline;
25 native images and 330 field observations are retained. This is a separate source revision requiring review.
Original blank-layout/full-save failures, trial-mark overlap and original top-edge label clipping remain visible;
complete readability, fresh validation and native full-save/revision qualification stay open.

The later [public transfer cohort](../examples/cad-handoff/qualification/public-validation-11/README.md)
adds six exact public-adapted candidates and 144 matching native/fresh-process field observations.
All twelve native full saves still fail strict preservation. Its receiving review found that the
bitmap helper expects X/Y/width/height rather than min/max coordinates; both 24-image batches
are retained. The earlier layout-10 canonical-frame claim is narrowed accordingly. Corrected
frames do not remove inherited label overlap or trial marks; complete readable/native UI
acceptance, unexplained full-save differences and unfamiliar-source coverage remain open.

The [causal CAD controls](../examples/cad-handoff/qualification/root-cause-12/README.md) add 144 exposed
native exports and 432 fresh-process field observations. They isolate and correct an unintended current-layer
change in the API edit harness. No-edit full saves still have 4,650 strict rows across twelve pairs; second
saves add 6,138. A before-load constructor change does not fix them. R15's matched residual is traced to
embedded save-time values, without excluding it. The subsequent [actual-GUI trace](../examples/cad-handoff/qualification/gui-scene-13/README.md)
explains the 62-pixel residual: native separate cubic glyph strokes extend beyond geometric bounds. Ordinary
and observed canvases match; actual primitive replay reproduces all 1,978 delta pixels exactly, and removing
curves removes all 62. Original failures and strict comparison remain intact. Whole CAD qualification,
native full-save preservation, complete readability and fresh UI/revision acceptance remain open.

The [save-boundary controls](../examples/cad-handoff/qualification/save-boundaries-14/README.md)
add 63 complete exports/fresh imports and 65 offline strict reports. Explicit source-version selection
works but does not fix preservation. Default line types are present before import; empty exports have
252–262 records. A testing-only fixed Qt hash seed makes two independent runs match strictly on all six
exposed cases, isolating a 53-resource-record repeatability component. Actual foreign-data omissions remain:
all 17 valid-integer controls lose the named XRECORD and unused APPID, while tested used XDATA, asset
attributes and valid USERI5 values survive. Earlier out-of-range integer probes and an incomplete native
helper are retained as failed controls. The diagnostic receiver now retains literal header bytes rather
than an inspection-library synthesized creation time. No strict waiver, new holdout or native UI
qualification follows; opaque exporter payloads and the original remaining gates stay open.

The [crossed record-path controls](../examples/cad-handoff/qualification/record-paths-15/README.md)
locate additional losses: dxflib reduces a mixed private record during import, while OpenDesign exposes
the full array but both writers fail to serialize it intact. Foreign dictionary identity and string
group codes are reconstructed. All 48 final jobs are observed: 46 exports/fresh imports, 12 strict
differences, 34 asset-profile refusals and two hydraulic symbol-table export failures. Twelve returns
have dangling links. The 72 dxflib-imported attributes target model space; all 24 dxflib-written returns
lack attribute sequence markers, explaining why displayed text is insufficient for this attributed
profile. Six separately frozen hydraulic controls identify the retained slash in block name
2/2-directional valve: target-only native renaming permits both exports, while unchanged and
unrelated-renamed controls fail. Both exported controls still refuse the asset profile. Exact
candidates still pass; old runs and failed preparations remain. Other payloads and fresh
UI/readability/revision qualification remain open.

The [header/dimension controls](../examples/cad-handoff/qualification/header-boundaries-16/README.md)
separate the ordinary imported header from the native dimension style. All48 predeclared single-cell
controls on the same six exposed sources establish that both tested writers use the style for DIMASZ:
style-only changes are written, known-header-only changes are overwritten, and an unrelated USERI5
persists. The original26-job observation retains25 exports, one hydraulic failure and no strict pass.
Expanded receiving finds8 failed fresh layout/plot inventories (46 exact value leaves), despite17
exact repeats. Those newly observed failures remain; the pinned constructor source is a lead, not
proof of the installed build's internal cause. Full CAD and the remaining gates stay unqualified.

Use the [acceptance exercise](ACCEPTANCE.md) for concrete tests, records and failure cases. It is prepared;
actual participant, recipient, native-system and tenant observations remain **not run**.

| Work category | Remaining work | Completion evidence |
|---|---|---|
| Engineering question quality | N082's bounded source/collection review now covers all 50 rules/126 requests; N065 and actual usefulness remain open. The final 22 add 88 exposed fictional controls. Default MGPI now asks C2 about represented measurement purpose; that is not a finding of the incident's missing safeguards. | Independent source/collection and matched software checks exist; actual engineer/recipient usefulness, unfamiliar-company coverage and engineering acceptance remain to be observed. |
| Evaluation and transfer | N086 original-source/key engineering acceptance, Native placement gaps, existing matrix failures, unfamiliar-source coverage, scorer limits and five missing historical prediction tables. | Matched experiments with frozen criteria, retained failures, exposure/split labels and independent source/key review. More files or rerunning familiar inputs is not generalization. |
| Optional adapters and receiving projections | General inverse graph conversion, captured-source consumers, managed-section merging and particular incumbent-system connectors are not implemented. Test changed/removed identifiers and complete retained history for the selected route. | A demonstrated engineering job, explicit supported contract, source preservation and subsequent-revision readback. Add only the adapter that job needs. |
| Review-history handoff | N107 now preserves selected JSON intact and unbound, then attaches events only through [individual supplied associations](REVIEW_HISTORY.md) to exact model/record bytes. Complete earlier history remains readable; full/core retain its qualifications. | Review the source/revision relationship in the company process. Matching hashes cannot detect a false supplied basis or establish writer lineage, reviewer authority, approval or permission to share. |
| Document contributions and analysis continuity | Local text/claim capture and combined-source review have a [revision exercise](../examples/engineering-onboarding/contribution-loop/README.md). [Explicit record joins](../examples/batch-analysis/record-joins/README.md) now check their upstream calculation inputs. The [investigation exercise](../examples/batch-analysis/investigation/README.md) now retains authored hypotheses, plans, record-check results, contrary evidence and proposed dispositions. Scientific/typed-role validation, accepted-resolution selection, automatic monitoring and general/live joins remain outside these tools. | Preserve admitted sources, hypotheses/unknowns, calculation basis and disposition for the job; test changed upstream input and unsuccessful explanations. The fictional examples establish no kinetics, actual recipient benefit or company acceptance. |
| Company acceptance and benefit | N062/N063: real engineer/recipient investigation, authorized company import/readback, client permissions and a subsequent revision. | Actual observations from the [acceptance exercise](ACCEPTANCE.md), not an agent simulation. Native PI/gateway acceptance, accepted Copilot tenant and operational benefit remain unverified. |

The [E13/C4/E24 source review](../examples/opportunity-screen/water-valve-records/README.md) repairs the known
blowdown, valve/bypass and cooling-water collection/action gaps. Its 25 fictional controls and preserved
original outputs support those bounded policies, not whole-catalog correctness or measured usefulness.
Revised questions reopen earlier partial answers through explicit context refresh; retained history and an
old-sheet refusal do not establish an authenticated company decision or complete physical impact analysis.

The company retains authority over accepted context, access, controlled documents, work execution and ownership.
Generic inverse graph conversion, live incumbent connectors, automatic managed-section merging and company
synchronization are not implemented services. Typed JSON/CSV/graph exports exist; an OKF export remains an
assessed additional format, with no Google import acceptance. Choose these adapters only for a demonstrated job.
No permitted IT/OT route means disconnected work or an approved released snapshot, not a new port or tunnel.

## Recommended order of work

1. Return one bounded source-backed contribution that another engineer can reconstruct. The local capture/revision
   exercise supplies reproducible preservation checks; run the real recipient comparison when permitted.
2. Close the job's evidence and calculation-continuity gaps. Before broad analysis features, demonstrate the required
   record joins, quality/time basis, competing explanations and retained outcome on that question.
3. Evaluate question usefulness with the engineer or manager using their permitted records before adding catalog breadth.
4. Improve corpus failures through matched source-informed experiments; reserve unfamiliar inputs before tuning.
5. Add only the receiving adapter or projection needed by an actual team, then test its next revision and permissions.
   Hand shared identity, concurrent work and release operations to a sustainably operated company service.

Workstream labels in the historical audit describe how work was assigned at that time; they are not a live
agent queue or a supported company service. Queued research, intentional tool boundaries and external
acceptance are not completed features.

## Historical audit records

The following sections retain bounded repair evidence, failed candidates and development-stage counts.
Words such as “current” or “follow-up” inside them refer to those recorded stages, not a later release.
Use the current verification and open-work sections above for today's status.

<details>
<summary>Expand earlier development checks and repair history</summary>

### Development snapshots preceding the verified release

The current runner registers **60 source-only and 78 full-suite programs**. The preceding demo integration passes all
56 then-registered source-only programs with eight skipped unittest cases and three explanatory platform notices; four focused
programs also pass 48 methods without skips. The basis-check follow-up's three focused programs pass 56 methods
without skips, followed by 57/57 source-only programs with eight skipped cases and three platform notices.
The first-installment review commit `a97e239` also passed [normal review CI](https://github.com/steve-vitale/industrial-context-toolkit/actions/runs/41522983712):
75/75 full-suite programs, with 18 individual cases skipped, and the optional MCP/protocol job. These are
software checks, not company or plant acceptance. Follow [committed-version CI](https://github.com/steve-vitale/industrial-context-toolkit/actions/workflows/tests.yml)
for the latest revision; earlier counts below retain their bounded development snapshots.

The reader-path follow-up carries that distinction into the generated client reports, manual Bayer tutorial,
review kit and 3D case. The own-P&ID tutorial now gives the model/questions-to-graph continuation; description
and DEXPI guides link the Native OPC binding and manual PI reconciliation steps. Reported counts, drawing images
and recorded decisions remain the supplied examples' evidence; refreshed prose does not add plant acceptance.

The [script registry](SCRIPTS.md) distinguishes tools for your inputs from repository checks, support modules
and research runners; tests are separate. The [feature reference](FEATURES.md) lists each feature and its current
registered example files, including inputs, generated outputs and retained history. Shared files can appear under more than one group; feature-file
references are not additional unique examples. Their evidence is bounded. A reviewed
example does not certify every input, current implementation or engineering conclusion.

The bounded process-data addition supplies [recorded batch phase calculations](../examples/batch-analysis/README.md)
with optional exact twin-graph asset-ID binding. V1 preserves its prefiltered linear contract; V2 explicitly
selects interpolation and external quality policy. Null quality is unchecked, not a filtering or good-data claim.
One [measured laboratory source](../examples/batch-analysis/public-distillation/README.md) adds independent
recorded-series arithmetic, with upstream interpolation and documented negligible anomalies retained.
The [worked context handoff](../examples/batch-analysis/context-handoff/README.md) keeps a partial proposal,
remaining evidence needs and history; a changed report reopens the answer. These examples do not establish
fermentation prediction, physical mass truth, a real recipient's benefit or plant acceptance. The feature catalog
owns the exact independent-review scope. [Process analytics](PROCESS_ANALYTICS.md) distinguishes working tools
and manual event/recipe/lab/model qualification from proposed automatic joins, balances, soft sensors and
dynamic-model adapters. The question engine does not automatically assess arbitrary kinetic-model sufficiency;
the MCP starter does not execute analyses, chase report dependencies or query live history.

## Known defects

The preceding audit's three implementation defects have bounded repairs that passed independent receiving
checks. This follow-up also repairs candidate-text encoding and the historical Docker address contract, with
runtime acceptance kept separate. These are reproduced findings, not a claim that every malformed input or
engineering task has been tested.

Own-plant receipt follow-up (A289/N105): `map_points.py --record-dir` keeps selected reports with the private
working packet; the omitted default remains `out/mapping/`. The [own-P&ID guide](../examples/own-drawing/README.md#4-review-then-map-to-real-signals)
now carries private review/mapping folders through to generation and lab import.

N106 now refuses known Native process models before I/O reading or mapping, with a clear path back to
`generate.py MODEL --out PRIVATE_FOLDER`. The independently received mapper module passes 36 methods without
skips. This is a CLI format boundary, not a Native OPC adapter or a native-platform acceptance result.

Review-history portability (A292/N107): newly generated intake JSON uses explicit LF, and the committed
illustrative intake manifest has a narrow LF checkout contract. Company source originals, exact raw association
checks and the review command's preservation of supplied model formatting remain unchanged. The retained
`3100959` Linux failure is not upgraded by local success; corrected exact-head CI remains a separate gate.
See [the failure and bounded repair](JOURNAL.md#140-make-generated-intake-json-portable-without-normalizing-originals).

Own-plant question context can now travel with explicitly selected `--io-list` originals rather than an
ambient checkout CSV. Modern byte/span/row matches and historically unverified legacy associations remain
distinct through graph/context; all mapped signals retain their identity uncertainty. The
[small fictional tutorial](../examples/opportunity-screen/mapping-descriptions/README.md) shows the handoff.
N108 has bounded independent source-change/readback controls; source identity does not establish plant truth.

Captured I/O rows now use their recorded locators without repeated whole-CSV scans, retaining the same
qualified descriptions and graph/context content. The [small generated diagnostic](../examples/opportunity-screen/mapping-descriptions/lookup-scaling/README.md)
records bounded work, not plant capacity or timing; reload read-only captures to refresh them. Source-file
selection and plain-dictionary fallback still scan, and additional index memory is unmeasured (A295/N109).

Relocated schedule working copies can declare stable logical source labels without bypassing source-choice
checks. The [own-record handoff tutorial](../examples/opportunity-screen/mapping-descriptions/retained-answer/README.md)
connects question screening, partial answers, source revision and paired read-only MCP access. A local fictional
exercise preserves qualifications and history through refresh/restart; company clients and engineering acceptance
remain separate. See [the bounded checks and retained failures](JOURNAL.md#144-carry-a-source-question-through-review-and-mcp-readback) (A296/N110).

C3 now retains each eligible valve for a neutral review of existing feedback/diagnostic records, including
foreign, unknown and disabled position-tag context. The [valve/loop handoff tutorial](../examples/opportunity-screen/valve-feedback-basis/README.md)
separates command, local feedback, control-room return, endpoint indication and performance history. The paired
fictional controls establish software/source behavior, not an installed-state finding or retrofit benefit (A297/N111).

The C3 review CI exposed a stale whole-graph MCP sample fingerprint even though its returned asset was
unchanged. A298/N112 recaptures the actual SDK stdio response and retains strict comparison, source-qualified
provenance and narrow LF checkout. Snapshot19 and checkout3 pass without skips; the failed C2 CI remains
failed, and full integration/successor CI are separate gates. See [the failure and repair](JOURNAL.md#146-recapture-the-whole-graph-mcp-sample-after-a-source-policy-change).

Typed evidence revisions now reopen affected answers under the existing canonical JSON binding, including
boolean/integer and signed-zero changes; conflicting derived context views refuse. Complete history and
unaffected answers remain. The [fictional typed-evidence route](../examples/context-register/typed-evidence/README.md)
and 90 public module methods pass without skips (A299/N113). This is local consistency, not source authority,
plant truth or company acceptance; full repository and exact-head CI are separate gates.

Retained answers now group once by exact question ID after incoming revisions instead of repeating the
latest-answer sort for every question (A301/N115). The grouped context module passes 62 methods without
skips; existing integrations retain one named optional source-cache skip. The [bounded local observations](../examples/context-register/grouping-observations.json)
preserve the old sort-guard failure and exact source identities. History, source checks and output construction
remain; no timing, memory or company-capacity result follows. Final integration and CI are separate gates.

C8 and E6 start with existing records and their declared scope: [alarm responsibility and coverage](../examples/opportunity-screen/alarm-basis/README.md),
and [compressor/service, valve duty and power basis](../examples/opportunity-screen/compressor-recycle-basis/README.md).
Supplied records and shared coverage remain qualified claims for the next responsible reviewer, not installed
adequacy or a compulsory project (A302/A303). The current local question module runs 164 tests: 163 pass and
one unnamed case skips; checkout three pass. Collection checks, whole-repository freshness and exact-head CI
are separate evidence scopes. The standard-library-only mode excludes Pillow-dependent drawing checks; full
mode retains every registered test. None of these checks establishes plant or company acceptance.

**Frozen-model review benchmark.** Explicitly reviewed Native values, roles, supplied CSV and
approved claim/source context are bound before the existing fixed-label scorer. Declared coverage and keyed
artifact contradictions remain separate from reviewer accuracy; the manual CSV remains the engineer route.
Six actual public-root scores and the six-entry registry check pass. Four focused stdlib programs report 63
tests: 62 passed and one unnamed skip. These focused results are separate from source-only mode
(55 programs), the full suite (72 programs), and exact-head CI.
The [profile and limits](../benchmarks/source-support/artifact-values/README.md) exclude automatic claim
discovery, general generator accuracy, source authority and current plant acceptance.

| Reproduced gap | Required behavior and bounded repair |
|---|---|
| Review summaries accepted changed packet evidence or non-review queue fields under the old bundle identity. | Recheck drawing, overlay, base queue and manifest digest; permit changes only in the declared `OPS_` columns of the submitted review copy. Hash agreement is integrity, not source authority or reviewer authentication. |
| Imported timers accepted invalid event sequences or changing reviewer identities. | Validate imported and appended events with the same state rules, one nonblank reviewer ID and ordered offset-aware timestamps; refuse before appending. Timer logs can record actual review observations; these software controls establish no measured human review time or benefit. |
| An unrepresentable numeric vendor coordinate aborted the batch. | Count that answer as failed/empty, preserve the other answers and retain the diagnostic in the report. This extends the existing malformed-answer guard, not the scoring criteria. |
| New literal candidate evidence could truncate a report on escaped lone surrogates. | Preserve values as JSON escapes where UTF-8 cannot encode them; reject invalid declared field names before changing either destination. Normal Unicode and legacy no-opt-in output remain unchanged. |
| All three fresh starts of the frozen Docker demo lost historical TE addresses. | An explicit pinned profile supplies 36 literal aliases beside the current 52 channels, leaving SC-212 unfed. Focused and independent source checks passed; fresh browser acceptance is recorded separately in the [Docker guide](../docker/README.md). |
| Retained screen-time candidate prompts said the request remained open after a later accepted question answer. | Label the original candidate facts separately from current question disposition. Six matched workflows preserve all 18 JSON outputs; the report does not track individual request completion. |
| A recovery exchanger named "Fryer exhaust" became a process-equipment subject after the missing-label gate was removed. | Exclude declared standalone helper types from these anchors while keeping them as candidate context. Four new tests retain true process units, name-based fallback and the expected 29-finding food case. |

CSV replay also now defaults to loopback, prints the selected interface, rejects nonfinite rates, and checks the
start row before server initialization. A different interface requires an explicit `--host`; this remains an
unauthenticated recorded-data lab service. See the [CSV guide](../examples/historian-csv/README.md).

Completed historical repairs are grouped [below](#earlier-repairs-and-their-scope). Research failures,
unimplemented adapters and unrun company acceptance are separate categories, not repaired software defects.

**Collection-policy improvement:** E31/E32/H6 now investigate existing exhaust-recovery coverage, residual
external-duty basis and burner operating records even when a drawing supplies a recovery or analyzer label.
Existing records come first; working coverage is acknowledged, and a question does not require a new retrofit
or field task. The [heating tutorial](../examples/opportunity-screen/function-basis/README.md#extend-the-same-investigation-with-heating-records)
adds 18 exposed development cases to the original 25, with separate oracles and retained before/after reports.
Their 18 candidate calls and 108 scoped literal controls establish bounded software behavior, not performance
on 43 plants, measured engineer usefulness or acceptance of the supplied engineering claims.

E16/C5 now separate combustion service from boiler water-level applicability and retain existing records as
qualified candidates. The [combustion-control cases](../examples/opportunity-screen/combustion-control-basis/README.md)
retain all 80 original/candidate reports and their source limits. Numeric retrofit-benefit claims are removed
from these two rules; this is bounded source-informed collection behavior, not installed-control acceptance.

## How this audit was checked

The 95-cell matrix records **64 pass / 23 fail / 8 n/a**. The preceding audit actually reran 15 scorer-control cells for
the vendor repair and two guide-bound intake/historian cells. Their substantive results remain exact; only
measured timings, the changed method/guide bindings and the same historian passage's shifted locator change.
The other 78 complete cell objects stay exact. Criteria, source/key inputs and historical failures are retained;
no binding is backfilled. The own-plant transfer follow-up actually refreshed the own-drawing intake and Bayer
export guide bindings, preserving the other 93 complete cell objects and all outcomes. These failures remain
research work, not failing unit tests.
The release before `037c523` passed **71/71 local test scripts**, with six Windows unittest case skips, three platform notices and
zero additional skipped-check notices. Those counts are distinct; the handoff's unavailable native-symlink
subcheck is a platform notice without a skipped unittest case. This is not a complete runtime pass. Targeted CLI
controls, source-preservation checks, full-value reproductions and independent cross-reviews support the bounded repairs.

The `037c523` own-plant follow-up local full run executes all 71 programs: **70 pass**, with one failure caused by placing a new guide
inside the team example's fixed 97-file packet. The guide now lives [in docs](TEAM_CONTEXT_IMPACT.md); its existing
two-test module passes after relocation, with the test and 94 evidence files unchanged. Both runs preserve all
3,025 input files. The original full result remains recorded rather than relabelled 71/71. See
[committed-version CI](https://github.com/steve-vitale/industrial-context-toolkit/actions/workflows/tests.yml)
for the separate complete-suite and optional MCP results; platform and missing-cache skips remain explicit.

The current heating/context follow-up separately checks four new equipment-role test methods, 18 heating
cases and 14 unique producing routes. Its original 31-finding food failure remains; the repaired food/roll-up
have 29/41 findings. The aggregate contains 84 fresh and eight inherited artifacts. A final wrapper bookkeeping
failure is retained and independently resolved by receipt-only postprocessing, without new product calls or
changed criteria. The [journal](JOURNAL.md#135-keep-heating-investigations-grounded-in-existing-records) distinguishes
those checks, the six matched context workflows and the two actually rebuilt description receipts. Those earlier
receipts lacked their catalog input; N104 adds the retained-input repair described below, preserving the old evidence.

The first `0884b2b` full local and CI runs each report **70/71**, failing an old assertion that a linked recovery
label silences its unit's question. The fixture and CLI remain unchanged; the corrected test retains both
investigations and checks candidate evidence stays with its own unit. The affected public module passes
**135 tests with one skip**; the original local full result stays failed, and the other 70 local programs are not
repeated. Refer to committed-version CI for the separate complete-suite follow-up.

The publication check matches 41 numerical claims and identifies one prose-only claim. The follow-up currently has
**50/52 stages fresh**: `te.pid_live` and `te.replay` retain their earlier runtime receipts and are stale after the
replay implementation change. Offline checks and the historical Docker demonstration do not renew those manual
runtime stages. Five benchmark suites reproduce on the prior release. Re-scoring saved predictions reproduces 30 tables
(23 MATCH, seven MATCH-OLD); five historical tables still report GAP. These checks do not rerun commercial models.
An initial clean Linux CI run caught two collection-declaration defects after the local suite passed. The
follow-up separates an absent selected collection from committed siblings and binds exactly the TE files its
consumer reads. Partial-present and strict missing-input checks remain. The matrix was actually rerun after
this correction; [the journal](JOURNAL.md#116-correct-collection-boundaries-after-clean-ci-refuses-the-first-repair-candidate)
retains the failed candidate and follow-up evidence.

The local audit made no model calls, new original-source downloads, company/plant imports or live gateway calls.
The full-run file-set guard caught four browser-research captures added concurrently to the checkout; all 2,978
frozen input files remained byte-exact. The captures were preserved privately and the original path set checked
again. The original guard failure remains recorded in [the journal](JOURNAL.md#133-audit-the-broader-toolkit-and-preserve-review-evidence).
Browser captures are now ignored alongside private LinkedIn drafts. Clean CI separately stages checksum-pinned public fixtures.

**N104 — retain the question rules with a description build.** Each bundle now includes raw
`question_catalog.json`; the engine consumes that captured copy, and `build.json` records its hash and
default/custom selection. The build-only `--catalog` option accepts an approved copy in the existing catalog
format. The two examples were actually rebuilt to 32 and 37 files: 59 earlier files remain raw-exact, with two
new catalogs and eight declared report/provenance changes. All 23 description tests and three checkout tests
pass without skips in the isolated integration check. The repository default catalog has an LF checkout policy;
custom CRLF input remains raw. Historical integrity and current-default publication freshness are separate:
an old bundle can retain its rules while a current publication needs an explicit rebuild. This supplies neither
company approval nor an automatic update service. See the [workflow guide](../examples/from-description/README.md)
and [journal evidence](JOURNAL.md#136-retain-the-question-rules-in-the-description-handoff).

## Earlier repairs and their scope

The [journal](JOURNAL.md) preserves the earlier source-output collision repairs, appearance/source-locator
preservation, field accounting, collection-basis controls and report-interpretation corrections. The
[attempt ledger](TRIED.md) retains tried methods and open work; [RESULTS.md](RESULTS.md) retains numerical
research evidence. Historical records and failed attempts remain available rather than being replaced by a
passing follow-up.

<details>
<summary>Earlier bounded repairs and their remaining limits</summary>

The initial review, collection, freshness and retrieval failures below now have bounded repairs and negative
controls. Keep the remaining source-adequacy and external-acceptance work separate from those software results.

| Repair | Observable behavior and remaining limit |
|---|---|
| **Model review — N072/N077** | Supplied alarm metadata and old receipts survive. Supported native tag corrections migrate live references; separate layouts, mappings and snapshots still need reconciliation. [Worked correction](../examples/review-and-mapping/native-identity/README.md). |
| **Schedule choices — N079** | Contradictory service declarations refuse in either input order. Exact source-bound selections retain candidates and supplied qualifiers; existing spelling choices remain drafts. No choice grants organizational approval. |
| **Description review — N078** | Every supplied record value and source line is exposed for review; all rows start unreviewed. Structural validity does not decide whether the interpretation is correct. [Description guide](../examples/from-description/README.md). |
| **Collection contracts — N071/N073/N080/N084/N085/N088/N082** | Twenty-five named rules keep candidate fields, electrical quantities, measurements, machine/function association and actual coverage distinct from suitable evidence. E16/C5 first establish heat/water service and applicable existing function records; an oxygen label or boiler name does not require a control retrofit. C8 reviews alarm/operator scope; E6 reviews compressor/service, record pairing, representative duty and real-power basis. The other 25 rules still need source-adequacy review; no whole-catalog correctness, operating acceptance or usefulness is established. [Collection limits](OPPORTUNITY_SCREEN.md). |
| **Context and readback — N075/N076/N083** | Rejected evidence changes dependent-answer freshness; validated selected packets serve full retained sources, values, decisions and ownership. Bound enriched-question re-export refuses: use the complete graph/context pair or explicitly refresh the preserved register. No automatic source fetching, rebinding, authentication or company authority. [Context guide](CONTEXT_REGISTER.md). |
| **Matrix provenance — N074** | Actual runs bind declared inputs/keys, inventories, registry, runner and code. Changed/missing required inputs refuse; absent optional caches are explicitly unverified. Strict input mode still requires them. Bindings are conservative declarations, not operating-system read tracing. |
| **Benchmark recipes — N081** | Re-scores retain exact historical recipe snapshots, attempts, predictions and reports. New provenance identities are not new model performance. |
| **Metadata exclusions — N087/N089** | The existing named-person field policy applies before metadata reaches receiving tools. Any protected GenericAttribute Name designation, including qualified/conflicting aliases, blocks values before tag, identity or fact derivation. Eligible metadata and separate occurrence counts survive. Regenerate selected artifacts; earlier packets are not scrubbed. A refreshed register can retain old evidence in decision history; review that history before sharing a regenerated packet. This is a bounded field policy, not general personal-data detection. |
| **Native intake and diagnostics — N090–N093** | Metadata without a `Name` attribute is reported as not mapped; duplicate-ID refusals retain the unique count without quoting identifiers. The same named-field policy applies to protected descendants and optional PNG diagnostic inventory. Unsupported protected physical/adapter nesting refuses, and short PNG headers fail safely. Originals remain unsanitized. Counter scopes, history and prewrite limits are in the [XML guide](../examples/from-dexpi-xml/README.md). |
| **Native read allocation — N100** | Original-byte acquisition and every existing source recheck use requests of at most 64 KiB, with the same cumulative limit, complete bytes, hash, parse and error behavior. The earlier cap-sized allocation is avoided; no integrity check is removed. Two saved-input observations show lower traced heap and runtime on one host. Company capacity, RSS and general throughput remain unmeasured. |

Schedule-field intake also rejects ambiguous case keys and conflicting values, merges only disjoint additions
and refuses previously ignored native-model schedules. These input checks preserve evidence and explicit choices;
they do not decide which source governs a company's engineering work.

**N086 — optional source intake observability.** Explicit `--capture-source` now retains eligible structured
XML occurrences, parsed attribute values, source identities and Native mappings, with unmapped occurrences
counted separately. The default remains the existing Native-only model and reports. Capture follows a declared
scope and named-field policy; omitted text/tail payloads and presentation/geometry records still require the
separate original XML. Source IDs are provenance, not shared engineering identities. This does not improve
Native placement or extraction accuracy, change historical matrix failures, or establish source authority.
See the [capture guide](../examples/from-dexpi-xml/README.md#optional-capture-structured-source-evidence).

**N097 — optional local handoff.** An already captured model can become a selected Native/evidence/manifest
trio with explicit inspection and a bounded brief. The [worked files](../examples/source-handoff/README.md)
retain complete captured evidence and checked byte bindings. The utility does not discover sources, collect
data or provide company authentication, release, latest-version checking, atomic publication or concurrent
editing. Graph/context/MCP consumers do not expose the captured packet. Ongoing identity, access, review and
decisions belong in the company-managed receiving system.

**N101 — readable finding references.** Generated screens now expose each complete local finding ID and ordered
asset IDs as JSON-encoded values for the [first-question handoff](../examples/first-pilot/README.md). Keep them with
the selected model/screen and catalog revisions; they are not company-wide identities. Published description
bundles also have a regression for their declared producer and artifact hashes. These changes preserve the
existing findings and evidence; question usefulness and real recipient acceptance remain unmeasured.

**N088 — bounded E27 repair.** The original thirteen matched runs preserve eight scope failures. A local,
shared, unrelated, unknown or negated reset label now stays a candidate while each applicable condenser retains
train/operating-basis review. Source pointers and complete selected graph/context history stay bound; old catalog
answers can become stale. This does not establish actual control coverage, operating suitability or site savings.

The [follow-up record](JOURNAL.md#120-keep-qualified-private-fields-and-condenser-train-review-at-their-source-boundaries)
preserves the original failures and independently reviewed repairs. The bounded N086 capture and N097 local
handoff are separate from source-owner acceptance and the real company receiving work in N062/N063.



The current design priority is [engineering context across teams](CONTEXT_LIFECYCLE.md): separately owned
scopes, explicit published dependencies, reviewed company identities and preserved conflicting proposals.
The [worked source revision](../examples/pump-revision/README.md) exercises one local maintenance loop with
fictional records. **N094** adds [four owned packets](../examples/team-context/README.md): Process/E&I share a
pinned publication; independent Maintenance and second-site evidence stays current after actual refresh;
same-field proposed strings remain disputed in both input orders. Its company identity mapping is supplied
teaching data. Neither local registers nor selected MCP packets provide concurrent editing, company permissions
or organizational release. Large-team capacity and actual recipient effort remain unmeasured; four fictional
scopes demonstrate composition only. Integration owns the real company handoff through N062/N063.

**N095 — checkout contracts.** A Windows checkout exposed three preexisting failures: regenerated statement and
impact reports differed in line endings, and current drawing inputs no longer matched their saved hashes.
Twelve narrow Git rules now retain the original LF bytes for 20 committed contracts. The new Git regression
checks both ingest and checkout modes while preserving existing raw-pinned packets. No golden, manifest, model
value or metric is rewritten. **N096 — generated drawing identity:** the topology verifier now uses the drawer's
existing text-hash rule for generator/model/layout dependencies. External CRLF inputs no longer fail solely
because the writer folded their line endings before hashing. Genuine edits, other whitespace, historical
generators and key mismatches still refuse. Original source-document pins remain raw; this is drawing-contract
compatibility, not permission to normalize company evidence. See the [format contracts](WORKFLOWS.md).


</details>

</details>
