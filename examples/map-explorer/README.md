# Explore your engineering context map

Find equipment, inspect its facts and source revisions, follow recorded
relationships, see disagreements and compare a previous snapshot. The explorer
is a **read-only local HTML package** for engineers, managers and their agents.
It uses existing one-map questions and comparisons. It adds no account, server,
job-readiness gate, assignment, reminder or approval workflow.

## Try it offline

Python 3.10+, standard library, from the repository root; choose new output folders:

```sh
python -B -S scripts/one_map.py build examples/one-map/inputs/site.json --out ../my-map
python -B -S scripts/map_explorer.py export --map ../my-map/graph.json --sources examples/one-map/inputs --item S1/P1/200/P-101 --out ../my-map-explorer
python -B -S scripts/map_explorer.py verify ../my-map-explorer
```

Open `../my-map-explorer/index.html` in a browser. It makes no network requests.
Search `P-101`, then choose **S1/P1/200/P-101** or **S1/P2/300/P-101**. They are
different items. For the first, the represented rated flow is **45 m3/h**, from
equipment datasheets rev 2, row 2; the disagreement retains **40 m3/h** from the
equipment export and its owner. Follow V-204 to see its relationships, or open a
related document to inspect its declared coverage, revision, release status and
source bindings. A broad coverage link or text mention does not prove equipment applicability.

The five question panels are exact `ontology.ask` answers: connections,
measurement/protection, documents, disagreements and configured record
expectations. Expected-complete means those configured record rules, not that a
job is ready, equipment is healthy or a plant requirement has been satisfied.
For qualified multi-edge routes use [path review](../../docs/PID_GRAPH_QUESTIONS.md);
this explorer displays stored edges without qualifying a route or inferring consequences.

## Substitute your map and evidence

1. Prepare your records using [ONE_MAP.md](../../docs/ONE_MAP.md), then run its
   `build` and `check`. This explorer accepts `twin-graph-2` from that route;
   `twin-graph-1`, CAD, images and unprepared exports need their existing adapters.
2. Replace `--map` with your built snapshot. Supply a qualified initial `--item`,
   a unique exact tag or an existing certified glossary term; or omit it and
   choose in the browser. Ambiguous tags fail before writing. Browser search
   includes aliases but never merges identities.
3. Optionally set `--sources` to the explicit local root that the graph's relative
   evidence paths use. Only files with matching declared **raw-byte SHA-256** are
   copied. Missing, unbound, mismatched, unsafe and oversized references remain
   explicit in `evidence.json`; no online fetch or basename substitution occurs.
   A hash match binds bytes, not interpretation or applicability.
4. Keep the **whole output directory**. The exact input snapshot is `current.json`;
   `exploration.json` contains every full node inspection, incident edge,
   subject conflict with its history, associated record rows and supported
   answers. The original snapshot also retains all other fields, including
   metadata/events not projected into dedicated views. Originals are retained
   by hash under `evidence/`; download links suggest their original filenames.

The export includes the **entire supplied map and retained originals**. Initial
selection is navigation, not an access-control filter. Use an approved private
location and authorized sources. No SharePoint, plant or company authentication
is provided by the package. An approved assistant can read its JSON without
MCP; Copilot's existing document access can be enough for a document question.

## Inspect a revision

Retain the earlier graph, update sources through their owners and rebuild a new
map. Add `--previous ../earlier-map/graph.json` and, if retaining earlier evidence,
`--previous-sources PATH-TO-EARLIER-SOURCES` to a new export. The snapshots must
have the same declared site identity. Switch snapshots in the explorer: an item
can be present now and absent before. The comparison retains complete before/after
nodes and the existing `map_changes` report, including relationship/document changes.
An omitted item or changed source is not proof of a physical change.

This package does **not** refresh a context register or stale previously accepted
answers. Use [context register](../../docs/CONTEXT_REGISTER.md) and the
[existing revision routine](../../docs/RUNNING_THE_MAP.md) for those supported
steps. Decide with source owners what to revisit; company systems keep approvals
and ongoing service responsibilities. Later managed receiving needs its own
contract and qualification; no governed-service importer is implemented here.

## Reopen and check a delivery

Copy the complete folder into a new location and run `verify` there. It checks
the file inventory and original-byte hashes, regenerates complete derived views
and comparisons from retained maps, and reproduces the HTML. Losing a conflict
or changing a typed field in the derived view fails even if its file inventory
is recomputed. Method fingerprints in `RECEIPT.json` identify the exact six
tool modules; use that repository revision for later verification.

Retain the SHA-256 of `RECEIPT.json` separately when handing a packet to another
person. Then verify that exact delivery with:

```sh
python -B -S scripts/map_explorer.py verify ../received-map-explorer --expected-receipt-sha256 YOUR_RETAINED_HASH
```

Without an independent expected hash, verification proves internal consistency;
it does not authenticate the sender or detect a deliberately substituted whole
map/package. Neither mode establishes engineering acceptance.

## What was actually exercised

[Plan](PLAN.md) and [acceptance key](ACCEPTANCE.json) preceded implementation;
the [ordinary-folder baseline](BASELINE.json) inventories the same sources without
pretending a person searched them. [Input typo](INPUT-CORRECTION.md) and
[first export/browser failures](FIRST-FAILURE.md) are retained. There is no timed
human comparison or measured saving.

- [Development](worked/development/SUMMARY.json): 11 checks, five separate-process
  CLI calls; scoped P-101s, attributed flow disagreement, unresolved document
  reference and complete portable receiving.
- [Frozen method](FREEZE.json), then [procedural transfer](worked/transfer/SUMMARY.json):
  17 checks, nine CLI calls; pasteurizer C-to-D revision and a public
  [OPEN100 development-sheet reading](../drawing-to-map/README.md).
- Desktop 1500 px and mobile 420 px browser checks exercise selection,
  neighbor navigation and, on the revision case, an added item's absence in the
  earlier snapshot. No page errors, horizontal overflow or HTTP(S) requests were
  observed. These are display/software checks, not a human usability trial.

The OPEN100 route uses a committed model reading with known limitations; it is
not new image extraction, independent drawing truth or a plant result. All
fictional/public cases were already available to the author. The transfer is a
preselected procedural check, not blind generalization or independent review.

Reproduce in separate new directories:

```sh
python -B -S examples/map-explorer/reproduce.py --phase development --out ../map-explorer-development
python -B -S examples/map-explorer/reproduce.py --phase transfer --out ../map-explorer-transfer
python -B -S scripts/test_map_explorer.py
```

Optional display repetition uses installed Playwright and a local Chromium/Edge
executable: run `check_browser.py --packet PACKET --out NEW-FOLDER --browser EXE`.
Those dependencies are not needed to build, open or verify an explorer.

2026-11-10: vendor names removed from this packet; hashes re-pinned.
