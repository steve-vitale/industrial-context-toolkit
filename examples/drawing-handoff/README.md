# Turn drawing findings into a receiving brief

An engineer needs to know which requested changes were implemented. An engineering
manager needs to know what to return, what to clarify and which technical review
remains. This rehearsal joins the existing tools to that receiving routine, with
source evidence available behind every summary.

Read the [worked brief](worked/BRIEF.md) first. It covers **two separate fictional
jobs**, a P&ID markup return and an editable valve DXF. The CAD valve is not part
of the P&ID example. The [full workflow](../../docs/DRAWING_HANDOFF.md) explains how
to apply the approach to your own transmittal and approved document environment.

## What the actual runs found

The markup tool retained all seven requests: one supported, one partly supported,
two not supported, two unverifiable and one with a baseline mismatch. The safety
valve removal, incomplete bypass and missing signal remain actionable. An
unrequested fail-action change and missing material evidence remain in the brief.

In the separate CAD job, all three requested equipment-attribute edits are observed,
while **335 unexpected strict differences remain a failed preservation result**.
The brief routes that investigation to the drawing custodian and responsible
engineer. No named owner, acceptance or due date is invented.

## Reproduce it

Python 3.10+ and the repository's pinned ezdxf dependency are sufficient. No CAD UI,
account, network or model call is used. From the repository root, use a new folder:

```sh
python examples/drawing-handoff/reproduce.py --out out/drawing-receiving-rehearsal
```

The runner executes four real CLI calls and checks 14 conditions. It retains the
complete markup and CAD packets, a portable markup replay, the intended collision
refusal, each command/exit/stdout/stderr, `brief.json`, `BRIEF.md` and a complete
file inventory. The CAD command's expected exit 1 records strict differences;
the markup command's exit 0 records a written comparison with open findings.
The collision's exit 2 leaves the first packet unchanged.

## Receive the next revision

The [next-return brief](next-return/REVISION-BRIEF.md) follows the same seven
requests through a corrected consultant return. Five are supported by the new
readings; M05's illegible instruction and M06's baseline mismatch stay open.
The supported safety item still requires engineering review. The separate CAD
preservation issue remains unresolved.

After the command above, run this fixed revision rehearsal into another new folder:

```sh
python -S examples/drawing-handoff/revisions.py --initial out/drawing-receiving-rehearsal --out out/drawing-next-return
```

Three real CLI calls and 11 checks verify the corrected result, its portable
replay and refusal of old readings paired with new drawing bytes. The previous
packet stays unchanged. Both versions, source locations and open engineering
decisions are retained. The [extension plan](REVISION-PLAN.md) precedes its
implementation and execution; the corrected fixture and key were already exposed.

The [plan](PLAN.md) was committed before the rehearsal and runner. These exposed
fixtures already informed their tools. The fixture readings are authored, not
an independent reading of images. Suggested actions are a working aid for review;
no human usability, measured time saving, consultant performance or engineering
acceptance has been established. Native CAD qualification remains unfinished.

For your own records, start with the [markup contract](../../docs/PID_MARKUP_REVIEW.md)
or [CAD receiving command](../cad-handoff/receiving-review/README.md), then prepare
the short brief in the workflow guide. This runner is a fixed tutorial, not an
adapter for arbitrary company records.
