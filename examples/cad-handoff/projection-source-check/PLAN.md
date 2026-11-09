# Re-read the retained drawing before projecting context

2026-11-08. Source inspection of project_to_map.py finds that it checks each
context node's source hash against source.dxf but does not check the node's
attributes or INSERT handle against that drawing. An edited context JSON can
therefore borrow an unchanged drawing hash. Removing a node and its explicit
mapping can also hide an asset. These are proposed failing controls, not an
observed plant or attacker event.

Before changing the adapter, add actual controls for an altered attribute,
altered INSERT handle, omitted asset and invented verified status. Keep the
source DXF and its hash unchanged; require refusal before any output folder.
Keep the original observed failures. Add a positive control for both already
exposed multi-asset CP1251 and UTF8/literal-brace originals, checking complete
attributes, Unicode/literal fields and exact retained drawing bytes.

Repair only the tutorial projection adapter: use the existing CAD snapshot reader
on its retained DXF; require the exact complete set of unverified context nodes,
stable IDs, tags, INSERT handles and attributes before applying the explicit
mapping. Retain source bytes/hash checks, no guessed mapping, no relationships
and draft drawing-reference status. Do not change cad_handoff.py, the value
patcher, independent byte verifier or historical outputs. Document the existing
pinned CAD dependency required for this re-read.

After the change, rerun the complete CAD test module, replay the existing
projection/context revision workflow and check that unchanged valid projections
remain identical. This establishes local projection integrity, not installed
state, source authority, reverse synchronization or engineering approval.
