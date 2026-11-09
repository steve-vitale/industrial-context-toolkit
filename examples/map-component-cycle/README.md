# Reuse engineering context for three component drafts

Start with equipment/instrument CSVs and work-order exports you already have.
The development tool retains your originals, identifies scoped positions, keeps
competing source accounts visible, and drafts a list, datasheet scaffolds and
loop/control-narrative outlines from the same facts. No account or network is
required. An agent can inspect the typed context directly through the CLI.

This is a bounded prototype over record exports and supplied source-bound
interpretation. Existing graph/model adapters, scoped source filtering, generator
projection, browser interaction and actual ChangePilot receiving remain part of
the [unfinished goal](PLAN.md). Local packet verification establishes source/draft
replay; it does not establish engineering truth or product acceptance.

## Obtain the first useful finding

Python 3.10+ and its standard library are sufficient. From the repository root,
choose new output folders:

```sh
python -B -S scripts/context_workflow.py capabilities
python -B -S scripts/context_workflow.py prepare --records examples/map-component-cycle/inputs/development/rev1 --site CF --plant P1 --out out/my-context-r1
python -B -S scripts/context_workflow.py query out/my-context-r1 --item CF/P1/U1/P-101 --field serial_number
```

The equipment export says OLD-101; the latest dated supplied closed order records
NEW-101. The result is disputed, with source/revision/CSV locators for both. The
open order's FUTURE-101 remains a proposal on its own maintenance record. None
establishes the current installed condition. U2's same-tag P-101 stays separate;
bare P-101 selection requests a qualified identity.

For your own records, substitute the records directory and site/plant. Recognized
headers include Tag/Equipment/Asset Number, Area/Unit/Functional Location, Serial,
Manufacturer, Model, Order, Closed and Installed Serial. Delimiters are detected
from comma, semicolon, tab or pipe. CSV values remain source text; blank cells do
not become observations. Unknown columns and uninterpreted documents remain in
the originals with an omission report. Unclear identity, duplicate mappings and
changed headers request clarification rather than guesses. Review generated
`mappings.json` once when your column dialect needs an explicit mapping; an agent
can prepare it. The customer does not need to author the projection JSON.

An optional `source-register.csv` uses File, DocumentID, Revision, Status, Owner,
Applicability columns. Without it, file names identify sources and revision,
owner and applicability remain unknown. The register is a declaration, not an
authenticated release. Supported dates are ISO by default; explicitly select
MDY or DMY when needed. Missing referenced files are retained as missing sources.

## Reuse the facts and revise them

The packet contains `basis.json`, all three typed component drafts in
`drafts.json`, readable `equipment-instruments.csv`, `datasheets.md` and
`control-outline.md`, saved mappings, exact originals and a receipt. Shared
fields reuse the same claim records. Missing facts stay UNKNOWN; disputed values
remain alternatives. The datasheet is a scaffold, not a vendor specification.

The narrative outline needs an explicit controller classification and supplied
reads/commands relationships. It infers no setpoints, sequences, fail positions,
trips, physical flow or control strategy from tags alone. The integration tests
supply a reading of NOTE line 4 via contribution CSV. The plain preparation
command above retains the note but does not interpret it automatically.

```sh
python -B -S scripts/context_workflow.py edit out/my-context-r1 --item CF/P1/U1/P-101 --field draft_review_note --value "Confirm manufacturer from permitted nameplate evidence." --rationale "Nameplate evidence is not supplied" --out out/my-context-edited
python -B -S scripts/context_workflow.py prepare --records examples/map-component-cycle/inputs/development/rev2 --site CF --plant P1 --previous out/my-context-edited --out out/my-context-r2
python -B -S scripts/context_workflow.py compare out/my-context-edited out/my-context-r2
python -B -S scripts/context_workflow.py verify out/my-context-r2
```

`--previous` reuses mappings, retains editorial proposals and complete earlier
packets. The proposal is not a replacement source claim. The second revision
changes rated-flow content in the list and datasheet. The datasheet source's
revision also changes the evidence basis of its unchanged temperature field;
independent instrument/other-unit fields remain exact. The third fixture withdraws
the datasheet: its value remains available as inactive evidence.

`reimport PACKET --draft PATH --out NEW` accepts an own-format draft against its
exact basis and explicit editorial proposals. Changing generated source fields
is refused. Reimport does not add sources or independent support. Use `edit` for
ordinary text/boolean/integer/number/null proposals; no JSON editing is required.

## Supply interpretation explicitly

`prepare --contributions PATH` accepts CSV with Subject, Predicate, Source,
Locator and Quote. Claims additionally use Value, Type and optional Unit;
relations use Target. A locator is `line N`, with a literal quote from the
hash-bound UTF-8 original. Subjects/targets use qualified identities. An empty
subject creates a document record for a document-only finding. Source-bound
contributions are supplied agent/engineer interpretation and remain unreviewed;
matching a quotation does not validate its engineering meaning. PDF/image reading
and structured-model adapters require their own supported preparation.

## Preserve and reopen privately

```sh
python -B -S scripts/context_workflow.py bundle out/my-context-r2 --out out/my-context-delivery.json
python -B -S scripts/context_workflow.py unbundle out/my-context-delivery.json --out out/my-context-reopened
python -B -S scripts/context_workflow.py verify out/my-context-reopened
```

The payload retains full originals and history, and reopens without the original
workspace. `--expected-sha256` on unbundle and `--expected-receipt` on verify can
check independently retained identities. Hash consistency is not authentication.
Keep company records in an approved private location. Selecting `--item` or
`--scope` limits component views, **not original-file access**: packets and bundles
still retain whole supplied files. Do not use selection as a sharing boundary.
Annotations for other items are excluded from selected component drafts; the
private basis retains them. A separately qualified scoped receiving export is
still required by the goal.

Limits: each JSON/source up to 128 MiB, complete packet up to 512 MiB, bundle
default 25 MiB, nine retained versions including the current packet, traversal
depth up to eight and at most 10,000 returned nodes/edges. These are software
bounds, not measured plant capacity. Values beyond supported float precision
are refused rather than silently rounded. Exact originals and typed alternatives
remain retained. No scale/load or product acceptance follows from these limits.

## What is tested and what remains

```sh
python -B -S examples/map-component-cycle/reproduce.py --out out/my-context-development-check
```

The current development suite passes 37 methods against exposed fictional
records and source-authored literal keys. It exercises actual separate-process
commands, three drafts, edits, three revisions, relocation, delivery reopening
and specific tamper refusals. The retained failures include source/selection faults,
column-order replay, correction lineage and proposal retention; see
[development evidence](DEVELOPMENT.md).
The [earlier-route baseline](BASELINE.md) remains separate.

All 31 full-goal acceptance cases remain incomplete. No frozen transfer, clean
clone release, browser/customer trial or actual authenticated product receiving
has passed. No native CAD failure is changed by this work.

The intended managed-service value is continuing ownership, access, source
maintenance, auditable decisions and revision history over the same foundation.
The customer should carry the existing context forward rather than re-enter facts.
Until actual ChangePilot receiving/readback/export passes, this guide offers only
the local reusable context and portable payload, not a ready product integration.
