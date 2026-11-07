# CAD qualification protocol — frozen before method development

2026-11-07. Goal: eliminate unexplained differences and qualify a declared CAD route without tuning to the
existing valve drawing. Starting implementation: f7a67372d257d0d3eec1be60014aa15a99b5b621. Current native-save
baselines have 335/344 strict differences and remain failures. No comparator exclusion or tolerance is added here.

## Target and separate routes

First qualification target: single-line asset-attribute changes in an ASCII DXF with the existing explicit ICT_ID/TAG
profile, ezdxf 1.4.5 readback and existing QCAD Professional 3.33.1 Qt5 native receiver. This is not DWG, a proprietary
intelligent-P&ID database, inferred connectivity or every CAD editor. Binary DXF and ambiguous/multiline attribute
serialization must refuse rather than claim preservation.

Compare three declared routes on the same supplied source and edit plan: current library save, direct native save,
and a candidate source-preserving value edit. A source-preserving route keeps the original drawing as authority;
it is not permission to discard unexpected edits in a native return or to call native-save differences resolved.
Native-return import/merge needs separate evidence if implemented. Report each route separately.

## Acceptance criteria

1. Exact source SHA and exact before values bind every proposal. Only the existing editable attributes may change;
   identity, geometry, layers, styles, header, layout, XDATA, unknown raw data and other attributes remain intact.
2. Candidate bytes differ from the retained source only at declared single-line attribute value spans. An independent
   byte-span reconstruction must recover the original. Preserve all other bytes, ordering, encoding and line endings.
3. The unchanged strict comparator passes with zero unexpected differences under the supplied plan. Every planned
   value must also be observed through the native reader after closing/reopening a new document/process.
4. Render source and candidate through the same native renderer/settings. Inspect geometry and unchanged labels;
   only declared attribute-label changes are expected. Rendering by itself does not establish editability.
5. Perform an actual native UI open/edit/save/close/reopen with editable identity/foreign attributes and retained
   returned file. Keep any native-save strict failures visible. No API-only run fills the interactive requirement.
6. Second source revision and concurrent manual change: stale proposals refuse; conflicts remain explicit; any
   selected context projection retains exact original/candidate sources and never overwrites installed authority.
7. Planted controls must reject stale hashes, wrong before values, duplicate/identity edits, newlines, ambiguous
   target serialization and output collision, and detect geometry, style/layer, foreign-attribute and XDATA changes.
8. CI must reproduce the offline evidence and existing regression suite. No model call or commercial trial download
   is required in CI. Human/site/company acceptance is outside this software qualification.

## Exposure and validation

Development: existing authored valve, existing test fixture, and two additional authored boundary cases. Reserve
at least six further authored cases spanning DXF versions, encodings, line endings, transformations, multiple assets,
attribute order, literal text and retained unfamiliar payloads. Generate and hash all fixtures before testing the
candidate on reserved cases; publish generator, split, source/key provenance and recipe. Reserved authored cases are
procedural validation, not independently authored plant evidence or model-training blindness.

Also select at least three public geometry categories by pinned upstream paths before inspecting their contents or
running the candidate: LibreCAD library air/water, mechanical and power-engineering geometry, plus an ezdxf hatch
example from a second upstream project. Categories from one library are not independent source families. Keep exact originals
and license attribution. If they lack the required identities, report rejection of the unmodified files, and label
any added test asset/metadata as an authored adaptation; never call an adapted fixture an untouched real plant.
Apply the same baseline and candidate to all applicable selected cases. No selection by favorable outcome.

Freeze the candidate method hash before opening reserved results. A validation failure is retained. If used to fix
the method, that case becomes development and a new independently selected case is needed for a fresh qualification
claim. Publish every attempted result, not just successes. Counts from variants of one source are not independent
plant examples. Source/scope exclusions must be explicit; never add a case-specific exception to obtain zero.

## Current status

Protocol frozen; method and validation not completed. GUI capture initially fails with FrameArrived timeout;
accessibility text is available, but an indexed startup click reports coordinate input geometry unavailable.
These are infrastructure failures, not CAD acceptance or a reason to mark the goal complete. Continue other
qualification work while attempting the documented bounded UI recovery.

Pre-method clarification: public selection measures category coverage across two upstream projects; it does not claim three independent plant/source families. This clarification precedes case execution or method code.
