# Goal, round 6 (written 2026-11-10, before any round-6 method change): the drawing as engineering relations

Earlier rounds (2 to 5) are pre-registered in [GOAL.md](GOAL.md), which stays unchanged because benchmarks pin its bytes.

## The goal, in one sentence

**One simple path, the `pid-to-context-map` skill, takes a P&ID set to the relations an engineer asks about: what is
piped to what and which way it flows, what each instrument measures, which signals run where and which control loops
close, with every tag read correctly. Each relation is scored on the bundle that path writes.**

## Why this round

Rounds 2 to 5 scored symbols and undirected network co-membership (review load), because that is what the PID2Graph
keys hold: on OPEN100 sheet 8 all 179 key edges are labelled `solid`, with no direction and no pipe/signal
distinction. The reader followed the key: `extraction/prompt_v2.md` asks for the six scored classes and says not to
report flow arrows. Useful relations were built anyway but stayed off the user's path. The pipe layer and line
classes (`scripts/line_layers.py`, A139-A196) and arrow-based flow direction (`scripts/flow_direction.py`, A037)
run as research and case-study scripts. Neither runs in the intake the skill uses. A comparable public tool reads
these relations with a model and checks itself, but publishes no scores. Round 6 makes them first-class targets,
measured the same way as everything else here.

## Scores (each reported per corpus family, beside the same deliberately wrong controls)

| Relation in the context map | Score | Key | Baseline before round 6 |
|---|---|---|---|
| `piped_to` (pipe segments) | pipe-segment F1 | existing topology truth (`line_layers.py score`) | OPEN100 0-5 0.931; DEXPI 1.3 C01-C03 0.916 (A196) |
| instrument connection / `measures` | instrument-connection F1 | same | OPEN100 0-5 0.835 (A196) |
| flow direction on `piped_to` | share of pipe segments directed, and direction precision where drawn evidence exists | TE generated sheets (truth from `data/te_process_model.json`); OPEN100 arrow nodes for detection only | 32% of process links directed on OPEN100; arrowhead detection 83% precision, 77% recall on sheets 6-11 (A037) |
| `signal_to`, `controls`, loops | loop recall and precision (sensor, controller, final element) | TE generated sheets (`data/te_control_loops.json`) | not scored before |
| tag text | tag match against the PDF text layer (`pdf_tag_check.py`) | CAD-exported PDFs with a text layer | Pahala P-401 14/14, P-501 13/13, one development run, 2026-11-10 |

**Review load stays the primary reader score.** No round-6 change may raise it beyond the run-to-run spread on the
development sets.

## The product-path rule

Every round-6 score is computed from the bundle `scripts/import_drawing_set.py` writes, which the skill runs. It is
never computed from a separate research script's output. A relation that only a case-study script produces does not
count as delivered.

## Increments, in order, each kept only if it passes the decision rules

1. **Wire the existing pipe and instrument layers into the drawing-set intake.** No method change: on every input
   the layers already accepted, the output and every score must be byte-identical. Drawings the bundle step refused (a line whose two ends
   the tracer placed on different networks, first seen on Pahala P-501) are accepted with the inconsistent lines
   dropped and listed.
2. **Carry flow direction into the bundle:** arrow, off-page flag, pump port and valve-chain evidence on `piped_to`,
   with confidence. A segment without drawn evidence stays undirected (N012 stands: no direction from layout).
3. **Loops and signals:** `signal_to` from instrument lines between instruments and `controls` from the ISA roles,
   scored on the TE sheets.
4. **A reader format change (prompt v3)** only for what steps 1 to 3 leave unread, for example dashed signal versus
   solid process lines, or a measuring point that code cannot place. It must be measured against the same
   development sets first.

## Protocol and decision rules

- Development: OPEN100 sheets 0-5, TE revisions A and D, Pahala P-401 and P-501. Held out, sealed until a method is
  frozen and scored once: OPEN100 sheets 6-11, the DEXPI held-out renders (A177 split), and other Pahala sheets with
  a text layer.
  *Qualification added 2026-11-11 (A408):* OPEN100 sheets 6-11 are not untouched for flow direction. The direction
  confidences that `flow_direction.py` attaches (`data/open100_direction_confidence.json`) were calibrated on a
  65-crop blind spot check, 31 of whose crops come from sheets 6-11 (`out/open100_structural/spot_check/manifest.json`),
  and A037 measured arrowhead detection there. A later "sealed" direction score on those sheets must say so.
  *Qualification added 2026-11-11 (A410):* the dashed signal-line tracer behind increment 3 was developed on TE
  revision D, the only development sheets that draw controllers and signal lines, so its loop scores there are
  development fits as well as upper bounds. Revision A draws no loops and OPEN100 0-5 draw no controllers; both
  check that nothing is asserted, and OPEN100 0-5 is a development fit too: the first version asserted 10-17 false
  signal_to per OPEN100 reading through solid instrument lines, and solid lines are now never signal evidence. The
  positive list of signal conditions was then shaped by three independent reviews' synthetic drawings, which are
  tests, not scores. Neither revision A nor OPEN100 0-5 draws a controller, so loop precision is in effect measured
  on revision D alone, and revision A traces no signal lines, so its zero proves nothing beyond that.
- Keep a change only if its relation score rises beyond the run and sheet spread on development, and review load
  does not rise beyond its spread. Record every attempt in `data/attempts.json`, kept or not.
- Corpus-matrix cells bound to changed code are re-recorded from a fresh clone. Statuses that change must be
  explained.

## Limits

- TE sheets are drawn by this repository from its own model, so scores on them are upper bounds for clean drawings.
- A text-layer tag match checks the reading of text, not the drawing's correctness.
- No round-6 score measures review time or plant acceptance.
