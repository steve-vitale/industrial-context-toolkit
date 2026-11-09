# The context map format (`context-map-1`), draft for review

**Status: design draft `1.1.0-draft`, 2026-11-04. No tool reads or writes a context-map-1 file yet;**
[`one_map.py`](ONE_MAP.md) already uses its registers, class tree, relation semantics, expectation rules and
glossary on its own graph. The machine-readable drafts are in [`schemas/context-map/`](../schemas/context-map/): the
JSON Schema, the register catalogue, a CSV template per register, wide-form datasheet templates, the standards-mapping
table, the class tree (`classes.json`), relation semantics (`relations.json`), the expectation rules template
(`templates/expectations.json`) and a small fictional example map. The owner's answers to the draft's open questions
are applied; see [Decided (2026-11-04)](#decided-2026-11-04). Version 1.1 adds a small, pragmatic ontology
([Classes](#classes) to [JSON-LD view](#json-ld-view)); every 1.0 file stays valid.
`python scripts/test_context_map_format.py` checks that they parse and agree with each other.

## In plain words

A plant's knowledge is spread over many records kept by different departments: P&IDs, the instrument index, the
maintenance equipment export, datasheets, the HACCP plan, lockout procedures, work orders, purchase orders. Each is
right about some things and out of date about others. The context map puts them side by side in one file, keyed by
the plant's own tags, so a person can ask "what do we know about P-101, and who says so?" and get an answer with a
source for every value.

The format is our own, assembled from standard parts. The hierarchy uses plant words (plant, unit, system), with
their ISA-95 and ISA-88 equivalents kept in the mapping table. Each other part names the standard it follows (DEXPI
for P&ID content, ISA-5.1 for tag letters, CFIHOS for registers and classes, ISO 14224 for
maintenance data, VDI 2770 for vendor documents) so a contractor handover or another tool can load in without a
custom translation for every site.

A plant fills in what it has. **Only identity is required: a tag and the unit (or other scope) it belongs to.**
Every other register, field and layer may be empty, and the file is still valid. A coverage report in the same
file says what is filled in and what is not, per layer and per unit.

The map has four layers:

| Layer | Holds | Example |
|---|---|---|
| **PLANT** | the site hierarchy, the tagged items in it, how they connect (piped to, measures, controls, acts on, protects, signal) and the loops | P-101 timing pump in unit PAST1, piped to hold tube HT-100 |
| **RECORDS** | rows from the department records, one register per record type | TT-2207 is CCP-1 with a critical limit of 72.0 degC (HACCP plan rev 7) |
| **DOCUMENTS** | the documents themselves: type, revision, draft or released, owner, what they cover, which tags they mention and where, what they were based on | HACCP plan rev 7 mentions TT-2207 on page 9 and was based on P&ID PAST1-01 rev B |
| **DECISIONS** | where two records disagree, which record is the authority for each kind of fact, and local rulings with reasons | the P&ID shows TT-2207; the maintenance equipment export does not hold it |

Routing a disagreement to people, approving a ruling and keeping its history are not part of the format. Those
belong to an external governed service; the map keeps only the disagreement, the ruling and its reason.

## What the plant supplies, and in what shape

People fill in registers as CSV files, one per record type, from the templates in
[`schemas/context-map/templates/`](../schemas/context-map/templates/). Each template is a header row and one to four
fictional example rows from a food plant (an HTST pasteurizer unit `PAST1` with the P-101 timing pump, the HT-100
hold tube, the TT-2207 hold-tube temperature CCP and the FDV-2210 flow diversion valve). Delete the example rows and
paste your own. The hierarchy columns use plant words: `plant`, `unit` and, where a register has one, `system`.
Column rules:

- **Identity columns come first** (`tag`, `plant`, `unit` for tag-keyed registers). `plant` is a plant id or a site
  scope id such as `UTIL`; `unit` is required when the plant has units.
- **Every other column is optional.** Leave a cell empty when the record does not say.
- **Values are copied as written,** with the unit of measure in its own column where the template has one. The
  format does not convert units or normalize text in this version.
- **The last three columns are the same everywhere:** `locator` (where in the source the row is, when it is not
  simply "this file, this row"), `status` (`unverified`, `confirmed`, `corrected`, `rejected`, `stale`; empty means
  unverified) and `note` (free text, never read as a value).
- **Extra columns are allowed.** A column the template does not have is kept as a property of the row, sourced to
  that file, and compared under the authority rules below.

The source of each file (its revision, owner, byte fingerprint and which scopes it is the record for) is declared
once in the map's `sources`, not on every row.

## Identity and tags

Identity is the part a plant must get right, so the rules are strict and few.

1. **An item is a tag in a scope.** Its id is the site-qualified path `SITE/PLANT/UNIT/TAG`
   (`S1/P1/PAST1/P-101`). Scopes are `SITE`, `SITE/PLANT`, `SITE/PLANT/UNIT` and optional systems below a unit.
   A site scope that is not a plant (site utilities) sits directly under the site: `S1/UTIL/CW-01`.
2. **The tag is kept exactly as written.** No renumbering, no trimming, no case change. A tag may not contain `/`
   or start or end with a space. A normalized key (upper case, spaces and hyphens removed) is used only to raise
   near misses (`P101` against `P-101`) as review items, never to join records.
3. **The same tag in two units is two items.** `S1/P1/PAST1/P-101` and `S1/P2/FILL2/P-101` are different pumps.
   A record that gives only a tag and a plant is resolved through the plant if the tag is unique there; otherwise it
   raises an `ambiguous_reference` conflict and joins nothing.
4. **A tag is a position, not a physical item.** The P&ID tag P-101 is the timing-pump position. The pump installed
   there (manufacturer, model, serial, install date) is a row in the maintenance equipment export. A pump swap
   changes that row, not the tag. This follows CFIHOS (tag versus equipment) and ISO 14224 (functional location
   versus equipment unit).
5. **Former tags and other names go in the tag lookup table** (`tag_alias`): the alias, what kind it is
   (`former_tag`, `cmms_number`, `functional_location`, `dcs_point`, `historian_tag`, `vendor_tag`,
   `handover_tag`), the current tag and scope, and optionally the dates it was valid. On any date an alias must
   resolve to exactly one item; if it does not, the map raises `ambiguous_reference`.
6. **A tag that moves to another unit becomes a new item.** The old item is kept with `lifecycle: retired` and
   `succeeded_by` pointing at the new one, so old records still resolve to where the tag was at the time.
7. **Shared systems have exactly one owning scope** (cooling water owned by `S1/UTIL`). A plant that uses one
   reaches it through a boundary item; a P&ID sheet that draws the shared system as its own raises a `boundary`
   conflict. (This is the one-map rule, unchanged.)
8. **Tag letters are a hint.** The ISA-5.1 letters parsed from a tag (`TT`, `FDV`) suggest an item kind for review.
   They never decide it on their own; plant-coded letters are declared in `settings.letter_overrides`.

## The PLANT layer

**Hierarchy.** Levels are `site`, `plant`, `unit` and an optional `system`, with items below. These plant words are
what the templates, the schema and this spec use. Their equivalents in other standards are kept in one place only,
the mapping table [`standards-mapping.csv`](../schemas/context-map/standards-mapping.csv); no scope records them:

| Plant word | ISA-95 equivalent | ISA-88 equivalent (batch plants) | DEXPI 2.0.1 crosswalk | ISO 14224 |
|---|---|---|---|---|
| site | Site | none | `PlantStructure/Site` | taxonomy level 3 (installation) |
| plant | Area | none | `PlantStructure/ProcessPlant` | taxonomy level 4 (plant/unit) |
| unit | a work center (production unit, process cell, production line, storage zone) | Process cell or Unit | `PlantArea` or `PlantSection` (the loader asks) | taxonomy level 4 |
| system | none | Equipment module | `PlantStructure/PlantSystem` | taxonomy level 5 (section/system) |

**Items.** Required: `id`, `tag`, `scope`. Optional: `kind` (one of `equipment`, `instrument`, `controller`,
`final_element`, `manual_valve`, `relief_device`, `line`, `offpage_connector`, `boundary`, `junction`, `other`),
`class` and `class_how` (since 1.1: a class id from `classes.json` and where it came from, see [Classes](#classes)),
`name`, `parent`, `aliases`, `class_refs` (pointers into DEXPI, CFIHOS or ISO 14224 classes), `isa_letters`,
`safety_relevant`, `status`, `lifecycle`, `appearances` (each P&ID sheet, revision and zone it is drawn on),
`listed_in` (the sources that hold it; empty means on a P&ID but in no register) and `attributes`.

**Relations.** Each relation has a `type`, `from`, `to` and a `source`, and may carry `revision`, `locator`,
`status` and, for lines, `line_type` and `signal_type`.

**The relation names are frozen.** The names and directions below are stable from `context-map-1` on, so other
systems can map to them. Adding a name is a minor version; renaming or removing one, or reversing its direction,
needs a new major format version (`context-map-2`). The containment relation is `contains` (parent → child); there
is no `has_part`.

| Type | From → to | Means | Status | DEXPI 2.0.1 reference |
|---|---|---|---|---|
| `contains` | scope → scope or item | hierarchy | stable | `PlantStructure` |
| `piped_to` | item → item | consecutive process items on a pipe run; `directed` when the source shows flow | stable | `PipingNetworkSegment`, `PipingConnection` |
| `measures` | instrument → item or line | what an instrument senses | stable | `SensingLocation`, `ProcessSignalGeneratingFunction` |
| `controls` | controller → final element | the controller's output | stable | `ProcessControlFunction` |
| `sets_point_of` | controller → controller | cascade | stable | `ProcessControlFunction` |
| `acts_on` | final element → item or line | what a valve or actuator changes | stable | `ActuatingFunction`, `ActuatingSystem` |
| `protects` | relief or safety device → item | what it protects | stable | none single; our own |
| `signal_to` | instrument → instrument | a signal line on the P&ID | stable | `SignalLineFunction`, `SignalConveyingFunction` |
| `actuated_by` | item → item | an actuator link, not pipe (kept from twin-graph-1) | stable | `ActuatingSystem` |
| `nozzle_of` | item → item | a nozzle on its equipment, not pipe (kept from twin-graph-1) | stable | nozzle classes |
| `references` | off-page connector or boundary item → item | where a connector or boundary leads (one map) | stable | `PipeOffPageConnector`, `SignalOffPageConnector` |
| `member_of` | item → loop | loop membership | stable | `InstrumentationLoopFunction` |
| `covers` | document → scope or item | what a document is about (DOCUMENTS layer) | stable | none; our own |
| `mentions` | document → item | a tag found in a document's text (DOCUMENTS layer) | stable | none; our own |
| `based_on` | document → document at a revision | the basis a document was written from (DOCUMENTS layer) | stable | none; our own |

Line types: `process_pipe`, `utility_pipe`, `measuring_line` (impulse line, DEXPI `MeasuringLineFunction`),
`signal_line`, `mechanical_link`, `unknown`. Signal types follow DEXPI's `SignalConveyingTypeClassification`
(`electrical`, `pneumatic`, `hydraulic`, `capillary`, `conducted_radiation`) plus `data_link` and `wireless` from
the ISA-5.1 line symbols, and `unknown`.

**Loops.** A loop has an id, a scope (one unit; loops never span units), a `loop_type` (`control`, `indication`,
`safety`, `cascade`), a controller, measurements and outputs, and an `outcome` once located against the P&IDs
(`located_and_consistent`, `partly_located`, `not_found_on_any_sheet`), exactly as one map reports today.

## The RECORDS layer

Each record type is a **register**: a declared set of fields with an owner, the facts it is authoritative for, and
its standard mapping. Adding a record type means adding a register entry and a template, not new code per type.
The full field definitions (type, required, fact kind, description, allowed values) are in
[`registers.json`](../schemas/context-map/registers.json). Every register also takes the shared `locator`,
`status` and `note` columns (except `ruling`). `unit*` is required when the plant has units.

| Register | Required | Optional | Default owner | Authority for | Standards |
|---|---|---|---|---|---|
| `tag_register` tag register | tag, plant, unit* | system, kind, description, dexpi_class, cfihos_tag_class, parent_tag, former_tag, safety_relevant | Engineering | (tags come from the P&ID) | ISA-95 level of the scope; DEXPI class; CFIHOS tag class; ISA-5.1 letters |
| `tag_alias` tag lookup table | alias, alias_kind, tag, plant, unit* | valid_from, valid_to | Doc control | - | CFIHOS tag number; ISO 14224 taxonomy |
| `drawing_register` P&ID sheet register | sheet, rev, plant, unit*, owner, path | doc_status | Doc control | - (the P&ID part of the document register) | DEXPI Diagram; CFIHOS document type |
| `maintenance_export` maintenance equipment export (equipment register) | tag, plant, unit* | functional_location, equipment_number, description, manufacturer, model, serial_number, installed_on, iso14224_class, criticality, system, former_tag, cmms_status | Maintenance | installed | ISO 14224 equipment data; CFIHOS equipment register; AAS Digital Nameplate |
| `datasheet` datasheet values (equipment datasheets and instrument specification sheets) | tag, plant, unit*, property, value, document, revision | uom, fact_kind, sheet_type, cfihos_property | Engineering | rating, size, material; instrument range and model where the rows are an instrument spec sheet | CFIHOS tag property value; CFIHOS property; DEXPI attributes |
| `line_list` line list | line_number, plant, unit* | from_tag, to_tag, nominal_size, piping_class, fluid, design_pressure, design_temperature, material, insulation, hygienic | Engineering | line_design | DEXPI PipingNetworkSegment; CFIHOS tag class (line) |
| `relief_device_register` relief device register | tag, plant, unit* | protects, device_type, set_pressure, capacity, sizing_basis, last_tested, test_interval_months, next_due | Process safety | relief_setting | DEXPI SafetyValveOrFitting; CFIHOS tag class |
| `instrument_index` instrument index | tag, plant, unit* | loop, service, instrument_type, range_low, range_high, range_uom, signal_type, manufacturer, model, description | I&C | instrument_range, instrument_model (where no instrument spec sheet is supplied for the scope) | ISA-5.1 letters; DEXPI ProcessInstrumentationFunction; CFIHOS tag class |
| `loop_list` loop list | controller, plant, unit* | measurement, output, loop_type, description | I&C | - (the control scheme comes from the P&ID) | DEXPI InstrumentationLoopFunction; ISA-5.1 loop number |
| `io_list` IO list | tag, plant, unit*, point | controller_system, io_type, historian_tag | I&C | io_assignment | ISA-95 level 1-2 boundary (informative) |
| `alarm_list` alarm list | tag, plant, unit*, alarm_type | setpoint, uom, priority, operator_action, rationalized_on | I&C | alarm_setting | ISA-18.2 (named, not adopted) |
| `interlock_list` interlock list (cause and effect) | interlock_id, plant, unit*, cause_tag, effect_tag | cause_condition, effect_action, is_sif, sil, bypass_allowed | I&C | trip_logic | DEXPI ProcessSafetyFunction; IEC 61511 (named, not adopted) |
| `work_order` work order history | work_order, tag, plant, unit* | work_type, opened_on, closed_on, failure_mode, failure_mechanism, failure_cause, detection_method, maintenance_activity, description, installed_manufacturer, installed_model, installed_serial_number, installed_size | Maintenance | maintenance_history | ISO 14224 failure and maintenance data |
| `pm_plan` PM plan | pm_id, tag, plant, unit* | task, interval, interval_unit, last_done, next_due, job_plan | Maintenance | pm_schedule | ISO 14224 maintenance data |
| `calibration_record` calibration record | tag, plant, unit*, calibrated_on | as_found, as_left, tolerance, result, reference_standard, work_order, next_due, performed_by | Maintenance | calibration_status | ISO 14224 maintenance data |
| `mro_item` stores item master (MRO items) | item_number | description, manufacturer, part_number, uom, min_qty, max_qty, critical_spare, lead_time_days | Stores | - | ISO 14224 maintainable item (informative) |
| `spares_bom` spare parts BOM | item_number, tag, plant, unit* | qty_installed | Maintenance | - | ISO 14224 maintainable item (informative) |
| `purchase_order` purchase order lines (read-only copy) | po_number, line | vendor_id, item_number, tag, plant, unit, description, spec_document, ordered_on, received_on, like_for_like | Procurement | - | CFIHOS purchase order (informative) |
| `approved_vendor` approved vendor register | vendor_id, approval_scope | name, food_contact, approval_status, approved_by, approved_on, review_due | Procurement | vendor_approval | none adopted |
| `operating_limit` operating limits (operating envelope) | tag, plant, unit*, parameter, limit_type | low, high, uom, basis | Production | operating_limit | none adopted |
| `ccp` critical control points (HACCP plan) | ccp_id, plant, unit*, haccp_plan | process_step, hazard, monitored_tag, parameter, critical_limit_low, critical_limit_high, uom, monitoring_frequency, corrective_action, verification | Quality | ccp_limit | Codex HACCP principles (named, not adopted) |
| `isolation_point` isolation points (lockout procedures) | isolates_tag, plant, unit*, point_tag, procedure | energy_type, isolated_position, verification, sequence | Safety/EHS | isolation | OSHA 29 CFR 1910.147 (context, not adopted) |
| `permit` work permits (read-only copy) | permit_id, plant, unit* | permit_type, tag, valid_from, valid_to, permit_status | Safety/EHS | - | none adopted |
| `capa` CAPA register (corrective and preventive actions) | capa_id, plant, unit* | capa_type, tag, document, document_revision, raised_from, raised_from_ref, opened_on, problem, root_cause, action, action_owner, due_on, closed_on, effectiveness_check, effectiveness_verified_on, capa_status | Quality | corrective_action | ISO 9001 clause 10.2, ISO 22000 clause 10.1, 21 CFR 117.150 (named, not adopted) |
| `criticality_ranking` equipment criticality ranking | tag, plant, unit*, criticality | method, method_document, safety_consequence, food_safety_consequence, production_consequence, environmental_consequence, likelihood, risk_score, ranked_on, ranked_by, next_review | Maintenance | criticality | none adopted (the site's own method) |
| `inspection_record` inspection records (vessels, piping, RBI) | tag, plant, unit*, inspected_on | inspection_type, component, finding, result, measured_value, minimum_allowed, uom, remaining_life_years, rbi_risk, interval_months, next_due, inspector, certification, work_order, report_document | Maintenance | inspection_status | API 510, 570, 580, 581 (named, not adopted); ISO 14224 maintenance data (informative) |
| `document_register` document register | document, revision | title, doc_type, cfihos_document_type, vdi2770_class, doc_status, owner, path, covers, based_on, manufacturer | Doc control | document_revision | CFIHOS document type; VDI 2770; AAS Handover Documentation |
| `glossary` glossary (plant terms and nicknames), since 1.1 | term, plant, unit* | synonyms, definition, maps_to_class, maps_to_item, owner, certification, certified_by, certified_on | Doc control | - | none adopted |
| `ruling` local rulings | ruling_id, concerns, ruling, reason, by, on | attribute, chosen_source, chosen_value, authority, evidence | the person ruling | - | none adopted |

Department grouping: engineering (`tag_register`, `drawing_register`, `datasheet`, `line_list`,
`document_register`), I&C (`instrument_index`, `loop_list`, `io_list`, `alarm_list`, `interlock_list`),
maintenance (`maintenance_export`, `work_order`, `pm_plan`, `calibration_record`, `spares_bom`,
`criticality_ranking`, `inspection_record`), procurement and supply chain (`mro_item`, `purchase_order`,
`approved_vendor`), production (`operating_limit`), quality and food safety (`ccp`, `capa`), safety and EHS
(`relief_device_register`, `isolation_point`, `permit`), cross-cutting (`glossary`). The `tag_register` also takes an
optional `class` column (since 1.1).

Notes on particular registers:

- **`datasheet` is long form** (one row per tag, property and value) because every equipment class has different
  properties. This is also the shape of CFIHOS property-value deliverables. Each row names the datasheet document
  and its revision. Long form is what the map stores.
- **Wide-form datasheet templates** are offered for filling in by hand, one row per item and one column per
  property, in [`templates/datasheet-wide/`](../schemas/context-map/templates/datasheet-wide/): pump, heat exchanger
  (plate or shell and tube), vessel and tank, control valve, transmitter and relief valve. Their columns and fact
  kinds are in `registers.json` (`datasheet_wide_forms`). They convert to long rows by a fixed rule:
  1. `tag`, `plant`, `unit`, `document`, `revision` are identity columns and `locator`, `status`, `note` are
     trailing columns. Every other column is a property column; its header is the property name, optionally
     followed by the unit in square brackets (`rated_flow[L/h]`).
  2. Rows are read top to bottom, property columns left to right. Each non-empty property cell gives one long row;
     an empty cell gives none.
  3. The long row copies the identity columns; `property` is the header without the bracket, `value` is the cell
     exactly as written, `uom` is the bracket text.
  4. `fact_kind` is the one the form defines for that property (a column the form does not define gets none, and
     the default guess applies); `sheet_type` is the form's (`equipment_datasheet` or `instrument_spec_sheet`).
  5. `locator` is the wide row's locator, or `row N` when it is empty, followed by `; column <header>`; `status`
     and `note` are copied.

  So the TT-2207 transmitter row gives, among others, the long row `TT-2207, P1, PAST1, range_low, 0, degC,
  instrument_range, instrument_spec_sheet, IS-TT2207, 1, , box 22; column range_low[degC], unverified, ...`.
- **`ccp`** rows are read from the HACCP plan, and each row names it (`haccp_plan`). TT-2207's critical limit is a
  `ccp_limit` fact: if the instrument index or an operating-limit row gives a different number, the HACCP plan
  wins by default and the disagreement is raised to Quality.
- **`isolation_point`** rows are read from the lockout procedure for the isolated equipment (`procedure`).
- **`permit`** and **`purchase_order`** stay in version 1 as **read-only copies** for context, linked to the plant
  by tag (`record_copy: true` in `registers.json`). They are authoritative for nothing. Issuing, approving and
  closing a permit, and requisitioning, approving and receiving a purchase, are workflows that belong to the permit
  system, the purchasing system and an external governed service; the map never writes back.
- **`capa`** holds corrective and preventive actions (and corrections), one row per CAPA and linked tag or
  document: a CAPA links to the plant by `tag` and to the record it changes by `document` (the HACCP plan, a
  procedure, a P&ID), repeating the CAPA id for each further link. It also covers deviations, through
  `raised_from` (`deviation`, `ccp_deviation`, ...). Raising and closing a CAPA stays in the quality system.
- **`criticality_ranking`** is the equipment criticality ranking as the site's own method writes it. The
  `criticality` column of the maintenance equipment export is a copy: where they differ, the ranking register wins
  and Maintenance gets the conflict.
- **`inspection_record`** holds inspections of vessels, tanks and piping, including risk-based inspection (RBI)
  results (`rbi_risk`, `remaining_life_years`). The inspection report itself is a document (`report_document`).
- **`loop_list`** keeps loop_audit.py's contract (`controller`, `measurement`, `output`).
- The loop list, interlock list and alarm list are separate registers because different people own them and they
  disagree in different ways.

A register that a plant has not supplied is **absent**. A register supplied with no rows is an **empty array**.
The difference matters: an empty instrument index for a unit says "we hold no instruments there"; an absent one
says nothing. Each source declares the `scopes` it is the record for, so only an item missing from a covered scope
raises `asset_presence`.

**Next planned registers** (listed in `registers.json` as `planned_registers`; not defined yet, so a map may not
contain them): PFDs and heat and material balances; electrical single-line diagrams and motor schedules; training
records; safety data sheets (SDS) and chemical inventory.

## Which record wins: authority per fact

Every field that can disagree with another record has a **fact kind**. The site's authority map names, for each
fact kind, an **ordered list** of record types. For a given scope, the **first record type in the list that is
present for that scope wins**; later entries apply only where the earlier ones are absent. A record type is present
for a scope when a source of that type is the record for it (its `scopes` list the scope or an enclosing one; a
source that lists no scopes is the record for the scopes of the items its rows resolve to). When no listed record
type is present, nothing is authoritative there and a disagreement is an `authority_gap`.

Defaults are in `registers.json` (`default_authority`, rule text in `authority_rule`). A site overrides one in
`settings.authority` with its own list (or a single record type), with the reason in `settings.authority_reasons`.

| Fact kind | Authority, in order | Fact kind | Authority, in order |
|---|---|---|---|
| connectivity, tags, control scheme | P&ID | installed (manufacturer, model, serial, install date) | maintenance equipment export |
| rating, size, material (equipment) | datasheet | line design (size, class, design conditions) | line list |
| instrument range, instrument model | 1. instrument spec sheet, 2. instrument index | relief setting | relief device register |
| CCP critical limit | HACCP plan (`ccp`) | isolation points | lockout procedure (`isolation_point`) |
| alarm setting | alarm list | trip logic | interlock list |
| IO assignment | IO list | calibration status | calibration record |
| maintenance history | work order history | PM schedule | PM plan |
| vendor approval | approved vendor register | operating limit | operating limits |
| corrective action | CAPA register | criticality | equipment criticality ranking |
| inspection status | inspection records | document revision | document register |

**Instrument range and model.** The instrument spec sheet is the authority where the site supplies one for that
scope; otherwise the instrument index is. "Instrument spec sheet" (`instrument_spec_sheet`) is a pseudo record
type: rows of the datasheet register with `sheet_type` `instrument_spec_sheet` from a datasheet source that is the
record for the scope. In the example map, the TT-2207 spec sheet covers unit `PAST1`, so on `PAST1` it wins; on a
unit with no spec sheet supplied, the instrument index does.

When two records disagree on a fact, the authoritative one's value is shown as current and the other record's
owner gets the conflict (a value printed on a P&ID is reference only for non-connectivity facts, as one map does
today). When neither side is the authority, the conflict is `authority_gap` and goes to the newer record's owner.
An authority choice never deletes the other value; both stay, with their sources.

## Provenance on every value

Every value carries **source, revision and locator**. It does not carry a standard reference: that lives on the
field definition.

- A `source` is one supplied file or export, declared once: id, record type, revision, path or address, SHA-256 of
  its bytes, owner, the scopes it is the record for, and (for handovers) where it came from.
- A register row records its `source` and `locator` (row number by default; a page, cell or clause when the row was
  transcribed from a document). A plain value in a row inherits the row's source, revision and locator.
- A value that came from somewhere else is written as a **fact**:
  `{"value": "0 to 100", "uom": "degC", "source": "IS-TT2207", "revision": "1", "locator": "box 22"}`.
- **The standard reference lives on the field definition,** in the mapping table
  [`standards-mapping.csv`](../schemas/context-map/standards-mapping.csv), once per field. A fact, relation or scope
  has no `std` of its own. The only `StandardRef`s in a map are values that are themselves a class or code (an
  item's `class_refs`, a document's `type_refs`) and a source's handover standard.
- Status vocabulary: `unverified`, `confirmed`, `corrected`, `rejected` (from twin-graph-1) plus `stale` for a value
  whose source has since been revised.

## The DOCUMENTS layer

A document has: id (`SITE/DOC/<id>`), `revision` (required), `title`, `doc_type` (the site's own name), `type_refs`
(CFIHOS document type for plant and project documents; VDI 2770 class for manufacturer documents), `status`
(`draft`, `released`, `superseded`, `withdrawn`), `owner`, `path` or `uri`, `sha256`, `manufacturer` for vendor
documents, and whether its text could be read (`text_extracted`). Three relations join documents to the rest:

- **`covers`**: the smallest scopes or items it is about, declared by exact id. Never guessed.
- **`mentions`**: a tag, alias or qualified id found in the document's text, with the locator (page and line, sheet
  and cell), the matched text and how it matched (`exact`, `alias`, `qualified_id`, or since 1.1 `glossary` with the
  `term`; see [Glossary](#glossary)). Text read by OCR never asserts a mention. Asserted only when it is
  unambiguous; otherwise an `ambiguous_reference` conflict or a near-miss review item. Mentions need readable text;
  a document whose text was not extracted has covers but no mentions, and coverage says so.
- **`based_on`**: another document at a stated revision. When that document is revised, this one is flagged
  `superseded_basis` and everything based on it reopens, transitively.

P&ID sheets are documents too; the P&ID sheet register (`drawing_register`) is their part of the document register.

## The DECISIONS layer

**Conflicts.** A conflict has an id (`SITE/CONFLICT/C-<hash>`), a `type`, the `subject` it concerns, the
`attribute` and `fact_kind`, the authority at detection time, two or more `sides` (each with source, record type,
revision, locator and what it says), the `record_owner` it is routed to by default, `other_parties`, a `status`
(`open`, `disputed`, `resolved`) and whether it is still `detected`. Types are the one-map types
(`asset_presence`, `value_disagreement`, `mention_not_in_register`, `ambiguous_reference`, `superseded_basis`,
`loop_pairing`, `loop_reference`, `unlisted_loop`, `boundary`) plus `authority_gap`.

**Authority per fact** is the site's `settings.authority` map above, with a written reason for every override.

**Rulings.** A ruling records a local decision and its reason: what it concerns (a conflict or an item), the
attribute, the kind of ruling (`accept_source`, `accept_value`, `no_conflict`, `authority_override`, `defer`), the
chosen source or value, the reason, who and when, and what it rests on (`authority`: `field`, `record` or `person`,
default `person`). A **field verification ruling** is a walkdown result settling a disputed conflict: `authority`
`field` with `evidence` (the photo file, nameplate reading or locator). It extends one map's `decisions.csv` and is
filled in through the `ruling` template; `one_map.py build --decisions` reads either file, keeps every ruling as a
history line on the conflict, and, when the ruling chose a value a record still contradicts, asks that record's
owner to update the record. Software never makes a ruling.

**Outside the format:** who a conflict is routed to beyond its default owner, approvals, sign-off chains,
notifications and the history of a ruling's discussion. Those belong to an external governed service. A ruling may
carry `external_ref`, the id of the matching record there.

## Classes

Since 1.1. [`classes.json`](../schemas/context-map/classes.json) is a small class tree (39 classes), each with a
definition in our own words, the DEXPI 2.0.1 classes it maps to (class names and class-page URLs, opened on
2026-11-04, with `match` exact, close, broader or narrower), a CFIHOS reference left `to_confirm`, its expected
properties (the datasheet property names) and its certification.

| Root | Tree |
|---|---|
| equipment | rotating equipment > pump > centrifugal pump, positive displacement pump; static equipment > vessel or tank (vessel, tank), heat exchanger (plate, shell and tube), hold tube |
| valve | control valve, on/off valve, divert valve, relief device, manual valve |
| instrument | by ISA-5.1 succeeding letters: transmitter (T), primary element (E), indicator (I), switch (S), controller (C), relay or compute (Y) |
| line | line-list line numbers |
| document | P&ID, procedure, HACCP plan, verification document, calibration certificate, inspection report, design basis, datasheet, check sheet, maintenance plan, note (matched from the document's own `doc_type`) |

An item's `class` is optional. It is set only where it is deterministic, in this order, and stays unset otherwise:

1. a record says so (the `class` column of the tag register or of a supplied list);
2. the tag letters: the site's `letter_overrides`, then the letter rules in `classes.json` (`FDV` divert valve,
   `PSV` relief device, `TCV` control valve, `TIC` controller, `TT` transmitter); a class outside the roots allowed for
   the item's `kind` is not assigned;
3. for equipment only, the site's equipment tag prefixes (`P` pump, `HT` hold tube, `PHE` plate heat exchanger). The
   shipped prefixes are common conventions, not a standard; a site replaces them;
4. a datasheet value refines down the tree, never sideways (`pump_type` `rotary lobe` makes a pump a positive
   displacement pump; `type` `tank` never makes a pump a tank).

Two records naming different classes, or a class not in the tree, is a review row for the record's owner. A class
assigned this way is still `unverified`: certifying a class certifies the word, never that an item belongs to it.

## Relation semantics

Since 1.1. [`relations.json`](../schemas/context-map/relations.json) gives every frozen relation its domain and range
(classes, which admit their subclasses, or the pseudo-classes `@scope`, `@connector`, `@loop`, `@any`), an inverse
name for reading backwards, whether it is transitive, and the expected cardinality per end.

| Relation | Domain -> range | Inverse | Transitive | Per from / per to |
|---|---|---|---|---|
| `contains` | scope, equipment -> anything | `contained_in` | yes | 0..* / 1 |
| `piped_to` | equipment, valve, line, in-line transmitter or element, connector (both ends) | `piped_from` | no | 0..* / 0..* |
| `measures` | transmitter, primary element, indicator, switch -> equipment, valve, line | `measured_by` | no | 0..1 / 0..* |
| `controls` | controller -> valve, rotating equipment (a drive) | `controlled_by` | no | 1..* / 0..* |
| `sets_point_of` | controller -> controller | `setpoint_from` | no | 0..* / 0..1 |
| `acts_on` | valve, relay -> equipment, line, valve | `acted_on_by` | no | 0..* / 0..* |
| `protects` | relief device, switch -> equipment, line, valve | `protected_by` | no | 1..* / 0..* |
| `signal_to` | instrument -> instrument, valve, rotating equipment | `signal_from` | no | 0..* / 0..* |
| `actuated_by` | valve, equipment -> anything | `actuates` | no | 0..1 / 0..* |
| `nozzle_of` | anything -> equipment | `has_nozzle` | no | 1 / 0..* |
| `references` | connector -> anything | `referenced_by` | no | 0..* / 0..* |
| `member_of` | instrument, valve, rotating equipment -> loop | `has_member` | no | 0..* / 1..* |
| `covers` | document -> anything | `covered_by` | no | 0..* / 0..* |
| `mentions` | document -> anything | `mentioned_in` | no | 0..* / 0..* |
| `based_on` | document -> document | `basis_of` | yes | 0..* / 0..* |

A link is checked only when both ends have a certified class (or are scopes, connectors or documents); a link with an
end of no class is counted, not checked. **A link outside its domain or range is never dropped:** it stays on the
map and becomes a review row, "link doesn't fit what it connects", for the owner of the record that asserted it (a
reader's `PI-2240 measures TIC-2207` goes to the P&IDs' owner). An upper bound of 1 exceeded (an instrument that
measures two items) is the same kind of row; lower bounds are the expectation rules' job. `relations.json` also maps
one-map's twin-graph-2 edge names (`connects` reads as `piped_to`, `signal_line` as `signal_to`, and twin-graph-1's
measurement-to-controller `controls` as `signal_to`).

## Expectations

Since 1.1. Completeness rules: what must exist for a kind of item or record row. They are declarative JSON
(`context-map-expectations-1`); the template is [`templates/expectations.json`](../schemas/context-map/templates/expectations.json),
which a site copies next to its site file and edits. A rule has an `id`, a `title`, what it `applies_to` (a `class`,
a `register` with an optional row filter, or `loops`), its `checks`, the `owner` of the gap, a `severity`, a
`certification`, and optionally `rollout` and `limit_per_scope`. Checks are `field` (a row value is filled in),
`resolves` (a row's tag is an item on the map, optionally of a class), `record` (a row of a register exists for the
item, optionally filtered, with `$as_of` for dates), `relation` (a link exists), `document` (a document of a class
covers or mentions the item), `loop_role` (a loop's measurement, controller and output resolve to the right classes)
and `any_of`.

| Rule | Applies to | Expects | Owner |
|---|---|---|---|
| `R-CCP-COMPLETE` | each `ccp` row | a critical limit, a monitoring instrument on the map, an in-date calibration record for it (`next_due` on or after `as_of`) and a verification document that covers or mentions it | Quality |
| `R-RELIEF-PROTECTS` | relief devices | a `protects` link or a relief device register `protects` value, and a test or inspection date | Process safety |
| `R-LOOP-COMPLETE` | listed loops | a measurement, a controller and a final element of the right classes | I&C |
| `R-CRITICAL-PM` | criticality ranking rows ranked A, 1, high or critical | a PM plan row | Maintenance |
| `R-PID-IN-CMMS` | equipment | in the maintenance equipment export; already the `asset_presence` conflict, so this rule only counts it and raises no second row | Maintenance |

**Absent is not empty.** A check names the registers it `needs`; where none of them is present for the subject's
scope (no source of that register is the record for the scope), the check is not evaluated: counted as "not
evaluable: no calibration_record covers S1/P1/CIP1", never a missing row. A supplied register with no row for the
item is a real gap. A date check without an `as_of` date (rules file or site file) is not evaluated either.

**Output.** Each subject gets a result (`complete`, `missing`, `not_evaluable`, `draft_rule`, `not_rolled_out`) with
what is missing and what could not be evaluated; a missing subject of a certified, rolled-out rule is an "expected
but missing" review row routed to the rule's owner; the coverage report gets per-rule counts (`by_rule`: subjects,
complete, missing, not evaluable, not rolled out, rows raised).

**Rolling rules out without flooding a queue.** A plant's first build would otherwise put every gap of every rule in
the queue at once. So:

1. every rule in the template ships as **draft**, and a draft rule raises **one summary row per unit** ("would raise
   N rows in S1/P1/PAST1, for example ...") to its owner, never one per item;
2. a person **certifies** a rule (status certified, by, on) to let it act;
3. `rollout.scopes` (per rule or for the whole file) limits a certified rule to some units first, and
   `rollout.owners` to the rules some owners are ready for; outside its rollout a rule only counts (`not_rolled_out`);
4. `limit_per_scope` caps a rule's rows per unit, with one row saying how many more there are.

The usual path: certify the CCP rule for one pasteurizer, read its rows, fix the rule or the records, widen the
rollout, then certify the next rule.

## Glossary

Since 1.1. The `glossary` register holds the words people write instead of tags: a `term`, its `synonyms` (separated
by `|`), a `definition`, what it names (`maps_to_class`, `maps_to_item`, or both), the `plant` and `unit` it is used
in, its `owner` and its certification. Document matching uses it beside tag matching:

- terms match case-insensitively as whole words; a term followed by digits (`FDV-2210`, `FDV 2210`) is a tag, not
  a term;
- a hit **links** (`mentions`, match `glossary`) only when the term is **certified** and maps to **exactly one item
  in the document's covered scope** (the plant and unit of each `covers` entry, inside the term's own scope);
- otherwise it is a `possible mention, confirm` review row to the term's owner, one per document and term: a draft
  term, a class-only term with two candidates (`product pump` with P-101 and P-102), a term outside the covered scope;
- a term that maps to nothing is a definition only and raises nothing.

Pasteurizer examples: `HTST` -> unit PAST1, `hold tube` -> HT-100, `divert valve` / `FDV` -> FDV-2210 (certified,
link); `timing pump` -> P-101 (draft: review row).

## Certification

Since 1.1. Classes, glossary terms, expectation rules and authority overrides carry a certification: `status`
`draft` or `certified`, with `by` and `on`. Only certified ones act on their own; `certified` without who and when
counts as draft.

| Piece | Certified | Draft |
|---|---|---|
| class | assigned by inference, used to check links | never assigned |
| glossary term | may link a mention | review row |
| expectation rule | per-item rows (within its rollout) | one summary row per unit |
| authority override (`settings.authority_certification`) | the override acts | the default stays; review row to the overridden record's owner |

An authority override with no certification entry keeps the 1.0 behaviour (it acts). The shipped classes are
certified as format vocabulary by its maintainers; the shipped rules are all draft.

## Answerability

Since 1.1. `one_map.py ask --map graph.json --question-kind KIND --item ITEM` answers one question, read-only, with
the source of every fact: `connects` (what X connects to), `measured-by` (what measures or protects X), `documents`
(which documents cover or mention X), `disagreements` (which records disagree about X), `complete` (is X
expected-complete). The item may be a qualified id, a tag unique on the map or a certified glossary term. When the
record a question needs is absent for X's scope the answer is **"can't answer from this map: no P&ID covers
S1/P1/FILL1"**, from the same coverage the rules use; "disagreements" with fewer than two records holding X says no
disagreement could be detected, rather than "none". Worked answers:
[`expected/pasteurizer/answers.md`](../examples/one-map/expected/pasteurizer/answers.md).

## JSON-LD view

Since 1.1, optional. `one_map.py jsonld --map graph.json --out map.jsonld` writes a JSON-LD view: classes as
`rdfs:Class` with `rdfs:subClassOf`, DEXPI class-page URLs as `rdfs:seeAlso` where `classes.json` verified them
(DEXPI publishes HTML class pages, not an RDF namespace), CFIHOS as `to_confirm`; items typed with their class; each
relation as a property and as a statement node with its provenance. Our terms live under
`https://github.com/steve-vitale/industrial-context-toolkit/schemas/context-map/vocab#`; item ids are
`urn:context-map:<qualified id>`. It is a view for interoperability; nothing reads it back and there is no reasoning
over it.

## Coverage report

Coverage is part of the file, recomputed on every build and never hand-edited. It answers "how much of this unit
do we actually have?" It does not say whether the values are right.

**Per register:** supplied or not; rows; rows resolved to items; fill rate per field (share of rows with a
non-empty value); scopes covered.

**Per unit:** items; items drawn on a P&ID; items in the tag register; equipment in the maintenance equipment export
out of all equipment; instruments in the instrument index out of all instruments; items with datasheet values;
loops listed and loops located; documents covering the unit; safety-relevant items and how many of them have a
protective record (relief device register row, CCP row, interlock row or isolation points); registers supplied and
not supplied; open conflicts.

**Per layer:** PLANT (items, relations, loops), RECORDS (registers supplied out of registers defined), DOCUMENTS
(documents, how many had readable text), DECISIONS (open conflicts, rulings).

**Since 1.1:** `by_rule` (per expectation rule: subjects, complete, missing, not evaluable, not rolled out, rows
raised) and `relations_checked` (links checked, links with an end of no class, links that do not fit).

A plant that has only a maintenance equipment export gets a valid map with one register supplied, items with no P&ID
appearance, and a coverage report that shows exactly that.

## Standards: one per layer

Where standards overlap, one is chosen per layer and the others become crosswalks used only when loading.

| Layer or part | Chosen standard | Also mapped | Why this choice |
|---|---|---|---|
| Hierarchy names | plant words (site, plant, unit, system); our own | ISA-95 (ANSI/ISA-95.00.01-2025, IEC 62264-1 Mod) and ISA-88 equivalents, DEXPI `PlantStructure`, ISO 14224 taxonomy levels, all in the mapping table only | the words plant people use; the equivalents let MES, ERP and DEXPI sources load |
| P&ID content: items, connections, line and signal types, loops | DEXPI 2.0.1 | ISA-5.1 for line symbols DEXPI lacks | open, machine-readable, CC BY 4.0, and the toolkit already reads DEXPI XML |
| Tag letters | ISA-5.1-2024 | none | the letters plants actually use; parsed as a hint only |
| Registers, classes, properties, document types | CFIHOS 2.0 | DEXPI class names on PLANT items; ISO 14224 equipment class on maintenance rows | the handover format contractors deliver; free to download and use |
| Maintenance and reliability data | ISO 14224:2016 | CFIHOS for the equipment register | the reference for failure and maintenance data fields |
| Vendor documents | VDI 2770 Blatt 1:2020-04 | AAS Handover Documentation submodel (IDTA 02004 2.0) as a load route | the vendor-document classification manufacturers deliver against |
| Installed-item identity from vendors | AAS (IDTA 01001, CC BY 4.0) where an item arrives with one | none | used only where useful; not required |
| Decisions, provenance, coverage | none; our own | none | no standard covers source disagreements |
| Reference-data base | ISO 15926 as the background idea of reference-data classes | none | its upper ontology is not adopted |

Item classes: on a PLANT item the class is a DEXPI class name (`RotaryPump`, `OperatedValve`, `Transmitter`); in
the records layer it is a CFIHOS tag class code; in maintenance data it is an ISO 14224 equipment class code. An
item may carry all three as separate `class_refs`. The map's own small `kind` stays the cross-cutting field.

### What the toolkit may reuse from each standard

Checked on 2026-11-04. "Reference" means storing an identifier (class name, code, level name, clause number) and a
link. That is what this format does for every standard; it never ships a standard's definitions.

| Standard | Current version found | Licence or terms found | What this MIT project may do | Source |
|---|---|---|---|---|
| CFIHOS (IOGP JIP36) | 2.0, November 2025 (release notes October 2025); 1.5.1 before it | The site says all documents are free to download and use; copyright reserved; no named open licence found | Reference CFIHOS codes and names and link to them. Do not redistribute the RDL or data dictionary files. | [jip36-cfihos.org/cfihos-standards](https://www.jip36-cfihos.org/cfihos-standards/) |
| CFIHOS RDL as hosted by POSC Caesar | CFIHOS RDL v2.0 at `posccaesar.org/cfihos/v2.0/CFIHOS-<number>` | PCA's general terms default to CC BY-ND 4.0 for common collections unless a resource shows its own licence; linking is allowed. Whether the CFIHOS RDL falls under that default was not stated | Link URIs and cite codes. Verbatim copies with attribution would be allowed under CC BY-ND but modified or excerpted definitions would not; we copy none | [posccaesar.org/terms](https://posccaesar.org/terms/), [example entry](https://posccaesar.org/cfihos/v2.0/CFIHOS-10000395) |
| DEXPI | Specification 2.0.1, released 2026-09-30 (2.0.0 on 2025-10-10; 1.4.0 in 2024) | CC BY 4.0 | Use class names and enumeration literals, and reuse with attribution to the DEXPI Initiative, marking changes. We use names only | [GitLab releases](https://gitlab.com/dexpi/Specification/-/releases), [2.0.1 HTML](https://dexpi.org/specification/2.0.1/html/index.html) |
| DEXPI OPC UA companion (OPC 30250) | 1.00, 2021-09-15, built on DEXPI 1.2; no 2.0 edition found | OPC Foundation specification licence (text not reviewed) | Name only; not used by this format | [OPC Foundation](https://opcfoundation.org/developer-tools/documents/view/277) |
| ISA-95 / IEC 62264-1 | ANSI/ISA-95.00.01-2025 (IEC 62264-1 Mod), April 2025, from IEC 62264-1 edition 2 | Paid, copyrighted standard | Use the level names (Site, Area, Work center) and cite the standard. Do not copy text or figures | [ISA news release](https://www.isa.org/news-press-releases/2025/april/update-to-isa-95-standard-addresses-integration-of) |
| ISA-88 / IEC 61512-1 | ANSI/ISA-88.00.01-2010 is the latest found; a joint ISA/IEC revision of Part 1 was announced in 2022 and was not found published | Paid, copyrighted | Level names only | [ISA-88 page](https://www.isa.org/standards-and-publications/isa-standards/isa-88-standards) |
| ISA-5.1 | ANSI/ISA-5.1-2024 (approved July 2024) | Paid, copyrighted | Cite it; parse letters by a short rule of our own. Do not reproduce the letter tables | [ISA product page](https://www.isa.org/products/ansi-isa-5-1-2024-instrumentation-and-control-symb) |
| ISO 14224 | 2016 edition; one source reports it under systematic review since 2022 | Paid, copyrighted | Cite taxonomy levels and data categories; plants enter class and failure codes from their own licensed copy. The code tables are not shipped | [iTeh catalogue entry](https://standards.iteh.ai/catalog/standards/iso/f09321bd-e41d-401f-8eca-c85c5c732c74/iso-14224-2016) |
| VDI 2770 Blatt 1 | 2020-04 | Paid, copyrighted; XML schema is in the paid annex | Field name `vdi2770_class` and class ids only; no classification text or schema copied | [VDI page](https://www.vdi.de/en/home/vdi-standards/details/vdi-2770-blatt-1-operation-of-process-engineering-plants-minimum-requirements-for-digital-manufacturer-information-for-the-process-industry-fundamentals) |
| AAS (IDTA, IEC 63278-1) | IDTA metamodel 3.1.1 (CC BY 4.0); 3.2 documents dated July 2026; definitions from IEC 63278-1 edition 1.0 (2023-12); Handover Documentation submodel IDTA 02004 2.0 (2025-06) | IDTA specifications CC BY 4.0 (3.1.1 checked; 3.2 not checked); IEC 63278-1 itself is a paid standard | Reuse IDTA names with attribution; cite IEC 63278-1 | [IDTA Part 1 3.1.1](https://industrialdigitaltwin.org/wp-content/uploads/2025/08/IDTA-01001-3-1-1_AAS-Specification_Part1_Metamodel.pdf), [IDTA 02004 2.0](https://industrialdigitaltwin.org/wp-content/uploads/2025/07/IDTA-02004-2-0_Submodel_Handover-Documentation.pdf) |
| ISO 15926 | not checked | Paid | Background reference only | none |

Not verified in this pass, and therefore only named, never adopted: ISA-18.2 (alarms), IEC 61511 (safety
instrumented functions), Codex HACCP principles, OSHA 29 CFR 1910.147 (lockout), ISO 8000 (material master data).

Only one CFIHOS code was opened and checked (`CFIHOS-10000395`, drawing position number). Every other CFIHOS
reference in the mapping table is marked `to_confirm`, including the exact table and column names of CFIHOS
deliverables; they must be checked against the C-DM-002 data dictionary of the version a contract names, and they
stay `to_confirm` until someone does.

**CFIHOS reference data is not redistributed.** This project ships no CFIHOS RDL, data dictionary or definition
text. A CFIHOS code in this format is a link only: the code and a URI pointing at the published reference data. That
stays the rule pending confirmation of the terms of use with IOGP (JIP36) and POSC Caesar, including whether the
CFIHOS RDL falls under POSC Caesar's CC BY-ND default.

## How today's toolkit formats fit in

This is the **design target**, not an implemented migration. It supports the
[shared engineering model and component-view direction](ENGINEERING_FOUNDATION.md#one-engineering-model-many-draft-components):
an agent queries the common context and drafts a component when its required
context exists, or returns a partial scaffold with explicit gaps. Derived
components retain original evidence lineage; reimporting a generated document
must not create independent corroboration. Existing graph readers/generators
continue to use their documented contracts until actual adapters are validated.

| Today | What it is | In `context-map-1` | Fate |
|---|---|---|---|
| Prediction format (`symbols`, `connections` per sheet) | a reader's output for one P&ID image | evidence behind PLANT appearances and relations, via the sheet read | **stays** as the reader slot contract; not stored in the map |
| `one-map-sheet-1` | a P&ID read: tags with zones, lines, signal lines, off-page connectors | PLANT items' `appearances`, `piped_to`, `signal_to`, placement relations, sourced to the sheet | **stays** as the P&ID input; not storage |
| Extracted twin (`plant_model.json`) | intake output from one P&ID image | PLANT items and relations with status `unverified`, source record type `pid` | **stays** as the intake bundle; loads into the map |
| Process model (`data/te_process_model.json`) | an authored or DEXPI-read model | PLANT layer, source record type `pid` (authored) | **stays** as the generator input; later a view written from the map |
| `twin-graph-1` | portable graph export | a projection of the PLANT layer | **becomes a view**, frozen for the existing graph, context and snapshot tools |
| `twin-graph-2` (one map's graph) | site graph with documents and conflicts | all four layers; the graph becomes a projection | **retired as storage**; kept as a view |
| `one-map-site-1` | site file: hierarchy, register paths, owners, routing, authority | `map`, `settings`, `sources`, `plant.scopes` | **retired** after one release in which loaders still accept it |
| `context-sources-1` | document manifest with owner, status, covers, based_on | `document_register` plus `sources`; locators become mention and evidence locators | **retired** into the DOCUMENTS layer; the context register reads a view |
| One map's `decisions.csv` | `conflict_id,status,by,on,note` | the `ruling` register (a superset) | **retired** after migration |
| `context-register-1`, `engineering-onboarding-1` | questions, answers, onboarding packets | not part of the map; they reference map ids | **unchanged** |

The CSV registers one map reads today (maintenance equipment export, instrument index, loop list, datasheets,
P&ID sheet register) keep their columns; the templates add only optional columns.

## Loading a contractor handover

**CFIHOS.** A CFIHOS handover is a set of tables (tags, equipment, property values, documents and document-to-tag
references; exact names per the contract's CFIHOS version). A loader maps them as: tag table → `tag_register`
(CFIHOS tag class into `cfihos_tag_class`; area or plant codes into scopes through a site-supplied scope mapping,
never guessed); equipment table → `maintenance_export` (physical item at a tag); property values → `datasheet`
(long form, `cfihos_property` = the property code); document table → `document_register`
(`cfihos_document_type`); document-to-tag references → document `covers`. Each table becomes one `source` with
`handover: "CFIHOS 2.0"`. Codes the RDL marks as unknown are kept as text and reported in coverage.

**DEXPI.** DEXPI XML loads through the existing `dexpi_reader.py` route into the PLANT layer: `PlantStructure` into
scopes (the site says which DEXPI level is its unit), tagged plant items into items with their DEXPI class in
`class_refs`, `PipingNetworkSegment` connections into `piped_to`, `MeasuringLineFunction` and `SignalLineFunction`
into `measures` and `signal_to` with `line_type` and `signal_type`, `InstrumentationLoopFunction` into loops.
Each element keeps its DEXPI id as a locator.

**Vendor documents (VDI 2770 or AAS Handover Documentation).** Each document becomes a `document_register` row with
`manufacturer` and `vdi2770_class`; the asset it belongs to becomes `covers` through the tag lookup table
(`vendor_tag` or serial number).

In every case the handover is one more source. It does not override plant records; disagreements become conflicts
under the authority map, and contractor tags that differ from site tags go through the tag lookup table
(`handover_tag`).

## Versioning

- The file says `"format": "context-map-1"` and a `format_version` (`1.minor.patch`). Additive changes (a new
  optional field, a new register, a new enum value) raise the minor version and stay `context-map-1`. Anything that
  makes an old file invalid or changes a meaning is `context-map-2`.
- `registers.json` carries the same version and is the one catalogue of registers; the schema's register names must
  match it (the test checks this).
- **Relation names are stable** (see the PLANT layer). Renaming or removing a relation name, or reversing its
  direction, is a breaking change and needs `context-map-2`; the test pins the frozen set.
- Every `StandardRef` records the standard version it points into, and `standards-mapping.csv` pins the version each
  mapping was made against. Moving to a new standard version is a mapping change, reviewed like any other.
- This draft is `1.1.0-draft` (1.1 added `class`, the glossary register, `Certification`, `expectations`,
  `settings.as_of`, `settings.authority_certification`, the `glossary` mention match and two coverage parts, all
  optional). `registers.json`, `classes.json`, `relations.json` and the rules template carry the same version.
  Nothing reads a context-map-1 file yet, so it may still change without a version bump.

## Non-goals

- **Not a workflow or approval system.** No routing beyond the default owner, no sign-off, no notifications, no
  ruling history. Those belong to an external governed service.
- **Not a reasoning ontology.** A small class tree, relation semantics and completeness rules (1.1), checked by
  plain code; no ISO 15926 upper ontology, no OWL, no inference engine. The JSON-LD view is optional.
- **Not a replacement or sync for the CMMS, document system, historian or permit system.** The map reads exports;
  it never writes back.
- **Not a redistribution of standards.** Identifiers and links only; no definitions, code tables, RDL files or
  schemas from paid or no-derivatives sources.
- **No unit conversion or text normalization** in this version. Values compare as written, with their unit.
- **No geometry, layout or 3D.** Locators point at places in documents; they do not draw.
- **No truth claims.** Every value stays `unverified` until a person reviews it; coverage counts what exists, not
  what is correct.
- **No access control.** The map file holds what it is given; who may see it is the company's decision.

## Decided (2026-11-04)

The owner answered the eight open questions of the first draft on 2026-11-04. Each is applied above and checked by
`scripts/test_context_map_format.py`.

1. **Hierarchy words.** Templates, schema and spec use plant words: plant, unit, system. ISA-95 and ISA-88
   equivalents live only in the mapping table (`standards-mapping.csv`, mirrored in the hierarchy table above); the
   per-scope `isa95_level` and `isa88_level` fields were removed.
2. **Datasheets.** Long form stays canonical. Wide-form templates (one row per item) were added for pump, heat
   exchanger, vessel and tank, control valve, transmitter and relief valve, with a fixed wide-to-long conversion
   (column = property, unit in square brackets). The test converts every wide template and validates the long rows.
3. **Instrument range and model authority.** Ordered authority: the instrument spec sheet where the site supplies
   one for that scope, otherwise the instrument index. Every default authority is now an ordered list (first
   present record type wins); the test exercises the rule on the example map.
4. **Standard references.** On the field definition (the mapping table) only. The per-value `std` was removed from
   facts, relations and scopes.
5. **Permits and purchase orders.** Kept in version 1 as read-only copies linked by tag; their workflow belongs to an
   external governed service. Marked `record_copy` in `registers.json`.
6. **Relation names.** Frozen now as listed in the PLANT layer, including `contains` (no `has_part`) and the
   document relations `covers`, `mentions` and `based_on`. Renames need `context-map-2`.
7. **CFIHOS codes.** All but the one checked code stay `to_confirm`. CFIHOS reference data is not redistributed;
   codes are links only, pending confirmation of terms with IOGP and POSC Caesar.
8. **Next registers.** Added now: CAPA register, equipment criticality ranking, inspection records (vessels, piping,
   RBI). Planned next: PFDs and heat and material balances; electrical single-line diagrams and motor schedules;
   training records; safety data sheets (SDS) and chemical inventory.

Still open, outside these decisions: confirming the CFIHOS 2.0 codes and terms (item 7) before any code ships, and
choosing a site override example once a real site's authority choices are known.

## For agents

```text
format:   context-map-1 (draft 1.1.0-draft); schema schemas/context-map/context-map-1.schema.json (JSON Schema 2020-12)
layers:   plant {scopes, items, relations, loops} | records {<register_id>: [rows]} | documents [] | decisions {conflicts, rulings}
also:     map {site,...}, settings {owners, authority, authority_reasons, fact_kinds, routing, letter_overrides}, sources [], coverage {}
required: format, map.site, plant.scopes, plant.items; item = {id: SITE/PLANT/UNIT/TAG, tag, scope}
hierarchy: plant words site > plant > unit > system; ISA-95/88 equivalents only in standards-mapping.csv
registers: schemas/context-map/registers.json (fields, required, fact_kind, owner, authority_for); templates/<id>.csv match it
datasheet: long form stored; templates/datasheet-wide/*.csv convert by registers.json datasheet_wide_forms.conversion
absent register = not supplied; [] = supplied, no rows
value:    scalar (inherits row source/revision/locator) or {value, uom, source, revision, locator, status, fact_kind}; no per-value std
authority: ordered lists, registers.json default_authority + authority_rule (first present for the scope wins), overridden by settings.authority
relations: frozen names ($defs.RelationType + covers, mentions, based_on); a rename needs context-map-2
semantics: relations.json domain/range (classes or @scope/@connector/@loop/@any), inverse, transitive, cardinality;
          a link that does not fit -> review row "link doesn't fit what it connects", never dropped
classes:  classes.json tree; item.class only from a record column, tag letters, equipment prefix, datasheet refine
rules:    templates/expectations.json (all draft); certified + rolled out -> "expected but missing" rows to the
          rule owner; draft -> one summary row per unit; absent register -> not evaluable, never a gap
glossary: glossary register; certified term naming one item in the covered scope -> mentions (match glossary);
          anything else -> "possible mention, confirm"; OCR text never links
ask:      one_map.py ask --map graph.json --question-kind connects|measured-by|documents|disagreements|complete
          --item X -> facts with sources, or "can't answer from this map: no <register> covers <scope>"
standards: schemas/context-map/standards-mapping.csv; identifiers and links only, never definitions; CFIHOS codes to_confirm except CFIHOS-10000395
never:    renumber or trim a tag; join on a normalized tag; resolve a conflict; ship standards text or RDL files
check:    python scripts/test_context_map_format.py; python scripts/test_ontology.py
```
