# Goal: isolation boundary candidates, a proof of concept (written 2026-11-11, before any method is built)

Pre-registered in the style of [GOAL_ROUND6.md](GOAL_ROUND6.md). Nothing below has been built or run. Changing this
page later is allowed, but only in a new dated commit that says what changed and why.

## What changed, and what did not

Until 2026-11-11 the standing rule was to produce no isolation or lockout guidance. `pid_path_review.py` says it
gives no isolation instructions, and the flow-direction work says a drawn direction "is not isolation or lockout
guidance". On 2026-11-11 the repository owner decided to try isolation guidance as a proof of concept and testing
ground, on condition that every result says it must be verified by a qualified professional. This goal is that
trial. It does not lift the old rule for any other tool: the path review and flow direction keep their
disclaimers, and the existing mockups (the TE 3D-tour LOTO still, the OPEN100 `loto_isolation_points.csv` view)
stay mockups. Neither meets the safeguards below. The TE scene lists control valves as candidates, and the OPEN100
view says "isolate at the first block valve".

## The goal, in one sentence

**For one item a user selects on a P&ID set, list the candidate boundary points (valves, blinds and other
isolating devices) that the drawing shows enclosing it, each with its drawing evidence, and every path out of that
boundary, including vents, drains, bypasses, instrument connections and off-page continuations. Report the
boundary OPEN, with the exact gap, whenever the drawing does not settle it.**

The name is **isolation boundary candidates**. The output is a list to check, not an isolation.

## The fixed header

Every output (REPORT.md, REPORT.html, the CSV, the JSON and any console summary) starts with this text, byte for
byte. No option, input or later step removes or shortens it:

> ISOLATION BOUNDARY CANDIDATES. PROOF OF CONCEPT AND TESTING GROUND. THIS IS NOT AN ISOLATION OR LOCKOUT/TAGOUT
> PROCEDURE AND MUST NOT BE USED AS ONE. Every point and every path below must be verified by a qualified person
> against the as-built plant and the site's energy-control program (for example under OSHA 29 CFR 1910.147). It
> is read from drawings, which are not as-built: a point it does not list may exist, and a point it lists may not
> isolate. Electrical, pneumatic, hydraulic, stored-pressure, gravity and thermal energy are not assessed.

In the CSV the header is a leading comment block and every row also carries a `status_note` column with the first
sentence. In the JSON it is a required top-level field that the reader of the file cannot miss.

## What it outputs, for one selected item

- **Candidate boundary points.** The first isolating device on each pipe-layer path leading out from the item.
  Each point has the drawing evidence behind it: sheet, symbol id and box, the device class as read, the pipe
  segments on each side, the reader source (answer-key symbols or a model reading) and the bundle's review status.
- **Every path out of the boundary.** Each pipe segment, junction, instrument tap, vent, drain, sample point,
  relief device, bypass and off-page or utility continuation that leaves the enclosed region. Each path is either
  closed by a listed point or listed as an open gap.
- **Not-positive-isolation crossings.** Control valves, check valves and relief valves on a path, listed as such.
  They never close a path.
- **Status.** `open`, with every gap named (the segment, junction, flag or symbol and the reason), or
  `closed_on_drawing`, which means only that every path the drawing shows meets a listed candidate device. It is
  not a statement that the item is isolated.
- **Not assessed.** The six non-piping energy types, always listed, for every item.

Listing order is by sheet and symbol id, and the report says it is not an isolation order.

## Safeguards (each with its test)

| Safeguard | Rule | Test |
|---|---|---|
| Recall first | A missed point or path is the dangerous error. Extra points are tolerated; precision is secondary. | Primary score below. A change that lowers recall on any development boundary is rejected, whatever it does to precision. |
| Refuse on incomplete | Any unresolved off-page link, untraced or dropped line, junction no line reaches, valve of unknown type, unread symbol on a path, or conflict in the bundle makes the boundary `open` with the exact gap. It is never `closed_on_drawing`. | Planted gaps on development fixtures: remove an off-page pairing, delete a traced line, blank a valve's class, add a conflicting record. Each must turn a `closed_on_drawing` boundary `open` and name that gap. |
| No positive isolation from check or control valves | A check valve, a control valve (any valve with an actuator) or a relief valve never closes a path. | Fixtures in which the only device on a path is each of these: the boundary must be `open`, the device listed as a not-positive-isolation crossing. |
| Non-piping energy | Electrical, pneumatic, hydraulic, stored pressure, gravity and thermal are listed as "not assessed" for every item, including items with no piping (the R-101 agitator SC-212, the K-101 drive). | Every output contains the six entries; no output contains an assessment of any of them. |
| No steps or zero-energy claims | No sequence, step numbers, valve positions to set, verification or try-start instructions, and no statement that energy is absent or the item is safe. | A banned-phrase check over every output (for example "step", "sequence", "zero energy", "safe to", "is isolated", "lock out", "close valve"), plus a check that point numbering, if any, is the sort order stated above. |
| No dependence on flow direction | Isolation is two-way, so the walk uses undirected pipe segments. | Output is byte-identical on the same bundle written with `--no-flow-direction`, and with every segment direction reversed. |
| The header | The fixed header above on every output. | Byte comparison on every output file of every scored run and fixture. |

## Measurement

### The truth set

- **Drawings:** the Tennessee Eastman (TE) sheets 101, 102 and 103 in their current revision (D, `data/te_pid/`)
  and revision C (`data/te_pid/rev-c/`), which draw a manual block valve each side of each inline control valve and
  a bypass with a hand globe valve. Revision A (`data/te_pid/rev-a/`) draws no manual valves.
- **Selected items, fixed now:** the six units in `data/te_process_model.json` (U-100, R-101, E-101, V-101, K-101,
  C-101) and its eleven valve final elements (FV-101, FV-102, FV-103, FV-104, FV-105, FV-110, LV-112, LV-115,
  FV-117, FV-119, TV-121), 17 boundaries per revision. SC-212 is a speed signal, not a valve, and is scored only
  for its "not assessed" entries. An item drawn on more than one sheet is one boundary across the set.
- **Source of truth.** The model holds no manual valves, so the truth comes from the model and from the drawer's
  own key and routes (`data/te_pid/key.json`, the `block_valve` and `bypass_valve` drafting additions, and
  `line_layers.drawn_truth`). Each truth boundary lists its points, every path out, and its status (`open` with
  the gaps, or `closed_on_drawing`), under the definitions on this page.
- **Who builds it, blind to the method.** A person or agent who has not written and will not see the method's code
  or outputs builds it by hand from the rendered sheets and this page alone, before the method's first scored run.
  The truth file and its sha256 are committed before that run. A second, independent reviewer checks every
  boundary against the sheets. The drawer's routes are then used as a mechanical cross-check: every truth point
  must exist in the key, and every drawn route out of each boundary must be closed by a truth point or listed as a
  gap. Every disagreement and its resolution is recorded with the truth file. A truth change after the first scored
  run is a scorer change and needs its own review.
- **What the truth will mostly say.** These sheets draw no vents, drains, blinds or instrument root valves, and
  every unit's streams run off-page or to a battery limit. Most unit boundaries will be `open`, and the
  control-valve stations are where `closed_on_drawing` is possible. Revision A should be `open` everywhere. That is
  the honest result for these drawings, so the goal adds the held-out revision below.

### Scores

| Score | Definition | Role |
|---|---|---|
| **Missed-point recall, per boundary** | truth points listed ÷ truth points, reported for every boundary, with the count of boundaries missing any point | primary |
| Missed-path recall, per boundary | truth paths out listed (closed or as a gap) ÷ truth paths out | primary, read with the above: a missed path is as dangerous as a missed point |
| **False-complete rate** | boundaries reported `closed_on_drawing` whose truth is `open`, or that miss any truth point or path, ÷ boundaries reported `closed_on_drawing` | must be **zero**, on every input and every planted-gap fixture |
| Point precision | listed points that are truth points ÷ listed points | secondary: review burden |
| Closed-when-closable | truth `closed_on_drawing` boundaries reported so ÷ truth `closed_on_drawing` | secondary: usefulness. Zero is reported, not hidden |

An always-`open` method scores zero false-complete, so that score alone proves nothing. Recall and the controls
below separate a method from that.

### Inputs

- **K:** the answer key's symbols with the tracer, which isolates the boundary logic from reading error.
  Revisions C and D.
- **R:** the committed model readings with the tracer (`predictions/tec-*`, clean and scan levels L1 to L3, on
  revision C; `predictions/te-*` on revision A). Revision D has no model reading, so it is K only.
- Following round 6's product-path rule, every score is computed from the bundle
  `scripts/import_drawing_set.py` writes (its pipe layer, junctions, instrument taps and cross-sheet pairings),
  never from a separate research script's output.

### Controls, each scored like a method

- **Empty:** no points, every boundary `open`. Recall 0, false-complete 0. It shows false-complete alone is cheap.
- **All valves in the graph:** every valve symbol reachable from the item, all called points. Recall near 1,
  precision low. It shows recall alone is cheap.
- **Nearest valves only:** the first valve symbol on each line leaving the item, any type, `closed_on_drawing`
  when each line has one (the existing OPEN100 view's rule). Expected to credit control valves, miss bypasses and
  taps, and report false complete.
- **Perfect:** the truth set itself, scored to check the scorer gives 1.0 recall and zero false-complete.

### Development and held-out split

- **Development:** sheets 101 and 102, all revisions. The method may be built, inspected and tuned on these.
- **Held out, sealed until the method is frozen and scored once:** sheet 103, all revisions. Its truth is built
  with the rest but not opened by the method's author. *Qualification:* sheet 103 has been read and scored in
  rounds 1 to 6 for symbols, connections, pipe segments and flow direction. It is untouched only for isolation
  boundaries.
- **Planned second held-out set:** a TE revision E drawn by the existing generator after the method is frozen,
  with vents, drains, a spectacle blind, a check valve and instrument root valves added as marked drafting
  additions, its truth built the same way. Drawing it is generator work for a separate task and a different author.
  If it is not built, the result says the vent, drain, blind and root-valve rules were tested only on development
  fixtures.

### Decision rules, fixed now

- Keep an increment only if, on development K inputs, no boundary misses a truth point or path, false-complete is
  zero on every input and planted-gap fixture, and every safeguard test passes.
- The method must beat **nearest valves only** on recall and on false-complete, and **all valves** on precision.
  Losing to all valves on precision is a usefulness failure, reported as such, not a safety pass.
- On R inputs report recall per run, with the run and scan-level spread. A reading error may make a boundary
  `open` but must never make it `closed_on_drawing`.
- Score the held-out sets once, after the freeze. A held-out miss is reported as a failure; the method is not
  re-tuned on held-out data.
- Record every attempt in `data/attempts.json`, kept or not.

### What would make the goal fail

- Any false complete, on any input, held-out or development.
- Any missed truth point or path on held-out K inputs.
- Any credited check, control or relief valve; any missing or shortened header; any output that changes with flow
  direction; any step, sequence or zero-energy wording.
- A truth set that cannot be built blind, or a reviewer disagreement that cannot be resolved from the drawing. The
  goal is then reported not attempted rather than scored on a weaker truth.

## Increments, in order, each kept only if it passes

1. **Reach from one item (backlog item 6).** Given an item id, list everything reachable along the bundle's pipe layer: pipe
   segments through junctions and instrument taps, across paired off-page flags, with every unpaired flag,
   dropped line and unresolved continuation listed. No stopping at valves yet and no isolation wording. Scored for
   recall and precision against the drawer's routes on development sheets; a reach that silently stops at a gap
   fails.
2. **Boundary.** Walk outward from the item and stop at the first candidate isolating device on each path. Record
   the points, every path out and the not-positive-isolation crossings; set the status by the refuse-on-incomplete
   rule. Scored with the measures above.
3. **Report.** The fixed header, REPORT.md and REPORT.html, the CSV and JSON, the evidence on every point, the
   not-assessed list and the gap list. Kept only if the header, banned-phrase and direction tests pass on every
   output.

Not planned here: the 3D tour's LOTO view, any sequence, any link to permits or a site's isolation list. A
reviewed `isolation_point` register ([CONTEXT_MAP_FORMAT.md](CONTEXT_MAP_FORMAT.md)) is the site's record and
always outranks these candidates.

## Limits

- Drawings are not as-built. A boundary read from a drawing can be wrong at the plant even when the drawing is read
  perfectly.
- The TE sheets are drawn by this repository from its own model, in a clean house style, with manual valves added
  as drafting choices. Scores on them are upper bounds for clean drawings, not real-plant accuracy.
- The six-class reader reads "valve" without a type. On model readings most valves will be type unknown, so most
  boundaries will be `open`. That is the intended result, not a defect to tune away.
- No field validation, no qualified person's review of any boundary, and no timed review. Nothing here measures
  whether a boundary would be safe to use.
