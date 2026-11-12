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
