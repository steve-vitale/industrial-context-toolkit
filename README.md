# Industrial Context Toolkit

[![tests](https://github.com/steve-vitale/industrial-context-toolkit/actions/workflows/tests.yml/badge.svg)](https://github.com/steve-vitale/industrial-context-toolkit/actions/workflows/tests.yml)

**Open source tools and repeatable methods for maintenance and engineering teams.** Reconcile equipment and
work-order records, prepare drawing recovery, check a consultant's P&ID markups, review editable CAD returns,
and retain shared engineering context. Prepare sourced draft models from supplied P&ID readings, descriptions
and supported DEXPI exports, with authored layouts for detailed draft drawings. Check supplied ports and
cross-sheet paths; prepare document/photo field candidates; analyze
recorded process and batch data; and generate Ignition/PI staging files. Sources, revisions, review states and
unresolved disagreements stay visible as the work moves between tools and people.

The repository also contains worked tutorials, assembled screen/replay/3D demonstrations and reproducible
task/model benchmarks. These support different parts of a maintained digital twin and engineering knowledge base;
the [supported workflows](docs/WORKFLOWS.md) state which inputs and outputs connect today.
Manual calculation/automation handoff worksheets, engineering onboarding and scoped consulting forms complement
the executable tools. They add no simulator, PLC deployment or managed alert service.

**Status:** prototypes tested on public and fictional inputs. Outputs need engineering review; site accuracy,
live mappings and receiving-platform acceptance need evidence from your environment. The
[feature reference](docs/FEATURES.md) distinguishes examples with an independent agent/model review from those
awaiting one; those reviews are not engineering sign-offs.

**Maintenance or engineering manager?** [Start with the decision you need to make](docs/MANAGERS_START_HERE.md).
The [manager review packet](examples/manager-review/README.md) gives you a no-install brief, owner actions and
copyable scope/review/effort forms. Use the tools below when you or your team are ready to prepare your own records.
For consultant drawing returns, follow the [engineer-to-manager receiving workflow](docs/DRAWING_HANDOFF.md):
requested changes, source evidence, correction actions and the organization's receiving decision.
The [worked resubmission](examples/drawing-handoff/resubmission-worked/BRIEF.md) uses
the reusable command to show which findings change after correction and what stays unresolved.
Changed request scope and missing evidence remain explicit; engineering disposition stays pending.

**Using an agent?** Point it at this repository and ask:

```text
Read README.md and docs/AGENT_START_HERE.md. Help me choose and finish one useful
maintenance or engineering job using the records I have. Show a concrete example
if I have not supplied records yet. Ask only what changes the next step.
```

The [reusable maintenance intake](docs/MAINTENANCE_INTAKE.md) turns your explicitly mapped equipment and work-order
exports into a sourced offline packet, with no P&ID required. It retains earlier packets for returned exports and
later replacements. The [fresh-agent rehearsals](examples/agent-rehearsal/README.md) retain actual sessions and
their limitations. Self-service use needs no contact with the author.

**Already using Copilot with SharePoint?** Use that access for document questions and comparisons. Toolkit
reports and tables can stay there too. [MCP is optional](docs/INTERNAL_CONNECTIVITY.md#if-copilot-already-reads-sharepoint-why-add-mcp):
it exposes named queries into prepared records or separately implemented services. This repo's starter serves
read-only snapshots; it does not search SharePoint, refresh sources or connect to a live CMMS/historian.

## Tools, tutorials and case studies

[Repository structure and canonical references](docs/REPOSITORY_GUIDE.md) ·
[Reproduce a current workflow](docs/REPRODUCE_A_WORKFLOW.md) ·
[Complete feature evidence](docs/FEATURES.md) · [Script roles](docs/SCRIPTS.md)

| Choose a destination | What you get |
|---|---|
| **Tools — use your inputs** | Draft models/drawings, review and revision tools, graph/context, recorded-data analysis, platform staging and bounded read-only MCP. [Choose a job below](#start-wherever-you-are); the [format map](docs/WORKFLOWS.md) states the file contracts. |
| **Tutorials — learn, then substitute your records** | [P&ID to review bundle](examples/own-drawing/README.md), [description to draft drawing/model](examples/from-description/README.md), or [DEXPI to model](examples/from-dexpi-xml/README.md). |
| **Case studies and evaluation — inspect the evidence** | [TE/OPEN100 screens, recorded replay and 3D orientation examples](docs/DELIVERABLES.md), [results and limits](docs/RESULTS.md), and [task/model benchmarks](benchmarks/README.md). The assembled demos retain their case-specific inputs and limits. |

## Start wherever you are

These tools accept your own records in their documented formats. Choose the work product you need first.

**Working on a plant problem?** Start with [maintenance records that disagree](docs/MAINTENANCE_START.md)
or [missing or outdated engineering drawings](docs/DRAWING_RECOVERY.md). The
[replacement walkthrough](examples/maintenance-handoff/README.md) follows one fictional valve through the
work order, equipment register, datasheet, field evidence and next revision. For help with a larger scope,
[connect with me on LinkedIn and message me there](https://www.linkedin.com/in/steve-vitale/).
See [working together](docs/WORK_WITH_ME.md) for inputs, deliverables and how a scoped engagement starts.

| Your engineering job | Starting material and guide | Work product |
|---|---|---|
| Reconcile maintenance records | [Equipment and replacement work-order exports](docs/MAINTENANCE_INTAKE.md) | Original-row disagreements, identity/coverage questions, proposed owner actions and a retained next-revision comparison. |
| Build your plant's first draft asset model | [P&ID image](examples/own-drawing/README.md) or [DEXPI XML](examples/from-dexpi-xml/README.md) | Sourced assets and represented connections, review material, graph and platform-staging routes. |
| Build from process knowledge | [Written description](examples/from-description/README.md) | An authored, source-linked model and layout, checked locally and rendered as draft P&ID sheets and exports. |
| Check whether a consultant incorporated P&ID markups | [Original, markups sent out and returned revision](docs/PID_MARKUP_REVIEW.md) | A check for each requested change, other observed changes, source locations and a correction/clarification queue. Readings are supplied by an engineer or approved assistant. |
| Prepare a receiving brief across supplied drawing returns | [One receiving job](docs/DRAWING_HANDOFF.md#run-one-receiving-job) | One command runs the existing markup and/or supported DXF checks, retaining all findings, source-linked actions and a portable job. Owners and the receiving decision remain pending. |
| Review a returned editable CAD drawing | [Profiled DXF pair and optional edit plan](examples/cad-handoff/receiving-review/README.md) | Readable attribute/field/layout comparison, exact drawings and a complete unresolved strict queue. Qualify the receiving editor separately. |
| Propose equipment-data edits without resaving geometry | [DXF equipment-data exchange](examples/cad-handoff/data-review/README.md) | A local form or agent proposal and a source-preserving value-span candidate. The original drawing stays intact; native full-save qualification remains separate. |
| Check exact endpoints and cross-sheet routes | [Port checks](docs/PID_CONNECTIONS.md) · [graph-path review](docs/PID_GRAPH_QUESTIONS.md) | Wrong-input/missing connection checks, source-qualified paths, unresolved continuations and affected-answer revisions from supplied readings/graphs. |
| Prepare fields from photos and scanned documents | [Nameplate exercise](examples/photo-to-record/README.md) · [document text](docs/DOCUMENT_TEXT.md) | Text/field candidates with source locations, unreadable values and review needs. OCR does not establish installed asset identity. |
| Review and enrich the model | [Sourced statements](docs/STATEMENT_REVIEW.md) · [model correction and mapping](docs/REVIEW_LOOP.md) | Checkable claims, supported local corrections and supplied signal mappings. |
| Investigate controls or performance | [Loop list audit](examples/loop-audit/README.md) · [question engine](docs/OPPORTUNITY_SCREEN.md) | Explicit discrepancies, investigation questions and evidence requests tied to represented assets. |
| Analyze or replay recorded process data | [Historian CSV](examples/historian-csv/README.md) · [batch analysis](examples/batch-analysis/README.md) · [analytics guide](docs/PROCESS_ANALYTICS.md) | Normal bands, phase calculations, selected record joins and a read-only OPC UA replay route for local tests. |
| Estimate a measured change | [Impact calculation](examples/impact-estimate/README.md) | First-draft energy, cost and CO2e calculations with measurements, assumptions and constants visible. |
| Keep and exchange engineering context | [Context register](docs/CONTEXT_REGISTER.md) · [read-only MCP](examples/internal-mcp/README.md) · [owned team packets](examples/team-context/README.md) | Source dependencies, retained answers and selected snapshots to hand to the next team or company system. |
| Connect plant records and documents site-wide | [One map](docs/ONE_MAP.md) · [document text extraction](docs/DOCUMENT_TEXT.md) · [a read P&ID on the map](examples/drawing-to-map/README.md) | One graph of P&IDs, equipment and instrument records, datasheets and documents; conflicts written to owner-specific review queues. |
| Keep the map current through plant routines | [Running the map](docs/RUNNING_THE_MAP.md) · [an MOC on the map](examples/one-map/README.md#the-pasteurizer-through-an-moc-pid-revision-moc-open-and-close-work-order-walkdown) | P&ID revision change reports, MOC-open affected records by owner and the closeout check, work order closeout, walkdown rulings, HACCP/PHA/criticality change flags. |
| Prepare platform files and supplied point mappings | [Generation/export contracts](docs/WORKFLOWS.md) · [review and mapping](examples/review-and-mapping/README.md) · [PI mapping](docs/PI_MAPPING.md) | Draft Ignition tag files, PI AF staging and explicit mapping records. Review signal identities and verify acceptance in the receiving system. |
| Evaluate or improve a method | [Drawing comparison](examples/vendor-evaluation/README.md) · [task/model benchmarks](benchmarks/README.md) · [review a frozen model](benchmarks/source-support/artifact-values/README.md) | Compare saved answers against reviewed source/key cases, with missing answers, mistakes and evidence limits visible. |
| Retain team knowledge or scope outside help | [Onboarding contributions](docs/ENGINEERING_ONBOARDING.md) · [consulting starter](examples/consulting-start/README.md) | Source-qualified notes and subsequent revisions, or manual scope/quote/receiving forms for one agreed job. Calculation and automation worksheets record a review basis; they do not implement a solver or controls. |

**Prefer a first result without installation?** Use the [first-question guide](examples/first-pilot/README.md)
by hand or with company-approved Copilot. For a team assignment, the [organization starting guide](docs/ORGANIZATION_START.md)
separates ready-to-run steps, source preparation and continuing ownership. [Dependencies](docs/DEPENDENCIES.md) vary by route.

## Try one concrete result

The [public-sheet tutorial](examples/own-drawing/README.md) uses a committed drawing and saved extraction to
build a draft asset model and review bundle offline. From a clone's repository root with Python 3.10 or newer,
choose a new output directory (`my-bundle` must not already exist):

```sh
python -S scripts/import_site_drawing.py --manifest examples/own-drawing/manifest.json --out my-bundle
python -S scripts/deliverable_report.py my-bundle
```

No accounts, model calls or additional packages are needed for this worked example. Open
`my-bundle/REPORT.html` to inspect the drawing, extracted items, review states and next steps.
The bundle includes:

```text
my-bundle/
  plant_model.json          Draft assets and represented connections
  review_queue.csv          Items for a reviewer to confirm, correct or reject
  svg/sheet_0.svg           Logical links over the drawing
  ignition/tags.json        Draft tags with unmapped placeholder values
  pi/                      PI AF staging and receiving-system instructions
  REPORT.html              Readable review report
```

The [committed sample report](examples/own-drawing/deliverable/REPORT.html) shows the same kind of output.
This is a public development-sheet demonstration, not a new accuracy result. To use your own drawing, follow
the tutorial's input and extraction steps, then review the model and supply the mappings your target system needs.

## Build and maintain a context map

The map represents site, plant, unit, system and equipment, including what's piped to, measures and controls what,
with each team's records tied to those identities. Supply a reading of each P&ID sheet through
`one_map.py sheet-from-prediction`, then compare it with the maintenance equipment export, instrument index and
loop list. Matches get spot checks; missing or disagreeing items enter review, with safety items always included.
Where no records exist, the supplied P&ID reading can start their unverified drafts. Datasheets supply ratings;
the P&ID supplies represented tags, connectivity and the control scheme.

Conflicts are retained in **owner-specific review queues** for people to distribute and resolve. The tools do
not send notifications or authenticate assignments. For a P&ID revision, supply the revised sheet reading and
rerun the build; unchanged sheet fragments are reused when their inputs and parsing code still match. The
[context register](docs/CONTEXT_REGISTER.md) retains answer dependencies; explicitly refresh it to reopen
answers affected by revised sources. These steps require explicit local runs; the tools do not monitor sources.

See [one map](docs/ONE_MAP.md#the-path), the [two-plant example](examples/one-map/README.md) where Plant 2 has
no records yet, and [one public P&ID sheet read end to end](examples/drawing-to-map/README.md).

**Input scope today:** equipment/instrument records and datasheets use structured CSV contracts. Supported
registers also cover work orders, PM plans, spares, calibration, critical control points and isolation records;
documents can cover or mention tags. The [one-map contract](docs/ONE_MAP.md) specifies the bounded checks.
These checks produce review needs, not operating authorization or an accepted safety assessment.

## What connects today: the hub and spokes

1. **Build the draft.** An image route uses a supplied or approved-assistant extraction; a description route
   uses an engineer/assistant-authored model and layout; supported DEXPI XML is read directly. Each produces
   a documented model form. The [workflow map](docs/WORKFLOWS.md) shows which outputs that form supports.
2. **Review and enrich it.** Check source identities, asset relationships and missing items, make supported
   corrections, and add the independent process/controls evidence the investigation needs. Detailed drawing
   geometry and engineering interpretation remain authored work.
3. **Connect the useful parts.** Generate graph/context snapshots, draft Ignition/PI files and investigation
   material. Supply reviewed point identities and verify selected connections in an approved lab or receiving
   system. The [connectivity guide](docs/INTERNAL_CONNECTIVITY.md) covers permitted Copilot, local and IT/OT paths.
4. **Maintain the evidence and decisions.** Retain source versions, refresh affected answers explicitly and keep
   review history. Company systems own accepted records, permissions, releases and continuing responsibility.

The reusable generators build from the model you supply. The TE gateway builder and recorded replay assemble
one particular case study; use its architecture as a reference while following the tool guides for your plant's
model, mappings and target environment. The [feature reference](docs/FEATURES.md) lists individual tool evidence.

**Bring a better reader.** Today's drawing reader drafts; trained models and commercial digitizers may read
drawings better ([prior art](docs/PRIOR_ART.md)). The surrounding review, provenance and export tools can use
another reader's output in the documented format. Use the [reader integration guide](docs/PLUG_IN_A_READER.md),
[vendor-evaluation kit](examples/vendor-evaluation/README.md) and [reader leaderboard](benchmarks/LEADERBOARD.md)
to compare results on matched sheets. [Contributing a public drawing with a verified key](docs/CONTRIBUTE_A_PID.md)
helps evaluate every reader on more sources. The [demo series](docs/DEMO_SERIES.md) shows how selected tools and examples connect.

Need public records to try first? The [public-data guide](examples/public-data/README.md) adds pinned maintenance
text, nameplates, energy readings, experimental batches, flowsheets and technical documents, with commands,
actual parser results and the remaining adapter/key requirements. The [linked maintenance cohort](examples/public-data/round-4/README.md)
adds public assets, dated work orders, parts movements and labor from one municipal system, with relationship
checks and interpretation limits. The [latest additions](examples/public-data/round-5/README.md) include
industrial batch logs, packaging alarms and NIST CAD/STEP references, with source rights and repeatable fetches.
Acquisition is separate from evaluation.

## Start with one question

The [first-question guide](examples/first-pilot/README.md) owns the no-install path and copyable brief.
Keep the result and the reasons behind it together; a saved note does not maintain itself when sources change.

Leaders and mentors can use the [onboarding guide](docs/ENGINEERING_ONBOARDING.md) to scope the assignment.
The [knowledge-only exercise](examples/engineering-onboarding/README.md) includes a worked evidence note and
a starter for your permitted records. The optional [contribution and revision tutorial](examples/engineering-onboarding/contribution-loop/README.md)
shows how to capture your selected text records and authored findings, preserve a combined answer's dependencies,
and reopen it when either source changes. It includes a fermentation-record example; practical team benefit remains unmeasured.

<details>
<summary>Tutorial: follow a pump from description to evidence request</summary>

[Follow one pump through the actual files](examples/from-description/assisted/PUMP_WALKTHROUGH.md):
description → authored model → draft drawing → investigation question → evidence request.
Then use the [own-description steps](examples/from-description/README.md#use-your-own-description-with-an-approved-assistant)
to substitute your source and authored response. The supplied pump is illustrative; it teaches the file contracts
and review process rather than establishing accuracy on your plant.

![Illustrative pump and tank draft produced by the description workflow](examples/from-description/assisted/result/pid/D1.png)

</details>

## From a first assignment to shared engineering context

[![Engineering foundations: what each layer unlocks and the managed-product handoff](assets/engineering-foundation.svg)](docs/ENGINEERING_FOUNDATION.md)

The [foundation roadmap](docs/ENGINEERING_FOUNDATION.md) explains the intended end goal, optional RAG/MCP roles,
and the handoff when shared context needs a sustainably operated company product. No single product must own
every layer or replace the existing engineering and operations systems.

Keep the selected records and the reasons behind changes together as more people rely on them. The
[source-revision tutorial](examples/pump-revision/README.md) and [owned-team tutorial](examples/team-context/README.md)
show how supplied evidence reopens affected answers while preserving history and independent context.
Use the [lifecycle guide](docs/CONTEXT_LIFECYCLE.md) to plan the handoff into your company's maintained home.
For a small team, a whole site or a global network of 50–100 plants, use the
[scaling guide](docs/SCALING_ENGINEERING_CONTEXT.md): failure modes, upgrade signals, robustness checks and when
to evaluate a managed context/governance service alongside existing company systems.

## Status

The tools are prototypes tested on public and fictional inputs. Their output is a draft for engineering review;
site accuracy, installed signal identity, native platform acceptance and operational benefit need evidence from
your environment. Public benchmark numbers do not transfer automatically to a new drawing style or plant.

- **Use it:** [Documentation map](docs/README.md) · [Plan work at your plant](docs/AT_YOUR_PLANT.md)
- **Connect it:** [Approved clients and IT/OT paths](docs/INTERNAL_CONNECTIVITY.md)
- **Assess it:** [Results and limits](docs/RESULTS.md) · [Current implementation status](docs/STATUS.md)
- **Improve it:** [Contribute cases, model runs and tested changes](CONTRIBUTING.md)

Code is MIT; drawing-derived assets have their own terms in [NOTICE.md](NOTICE.md).
AI coding agents wrote most of the implementation; the [journal](docs/JOURNAL.md) records authorship and mistakes.

<details>
<summary>Links retained for earlier research references</summary>

### Results (held-out drawings, and how they were used)

Moved to [results and interpretation](docs/RESULTS.md#results-held-out-drawings-and-how-they-were-used).

### From a first packet to company context

See [from a first assignment to shared engineering context](#from-a-first-assignment-to-shared-engineering-context).

### Drawings only, process knowledge only, or both

See [supported workflows](docs/WORKFLOWS.md) and the [TE/OPEN100 demo comparison](docs/DELIVERABLES.md).

### Tutorial: reproduce it

Use the [research reproduction guide](docs/REPLICATE_AT_YOUR_PLANT.md).

### What's a tool and what's a record

Use the [documentation map](docs/README.md#reference-and-research-records) and [script reference](docs/SCRIPTS.md).

</details>
