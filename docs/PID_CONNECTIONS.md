# Check the exact connection, including its ports

Use this optional route when the right instrument tags are present but a connection may go to the wrong
input, have the wrong direction or use an incompatible signal type. Start with the original record,
the exact instructions sent out and the returned revision. An approved assistant or engineer supplies
the observations. The tool checks those records; it does not read images, discover annotations or infer wiring.

For a complete markup inventory, use [the markup-review workflow](PID_MARKUP_REVIEW.md). It now also accepts
an exact `port_connection` fact. The separate checker below additionally checks supplied endpoint meanings
against a versioned catalog. Neither route requires MCP, a CAD UI or a live system connection.

## Try the fixed example

Python 3.10+, standard library only, from the repository root. Choose a new output folder with an existing parent:

```sh
python examples/pid-port-review/replay.py --out ../my-port-review
```

Open `initial/REPORT.html` and `initial/review_queue.csv`. The corrected return is a separate packet.
[The example](../examples/pid-port-review/README.md) explains every expected finding and the actual provenance.
This is software validation on exposed fictional records. It is not a measured drawing-reading service.

## Supply your own prepared records

Copy the [example inputs](../examples/pid-port-review/worked/initial-inputs/manifest.json) to an approved private
folder, replace all sources/meanings/observations and recompute their SHA-256 bindings. Do not publish plant data.
The manifest (`pid-port-review-1`) contains:

- `documents`: unique `id`, `role` (`original`, `markup`, `returned`), `revision`, local `path`, raw `sha256`.
  All three roles must be present. Company document control supplies authoritative sheet/revision correspondence.
- `catalog`: path/hash of a `pid-port-catalog-1` file with a nonempty `revision`, `authority` and `symbols`.
  Each symbol has an ID, separate `glyph` reference and unique port IDs. Port fields are `direction`
  (`in`, `out`, `bidirectional`), `relation` (`process`, `signal`) and `medium` (an exact locally defined term).
  Explicit null means unknown. This is an interpretation contract, not a standards symbol library.
- `records`: path/hash of a `pid-port-records-1` file with qualified `sheet`, source `identity`
  (`confirmed` or `uncertain`), reading `method`, and all five lists below.

| List | Required interpretation |
|---|---|
| `assets` | Tag, symbol ID and returned-source evidence. Duplicate tags remain unresolved; no fuzzy identity match. |
| `connections` | Unique ID, `from` and `to` objects with exact `tag`/`port`, `relation`, `medium`, `state` (`known`/`unknown`), returned-source evidence. Unknown rows need a reason. |
| `requirements` | Unique ID, exact desired connection and markup evidence. One desired outgoing connection per source-port/relation/medium selector. Represent broader fan-out or alternatives in another reviewed contract; do not compress them into this one. |
| `allowed_connections` | Exact unchanged connections authorized by original-source evidence. Do not include superseded connections here. This is an explicit allowance, not automatic baseline discovery. |
| `coverage` | Source `from`, `relation`, `medium`, Boolean `complete`, basis and returned evidence. Completeness is supplied, not established by the program. Every matching declaration must be complete before missing observations establish absence. |

Every row has an `evidence` list: document ID, exact source `sha256`, positive `page`,
`box_0_1000: [left,top,right,bottom]` and a readable `description`. Boxes use page-top-left coordinates;
for structured records, describe the exact row/columns and use a whole-record box. The tool validates bindings
and bounds, not the existence of a visual mark at that location. It does not verify page counts or quotations.
Whole-sheet correspondence is supplied in `identity`; unclear correspondence must stay `uncertain`.

```sh
python -S scripts/check_pid_connections.py --manifest PRIVATE_INPUT/manifest.json --out PRIVATE_NEW_PACKET
```

Malformed input, stale hashes, unsafe paths and an existing output refuse (exit 2). Exit 0 means a draft packet
was written, including unresolved findings. Keep the entire packet: exact sources, catalog, readings, portable
manifest, reports, queue and integrity receipt. A later revision requires fresh observations; changing only the
manifest's source hash refuses. Hashes establish integrity, not authenticated engineering approval.

## Interpret the result

`supported` means an exact known observed connection has compatible supplied endpoints. `missing` requires
declared complete coverage with no matching known connection. `unknown` retains missing meaning, unresolved
identity, uncertain observations or incomplete coverage. Duplicated known connections become `ambiguous`.
`incompatible` means the desired connection itself conflicts with the supplied port meanings.
Known observations carry their own validation findings even if no requirement names them.
Other connections outside the explicit allowed/required set remain visible for assessment.

A supported connection can coexist with another unwanted connection; inspect the whole report and queue.
No inference of a safe process, correct control strategy, electrical compatibility, terminal wiring, live signal
mapping, alarm adequacy, full drawing equivalence or complete port cardinality is made. Medium names are exact;
there is no synonym, unit or vendor dialect conversion, graph path traversal or cross-sheet stitching here.

Keep three receiving decisions separate:

| Check | Evidence | What it does not establish |
|---|---|---|
| Record structure | This parser accepts the declared schema and bindings | That the prepared interpretation matches the drawing |
| Represented connection consistency | Exact endpoints and applicable declared port meanings | Design adequacy or installed condition |
| CAD preservation/editability | [Native receiving checks](../examples/cad-handoff/receiving-review/README.md) | This tool never qualifies CAD; existing failures remain open |

## Return a useful correction handoff

Use the queue to assign a named owner, correction/clarification and disposition in the company's existing process.
For each issue retain request ID, expected endpoint, observed endpoint, exact evidence and coverage limitation.
Agree the scope and receiving format before expanding to a drawing backlog. After correction, review a new packet
against the exact new revision and verify the actual receiving CAD file separately when CAD delivery is required.
No automatic edits, drawing release, map update or MOC closeout occur.

For help with a larger backlog, [connect with me on LinkedIn and message me there](https://www.linkedin.com/in/steve-vitale/).
The [public-methods review](PID_RULES_RESEARCH.md) explains DEXPI reuse and why design heuristics need applicability review.
