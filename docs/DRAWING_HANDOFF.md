# Review a consultant's drawing return

Use this workflow for one drawing transmittal: **what was requested, what the
return shows, what else changed, and who needs to resolve the open items?**
An engineer prepares and checks the evidence. An engineering manager uses the
brief to arrange corrections, resolve scope and route the receiving decision.
Start with one sheet or a clearly bounded set of sheets.

## Run one receiving job

Use [receive_drawings.py](../scripts/receive_drawings.py) to run the existing
markup and/or supported DXF checks and assemble one brief from their results:

```sh
python scripts/receive_drawings.py --manifest YOUR_JOB.json --out NEW_RECEIVING_FOLDER
```

The job format is shown in [job.json](../examples/drawing-handoff/job.json).
Try the fictional example from the repository root:

```sh
python scripts/receive_drawings.py --manifest examples/drawing-handoff/job.json --out YOUR_NEW_FOLDER
```

Compare the [generated brief](../examples/drawing-handoff/job-worked/BRIEF.md),
then replace the example's references with your own prepared inputs.
Give each drawing its own ID, then supply `markup_manifest`, `cad` or both.
Paths resolve from the job file. A CAD entry names `before`, `after` and an
optional attribute `plan`. A markup manifest is the existing source-bound
original/instructions/return and readings contract described below; your agent
prepares those readings using its available reader. This command performs no
image interpretation. Markup-only use requires the Python standard library;
DXF use requires the repository's pinned CAD dependency.

Open `BRIEF.md` for the receiving actions and `brief.json` for full source checks
and locations. Each detailed checker packet retains its original evidence.
`job.json` in the output is rewritten to those retained sources, so another agent
can reproduce the job in a new folder. `input-job.json` keeps the exact submitted
job. No named owner, engineering acceptance or CAD/readable-sheet equivalence is
invented. If both representations are supplied for one drawing, their physical
correspondence remains an explicit review item.

## Receive a correction or resubmission

Keep the original drawing IDs and original/instruction scope in a new job. Supply
fresh source-bound readings for the new return, then run:

```sh
python scripts/receive_drawings.py --manifest YOUR_NEXT_JOB.json --previous EARLIER_RECEIVING_FOLDER --out NEW_RECEIVING_FOLDER
```

The command verifies the earlier packet inventory and reproduces its findings
from retained inputs before comparing. `BRIEF.md` adds a previous/current table;
`revision.json` retains each finding, both versions and current source checks.
The new packet carries the earlier packet and writes `previous_packet` into its
portable `job.json`, so replay needs only the new folder. Keep output outside the
earlier packet. Inventories detect changes; they are not authenticated signatures.

Changed original bytes, original readings, request inventory or CAD plan are
explicit **changes of basis**. Omitted drawings/checks remain unresolved follow-ups.
A disappeared collateral finding needs a current source-bound observation or an
unchanged CAD field check to establish that it matches the original; missing
evidence does not close it. Historical follow-ups remain pending for reconciliation.
Current support and restored values still require engineering disposition.

Try [resubmission-job.json](../examples/drawing-handoff/resubmission-job.json)
with `--previous examples/drawing-handoff/job-worked`. The fictional markup return
supports five of seven requests; illegibility, baseline mismatch, unknown material
and safety review remain visible. Its separate CAD return still has 335 strict
differences. The [worked resubmission](../examples/drawing-handoff/resubmission-worked/BRIEF.md)
retains those distinctions. No reader, CAD UI or engineering acceptance is invoked.

## Choose the checks that answer your question

| Your question | Input and executable route | Result to use |
|---|---|---|
| Did the consultant implement the marked-up P&ID correctly? | Retain original, exact markups/instructions sent out and returned revision. Follow [markup review](PID_MARKUP_REVIEW.md), using separately prepared source-bound readings. | A result for every inventoried request, original/returned page locations, other observed changes and coverage gaps. |
| Did an editable DXF return preserve the drawing and equipment fields? | Retain original and returned DXFs plus the exact attribute edit plan. Use [CAD receiving review](../examples/cad-handoff/receiving-review/README.md) on its supported identity profile. | Planned/missing/unexpected attribute values and the complete strict drawing-difference queue. |
| Can I correct equipment data while retaining the original drawing bytes? | Use the [source-bound equipment-data review](../examples/cad-handoff/data-review/README.md). | A proposed single-line attribute edit with exact original/before-value binding and source-preserving candidate bytes. |

For a P&ID delivered as both readable pages and editable CAD, use the first two
checks together. A matching equipment value does not establish correct piping,
port connectivity, fail action or control function. The current CAD edit route
handles declared equipment attributes; general geometry editing, native DWG and
intelligent-P&ID database exchange need their own demonstrated methods.

## Before sending work out

The responsible engineer retains the exact baseline and the exact instructions
sent to the drawing author. Record the drawing/sheet identity, revision, intended
change, reason and source location. Split compound instructions: adding a bypass
valve and connecting both ends are separate checks. Record unclear instructions
as questions. Freeze this request list before assessing the returned revision.

The manager or project coordinator confirms the transmittal scope and who owns
technical review and the released drawing. Agree what the consultant must return:
readable sheets, editable source/project files where required, revision details
and a response against each request. The toolkit supplies working records; the
organization's transmittal and approval process remains authoritative.

## When the return arrives

1. **Confirm the baseline and return.** Check title blocks, sheet correspondence,
   revision and transmittal scope against the actual records. Keep exact files in
   a new working folder. Uncertain identity or missing sheets stay open.
2. **Record what the return shows.** Prepare original/returned readings with page
   and region references. Inventory every markup, including illegible ones. Trace
   connection endpoints and continuations. An absent extraction row is unknown.
3. **Run the applicable comparison.** Use the linked commands above. Open the
   readable report and follow its source links; keep the whole output folder.
   Check safety items even when the comparison says supported.
4. **Review collateral changes and coverage.** Investigate unrequested changes,
   unread areas and CAD strict differences. Counts identify work to examine;
   added/removed CAD handles are not counts of changed physical assets. Inspect
   appearance, paper layouts and editability in the intended receiving editor.
5. **Prepare the decision brief below.** Keep each finding tied to its request,
   evidence and required resolution. Have the responsible engineer review it.

An approved assistant with access to SharePoint can prepare readings and this
brief within that environment. MCP is optional: the local comparison adds explicit
source/revision binding and retained findings. Access to documents alone does not
establish complete markup coverage or correct engineering interpretation.

## A brief for the receiving decision

Keep this at the front of the packet. Reference the detailed report rather than
copying hundreds of CAD differences into a meeting note.

```text
Drawing / sheets and transmittal:
Exact original, markup/instruction and returned revisions:
Review scope / unchecked sheets or regions:
Requested changes supported / partial / missed / unverifiable:
Safety items needing engineering review:
Unrequested changes and unresolved CAD preservation findings:

Item | Request / finding | Original and returned evidence | Next action
     | Suggested responsible role | Named owner (unassigned until confirmed)
     | Required closure evidence | Disposition / due date

Decision requested: accept into the organization's release process,
return for correction, or escalate for technical/scope clarification.
Responsible engineer's recommendation and reason:
Authorized decision and record reference: pending
```

| Finding | Useful next action | Typical review responsibility |
|---|---|---|
| Requested change missing or partly implemented | Return the exact incomplete checks for correction. | Drawing author; responsible engineer checks the resubmission. |
| Wrong baseline, unclear instruction, conflicting or missing evidence | Clarify intent or obtain the missing record before judging completion. | Requesting engineer / project coordinator. |
| Safety-relevant or unrequested functional change | Assess the effect and applicable change-control requirements. | Responsible discipline engineer / designated technical authority. |
| Unresolved CAD preservation, appearance, layout or editability difference | Retain the return, investigate the exact difference and agree a supported delivery route. | CAD/drawing custodian with the responsible engineer. |
| Supplied checks supported and other review complete | Present the evidence for the organization's receiving/release decision. | Authorized reviewer; no software-generated acceptance. |

Several actions can apply to the same return. A manager can request corrections
while an engineer investigates an unrequested change. Unknown owners remain
unassigned. A supported row does not close a separate coverage or preservation
finding. The software does not send messages, assign work or release the drawing.

## Close the loop on the next revision

Keep the first packet and decisions. A resubmission is a new exact return with
new bound readings and a new comparison folder. Recheck every outstanding item,
the corrected region's connections and other observed changes. Retain resolved
and unresolved history; do not carry a previous supported label onto a new source.
After organizational acceptance, reconcile accepted records through the existing
[map revision route](RUNNING_THE_MAP.md), with installed-state authority explicit.
The [corrected-return rehearsal](../examples/drawing-handoff/next-return-2/REVISION-BRIEF.md)
shows a useful partial closeout: five requests supported by current readings,
two still open, safety review pending and a separate CAD finding still unresolved.

For concurrent edits, the [two-asset revision rehearsal](../examples/cad-handoff/qualification/full-ui-22/REVISION-LOSS-BRIEF.md)
shows why the original scope must stay visible: a selected second plan passes
its own comparison while an unrequested SERIAL remains a difference against
the original request. Keep that question for the responsible reviewer; changing
the baseline does not approve it.
The [actual native-return rehearsal](../examples/cad-handoff/qualification/full-ui-22/NATIVE-REVISION-BRIEF.md)
adds saved CAD files and native edit/reopen checks. Its second proposals preserve
the returned files while keeping the original native-save failures unresolved.

For a first trial, compare an agent-assisted review with an engineer's normal
review on the same bounded transmittal. Record preparation, review and correction
effort separately, missed/false findings and remaining uncertainty. No timing or
benefit is established by the repository's fictional simulations.

The [receiving rehearsal](../examples/drawing-handoff/README.md) includes real
commands, saved packets and a worked decision brief. The [CAD qualification protocol](../examples/cad-handoff/qualification/PROTOCOL.md)
defines the separate software evidence needed for a declared format/editor route;
it does not replace this project receiving decision. For a larger drawing backlog,
[connect with me on LinkedIn and message me there](https://www.linkedin.com/in/steve-vitale/).
