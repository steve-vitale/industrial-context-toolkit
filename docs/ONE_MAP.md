# One map: P&IDs, equipment and instrument records, datasheets and documents in one graph

`scripts/one_map.py` is a prototype that puts a site's P&IDs, its equipment and instrument records, its datasheets
and its documents into one graph (`twin-graph-2`, an additive extension of [twin-graph-1](GRAPH_EXPORT.md)). Each
department keeps its own records. The tool connects them, keeps every disagreement as a conflict record, and sends
that record to its owner's review queue for a person to hand over. It is deterministic, runs offline on the Python standard library and calls no
model. Three worked examples: a fictional two-plant site ([examples/one-map](../examples/one-map/README.md)), a
fictional dairy pasteurizer that shows classes, link checks, expectation rules and the plant glossary
([pasteurizer](../examples/one-map/README.md#the-pasteurizer-classes-expectations-glossary)) and one public P&ID sheet
read by the drawing reader ([examples/drawing-to-map](../examples/drawing-to-map/README.md)).

"Equipment and instrument records" below means the **maintenance equipment export**, the **instrument index** and
the **loop list**. The **sheet index** says which unit each P&ID sheet covers (`drawing_register` in the site file).

For questions across sheets, use the [path and review-status consumer](PID_GRAPH_QUESTIONS.md): current
pairings retain evidence and disagreements; explicit traversal rules qualify their use in an answer.
Network membership, physical adjacency and operating consequences require different evidence.

## The path

To **use a map you have built**, open the [offline map explorer](../examples/map-explorer/README.md).
It connects item selection, sourced facts/questions, related documents, stored
relationships, disagreements and previous/current snapshots in one read-only
package. It retains complete maps and optional hash-bound originals. It does not
qualify operating routes or manage work; use the path-review rules above when a
route question needs them. An assistant can read the same exported JSON directly.

For a bounded equipment/work-order comparison, you can start without P&ID sheets. The
[ordinary-export example](../examples/agent-first-use/README.md) prepares equipment and closed-work records with
an empty drawing register. This compares supplied values; it supplies no drawing geometry or connectivity.

For the drawing-backed site-wide map, follow these steps. What a site starts with changes which steps need preparation.

1. **Read every P&ID sheet of the unit.** The drawing reader writes a prediction per sheet in the documented format
   ([PLUG_IN_A_READER.md](PLUG_IN_A_READER.md); the [own-drawing runbook](../examples/own-drawing/README.md) makes
   one from a PNG). `one_map.py sheet-from-prediction` converts it into a sheet read (`one-map-sheet-1`): tags with
   sheet zone and box, piping runs between tagged items traced through untagged valves and fittings, instrument
   placements where the reader's connections make them unique, off-page connectors, and every symbol it could not
   place carried under `untagged`. A sheet read can also be written by hand. Add each sheet to the sheet index.
2. **Line the P&ID read up against the equipment and instrument records that exist.** A tag on both gets its sheet
   and zone and a green review queue row with a deterministic spot-check sample; a tag in only one of them is an
   `asset_presence` conflict for the owner of the record that should hold it.
3. **Where no record exists for a scope, the P&ID read becomes its draft.** `one_map.py draft-lists` writes a draft
   maintenance equipment export, draft instrument index and draft loop list in the import formats, every row
   `unverified`. After review they are ordinary records and step 2 applies on every later revision.
4. **Compare values between datasheets and the equipment and instrument records.** Ratings, sizes and materials
   come from equipment datasheets and instrument spec sheets; the P&ID owns tags, connectivity and the control
   scheme. A disagreement is routed to the owner of the record that is not authoritative
   ([which record owns which fact](#which-record-owns-which-fact)).
5. **People work the review queue, safety items first.** Conflicts are red, review items amber, matches green;
   safety-relevant items are never green. The queue splits by owner, plant and unit.
6. **A P&ID revision re-reads that sheet only.** `build --out DIR` keeps state; a changed sheet is re-read, the map
   is reassembled, and documents based on a changed document reopen.

```sh
python scripts/one_map.py sheet-from-prediction predictions/r2-tiles-trace/codex/0.json --sheet 140 --rev A \
    --plant NPP --unit MSS --zone-frame 9.4,19.5,857.1,981.1 --out my-site/sheets/140.json   # step 1
python scripts/one_map.py build my-site/site.json --out out/my-map                               # steps 2, 4, 5, 6
python scripts/one_map.py draft-lists my-site/site.json --out out/my-drafts                      # step 3
python scripts/one_map.py check out/my-map/graph.json
python scripts/one_map.py ask --map out/my-map/graph.json --question-kind complete --item TT-2207  # read-only
python scripts/one_map.py jsonld --map out/my-map/graph.json --out out/my-map/map.jsonld          # optional view
```

### Bonus steps by goal

| If the goal is | Add | With |
|---|---|---|
| A sourced draft asset model, Ignition tags and PI staging files for one sheet | the per-sheet intake bundle from the same reader output | [`import_site_drawing.py`](../examples/own-drawing/README.md) |
| Grading a loop list against a P&ID answer key or model | a loop audit | [`loop_audit.py`](../examples/loop-audit/README.md) |
| Answers that reopen when the documents they cite change | a context register (`build --register`) | [`context_register.py`](CONTEXT_REGISTER.md) |
| Loop candidates on an existing twin-graph-1 export | `one_map.py loops-from-graph` | this tool |
| Splitting an intake review queue by any column | `one_map.py split-queue` | this tool |
| Choosing or replacing the reader | scoring beside perfect, wrong and empty controls | [vendor evaluation](../examples/vendor-evaluation/README.md), [PLUG_IN_A_READER.md](PLUG_IN_A_READER.md) |

A [DEXPI export](../examples/from-dexpi-xml/README.md) skips reading for the asset model route; converting a DEXPI
export into a one-map sheet read is not built yet.

## Which record owns which fact

The site file's `authority` maps each kind of fact to the record that owns it; any entry may be overridden.

| Fact kind | Default authority | Attributes it covers by default |
|---|---|---|
| `connectivity`, `tags`, `control_scheme` | `pid` | piping lines, signal lines, which tags exist where |
| `rating` | `datasheet` | `rated_*`, `design_*`, `max_*`, `min_*`, `rating`, `duty`, `capacity`, `set_pressure` |
| `size` | `datasheet` | `size`, `line_size`, `nominal_size`, `*_size` |
| `material` | `datasheet` | any name containing `material` |
| `instrument_range`, `instrument_model` | `instrument_index` | any name containing `range`; `model`, `manufacturer`, `make`, `vendor` |
| `installed` | `maintenance_export` | `installed*`, `serial`, `serial_number`, `asset_number` |

`fact_kinds` in the site file names the kind of any other attribute (`{"trip_setting": "rating"}`). Datasheets are
CSV files (`tag,plant,unit` plus one column per value), declared under `datasheets` with an `id`, `path`,
`revision` and `scopes`, owned by `record_owners.datasheet`. A datasheet adds values to an item that an equipment
or instrument record or a P&ID holds; a row for an item nobody else holds is a review item for its owner.

When two records give different values, the authoritative one is source A and the `value_disagreement` goes to the
owner of the other (datasheet 45 m3/h, maintenance equipment export 40 m3/h: Maintenance). When neither is the
authority, it goes to the owner of the record read later. **Values printed on a P&ID are reference only**: one that
differs from the records is a low-priority `P&ID value note` for the P&ID owner (amber, after every other amber
row), never a value conflict, and the record's value stays on the item.

## The two halves

**The plant half** is a hierarchy with a site-qualified identity: `SITE/PLANT/UNIT/TAG` (`S1/P1/200/P-101`).
The same legacy tag in two plants stays two items (`S1/P1/200/P-101`, `S1/P2/300/P-101`); nothing is renumbered,
and earlier tags stay as aliases (`former_tag`). A site scope that is not a plant (site utilities) owns shared
systems: a shared system such as cooling water has exactly one owning scope, and each plant that uses it reaches it
through a boundary node (`S1/P1/BND-CW references S1/UTIL/CW`). A P&ID sheet that draws the shared system as its own
raises a boundary conflict; it never gains a second owner.

**The document half** holds document nodes: id, revision, `draft` or `released`, owning department and a raw-byte
fingerprint. The registered P&ID sheets are documents too (`PID-P1-200-01` rev D). Three relations join the halves:

| Edge | From | To | Means |
|---|---|---|---|
| `covers` | document | the smallest scope it is about (equipment, system, unit, plant or site) | declared in the document manifest by exact id; never guessed |
| `mentions` | document | an item on the map | a tag, former tag (alias) or site-qualified id found in the text; keeps file, locator, matched text, confidence and, for a format-only match, `matched: format-insensitive` |
| `based_on` | document | another document | with the revision it was based on |

**Reading the documents.** Each document file is read by [`extract_text.py`](DOCUMENT_TEXT.md): PDF (text layer),
Word, Excel, PowerPoint, HTML and plain text, as ordered pieces with a locator (`paragraph 2`, `table 1 row 2`,
`sheet 'PM plan' cell A3`, `page 3`, `slide 4`, `line 7`). Tags are matched within each piece, and a mention's
locator is the piece's locator plus the column, with the line inside the piece when the piece has more than one
line: `paragraph 2, column 41`, `page 3, line 4, column 2`, `line 7, column 12` for a text file. The document node
records what the reader returned (`document.text`: status, format, piece count, reader version).

A document that was not fully read never stops the run. Its status becomes a low-priority **document text note**
to the document's owner (amber, after every other amber row, beside the P&ID value notes):

| Text status | What happened | The note asks for |
|---|---|---|
| `ok` with no text | the file holds no text | a check that this is the right file |
| `partial` | some PDF pages have no text layer, or the text was cut at the character limit (the note says which) | an OCR copy of those pages or the rest of the document; mentions there are not on the map |
| `needs OCR` | no page has a text layer (a scan) | an OCR copy; mentions on those pages are not on the map |
| `needs dependency` | PDF text needs the optional `pypdf` package or a `pdftotext` program | installing one |
| `unsupported` | legacy `.doc`/`.xls`/`.ppt`, RTF, password-protected or an unknown type | a conversion (the note names it) |
| `error` | missing, corrupt, hostile or over a size limit | a readable copy |

**Matching rules.** A mention is linked only when it names exactly one item:

| What the text says | Example | Result |
|---|---|---|
| The tag or a former tag (`former_tag`) exactly, unique on the map | `P-102`, `FP-01` | `mentions`, confidence `exact, unique on the map` (or `via alias (former tag)`) |
| An exact tag that exists in two scopes, one inside the document's `covers` | `P-101` in the Unit 300 check sheet | `mentions`, `exact in covered scope` |
| A site-qualified id | `S1/P2/300/P-101` | `mentions`, `site-qualified exact` |
| The same tag or former tag with other separators, spacing or case, matching exactly one item on the map | `PSV 204`, `TT2205`, `ft-2203`, `FP01` | `mentions` with `matched: format-insensitive` |
| An exact tag in two scopes the `covers` do not choose between | a bare `P-101` in the site cooling water note | `ambiguous_reference` conflict to the document owner |
| The same tag in another format, in more than one scope (even when the `covers` point to one) | `P101`, `P 101` in a Unit 200 procedure | review row `possible mention, confirm`, naming the candidates and the one the covers point to |
| A suffix the map does not have, or a base tag when the map has only suffixed tags | `P-101A` (map: `P-101`); `TE2207` (map: `TE-2207A/B`) | review row `possible mention, confirm` |
| A format-only match to one item outside the plant/unit of every `covers` scope | `P102` in a Unit 300 check sheet when only Unit 200 has P-102 | review row `possible mention, confirm` |
| Lower-case letters followed by a space | `at 2207` | review row `possible mention, confirm` (it may be ordinary words) |
| Upper-case tag-like text not on the map | `ISO 9001` | review row `mention` |
| A certified glossary term naming exactly one item in the document's covered scope | `hold tube`, `FDV` (synonym of `divert valve`) | `mentions`, `matched: glossary`, with the term |
| A draft glossary term, or a term naming several items or none in the covered scope | `timing pump` (draft), `product pump` (two pumps) | review row `possible mention, confirm`, to the term's owner, one per document and term |
| Anything in text read by OCR, exact, format-insensitive or glossary | `EDV-0756` read for `FDV-0756` | review row `possible mention (OCR), confirm`, one per document and text, naming what the map has |
| Lower-case text that is no map tag | `page 12`, `unit 200` | nothing |

**OCR text never links.** OCR turns tags into other tag-shaped strings (`ZSO-8170` read as `7S0-8170`, `FDV-0756`
as `EDV-0756`, `TI-110` as `T-110`), so an exact match in OCR text proves nothing. `extract_text` records OCR per
piece: `ocr` maps each OCR'd piece's locator (`page 2`) to its mean word confidence, and `ocr_engine` is set when
any piece came from OCR. A PDF with some scanned pages keeps engine `pypdf` and status `partial` or `ok (ocr)`, so
the locator decides: a piece named in `ocr` is OCR (the review row gives the confidence), the other pages are a
text layer and link as usual. When `ocr_engine` is set but no piece is named, the whole file counts as OCR. Older
signals still apply when `ocr_engine` is absent (engine starting `tesseract`, status `ok (ocr)`, an `ocr_pages`
list); a result with none of these is read as not OCR.

**Reading options.** The site file may switch on `extract_text` add-ons for every document with a
`document_text` object: `ocr` (`auto` or `off`), `ocr_lang`, `ocr_dpi`, `convert_legacy`, `pdf_layout`,
`excel_display` ([DOCUMENT_TEXT.md](DOCUMENT_TEXT.md) describes each). All are off by default; an unknown option or
a bad value stops the build with a message. With `"ocr": "auto"`, scanned pages are read but their mentions still
only become `possible mention (OCR), confirm` rows.

Format-insensitive means only hyphens, spaces, underscores and letter case are ignored. Digits and suffix letters
must agree exactly, so `P101` never reaches `P-1010` or `P-101A`, and `TT2205` never reaches `TE-2205`. When one
document names the same item both ways, its edge keeps the exact mention's locator and lists the others under
`more_locators`. The matching is deterministic: the same files give the same links in the same order.

## Inputs

| Input | Format | Role |
|---|---|---|
| Maintenance equipment export | CSV `tag,plant,unit[,system,description,status,former_tag,...]` | equipment, valves and relief devices |
| Instrument index | CSV `tag,plant,unit[,description,status,...]` | transmitters, controllers and other instruments |
| Loop list | [loop_audit.py's contract](../examples/loop-audit/README.md) (`controller,measurement,output`), optional `status`; one per unit | the loops |
| Datasheets | CSV `tag,plant,unit` plus value columns | ratings, sizes, materials (see the authority map) |
| Sheet index | CSV `sheet,rev,plant,unit,owner,path[,status]` | which P&ID sheets exist, their revisions, units and owners |
| Sheet reads | `one-map-sheet-1` JSON per sheet: tags with zone/box, lines, signal lines, off-page connectors, `untagged` | what each P&ID sheet shows; written by `sheet-from-prediction` or by hand |
| Records (`records`) | any register of [`registers.json`](../schemas/context-map/registers.json) as CSV in its template's columns, each with `id`, `register`, `path`, `revision`, `scopes` | HACCP plan CCPs, calibration records, relief device register, criticality ranking, PM plan, glossary, ...: read by the expectation rules, the glossary and `ask`; they never create items |
| Expectation rules (`expectations`) | a copy of [`templates/expectations.json`](../schemas/context-map/templates/expectations.json) | completeness rules, certified and rolled out per unit or owner ([Expectations](CONTEXT_MAP_FORMAT.md#expectations)) |
| `as_of`, `letter_overrides`, `equipment_prefixes`, `authority_certification` | site file keys | the date rules compare dates against; the site's own tag letters and equipment prefixes for classes; who certified an authority override (a draft one does not act) |
| Documents | a [context register](CONTEXT_REGISTER.md) `context-sources-1` manifest plus `owner`, `status`, `covers`, `based_on`; the files may be PDF, Word, Excel, PowerPoint, HTML or plain text ([DOCUMENT_TEXT.md](DOCUMENT_TEXT.md)) | the document half |

### Converting a reader's prediction (step 1)

`sheet-from-prediction PREDICTION --sheet --rev --plant [--unit] --out FILE` takes one prediction file, bare or in
its stored `predictions/<label>/<tool>/<sheet>.json` form, and validates it with the intake's own validator first.

- **Tags.** A stacked bubble (`TCV` over `1401`) becomes `TCV-1401`; the text as printed is kept (`printed_tag`).
  Text that is not tag-shaped or has fewer than two digits (a nozzle `N1`, an operator letter `H`, a flag's
  destination) is not a tag. A placeholder (`XXX`, `???`, `TBD`) is kept with `tag_status: placeholder` and becomes
  a `placeholder tag` review item; a tag read twice stays twice and becomes a `duplicate tag` review item.
  Tanks and pumps (and `general` symbols with a `SYS-TYPE-NUM` tag) go to `equipment`, the rest to `instruments`.
- **Zones** come from `scripts/sheet_zone.py`, the same rule `draw_pid_from_model.py` letters its generated sheets
  with: a box is zoned by its centre on a grid of `--zones ROWSxCOLS` (default **8 x 12**) over `--zone-frame
  x0,y0,x1,y1` in 0-1000 units (default the whole image). With the default `--zone-origin bottom-right` (ASME Y14.1
  style, as the OPEN100 and generated TE borders print it) rows are lettered **A at the bottom** to H at the top and
  columns numbered **1 at the right** to 12 at the left; `top-left` (ISO 5457 style) puts A at the top and 1 at the
  left. Zones are written `ROW-COL` (`G-6`). Pass the sheet's frame: computed over the whole image they can be off by
  a row or column near the edges.
- **Piping runs** (`lines`): see [connectivity from a reader prediction](#connectivity-from-a-reader-prediction).
- **Instrument placement**: `on` a vessel or pump, `on_line` a run, or `placement_candidates` for review (same
  section).
- **Off-page connectors** keep their printed reference as `drawing_reference`; `to` stays empty and the map pairs
  them by reference (same section).
- **Not inferred:** signal lines. The prediction format has no line type and the reader has no field that tells a
  signal or instrument line from a pipe, so `signal_lines` stays empty and no loop is proposed from connectivity.
  Loops come from the loop list or a format that carries line types (e.g. DEXPI).
- Every symbol ends up in exactly one of `equipment`, `instruments`, `offpage` or `untagged`; `conversion` counts
  them and lists everything not converted. Untagged tanks, pumps and instrument bubbles each become a review item;
  untagged valves and fittings one summary row per sheet.

### Connectivity from a reader prediction

The reader's connections join symbols, not lines: an untagged valve or fitting is a node like any other, and on
OPEN100 sheet 0 the code line tracer joins every symbol touching one drawn header to every other. The conversion
turns them into runs between tagged ends with these rules (`scripts/one_map.py`, constants `MAX_RUN_ENDS`,
`PLACE_HOPS`):

- **Run ends and in-line items.** Tagged tanks, pumps, valves and fittings and off-page connectors end a run.
  Untagged valves and fittings (class `valve`/`general`, no usable tag: reducers, tees, junctions, nozzles, traps)
  are in-line items a run passes through, whatever their number of connections. Instrument bubbles never carry a
  run: a bubble's link is its leader or signal line, not pipe.
- **Tees and branches.** Each connected group of untagged in-line items is a network. A network touching N run ends
  yields one run per pair of ends (a tee joining three ends gives three runs), so a run is a statement that two
  tagged ends are connected through untagged items, not a line number. A network with more than `MAX_RUN_ENDS` = 12
  ends (66 runs) writes no runs and is listed under `conversion.branched_networks` with `runs_written: false`.
- **What a run carries.** `through` counts the in-line items (`2 valves and 1 other in-line symbol`);
  `via_symbols` lists them in path order; `prediction_connections` lists the reader's connections along the path
  (`c12` is index 12 of the prediction's `connections` list), so every run traces back to the prediction. The path
  is one shortest path (fewest symbols, ties by symbol id); in a network with three or more ends,
  `branched_network` says so and other paths may exist. Direction is `unknown`: the ends are ordered by symbol id,
  not by flow.
- **Instrument placement.** From a tagged instrument bubble the conversion walks out through untagged in-line items
  one hop at a time, up to `PLACE_HOPS` = 2. At the first hop that reaches anything, the candidates are the tagged
  vessels or pumps reached, the runs with a shortest path through each in-line item reached, and the runs ending at
  each tagged valve or connector reached. Exactly one candidate places it: `on` a vessel or pump (a `measures`,
  `acts_on` or `protects` edge) or `on_line` a run (the run's `instruments_on` claim and the appearance's
  `on_line`). Two or more go to the review queue as `placement unclear` with the candidates, never guessed; a bubble
  that reaches nothing within the limit is counted, not placed.
- **Off-page pairing.** A connector with no `to` is paired by [`offpage_pairing.py`](../scripts/offpage_pairing.py),
  the repository's one cross-sheet rule (the drawing-set importer uses it too), with each registered sheet id as the
  number its connectors print (`PID 180-1` names sheet `180-1`, `180-01`, or `180` for a drawing registered without
  sheet numbers; an unreadable separator such as `140?1` still reads). Both connectors must name each other's sheet;
  several matches narrow on the printed description with the reference removed. A tie is never decided by order:
  every end of it becomes an `off-page pairing unclear` row naming the candidates, as does a connector whose only
  candidates paired elsewhere. The edge's `how_found` is the rule's method. Otherwise the connector is an `off-page
  connector unpaired` row (no reference read, the named sheet is not in the sheet index, or nothing there points
  back). A connector with an explicit `to` pairs as before.

### Lining up and locating (step 2)

Each record row becomes an item with its record's status. Each sheet read then **locates** recorded tags (sheet and
zone), supplies piping (`connects`), placement (`measures`, `acts_on`, `protects`) and drawn signal lines. A match
gets a green review queue row and a deterministic spot-check sample flag instead of full review. Mismatches become
conflicts:

- on a P&ID but in no record → `asset_presence`, routed to the record that should hold it;
- in a record but on no registered sheet of a covered unit → `asset_presence`, routed to the P&IDs' owner (a unit
  with no registered sheet yet is reported, not flagged item by item).

Each loop list row becomes `controls` (or `sets_point_of`, for a cascade) edges sourced to the loop list, then is
located: **located and consistent** (all three tags on the unit's sheets and both signal lines drawn), **partly
located** or **not found on any sheet**. Only the last two go to review: to the loop list's owner when a tag is held
by no record, otherwise to the P&IDs' owner. A drawn signal line that pairs a listed controller differently becomes
a `loop_pairing` conflict.

Loop-number grouping on the P&IDs is secondary. Inside one unit only, instruments sharing a loop number with
compatible letters (`FT-2203`, `FIC-2203`, `FV-2203`; `TE-2207A/B`; split-range `FV-10A/B`), or joined by a drawn
signal line, form a candidate. A candidate the loop list lacks is flagged to its owner (`unlisted_loop`); it is
never asserted. Two units with the same loop number are never grouped.

### Drafts where no record exists (step 3)

`draft-lists` writes, for every scope no equipment or instrument record covers, a draft maintenance equipment export,
draft instrument index and draft loop list in the formats above. Loops come from the same grouping and signal lines,
with `how_found` (`loop_number`, `signal_line`) and a confidence; a controller with more than one candidate
measurement or output is written as a comment for review, not as a loop. Every row is `unverified`, tiered
green/amber for review; safety-relevant tags (the [twin's safety floor](TWIN_OUTPUTS.md)), placeholder tags and
duplicate tags are never green. In the map, items from a scope with no record are review items (`on the P&ID, not in
the instrument index` or `on the P&ID, not in the maintenance equipment export`), not conflicts. After a person reviews a draft and sets each row's status, add it to the site file with
`scopes`.

## Conflicts and their owners

A conflict is a graph node (kind `conflict`) with a `concerns` edge to its subject. It keeps what source A says,
what source B says (each with its source and locator), the attribute, the record owner, other parties, a status
`open`, `disputed` or `resolved`, and a decision history. The record owner comes from the site file's
`record_owners` map (record type to department: `pid` → Doc control, `maintenance_export` → Maintenance,
`instrument_index` and `loop_list` → I&C, `datasheet` → Process in the example), a document's own owner, or the
owning scope of a shared system. An optional `routing` table overrides the record type per conflict type.

| Type | Raised when |
|---|---|
| `asset_presence` | an item is in a record but on no P&ID sheet, or on a P&ID sheet but in no record |
| `value_disagreement` | two records (datasheet, maintenance equipment export, instrument index) give different values for one attribute; source A is the authority for that fact kind |
| `mention_not_in_register` | a document mentions a tag the covering record lacks |
| `ambiguous_reference` | a document names a tag in two scopes and its covers do not choose |
| `superseded_basis` | a document's `based_on` revision is not the current one |
| `loop_pairing` | a drawn signal line pairs a listed controller with another tag |
| `unlisted_loop` | the P&IDs show a possible loop the unit's loop list lacks |
| `boundary` | off-page connectors do not point back at each other, disagree on an attribute, or a sheet claims a shared system |

A `P&ID value note` (a value printed on a P&ID that differs from the records, or from another sheet) is a review
item, not a conflict. Off-page connector attributes compared across a `boundary` are still conflicts: they are a
consistency check between two P&ID sheets at a shared-system boundary, routed to the shared system's owner.

Software never resolves a conflict. `--decisions decisions.csv` (`conflict_id,status,by,on,note`) records a
person's decision; it persists across runs. A conflict that is no longer detected keeps its last status with
`detected: false` until a person resolves it.

`--decisions` also reads rulings in the context map's [`ruling` template](../schemas/context-map/templates/ruling.csv)
(`ruling_id,concerns,attribute,ruling,chosen_source,chosen_value,reason,by,on,authority,evidence`) and may be given
more than once. `concerns` is a conflict id (`S1/CONFLICT/C-...` or `C-...`) or an item id with the `attribute`
(the one detected conflict on that item and attribute). `accept_source`, `accept_value`, `no_conflict` and
`authority_override` resolve the conflict; `defer` marks it disputed. A **field verification ruling** records a
walkdown that settles a disputed conflict: `authority` `field`, the date and who, the reason and, required,
`evidence` (photo file, nameplate reading or locator). Every decision and ruling becomes a history line on the
conflict (`conflicts.md`, "Decision history"). When a ruling chose a value (or a source) and a record still says
something else, the record's owner gets a review row `record differs from a ruling` asking them to update it: the
ruling settles the dispute, the record stays its owner's to change.

**Work order closeout.** A `records` entry with register `work_order` whose rows have `closed_on` and any of
`installed_manufacturer`, `installed_model`, `installed_serial_number`, `installed_size` is compared with the item's
records. An installed value that differs from the maintenance equipment export or instrument index is a
`value_disagreement` to that record's owner (the work order is source A). One that differs from a datasheet is a
review row `replacement may not be like-for-like` to the datasheet's owner: a possible management of change trigger,
flagged and never decided. Manufacturer, model or serial number that no maintenance equipment export or instrument
index row holds is a `work order closeout note`. Values compare ignoring case and repeated spaces; an open work order
(no `closed_on`) is not compared.

## Changes, affected records and change flags

Three read-only reports on built graphs (`scripts/map_changes.py`, run through `one_map.py`); each writes Markdown and
JSON with `--out DIR`, or prints the Markdown. How plant teams use them: [RUNNING_THE_MAP.md](RUNNING_THE_MAP.md).

```sh
python scripts/one_map.py changes OLD/graph.json NEW/graph.json [--tags T ...] [--scope S ...] --out out/changes
python scripts/one_map.py affected --map graph.json --tags FDV-2210 TT-2208 --out out/moc-open
python scripts/one_map.py affected --tags FDV-2210 TT-2208 --closeout OPEN/graph.json CLOSE/graph.json --out out/moc-close
```

- **`changes`** compares two builds of one site: items (name, kind, class, owner, listed in, P&ID sheet:zone and
  values printed there, attribute values with their record), links, record rows (`records` registers), documents
  and P&ID sheets (revision, status, owner, content hash, text status), conflicts (added, removed, status) and
  expectation results. `--tags`/`--scope` keep only those items, their links, rows, the documents that cover their
  unit, mention them, show them (P&ID sheets) or are based on one of those, and their conflicts and expectation
  results. A tag on neither map is listed, not refused (a new item). Written as `changes.md` and `changes.json`.
- **`affected`** lists, for the tags or scopes, every record and document that holds or names them, one row per
  owner, record and item: equipment/instrument record rows, datasheet values, `records` rows that hold the item or
  name its tag in any field (a CCP's corrective action naming FDV-2210), loop list loops, P&ID sheets showing it,
  documents covering its unit, mentioning it or based on a P&ID sheet that shows it, open conflicts, expectation
  gaps (missing, not evaluable, draft rule) and change flags. Linked items (connects, controls, measures, protects,
  signal lines) are listed separately with their owners. A tag not on the map is reported as "not on the map yet".
- **`affected --closeout OPEN CLOSE`** takes the affected rows at both ends and compares what each record says
  about the item: `changed`, `unchanged`, `new since open`, `gone at close`; conflicts and expectation gaps
  `still open` or `closed`; change flags `not checked here`. `closeout.md` lists the unchanged rows per owner first.
  `changed` is not proof the change is right, and `unchanged` may be correct: the owner confirms.
- **Change flags** (flags only, never decisions): an item that is a CCP's monitoring instrument or is named in a CCP
  row -> `HACCP reassessment`; a relief device (kind, or a row in the relief device register) or a cause/effect tag
  of an `interlock_list` row -> `PHA revalidation`; a `criticality_ranking` value in `--critical` (default
  `A,1,critical,high,very high`) -> `criticality review`. Each flag names the record that raised it and goes to
  that record's owner in `affected`.

## Review queue

`queues/review_queue.csv` (`rank,tier,owner,plant,unit,item,kind,why,safety,spot_check`) holds every row,
risk-sorted: red (conflicts), amber (review items, partly located or not found loops, safety-relevant items, then
P&ID value notes), green (matches, with `spot_check` = `sample` on a deterministic 1-in-N sample; `spot_check_every`
in the site file). Safety-relevant rows sort first in their tier and carry `safety`. Locations in `why` are
`sheet:zone` in the sheet read's own zones (for a converted read, the `sheet_zone.py` convention above, recorded in
the sheet read's `zone_grid`). `queues/by-owner/`, `by-plant/` and `by-unit/` split it, preserving order; the split
refuses to write a safety-relevant row as green. `split-queue` applies the same order-preserving split to an existing
`generate.py` `review_queue.csv` by any column, refusing an input whose safety floor is broken.

## Classes, link checks, expectations and the glossary

These follow the context map format's 1.1 ontology ([Classes](CONTEXT_MAP_FORMAT.md#classes) to
[JSON-LD view](CONTEXT_MAP_FORMAT.md#json-ld-view)); one map applies them to its own graph.

- **Classes.** Every item gets a `class` (and `class_how`) where it is deterministic: a `class` column in a list,
  the tag letters, the site's equipment prefixes, refined by a datasheet value (`pump_type`). Documents get one from
  their `doc_type`. Otherwise the class stays unset and the report counts it.
- **Link checks.** Every edge is read as a context-map relation and checked against its domain and range. A link
  that does not fit (`PI-2240 measures TIC-2207`: a gauge cannot measure a controller) is an amber review row "link
  doesn't fit what it connects" for the owner of the record that asserted it; the link stays on the map.
- **Expectations.** With `expectations` in the site file, each certified, rolled-out rule raises an "expected but
  missing" row per subject that lacks something, routed to the rule's owner; a draft rule raises one summary row per
  unit; a check whose register is absent for the unit is counted as not evaluable. The report has a per-rule table
  and the graph keeps every result under `expectations`. A CCP's monitoring instrument is safety relevant, so it is
  never green.
- **Glossary.** A `glossary` record feeds document matching (rules above); `ask` also resolves an item by a
  certified term.
- **Answers.** `ask` reads `graph.json` only: `connects`, `measured-by`, `documents`, `disagreements`, `complete`, each
  fact with its source, or "can't answer from this map: no P&ID covers S1/P1/FILL1" from the graph's
  `coverage.sources` (which record is the record for which scope).

## Incremental runs and reopening

`build --out DIR` keeps `DIR/state.json`. On the next run, only sheets whose revision, raw bytes, plant, unit or
owner changed are re-read (a change to the tool's code re-reads all); assembly, pairing and checks are rerun over
the whole map with dictionary lookups, linear in items. Off-page connectors pair across sheets and plants by
`(plant, sheet, connector)`, or by printed reference when they have no `to`.

When a document's revision or bytes change, every document `based_on` it reopens, transitively. With `--register
context.json`, answers in a [context register](CONTEXT_REGISTER.md) whose evidence cites a changed or reopened
document are listed to reopen; the register's own refresh then marks them stale. The document manifest is the same
`context-sources-1` file the register reads.

## Limits

- A prototype tested on the fictional example, synthetic cases and one public development P&ID sheet (OPEN100 sheet
  0). No plant's records, P&IDs or documents have been run through it, and no one has timed a review with these
  queues.
- `changes`, `affected` and the closeout compare what two graphs hold. They see a record only through the map: a
  document that names an item in words the map cannot match, a record not exported, or a row whose tag does not
  resolve is not in them. `changed` in a closeout means the record says something different about the item, not
  that the change is right; review rows (like-for-like, record differs from a ruling) are in the review queue, not in
  the graphs these reports read. Change flags are never tracked to completion. Tested only on the fictional
  pasteurizer MOC. No fixed weekly review allowance is established; measure actual effort with the record owners.
- The work order closeout compares only `installed_manufacturer`, `installed_model`, `installed_serial_number` and
  `installed_size`, as text (case and repeated spaces ignored): `DN65` and `65 mm` differ. Part numbers, spares and
  purchase orders are not compared.
- P&ID images are read by the drawing reader, converted by `sheet-from-prediction`, and reviewed in the same queue.
  The conversion is only as good as the reading: on OPEN100 sheet 0 it fills in 38 piping runs between the two
  vessels, MSCV-XXX and the off-page connectors, but places no instrument (20 bubbles reach a header the tracer
  joined to everything, so they are `placement unclear`; 16 have no connection), writes no signal lines, and pairs
  no off-page connector because the sheets they name are not in the sheet index
  ([worked example](../examples/drawing-to-map/README.md)). Runs are connections, not line numbers: the printed
  line numbers (`SIZE-MSS-140076-...`) are not read.
  `loops-from-graph` on the same sheet's graph export finds loop-number groups (`TE 14089A/B`; `TCV 1401` with
  `FT 1401`) but no controller bubbles, so it proposes no loop
  ([result](../examples/one-map/expected/open100-sheet0-loops.md)).
- Letters decide roles by a short rule (controller `?[D]IC`, measurement `?[D]T`/`?E`, final element `?[C]V`);
  plant-coded or unusual letters are left unclassified, and the safety rule reads letters too (on OPEN100 sheet 0 the
  plant's own main steam valves `MSV-1404/1405` are flagged as relief devices: kept amber, a false alarm a person
  clears). Tags need two or more digits.
- Classes come from a short letter rule and site-convention equipment prefixes; on a reader's sheet they are only
  as right as the tags read. Expectation rules see only the registers supplied; they say nothing about whether a
  record is right, only whether it exists. The shipped rules and the pasteurizer's certifications are fictional
  examples; no plant has certified or rolled out a rule. Glossary matching is whole-word text only (no stemming, no
  plural forms).
- Values compare as exact text; units and synonyms are not normalized. Fact kinds come from attribute names (or the
  site file's `fact_kinds`); an unrecognized attribute has no authority and two records disagreeing on it go to the
  owner of the record read later.
- Identity is the qualified id. A tag that moves between units, or a record that uses different plant/unit codes
  from the site file, needs an explicit mapping first; the tool does not guess one.
- The graph is `twin-graph-2`; tools that read only `twin-graph-1` (`graph_export.py --check`, context register,
  snapshot) do not read it yet.
- Mentions need one to five letters and two to five digits. Format-insensitive matching ignores only hyphens,
  spaces, underscores and case: a leading zero (`P-0101`), a unit-qualified form (`200-P-101`, `P1-P-101`), a
  letter inside the number or a tag split across two pieces of a document is missed, and a former tag reused for a
  different item makes both a review row. Columns count from the first non-blank character of the piece the reader
  returned. Scanned PDFs are not read unless the site file sets `document_text.ocr` to `auto` (otherwise a document text note asks for OCR). Paths in the register and site file are
  relative to that file's folder.

## For agents

```text
schema: twin-graph-2 = twin-graph-1 + node kinds site, unit, scope, document, conflict
                       + edge types covers, mentions, based_on, references, signal_line, concerns
ids:    SITE/PLANT/UNIT/TAG; documents SITE/DOC/<id>; conflicts SITE/CONFLICT/C-<hash>; off-page SCOPE/@<sheet>/<id>
inputs: site.json (one-map-site-1) -> sheet index (drawing_register), sheet reads (one-map-sheet-1), maintenance
        equipment export, instrument index, loop lists (loop_audit contract), datasheets, documents
        (context-sources-1 + owner/status/covers/based_on); optional authority and fact_kinds maps
path:   read P&IDs (sheet-from-prediction) -> line up against the records -> drafts where none exist (draft-lists)
        -> values: datasheet vs records under the authority map -> review queue, safety first -> re-read changed sheets
docs:   documents are read by extract_text.py (PDF, Word, Excel, PowerPoint, HTML, text); mention locator =
        "<piece locator>[, line N], column C"; non-ok text status -> "document text note" to the document owner
match:  exact tag/alias/site id -> link; format-only (separators/case) and unique on the map -> link with
        matched=format-insensitive; same normalized tag in 2+ scopes, suffix near miss, lower-case + space ->
        "possible mention, confirm" review row
never:  asserts an ambiguous or near-miss mention; asserts a loop from P&IDs; groups across units; treats a P&ID
        value as a value conflict; resolves a conflict; renumbers a tag; gives a shared system two owners
zones:  scripts/sheet_zone.py: ROW-COL, default 8x12, A at the bottom, 1 at the right, box centre, over --zone-frame
ontology: node.class/class_how (classes.json); "link doesn't fit what it connects" rows (relations.json);
        site file records/expectations/as_of -> "expected but missing" and "draft expectation rule" rows,
        graph["expectations"] {results, by_rule}; glossary register -> mentions matched=glossary or confirm rows;
        OCR text (locator in extract_text result.ocr, or result.ocr_engine with no per-piece map; else engine
        tesseract*, status "ok (ocr)", ocr_pages) never links: "possible mention (OCR), confirm"; site
        document_text {ocr, ocr_lang, ocr_dpi, convert_legacy, pdf_layout, excel_display} -> extract_text options; graph["coverage"]["sources"] says which record covers which scope
reports: one_map.py changes OLD NEW [--tags|--scope] (one-map-changes-1); affected --map G --tags|--scope
        (one-map-affected-1, rows by owner); affected --closeout OPEN CLOSE (one-map-closeout-1); change flags
        HACCP reassessment / PHA revalidation / criticality review are flags, never decisions (map_changes.py)
closeout: work_order rows with closed_on + installed_* -> value_disagreement vs maintenance export/instrument index,
        "replacement may not be like-for-like" vs datasheet; --decisions reads decisions.csv or ruling CSVs
        (authority field + evidence = field verification ruling), history kept, "record differs from a ruling"
ask:    python scripts/one_map.py ask --map graph.json --question-kind KIND --item X   (read-only, with sources)
check:  python scripts/one_map.py check graph.json   (every twin-graph-1 rule plus the one-map rules;
        graph_export.py --check still accepts only twin-graph-1)
graph:  graph["loops"] lists each listed loop's outcome; node.appearances lists sheet/zone locations (values
        printed there under printed; reader_symbol, reader_class, reader_confidence, printed_tag for
        converted reads); coverage.sources carry each record's owner; node.listed_in names the
        records holding an item ([] = P&ID only); node.tag_status = placeholder for a placeholder tag
```
