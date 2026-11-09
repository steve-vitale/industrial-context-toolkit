# Start with a maintenance or engineering decision

Choose one system where finding and reconciling the records repeatedly delays work. The first useful result is
a checkable answer and a short list of owned corrections. A site-wide model or new software platform can follow
when the work justifies it.

**Have an agent help:** use the [task-first guide](AGENT_START_HERE.md) and [reusable export intake](MAINTENANCE_INTAKE.md).
The agent can inspect the records and prepare supported inputs for you; ask about meanings or identities that
are unclear. You can start with a few records and a useful partial answer before completing a larger scope form.

If your Copilot already retrieves the required SharePoint documents, start there. You can use these methods
and publish the resulting reports there without MCP. [Add a service interface only for a concrete recurring need](INTERNAL_CONNECTIVITY.md#if-copilot-already-reads-sharepoint-why-add-mcp),
such as repeated exact-record lookups; an MCP connection itself adds no engineering validation.

**No installation needed:** [read the manager example](../examples/manager-review/BRIEF.md) or
[download its offline packet](../examples/manager-review/manager-review.zip?raw=1). The packet includes a browser
brief, source snapshots and blank forms. It is fictional; no plant has accepted it or measured a saving.

## Choose the job

| Your recurring problem | Start with | What your team gets | Manager's receiving check |
|---|---|---|---|
| Closed replacement jobs leave equipment records wrong | [Maintenance reconciliation](MAINTENANCE_START.md): selected closed work orders, equipment export, datasheets and permitted field evidence | Conflicting installed-record values, source locations and owner corrections | Confirm identity and accepted values, then read the corrected record back from the CMMS. |
| The same assets keep generating work, but the history is scattered | [Maintenance history](MAINTENANCE_HISTORY.md): selected asset/work-order exports and optional parts/labor exports | Offline asset histories, recurring-work candidates, justified booked-hour subtotals and source-linked gaps | Confirm equipment versus location identity, planned work and parent/correction records before investigating failure. Request missing evidence and retain the next export. |
| Work planning starts by searching for drawings, manuals and asset details | [Record organization](ORGANIZATION_START.md) and the [manual packet](../examples/manager-review/templates/scope.md) | A scoped source inventory, missing evidence and a handoff for the planner | Have the intended planner find the right revision and identify what is still needed. Parts compatibility and a complete job plan require separate review. |
| Missing or outdated P&IDs hold up engineering work | [Drawing recovery](DRAWING_RECOVERY.md): available sheets/redlines, equipment records, field knowledge and target CAD requirements | A drawing backlog, reconstruction questions and a qualified editable-delivery scope | Open/edit/save in the named receiver; verify identities, attributes, connections and explicit losses. The public DXF case has not passed this acceptance. |
| Consultants return revised P&IDs, but requested markups may be missed | [Markup return review](PID_MARKUP_REVIEW.md): original, exact instructions sent out and returned revision | A check for each annotation, partial/missed changes, other observed changes and source locations | Review reading/inventory coverage, trace affected connections and disposition open issues before accepting the drawing. A found tag or a matching prepared value alone is insufficient. |
| Project or change closeout says records were updated, but no one can show which | [Change/closeout checks](RUNNING_THE_MAP.md): retained before/after records and selected affected tags | Changed/unchanged records by owner, open gaps and review confirmations | Each owner verifies required changes or justifies no change; the responsible company process makes the closeout decision. |

For a return containing the right tags but possibly the wrong input, use
[port-aware revision checks](PID_CONNECTIONS.md) and assign the retained correction queue.
For the full drawing-return routine, use [the engineer/manager receiving workflow](DRAWING_HANDOFF.md)
and its [worked correction and clarification brief](../examples/drawing-handoff/worked/BRIEF.md).
The [corrected-return brief](../examples/drawing-handoff/next-return-2/REVISION-BRIEF.md)
keeps both versions and separates supported corrections from unresolved instructions and pending approval.
For a prepared multi-sheet graph, the [path review](PID_GRAPH_QUESTIONS.md) shows supported or qualified
connections and missing continuations. A missing route is an evidence gap, not proof of disconnection.
To agree a bounded outside assignment, use the [paid review scope and acceptance forms](../examples/consulting-start/README.md).

For repeat-failure investigation, first assemble the work-order descriptions, identity/operating context and
permitted observations behind a specific question. The [first-question brief](../examples/first-pilot/README.md)
and [recorded-data routes](PROCESS_ANALYTICS.md) support investigation. This toolkit does not determine root cause,
optimize PM intervals or calculate defensible MTBF from unreviewed work-order text.

## Agree the first assignment

Copy the [scope form](../examples/manager-review/templates/scope.md) into your approved company location. Name
the question, site/unit/assets, intended decision and exclusions. Identify the spending/scope approver and the
recipient who will actually use the result; they may be different people. Choose an existing work order,
drawing revision or project milestone to which the check belongs.

Assign a coordinator, each record owner, an engineering reviewer and the person who accepts the receiving
format. A department label in a generated queue is not an assigned person. Agree a due date and available
review capacity before expanding the scope. Use the company's priorities and consequence assessment; red,
amber and green in this repo describe particular software checks, not an approved asset criticality ranking.

Request only permitted exports needed for the job. At minimum retain IDs, revisions/cut-off, unit coverage,
units, source authority by fact, missing fields and identity mappings. The [input contracts](ONE_MAP.md)
describe the structured routes; use the manual source form when exports need preparation. An absent row in a
partial export does not establish an absent asset, PM or spare. Keep originals in their approved home.

## Run the review, then return the correction

Use the [review form](../examples/manager-review/templates/review-log.md) in the team's existing work system.
Start with issues that block the declared decision, retain other findings, and assign each correction or evidence
request to a named owner. Keep the supporting source locator with it. Consolidate duplicate findings explicitly;
retain all their evidence. Document why a finding needs no change rather than deleting its history.

For the example, a field ruling settles which serial to use while the CMMS export still contains the old serial.
The record correction remains open. A green row only says that the equipment was located on a drawing; it
cannot close that correction, the PM evidence gap or the unresolved size/design question.

The receiving owner confirms the actual corrected version, exact ID/value and date. A proposed CSV, a closed
work order, an acknowledged alert or a signed local worksheet cannot substitute for that readback. Preserve
the earlier source and decision history and try one subsequent change. No part of the packet authorizes field
work, release, startup or a change of operating limits.

## Decide whether to continue

Use the [effort and outcome form](../examples/manager-review/templates/effort-and-outcome.md). Compare the same
question and source coverage against the current method, including preparation, field verification, review,
rework, recipient reconstruction and receiving-system effort. Record errors and missing evidence alongside time.
Use continue, narrow, change or stop with the recipient's reason. Expand only after the intended person can
reconstruct the result and the receiving owner can maintain it.

Do not turn counts of flags or linked records into uptime, PM compliance or cost savings. Those require their
own definitions, complete coverage, operating/exposure data and qualified review. No sample ROI or benchmark
percentage in this toolkit is a site saving. Price a consulting scope after source/fieldwork uncertainty is understood.

This decision-first approach is consistent with NIST's discussion of
[different information needs for maintenance decisions](https://www.nist.gov/publications/selecting-optimal-data-creating-informed-maintenance-decisions-manufacturing)
and PNNL's discussion of [prioritizing O&M work with defined metrics](https://www.pnnl.gov/projects/om-best-practices/prioritizing-om-actions).
These resources support the method, not the accuracy or benefit of this toolkit's examples.

For help with preparation, a larger package or ongoing ownership,
[connect with me on LinkedIn and message me there](https://www.linkedin.com/in/steve-vitale/).
