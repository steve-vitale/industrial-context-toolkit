# Optional unit requirements and automation handoff review

Use when a real project needs agreement between process, maintenance and automation owners. Copy to an
approved private location and attach it to the agreed [scope](SCOPE.md). This is a manual review worksheet;
it is not an MTP/rMTP file, a complete functional design specification, an executable control strategy or
a conformance assessment. Ordinary maintenance/drawing reviews do not require this extension.

## Identify one unit and its receiving job

Assignment / site-qualified unit and asset IDs / revision: ____
Job and milestone (for example, review a package-unit supplier's revised functional description): ____
Process / maintenance / automation reviewers and spending approver: ____
Included equipment, module boundary and external interfaces: ____
Approved source inventory with exact revisions, locators and owners: ____
Receiving team / existing software and version / required delivery format: ____
Selected scope and exclusions, including field verification: ____

## Separate what is requested from what has been demonstrated

Give each requirement its own ID. Do not overwrite the original request with a supplier's response.
Keep a proposed function distinct from an observed existing function. Unknown behavior remains an
evidence request; do not infer it from a line, symbol, template or neighboring plant.

| Requirement ID and requested behavior | Owner's source/revision/locator | Supplier response and exact returned source | Receiving observation, conditions and evidence | Disposition / intended owner / next check |
|---|---|---|---|---|
| ____ | ____ | ____ | Not tested / ____ | Supported / partial / disagreement / unverifiable / ____ |

Record only the applicable, sourced details for the agreed scope:

- Function or service, operating envelope and equipment boundaries.
- Modes, states, phase/sequence transitions, start/stop conditions and responsibilities at interfaces.
- Required inputs/outputs and exact identities, units, ranges, signal direction and meaning.
- Setpoint/parameter definitions and the source of each value; blank does not mean zero or default.
- Applicable alarms, permissives, trips, reset conditions and documented response to signal/power loss.
- Maintenance, local/manual and restart behavior where the approved basis describes them.
- Required operator information and the owner of each unresolved behavior or interface.

This list prompts evidence collection. It supplies no universal control requirements or safe values.
Changes to protective functions, alarm response or isolation need the client's applicable engineering
and operating processes; a completed table cannot authorize them.

## Reuse an existing pattern with an explicit applicability review

Candidate pattern / source project / exact version / reuse permission: ____
Applicable service and assumptions / exclusions: ____
Differences in fluid, equipment, interfaces, modes and operating basis: ____
Assumptions still unknown / owner and evidence needed: ____
Reviewer decision and required changes for this unit: ____

## Agree the receiving check before the return

Named requirement(s) / returned artifact and version: ____
Check type: document comparison / offline import-readback / simulation / separately authorized site test ____
Acceptance condition, permitted environment and actual evidence to retain: ____
Responsible reviewer and disposition authority: ____
Required standards profile/version, if any, and evidence of receiver support: ____
CAD, DEXPI or MTP exchange included only under its own named acceptance scope: ____

Keep receipt of a document, evidence supporting a requirement and engineering release separate.
A supplier's statement is not a successful operational test. Tool execution is not authenticated approval.

## Receive one correction and its next revision

New source / revision / changed requirement IDs: ____
Affected drawings, lists, interface descriptions and retained answers: ____
Prior evidence retained at / checks repeated / disagreement remaining: ____
Authoritative receiving record and readback / owner / date: ____
Acceptance or next evidence request / actual responsible person / date: ____

Use [REVIEW_AND_NEXT_JOB.md](REVIEW_AND_NEXT_JOB.md) to capture total effort and demand for further work.
The [research note](../../docs/COMPETITIVE_WORKFLOWS.md) explains the vendor inspiration and current limits.
