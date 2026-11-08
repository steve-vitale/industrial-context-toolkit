# Questions across P&ID sheets: review status must travel with the answer

Reviewed 2026-11-08 after [Maetee Lorprajuksiri's public example](https://www.linkedin.com/posts/maetee-lorprajuksiri-22378a46_processengineering-pid-dexpi-activity-7524669143963525121-jNHS),
shared as [this short link](https://lnkd.in/p/gmVa2TTE). The author describes connecting three sheets,
holding uncertain matches and a size disagreement for review, retaining status in derived registers,
and exporting DEXPI. These are the author's reported outcomes; no input/key/output packet or independent
score was supplied in the post. Its counts and claimed extraction quality are not toolkit results.

## Useful work for a maintenance or engineering manager

Start with a specific question: which drawings and records need checking before this pump replacement?
Give the agent the relevant supplied sheets, equipment export and instrument records. The existing
[one-map route](ONE_MAP.md) connects these sources and produces a review queue. Its `draft-lists` command
can prepare draft equipment, instrument and loop records. Those are useful starting points now.

The path consumer returns a visible path, source sheet/revision/locator for each
step, review status and every stopping boundary. Separate a confirmed continuation from an unresolved
candidate. For example, a connector pair with disagreeing sizes should remain visible in the review map
while an accepted-only path query stops there and asks the owner to resolve it. A deliberately exploratory
query may display the candidate, with its disagreement carried into the answer and downstream exports.
An empty accepted path means no supported path was established within the supplied coverage; it does not
prove physical disconnection or adequate maintenance isolation.

The bounded path consumer below now implements these policies on supplied graph records. Current `one_map.py`
`pair_offpage` retains reciprocal connector pairs as `connects` / `offpage_pair`, marks direction unknown,
and separately records shared-attribute disagreements. The path consumer reconciles edge status and applicable
open conflicts before treating a pair as traversable. It preserves the distinction between an observed pairing
and a disputed attribute.

## Three distinctions the answer must preserve

| Evidence | Supported use | Additional evidence needed |
|---|---|---|
| Shared line network or logical stream | Candidate relationship and records to inspect | Physical pipe adjacency, actual direction and selected route |
| Reviewed physical path | Trace the supplied topology within stated coverage | Operating lineup, check-valve orientation, control mode and current installed state |
| Path plus a process description | Frame a conditional investigation | Applicable balances, dynamics, safeguards, failure mode, approved operating basis and engineering judgment |

`graph_export.py` already distinguishes network co-membership, logical streams, physical `piped_to`
segments, instrument connections and actuator/nozzle relations. A generic graph walk must not turn them
all into process flow. A topology trace alone cannot establish a failure consequence or issue an isolation
instruction. A graph retains sourced assertions; it does not become the engineering authority by being
structured. Company records, accepted decisions and ownership still govern the work.

Register outputs should retain row-level source and review state plus any dependency on a disputed link.
An asset's own tag may be supported even while its inferred service or downstream association remains open.
Do not blanket-confirm a whole row because one field matched, or reject every local fact because a remote
continuation is uncertain. Current draft records remain unverified; richer cross-sheet register propagation
and complete line/valve list generation require their own supported contracts and receiving checks.

## Run a path review on your records

`scripts/pid_path_review.py` accepts an existing `twin-graph-1` or `twin-graph-2` JSON snapshot. Use exact
site-qualified node IDs. The tool validates the existing graph contract first; it does not read drawings,
invent connections, certify review labels or retrieve the original source files named in a graph.

```sh
python scripts/pid_path_review.py your-graph.json --from SITE/P1/U1/P-101 --to SITE/P1/U1/V-301 --basis logical --policy reviewed --out review-1
python scripts/pid_path_review.py your-graph.json --from SITE/P1/U1/P-101 --to SITE/P1/U1/V-301 --basis logical --policy exploratory --out exploration-1
python scripts/pid_path_review.py revised-graph.json --from SITE/P1/U1/P-101 --to SITE/P1/U1/V-301 --basis logical --policy reviewed --previous review-1 --out review-2
```

Python 3.10+ and the standard library suffice. Pick one network (`--network process` or `signal`) and
one basis (`physical`, the default, or explicitly `logical`). One-map sheet runs are logical `stream`
relationships; they are not promoted to physical pipe segments. Prepare and review the graph with the
[existing input routes](WORKFLOWS.md), preserving original source records in their approved location.

| Relationship | Eligible scope |
|---|---|
| `piped_to` | Physical process trace |
| `connects` with `layer: stream` | Explicit logical process trace |
| `signal_line` or `instrument_connection` | Signal/impulse-connection trace; this does not establish control function |
| `connects` with `layer: offpage_pair` | Supplied `network_kind` claim identifies process or signal; absent meaning is exploratory only |
| Network co-membership, hierarchy, controls/protects/acts-on, actuator/nozzle links | Excluded from this path traversal; retained in the input |

An off-page `network_kind` is a normal sourced edge attribute, for example
`{"name":"network_kind","value":"process","status":"confirmed","source":{"document":"PID-101","revision":"A","locator":"connector A12"}}`.
Unknown vocabulary refuses. A pair without this declaration is not assumed to be process piping.
The existing producer is unchanged and does not manufacture this additional reviewed meaning.

`known` direction means forward from the supplied `from` to `to`; `both` explicitly permits either
direction. `unknown` or null direction requires exploratory qualification. A known reverse edge is never
followed backward. Reviewed-only requires confirmed/corrected node and edge labels, qualified edge claims,
and a source document/file/drawing, revision or hash, and locator/sheet/zone/pointer. Open/disputed detected
conflicts attached to an endpoint or edge also stop that continuation. Rejected/unresolvable records are
excluded under both policies. Exploratory carries unresolved status, source, claim and direction findings
through the downstream association. Source references/hashes in a supplied graph remain assertions;
this consumer does not independently validate originals or authenticate engineering decisions.
An active unresolved conflict whose subject is outside the graph refuses tracing until its applicability
is reconciled. Retired/resolved conflict history stays in the exact input without blocking unrelated facts.

Open `REPORT.html` first. `REGISTER.csv` retains every reachable item's own facts/status separately from
its query-relative path/qualifications; cells use JSON encoding to preserve types and avoid spreadsheet
formula execution. `result.json` retains all selected steps, applicable conflict details, boundaries and
dependency comparisons. `input.json` is the exact graph byte copy. This association register is not a
complete equipment, line or valve list, and a reached off-page connector may still have a missing continuation.

The selected route minimizes the number of qualification occurrences, then hops; exact-ID ordering breaks
ties. This is a deterministic evidence-ranking rule, not a hydraulic, safety or operational preference.
The search explores the selected supplied network completely. Answer dependencies cover the selected-route
search prefix, or the full reachable search for a negative answer. They include incident-edge sets,
record/source values and applicable conflicts, so new edges/conflicts can reopen an answer. The wider
reachable register is compared separately: a remote register change need not invalidate a local answer.
One answer/route per query is returned; alternatives and minimum qualifier counts do not prove engineering correctness.

`--previous` verifies the retained packet, re-scores its answer and projections, preserves its complete
history and reports reopened/unchanged prior-answer basis plus explicit register changes. It does not accept
corrections or overwrite earlier packets. Changed query/policy/method basis refuses comparison; retain that
packet and start a new one. Limits are 8 MiB per input/result JSON, 2,000 nodes, 5,000 edges, 64 MiB per packet
and at most eight prior revisions. Narrow an oversized scope; no truncated search is labeled complete.
Use a new destination outside the previous packet. There is no background watcher, live interface, CAD
writeback, context-register mutation, DEXPI export or failure-consequence engine in this consumer.

## Exposed development exercise and remaining depth

The [three-sheet exercise](../examples/pid-path-review/README.md) now runs on authored schedules and
prepared graph assumptions with all ten policy/key outcomes, an unrestricted baseline, missing continuation,
qualified register and selective source-revision checks. The original prototype's missing off-page network
meaning is retained beside a separately frozen preparation correction. Original keys and graphs remain.

Use attributed public sheets where available; otherwise label the authored case fictional and exposed.
Separate a fixed-key software exercise from reader accuracy, engineering review and human time saved.
Public multi-sheet drawing interpretation and independent source/key engineering review remain unrun.
No image-reader accuracy, human time saving, plant acceptance or complete line/valve register is established.
Do not convert a successful data parse into DEXPI exchange qualification.
Reuse the public-model review in [PID_RULES_RESEARCH.md](PID_RULES_RESEARCH.md)
before considering a new DEXPI adapter; returned-file semantic checks remain a separate gate.
