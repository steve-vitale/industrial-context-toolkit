# Hand off one unit's evidence and handle its next change

Use this when a maintenance investigation also needs a drawing-return finding and
document evidence. The job is to leave a reconstructable foundation: scoped asset
identities, source versions, typed findings, questions, declared owners and history.
Start with one unit and a decision, such as what needs checking before a pump job.

`scripts/foundation_handoff.py` connects **supplied, already prepared records**.
It projects selected maintenance dossiers and exact single-subject markup requests
onto an authored `twin-graph-1` graph, then packages the graph with an existing
`context-register-1` sidecar. The actual receiving target is the toolkit's bounded
`serve_snapshot.Snapshot` reader. This is a software receiving route, not an
implemented ChangePilot importer or an organization's approval system.

## Try the complete local cycle

Python 3.10+ standard library, no network or accounts, from the repository root:

```sh
python -S examples/foundation-cycle/reproduce.py --out out/my-foundation-cycle
```

Use a new folder. Read `summary.json`, `checks.json`, `commands.json`, then
`delivery-2/HANDOFF.md`. The runner uses actual producer, context, receiving and
export/reopen CLIs in separate processes. Its fictional record preparation and
authored proposals are not model reading or an independent engineering review.
The [preimplementation plan](../examples/foundation-cycle/PLAN.md) and
[acceptance key](../examples/foundation-cycle/ACCEPTANCE.json) precede the tool.

The same bare pump tag appears in two units. The first unit has three selected
orders and 2.5 booked hours under the supplied signed ledger; the second has one
order and three hours. These are selected-record results, not failure counts or
total lifetime labor. A requested valve removal remains unsupported in the first
return, and becomes supported by prepared readings in the next. That does not
authorize an isolation or establish installed condition.

A document-only change reopens its dependent answers and synthesis while keeping
the independent drawing answer current. A later history/drawing revision reopens
their dependent answers. An omitted note remains a missing source, not closure.
Two incompatible proposals remain disputed in either arrival order. Earlier
originals, proposed decisions and owner declarations remain reconstructable.

## Use your own prepared records

First run [maintenance history](MAINTENANCE_HISTORY.md) and the
[drawing receiving job](DRAWING_HANDOFF.md) on permitted exports and supplied
readings. Supply a source graph before context binding, with questions separately.
Copy `first/profile.json` from your rehearsal as the profile shape and replace
every fictional identity, source, question and review declaration.

The profile uses `schema: foundation-input-1`, an `id`, local `graph` and `questions`
paths, optional `history` and `drawing` packet specifications, `documents` and
`unavailable` lists. Paths are relative POSIX paths within the profile directory;
symlinks and escaping references are refused. The source packets remain immutable.

| Supplied item | Required meaning and receiving behavior |
|---|---|
| History packet | Existing verified `maintenance-history-result-1` packet with originals/receipt. Supply a package revision label, selected scoped `[scope, record_id]` mappings, node ID, reviewer/date declarations and dependent question IDs. Original table revisions and row locators stay in the archive/projections. |
| Drawing packet | Existing verified receiving packet. Each selected request requires exact drawing ID, request ID, sheet, expected returned revision, scoped asset key and node, reviewer/date declaration and dependent questions. This narrow route refuses requests with multiple subjects; use the original drawing brief for their review. |
| Authored graph | Existing graph schema. Each mapped node needs exactly one `scope` and one `record_id` attribute agreeing with the supplied key. Equal tags alone never join. Existing relations remain sourced and retain their statuses. A declared match is not proof of installed identity. |
| Questions and documents | Existing opportunity-questions/context-sources contracts: exact question IDs, source IDs/revisions, paths, locators and question bindings. Supply the interpretation/proposed answer yourself after checking the evidence. The tool does not understand the document or answer the question. |
| Unavailable sources | Explicit source ID, reason and affected question IDs. Excluded from current supplied sources; previous answers citing them become stale. Do not fabricate a blank document or claim an omission is a removal decision. |

The small adapter flattens **every JSON leaf of each selected dossier/request** into
unverified graph attributes named `foundation.history.*` or `foundation.drawing.*`.
Each attribute retains the source record/version/hash/JSON pointer. Booleans,
numbers, null, empty strings and lists retain their JSON types; decimal strings
stay lexical strings. Empty objects have no plain graph representation and are
listed in `projection.json`. Complete structured records, unselected findings,
source documents and receipts stay in the source archive. This is not native
ingestion of a complete maintenance database, arbitrary CAD objects or every
information type into a graph.

```sh
python -S scripts/foundation_handoff.py prepare --profile my-records/profile.json --out out/prepared
python -S scripts/context_register.py prepare --model out/prepared/graph.json --questions out/prepared/questions.json --sources out/prepared/sources.json --out out/context-prepared
```

Inspect the retained source evidence. Complete a copy of `answers.csv` using
`evidence_choices.csv`; preserve fingerprints. Follow the
[context register guide](CONTEXT_REGISTER.md) for answer/owner declarations.
For example, write the edited copy as `out/reviewed-answers.csv`:

```sh
python -S scripts/context_register.py apply --model out/prepared/graph.json --questions out/prepared/questions.json --sources out/prepared/sources.json --answers out/reviewed-answers.csv --out out/context-applied
python -S scripts/foundation_handoff.py deliver --prepared out/prepared --context out/context-applied --out out/delivery-1
python -S scripts/foundation_handoff.py receive --packet out/delivery-1 --out out/received-1
```

Each output folder must be new. `receive` actually loads the graph and bound
sidecar, pages all decision/relationship/current-question records, reads complete
nodes, questions and per-question sources/ownership, and compares all represented
content with type-sensitive checks. It then reopens a relocated copy and requires
the complete file inventory to match. Graph review events and metadata remain in
the graph file; they are explicitly reported as unserved graph-tool records.
Counts alone cannot establish receiving success.

## Receive the next change

Prepare the next source packets and a new foundation directory. Run context
`prepare` or `apply` with `--register out/received-1/context.json`. The existing
register recomputes answer freshness against source bytes/revision/locator and
the whole bound asset/question semantics. It does **not** provide field-level
impact analysis: changing any bound asset content can reopen an answer about it.
Choose truly independent records when testing selective reopening.

Deliver with `--previous out/received-1`. The earlier packet and ordered history
must remain intact. `changes.json` exposes changed identity/review declarations
and unavailable sources. Read the previous packet's receipt SHA256, then receive:

```sh
python -S scripts/foundation_handoff.py deliver --prepared out/next-prepared --context out/next-context --previous out/received-1 --out out/delivery-2
python -S scripts/foundation_handoff.py receive --packet out/delivery-2 --expected-base PREVIOUS_RECEIPT_SHA256 --out out/received-2
```

The receiver supplies the base it actually holds. A different base, existing
destination or duplicate delivery is refused; reconcile competing histories in a
new reviewed job. This CLI preserves immutable delivery chains (maximum eight)
and does not operate a shared concurrent publication database. A hash proves byte
identity, not the author's authority or the truth of the source. Review/owner names
are declarations, never authenticated company acceptance.

For an organization, agree where accepted source records and facts remain
authoritative, who publishes and reviews each change, permitted access/retention,
the next refresh trigger and receiving acceptance. Qualify the actual destination's
mapping/readback, conflicts, permissions and recovery separately. This workflow
does not establish a maintained connector, live synchronization, human benefit,
plant truth, CAD qualification or product compatibility. See the
[foundation roadmap](ENGINEERING_FOUNDATION.md) and [consulting scope](WORK_WITH_ME.md).
