# Answer contract and drafting guide

Return one JSON object with exactly `model`, `layout` and `evidence`. The complete reference answer uses the
illustrative reference_source.txt, not the selected source. Its equipment, connections and controls are examples
of the existing format, not facts to copy into your answer.

## Model

Keep `meta.model_id`, `title`, `source_document`, `source_sha256`, `unknowns` and `assumptions`. The source document
is `source.txt`; copy its exact SHA-256 from packet.json. Unknowns and assumptions are lists of strings. Keep
unknown process facts unknown; only drafting geometry should be proposed without source facts.

The required lists are `units`, `streams`, `instruments`, `final_elements`. Empty lists are valid when the source
does not specify that class. Optional lists are `controllers`, `manual_valves`, `relief_devices`, `interlocks`
and `limits`. Every represented record needs `source`: one `source.txt:LSTART-LEND` citation. In `evidence`, map
each used citation to the exact full line span joined with newline characters, without the numbered display
prefix. No unused citations. A matching quotation checks the locator, not whether the claimed interpretation
is true. Keep supplied identifiers; use `assigned_tag: true` when an identifier is newly assigned.

Units require id/name/type. Supported process symbol types: pressure_vessel, vessel, tank, pump, heat_exchanger,
reactor, condenser, separator, compressor, stripper, feed_header. Streams require id/name/from/to, using unit IDs
or BL for battery limits. Instruments need tag/unit/variable/uom/description, plus stream when inline. Use an
empty uom when unspecified, not a guessed value. Final elements need tag/unit/uom/description and their known
stream. Controller measurement names the supplied instrument; output.final_element names the supplied valve,
output.split_range lists distinct supplied valves, or output.setpoint_of names a supplied inner controller. Use exactly one output key. A known relationship must not be replaced by a guess
just to make validation pass. No fabricated verification or operations-review metadata is permitted in this
first-draft authoring route. Existing advanced model workflows remain separate.

Do not drop equipment the source names because no supported type fits it (for example a turbine): represent it
with the closest supported type, keep the source's name for it, and record the substitution in meta.assumptions.
Connections need not be stated as pipes. Where the source gives the order in which material passes through
equipment (before, after, prior to, entering, downstream of, the outlet of, or a list of units in process order),
represent each connection that order implies as a stream citing the lines that give it, and record each such
stream in meta.assumptions as an order-based interpretation for review. Never connect units whose order the source
does not give; keep those questions in meta.unknowns.

## Layout

Use the reference layout structure. `sheet_px` is [3200,2130]; keep equipment/routes in the drawing frame, clear
of border/legend/title block. Keep control_valve_stations false: no invented block/bypass valves. Sheet IDs must
be safe letter-led identifiers (letters/digits/underscore/hyphen, maximum64 characters, no reserved device names).
Other record IDs preserve nonempty identities (maximum128 characters); unit IDs also pass the exporter's
filename checks. The fixed legend fits six units per sheet; split larger models over named sheets. Preserve
every model item and connection. Layout positions are proposed geometry, not physical nozzle coordinates.

Equipment type determines its supported symbol: tank/vessel/pressure_vessel/reactor/separator use vertical_vessel; stripper uses column; heat_exchanger/condenser use horizontal_exchanger; pump/compressor retain their symbol; feed_header uses mixer. Advanced alternate symbols need a separate reviewed drafting workflow.

Units: vertical_vessel uses cx/top/bottom/w/head; column adds trays; pump uses at/r; horizontal_exchanger uses
x0/x1/cy/h; compressor uses at/r; mixer uses at only (a fixed 70 by 70 pixel outline centred on at; any r is
ignored). A generic symbol must not imply dimensions stated nowhere.
Use mounts {tag:[x,y]} for unit-mounted instruments. Place inline items on their known route with place
{tag:[x,y]}; points must lie on that polyline. Avoid symbols, text and unintended line joins. A route names its
stream, from/to endpoint objects, and orthogonal pts. Endpoint objects use unit or flag; a true branch can use
{tee:route_id,at:[x,y]}. The branch point must be on that route. Battery-limit flags name their stream/label/at/dir. One route per stream per sheet is supported. Paired continuation flags on two sheets must use opposite endpoint roles. Named net joins and unsourced utility routes are unsupported here. Route endpoints must touch the declared equipment bounds or flag port; tee endpoints coincide with the parent route. These consistency checks do not certify nozzle geometry.
Controller positions use controllers {tag:[x,y]}. Signals name exact from/to tags with optional orthogonal via
points. Include every source-backed measurement/output/setpoint/interlock signal. Do not create new controls.
Keep title_block.revision exactly DRAFT and title_block.notes exactly the four reference notes, in order.
The independently consumable drawing must retain its draft/source/geometry/placeholder disclaimers.

## Feedback and review

The engineer or approved local toolkit operator runs check, then returns its JSON diagnostics to the approved assistant if correction is needed.
Correct only source-backed structure, citations and drafting issues. If missing evidence prevents a correct
model, return the unresolved question to the engineer; do not invent data to silence errors. Rendered sheets
must be inspected for source interpretation, joins, symbols and readable labels before any engineering use.
This format/quotation check does not establish plant truth, current revision, source authority or approval.
