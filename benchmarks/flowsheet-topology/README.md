# Flowsheet topology from a written description (task `flowsheet-topology`, contract `role-aligned-arcs-v1`)

A user describes a process in prose and the description workflow (`scripts/description_workflow.py`, feature
`description-workflow`) turns it into a checked draft model. This task asks whether the units and connections in
that model match a real flowsheet that a third party wrote as code, when the tool sees only the prose.

## Source, input and key

- **Source:** IDAES examples at commit `eb64e38ac429b7e3ae4f8db071f8d8cad2eef675` (corpus group `idaes-processes`,
  pinned in `data/corpus_pins.json`; BSD-style license with a DOE notice, copied in [IDAES-LICENSE.md](IDAES-LICENSE.md)).
  The originals stay in `data/external/idaes-processes/` and are not committed.
- **Input (what the tool sees):** the markdown cells of `methanol_synthesis.ipynb`, in order, with code cells and
  their outputs dropped and trailing spaces stripped (`flowsheet_topology.py prose`). The development input stops
  before the cell that starts `# 4.` (the recycle section); the held-out input is every markdown cell, because a
  user describing the recycle process would give the whole description. The notebook's flowsheet PNGs are not
  given: they draw the answer. Committed as [inputs/](inputs/), derived text redistributed under the license.
- **Key (what the tool never sees):** units and `Arc(source=..., destination=...)` connections parsed from
  `methanol_flowsheet.py` (development) and `methanol_flowsheet_w_recycle.py` (held out) with Python `ast`, never
  executed (`flowsheet_topology.py key`). A unit is a class imported from the IDAES unit model library; Feed and
  Product blocks are boundary terminals. Committed as [keys/](keys/): derived facts with the source hash.
- **Independence:** the key is the third party's code; the input is their prose about it. Neither was written by
  this repository. The prose and the code come from one author and one notebook, so they agree by construction
  where the prose is explicit; the prose never names the mixer or every connection.

## Method (frozen before the held-out run)

`scripts/run_description_author.py` stands in for the approved assistant on the documented route: `prepare` the
packet, give a model only `prompt.md`, `contract.md`, `reference_source.txt`, `reference_answer.json` and
`source_numbered.txt` (no tools, empty temporary folder), run `check`, return its diagnostics, at most four rounds,
then `build`. The scored answer is the `model.json` that `build` writes. A run that never passes `check` is a failed
answer and scores as empty. Three replicates per case; the spread is their range.

### Development (A419, 2026-11-12) and the frozen method

| Run | Built | Unit-role F1 | Connection F1 (per replicate) | Mean (SD) | Reversed / shuffled (wrong) | Mention-order chain |
|---|---|---|---|---|---|---|
| v0: workflow as on main `9ba93ccc` | 0 of 3 | 0.000 | 0.000, 0.000, 0.000 | 0.000 | n/a | n/a |
| v1: frozen A419 contract | 3 of 3 | 1.000 (7/7) each | 0.462, 0.462, 0.947 | 0.624 (0.281) | 0.000 / 0.105-0.154 | 0.105-0.211 |

Key controls on the development key: reference 1.000, reversed 0.000, shuffled 0.300, empty 0.000.

- **v0 failure:** every replicate spent its four check rounds on one diagnostic, `route endpoint must touch the named
  equipment outline bounds`, at the feed mixer. The contract said the mixer uses `at/r`; the check ignores `r` and
  uses a fixed 35-pixel half-size, and the diagnostic never said where the outline was. No build, so the user gets
  nothing. The unchecked answers also left out the turbine (no supported type) and every unit-to-unit connection
  (the prose gives an order, not pipes).
- **v1 changes, in `scripts/description_workflow.py` with RED-first tests:** the diagnostic names the outline and the
  endpoint; the contract states the fixed mixer outline; and the contract asks the assistant not to drop equipment
  the source names (closest supported type, substitution recorded in `meta.assumptions`) and to represent
  connections the source gives by process order as streams, each recorded in `meta.assumptions` for review, never
  connecting units whose order the source does not give.
- **v1 result:** two of three replicates still left the seven process units unconnected: the prose lists them only
  in a degrees-of-freedom sentence, and those replicates recorded that it is not a stated process order. One read the
  list as order and recovered 9 of 10 arcs. All three missed the flash vapor to exhaust. The development cell
  criterion (mean connection F1 >= 0.75) is not met.

The method is frozen at v1 in the commit that adds this section. Before the held-out run, the held-out key was
written once with `flowsheet_topology.py key`; its first parse refused the class `Splitter` (unit `S101`), and one
mapping line (`Splitter` is a splitter, as `Separator` already was) was added. Only its counts (13 units, 13 arcs,
as surveyed on 2026-11-12) and the key-control check were displayed; no answer had been produced for it.

## Score and controls

Units: agreement of coarse unit roles (mixer, compressor, expander, pump, heat exchange, reactor, separator, splitter,
column). Boundaries: feed and product terminal counts. Connections (primary): directed edges, after the
role-preserving alignment of answer units to key units that matches the most key arcs. Every table reports:

- key controls: reference (the key as a native model, must be 1.000), empty, reversed, shuffled (wrong, each at or
  below connection F1 0.35);
- answer controls: the answer's own streams reversed and shuffled (wrong), and a naive mention-order chain of the
  answer's own units (a baseline to beat, not a wrong answer).

## Pre-registered criteria (2026-11-12, before any method run)

- **Cell pass** (corpus matrix row 9): every replicate built; mean connection F1 >= 0.75 and mean unit F1 >= 0.75;
  key controls pass; mean connection F1 at least 0.30 above the mean of each answer-derived wrong control.
- **Verdict of the held-out run:** *kept* if the held-out cell passes and its mean connection F1 is above the
  mean-order chain's by more than the larger of the two replicate ranges; *inconclusive* if it passes without that
  margin (the structure then adds nothing measurable over mention order); *rejected* if it fails.
- One sealed held-out run of three replicates, after the method, scorer and this file are committed. No change
  after it.

## Limits

- One notebook, one author, one publisher (IDAES): a first real source for the area, not a generalization claim.
- The scorer cannot see names, ports, operating conditions or which of two same-role units is which (a heater and a
  cooler can be swapped unseen). Feed identity (hydrogen versus carbon monoxide) is not graded.
- The native model vocabulary has no turbine, splitter or mixer type. The scorer reads a `compressor` named turbine or
  expander as an expander, a vessel or feed header named split as a splitter, and `feed_header` as a mixer.
- The model is a simulation flowsheet, not a plant, and the task scores interpretation of prose, not engineering
  correctness or a drawing.
- The model used is the only one available on this host on 2026-11-12 (Claude through the Claude Code CLI; the
  Codex CLI is unavailable until 2026-11-16 and there is no Gemini key). Same-family results only.
