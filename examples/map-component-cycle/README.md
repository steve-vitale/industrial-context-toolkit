# Reuse engineering context for three component drafts

Start with equipment/instrument CSVs and work-order exports you already have.
The development tool retains your originals, identifies scoped positions, keeps
competing source accounts visible, and drafts a list, datasheet scaffolds and
loop/control-narrative outlines from the same facts. No account or network is
required. An agent can inspect the typed context directly through the CLI.

This is a bounded prototype over record exports and supplied source-bound
interpretation, with an equipment-only projection into the existing generator.
Existing graph/model adapters, scoped source filtering and complete ChangePilot receiving qualification remain part of
the [unfinished goal](PLAN.md). Local packet verification establishes source/draft
replay; it does not establish engineering truth or product acceptance.
The [receiving development record](RECEIVING_DEVELOPMENT.md) separates actual
isolated application results, including sequential scoped receiving, from the
remaining broader application controls and release checks.

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
Manufacturer, Model, Order, Closed and Installed Serial. Delimiters are selected from comma, semicolon, tab or pipe only when complete quoted
record structure is unambiguous. Ambiguous inputs request a source-level delimiter choice in the
existing reviewed mapping; its retained delimiter is reused on replay and revisions. CSV values remain source text; blank cells do
not become observations. Unknown columns and uninterpreted documents remain in
the originals with an omission report. Unclear identity, duplicate mappings and
changed headers request clarification rather than guesses. Review generated
`mappings.json` once when your column dialect needs an explicit mapping; an agent
can prepare it. The customer does not need to author the projection JSON.

This route treats the mapped Tag/Equipment column as a **functional-position
key within the declared unit**. Confirm that meaning before using your exports:
an asset number for a movable physical item is not automatically a position key.
Retain a supplied physical-item ID separately and request the owner's explicit
position mapping when needed. A matching serial, tag spelling or header does not
settle that engineering identity question.

An optional `source-register.csv` uses File, DocumentID, Revision, Status, Owner,
Applicability columns. Without it, file names identify sources and revision,
owner and applicability remain unknown. The register is a declaration, not an
authenticated release. Supported dates are ISO by default; explicitly select
MDY or DMY when needed. Missing referenced files are retained as missing sources.

### Reproduce the document and drawing context routes

For a document-only question or supplied drawing interpretation, run the exposed
fixture replay with Python's standard library:

```sh
python -B -S examples/map-component-cycle/reproduce_entry_jobs.py --out out/my-entry-jobs
```

The document example retains the original onboarding notices: notice B says
text `2.5`, displayed unit `bar`, and does not establish a governing deployed
revision. An attributed peer explanation stays unverified. The drawing example
keeps the original DXF/request bytes and both returns: the returned model changes
from `OTHER-CHOICE` to requested `Assembly {D}`, while the separately observed
serial remains `FIELD-OBSERVED`. The whole-basis comparison includes that custom
field instead of relying only on changes to the three standard components.

The replay uses **supplied interpretations**, not an automatic document or
drawing reader. Inspect the CSVs and frozen source keys in
[inputs/entry-jobs](inputs/entry-jobs/INPUTS.json): seven document interpretation
rows and four drawing rows per revision, plus four/three source-register rows.
For your records, an engineer or permitted assistant prepares those source-linked
rows, including exact quotations and original locations. Matching a quotation
does not validate its engineering interpretation. No customer JSON editing or
account is needed; preparation and review still take work.

Actual commands, outputs and failures are retained in the selected output folder.
The replay withholds its preparation folders before fresh-process reopening and
checks exact packet files, original typed values and drawing history. It writes
`document.context.json` and `drawing.context.json` for a separately qualified
receiving route. This does not rerun the native CAD qualification or establish a
released ChangePilot import; the drawing's unresolved receiving findings and
engineering acceptance remain separate.

## Scaffold existing generator outputs from the same basis

Use the packet above to project supported equipment into the existing process-model
consumer and produce actual readable SVG, Ignition equipment templates without measurement tags,
PI equipment staging rows and an operations review sheet:

```sh
python -B -S scripts/context_workflow.py generate out/my-context-r1 --out out/my-equipment-scaffold
python -B -S scripts/context_workflow.py verify-generated out/my-context-r1 out/my-equipment-scaffold
```

The bridge honors the packet's draft selection. A functional position needs an
explicit area/unit scope and unambiguous active source-declared `class` and
`description`. The class must already be supported by `generate.py`; no new
class catalog or guessed fallback is used. Wrapped human labels and export descriptions retain source tags, scopes and names.
Safe export IDs map reversibly to the
original qualified identities in `projection.json`, so U1/P-101 and U2/P-101 stay
distinct. `model.json` contains no assumed pipe streams, instruments, final
elements, measurements, owning units, setpoints or numeric engineering values.
All exported equipment remains unverified.

Unknown, conflicting, inactive and proposed facts, unsupported instrument/model
classes, source revisions/locators/roots, and editorial proposals remain in the
projection's context and omission records. Retained source statements are not
engineering acceptance; a proposed edit does not replace its source facts. The
same input packet remains the home of exact originals, history and three drafts.
This scaffold output alone is not a full-source transfer.

`generated/` is built by the actual existing `generate.py` CLI. Its automatic
screen positions are presentation, not engineering layout. UDT type BasePath
defaults are empty, OPCServer defaults to `Ignition OPC UA Server`, and instance
BasePath values are generated `ns=1;s=context_<basis digest>.<safe equipment key>`
placeholders. These nonempty defaults are not discovered OPC addresses or working
signals; there are no atomic measurement tags. PI rows are equipment staging,
not a site import. `verify-generated` reopens the source packet, reprojects the model and
runs that consumer again, comparing every delivered file. A changed method,
source, model, projection or output refuses; choose a fresh output folder for a
new revision. These checks establish bounded software replay, not CAD, gateway,
PI or plant acceptance.

## Find changed tags through an explicit source crosswalk

If your exports already use stable functional-position keys, supply an ordinary
CSV with `Position,Area,Alias` columns to associate drawing or legacy tags with
those existing positions. This is an explicit source declaration, not a fuzzy
match or an entity merge. A source register can record its revision, owner,
applicability and supplied/withdrawn status; exact original bytes are retained.
Try the fictional ordinary-export example without editing JSON:

```sh
python -B -S scripts/context_workflow.py prepare --records examples/map-component-cycle/inputs/identity-change/rev1 --site IX --plant P1 --identity-crosswalk identity-crosswalk.csv --out out/identity-r1
python -B -S scripts/context_workflow.py query out/identity-r1 --item LEGACY-7 --field class
python -B -S scripts/context_workflow.py query out/identity-r1 --item IX/P1/U1/P-101 --field class
```

`LEGACY-7` resolves to `IX/P1/U1/FP-1001`, with the exact crosswalk claim, source
revision, CSV locator, hash and source roots in `identity_resolution`. Bare
`P-101` is ambiguous between U1 and U2 and requests a qualified identity. Aliases
form a declared set, not competing scalar values. Each lookup can still be
ambiguous across positions. Existing unqualified legacy alias arrays remain
legacy declarations; this mode does not invent provenance for them.

```sh
python -B -S scripts/context_workflow.py prepare --records examples/map-component-cycle/inputs/identity-change/rev2 --site IX --plant P1 --previous out/identity-r1 --out out/identity-r2
python -B -S scripts/context_workflow.py query out/identity-r2 --item P-201 --field identity_alias
python -B -S scripts/context_workflow.py prepare --records examples/map-component-cycle/inputs/identity-change/rev3 --site IX --plant P1 --previous out/identity-r2 --out out/identity-r3
python -B -S scripts/context_workflow.py query out/identity-r3 --item IX/P1/U1/FP-1001 --field identity_alias
```

`--previous` reuses the explicit relative crosswalk path. Revision3 withdraws the
crosswalk: `P-201` then refuses current lookup; its old declaration remains in
history. Direct stable-position queries continue to work. A crosswalk target
must already exist as a functional position; a missing target or an alias that
shadows a different canonical ID refuses. Rekeying all source position IDs,
merging entities or tracking a physical item globally across unit moves needs a
separately defined mapping. This feature does not perform that reconciliation.

The supplied closed-order history reports distinct `ITEM-A` and `ITEM-B` at the
same stable position, even though both records contain `SERIAL-X`. A serial
alone never merges those physical identities. Installation links remain supplied
historical accounts, with no unqualified claim about what is installed now.
Open-order physical proposals do not create an installed physical entity.

The crosswalk is an original source file. Selecting an item does not remove
other-unit rows from that file; a scoped transfer must inspect its whole-file
privacy preview. External boundary references do not become selectable entities
or alias targets. Local source-bound lookup and packet replay do not establish
ChangePilot alias-query compatibility; product lookup/readback needs its own
qualified receiving check.

## Reuse the facts and revise them

The packet contains the complete typed `basis.json` and an explicitly named
compact view specification in `drafts.json`, plus readable
`equipment-instruments.csv`, `datasheets.md` and `control-outline.md`, saved
mappings, exact originals and a receipt. The specification binds the selection,
method and canonical full-draft digest; reopening regenerates all three views
and checks the actual readable files. Shared fields reuse the same claim records.
Older packets containing full typed `drafts.json` remain readable without rewriting.

Use `materialize` to export a full typed draft for inspection or explicit edits:

```sh
python -B -S scripts/context_workflow.py materialize out/my-context-r1 --out out/my-context-full-draft.json
```

When a target has no supported items, the retained `control-outline.md` wording
"inspect the explicit gaps in drafts.json" refers to the full typed draft. In a
compact packet, `drafts.json` contains only the view specification; use the
`materialize` command above and inspect `components.loop_control_narrative_outline.gaps` in
`out/my-context-full-draft.json`. The existing readable artifact wording is
retained so earlier packets continue to replay byte for byte.

The materialized artifact uses the existing full-draft schema. It is bounded by
the same 128 MiB JSON input limit used by reimport; an oversized materialization
refuses without publishing a partial file. Optional `--item` or `--scope` selects
a draft view. Neither draft selection nor compact storage filters retained basis
facts or original files; a source-private scoped transfer is a separate route. Missing facts stay UNKNOWN; disputed values
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

The `compare` result keeps the existing component `changes` and adds
`basis_changes` for the whole represented map, including custom fields that no
component uses. It compares scoped identity/boundary declarations, every claim
and outgoing relationship group, source records and their declared lineage,
and retained preparation, omissions and editorial proposals. For example, a
source-bound `returned_model` change appears here even when none of the three
draft components depends on that field.

Each changed field includes its before/after query evidence and fingerprints.
`content_changed` means its retained typed literal or unit changed; units are not
silently normalized. `availability_changed` means retained evidence became active
or inactive, or the field's availability changed. `basis_changed` retains changes
to sources, locators or review declarations without establishing a typed-literal change.
For relationship targets, comparison also matches unique declared occurrences
by subject, predicate, source, locator and role, excluding the mutable target.
Two sources exchanging targets are therefore content changes. When a source
location names several relationships, `occurrence_matching.ambiguous_anchors`
retains their IDs without guessing row pairs; individual content attribution can
remain unresolved even if the group is classified `basis_changed`. Direction,
role and all other retained evidence remain visible in the before/after records.
Added/removed fields remain distinct from an explicit null; a field absent from
a retained item is `unknown`, while an absent item is `subject_unavailable`.
These are record differences, not proof of equipment removal, accepted changes
or independent support. No affected output is inferred beyond the component
dependencies reported separately. Packet `changes.json` retains its existing
component-only contract; whole-map comparison is an explicit CLI query over the
two retained bases. A large comparison can contain extensive before/after evidence;
it is not a paged browser or a measured plant-scale service.

`reimport PACKET --draft PATH --out NEW` accepts the full typed artifact exported
by `materialize` (or an older full draft) against its exact basis and explicit
editorial proposals. A compact view specification is not an editable full draft. Changing generated source fields
is refused. Reimport does not add sources or independent support. Use `edit` for
ordinary text/boolean/integer/number/null proposals; no JSON editing is required.

## Review and edit without writing JSON

```sh
python -B -S scripts/context_workflow.py review out/my-context-r1 --out out/my-context-review.html
```

Open the HTML in a browser. Search by tag, choose the fully scoped item, and
switch between the three component drafts. Inspect disagreements, missing
prerequisites, inactive evidence, source filenames/revisions, declared owners
and applicability. Expanded source details retain exact value types and literals.
The page works offline and contacts no service.

Choose a field or review note, enter proposed text and a reason, then select
**Download proposed edit**. Keep that file and ask your agent to apply it:

```sh
python -B -S scripts/context_workflow.py apply-review out/my-context-r1 --edit context-review-edit.json --out out/my-context-reviewed
python -B -S scripts/context_workflow.py review out/my-context-reviewed --out out/my-context-reviewed.html
python -B -S scripts/context_workflow.py verify-review out/my-context-reviewed out/my-context-reviewed.html
```

The downloaded text proposal is bound to this exact packet and field/source
dependencies. A changed packet refuses it; reopen the current review and
explicitly rebase. Earlier proposals remain available, while source facts remain
unchanged. Numeric or structured proposals can use the existing typed CLI/API
contracts; the browser form deliberately proposes text. It saves to a download,
not to the page or a managed service. Review HTML is capped at 32 MiB; edits at
128 KiB and 32,768 characters per text field. The page checks encoded byte size
before download, including Unicode/escaping overhead.

[View the saved fictional review](development/review-browser-01/review.html) after
downloading/opening it locally. The [browser run](development/review-browser-01/run.json)
records actual desktop and 390px interactions, downloaded edits and fresh-process
readback. This selected view does not redact the underlying source packet.

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

For an explicit local scoped packet, verify the full packet, preview exact included whole files, then
acknowledge the returned preview SHA before packaging:

```sh
python -B -S scripts/context_workflow.py scope-preview out/my-context-r1 --item SITE/PLANT/UNIT/ITEM --out out/scope-preview.json
python -B -S scripts/context_workflow.py package-scope out/my-context-r1 --item SITE/PLANT/UNIT/ITEM --permit-whole-files-preview PREVIEW_SHA --out out/scoped-context
```

Replace the qualified item with the actual identity returned by your packet. This `records_scoped_v1`
route omits unrelated structured context, files and history; every included original is still WHOLE and
may contain unrelated content. This is not row redaction or an access grant. Incoming identity-only
subjects are explicit unexpanded references, excluded from lookup/draft targets; further traversal refuses
missing context. Fully retained supporting records can be explicitly materialized in the separate
`engineering-scoped-component-materialization-1` JSON envelope; default targets remain selected items.
Corrections retain immutable original proposals and qualified historical field witnesses, not verification
of an omitted whole-parent basis. New edits use the original permitted packet followed by a new preview.
Managed scoped receiving/persistence remains separately unqualified.

For the next customer revision, pass the previously delivered scoped packet to **both** commands:

```sh
python -B -S scripts/context_workflow.py scope-preview out/my-context-r2 --item SITE/PLANT/UNIT/ITEM --previous-scoped out/scoped-r1 --out out/scope-r2-preview.json
python -B -S scripts/context_workflow.py package-scope out/my-context-r2 --item SITE/PLANT/UNIT/ITEM --previous-scoped out/scoped-r1 --permit-whole-files-preview NEW_PREVIEW_SHA --out out/scoped-r2
```

Prepare the new full packet with `prepare --previous` first. The scoped builder verifies the supplied
prior packet against that actual original ancestor and retained selected semantics, then copies its entire
inventory, receipts and original whole-file permissions unchanged. The new preview discloses the new and
retained historical whole files; its new acknowledgement does not grant permission for omitted files.
The explicit `engineering-context-incremental-history-1` marker binds each adjacent scoped predecessor
and original source receipt. The preview separately binds the fixed already-delivered anchor, avoiding a
receipt/preview hash cycle. A unit selector can gain real source identities on a later revision; its policy
must remain the same. Without `--previous-scoped`, the existing route projects an entire historical chain
under one preview and does not promise continuity with an independently delivered earlier scoped packet.
Intervening editorial revisions remain in order. A receiving product may require those revisions to be
admitted sequentially; local verification does not establish a single-jump or authenticated receiving claim.

Sparse identity-only exports retain the ordinary CSV constructor source and exact row locator as a
`scoped_identity_origin` preparation witness when that source would otherwise be lost. It declares an
identity occurrence/prerequisite, not an engineering fact, additional alias support, authenticated origin
or verified current installation. Inactive source declarations remain inactive. No fake engineering field
is added to make an identity selectable.

When the existing source-bound identity crosswalk is retained, scoped input/config explicitly carries
its same relative CSV path. Only retained subject rows are interpreted, with original physical row locators;
whole mixed-unit crosswalk bytes remain disclosed. Omitted target records do not require importing their
unrelated source files or declarations. Before-scoping ambiguous aliases refuse. After an explicit qualified
selection, alias uniqueness is projection-local, never global or namespace-wide identity. Only exact
retained active source lineage activates aliases; withdrawn rows stay readable as inactive evidence.

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

The current development suite passes 154 methods against exposed fictional
records and source-authored literal keys. It exercises actual separate-process
commands, three drafts, edits, three revisions, relocation, delivery reopening
and specific tamper refusals. The retained failures include source/selection faults,
column-order replay, correction lineage and proposal retention; see
[development evidence](DEVELOPMENT.md).
The [earlier-route baseline](BASELINE.md) remains separate.

The optional actual-browser development runner needs Node, Playwright and a
supported installed browser: `node examples/map-component-cycle/reproduce_review.cjs out/my-review-check`.
`PLAYWRIGHT_PACKAGE` can select an existing Playwright install; `BROWSER_EXE`
can select its executable. These are verification prerequisites, not customer
requirements for opening the HTML. The runner serves only the review page on
an ephemeral loopback port and closes its server/browser afterwards.

All 31 full-goal acceptance cases remain incomplete. Final frozen transfer,
clean-clone release and complete product receiving/release qualification remain
unfinished. No human/customer trial has run. No native CAD failure is changed by this work.

The intended managed-service value is continuing ownership, access, source
maintenance, auditable decisions and revision history over the same foundation.
The customer should carry the existing context forward rather than re-enter facts.
Until the full ChangePilot receiving/readback/export and release checks pass, this guide offers only
the local reusable context and portable payload, not a ready product integration.

The consumed second-record dialect case is a development regression after its first frozen run failed. Passing the repaired parser controls does not create a new transfer result; any later transfer uses separate inputs and a new pre-execution method lock.
