# Preserve a bounded CAD handoff

**Reusable DXF tools with source-retaining draft edits.** The value-span route changes only the declared
single-line attribute bytes and retains every other source byte. It works on the supplied explicit identity
profile without flattening the drawing. The separate library/native full-save baselines remain visible.
The [qualification evidence](qualification/README.md) reports the actual cases, failed attempts and open gates;
it does not establish native GUI or engineering acceptance, DWG or an intelligent-P&ID project database.

## Try the saved fixture

Python 3.10+ and `pip install -r requirements.txt` (includes ezdxf 1.4.5). No network is used by these commands.
Run from the repository root, with unused output destinations:

```sh
python scripts/cad_handoff.py inspect examples/cad-handoff/source/valve.dxf --out out/cad-inspect
python scripts/cad_value_patch.py examples/cad-handoff/source/valve.dxf examples/cad-handoff/source/edit-plan.json --out out/cad-proposal
python scripts/cad_handoff.py compare examples/cad-handoff/source/valve.dxf out/cad-proposal/candidate.dxf --plan examples/cad-handoff/source/edit-plan.json --out out/cad-readback.json
```

Inspect the earlier [saved library proposal](worked/comparison.json), [source identity](source/PROVENANCE.json),
[before context](worked/cad_context.json) and [proposed context](worked/candidate-context/cad_context.json).
The fixture shares the fictional FDV-2210 identity with the [maintenance example](../maintenance-handoff/README.md).
It proposes model SRC-3, serial AV-88412 and size DN65; acceptance of that engineering change remains separate.
The small authored symbol is not a reconstructed full P&ID.

## What is preserved and checked

- The exact original DXF bytes remain in `source.dxf` and are never overwritten.
- `cad_value_patch.py` reconstructs the source from the edited spans and refuses changes outside the declared
  attribute values. Unknown raw data, original encodings, line endings and ordering stay byte-for-byte intact.
  [Independent reconstruction](qualification/verify_bytes.py) consumes source/plan/candidate, not patch receipts.
  The [offline recheck](qualification/README.md) rebuilds the committed cohort and re-scores retained returns.
  The older `cad_handoff.py apply` route uses a library save; a decoded strict pass on that route is not raw-byte preservation.
- Every model-space asset block has explicit `ICT_ID` and `TAG` attributes. Stable IDs survive a tag/value edit;
  they are supplied identities, not matches inferred from geometry or names.
- Every other attribute, including the unfamiliar `VENDOR_NOTE`, remains. The tests deliberately change geometry,
  layer properties, a foreign attribute and XDATA to prove those changes are detected.
- Readback compares ezdxf-decoded entity tags by handle, including block definitions, attributes, layer/table and
  object entities. All decoded header values are compared except the explicitly listed writer/save metadata;
  changes to that metadata are reported. Child entities are checked in their own rows.
- A proposal binds the exact source hash and before-values. A stale source, duplicate edit, missing field or
  stable-ID edit is refused. New packets use new destinations to retain earlier history.

`cad_context.json` is an attribute context snapshot (`cad-context-1`), not a one-map graph or a pipe network.
`asset_candidates.csv` is unverified staging. Reconcile the site/plant/unit identity and record authority before
mapping accepted fields into the [one-map contracts](../../docs/ONE_MAP.md). The tool does not update a CMMS,
released drawing or site graph automatically. Relationships are empty rather than inferred from drawn lines.

## Carry the explicit exchange into the context map

The tutorial adapter uses an [authored position mapping](source/site-mapping.json), retains the DXF and publishes
its attributes as **draft drawing-reference values**, all prefixed `cad_`. They do not overwrite installed-state
authority. Every stable ID must be mapped; changed tags or source hashes require explicit reconciliation.

```sh
python examples/cad-handoff/project_to_map.py examples/cad-handoff/worked examples/cad-handoff/source/site-mapping.json --out out/cad-map-before
python examples/cad-handoff/project_to_map.py out/cad-proposal/candidate-context examples/cad-handoff/source/site-mapping.json --out out/cad-map-after
python scripts/one_map.py build out/cad-map-before/site.json --out out/cad-map-before/map
python scripts/one_map.py build out/cad-map-after/site.json --out out/cad-map-after/map
python scripts/one_map.py changes out/cad-map-before/map/graph.json out/cad-map-after/map/graph.json --out out/cad-map-change
```

The proposed revision reaches the same `S1/P1/PAST1/FDV-2210` map node; the original DXF, source hash and earlier
map remain available. [Saved map change](worked/map-change/changes.md) shows that exchange. The maps deliberately
contain no inferred pipe/control relationships. The generated queue flags missing owning records; there is no
accepted CMMS correction, engineering release or automatic bidirectional sync. This is a controlled projection,
not the general inverse of a graph export.

## Use your own DXF

Retain the original first. Qualify one tool/version and its exchange settings. This profile requires unique
`ICT_ID` and `TAG` attributes on every model-space INSERT; unprofiled blocks, flattened drawings and proxy
objects are refused. Nested assets, XREF resolution and proprietary application databases are not supported
asset-intake routes. An unfamiliar field is retained, not interpreted.

Run `inspect`, author an explicit plan using the new source hash and exact before-values, then run
`cad_value_patch.py SOURCE.dxf PLAN.json --out NEW_FOLDER`.
The tool proposes edits to TAG, MANUFACTURER, MODEL, SERIAL and SIZE only. Units and engineering meaning remain
the reviewer's responsibility. The plan's reason is supplied provenance, not an authenticated approval.
The source-preserving route requires ASCII DXF record framing and unambiguous single-line ATTRIB values;
binary/proxy input, multiline/ambiguous serialization, unsafe control sequences and overlong encoded values
are refused. It does not import or silently merge a native editor's other changes back into the source.

## Native-editor acceptance remains a separate test

The original saved example uses the ezdxf writer/reader. The later [qualification work](qualification/README.md)
adds exact-byte candidates, matched baselines, QCAD native-engine edits and fresh-process stored-text readbacks.
**No successful interactive native CAD open/edit/save/close/reopen is claimed.** Use
[the receiving checklist](RECEIVING_CHECK.md) in the actual target. Save the returned DXF, then run `compare`.
The [LibreCAD native-render attempt](NATIVE_ATTEMPT.md) retains its partial result and GUI automation failure;
it does not supply an editable-attribute or save/readback pass.
The [receiving review command](receiving-review/README.md) turns a returned DXF into a readable packet, with
planned/missing/unexpected attribute values, named fields/layouts and the complete strict queue. Its two actual
QCAD native-engine returns remain unqualified (335 and 344 strict differences); no GUI acceptance is claimed.

Handle renumbering, added objects, removed attributes and header differences produce differences; inspect them
explicitly rather than treating a visually similar drawing as a pass.

The comparison observes what ezdxf decodes/exports; it cannot attest to opaque unsupported content, every raw
section, rendering, an external project database or engineering correctness. Keep the original and native
project. A successful result establishes this declared software profile only.

Sources: [ezdxf block attributes](https://ezdxf.readthedocs.io/en/stable/howto/content.html),
[XDATA](https://ezdxf.readthedocs.io/en/stable/xdata.html),
[DEXPI versions](https://dexpi.org/specifications/) and
[Autodesk project-data mapping](https://help.autodesk.com/cloudhelp/2024/ENU/Plant3D-UserGuide/files/GUID-982DD218-E19A-4EA0-B53A-FDBBED503566.htm).
