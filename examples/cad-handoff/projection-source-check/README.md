# Keep projected fields tied to the retained drawing

The [plan](PLAN.md) precedes four controls that the old adapter accepts: changed
MODEL, changed INSERT handle, a missing node/mapping and invented verified status.
The DXF bytes and node source hash stay unchanged in each control. The original
adapter and actual [baseline failure](baseline/stderr.txt) are retained.

The repaired tutorial adapter re-reads source.dxf using the existing CAD parser
and requires its complete, exact unverified context before the supplied identity
mapping. Both exposed CP1251 and UTF8/literal-brace two-asset originals project
with every attribute and source byte retained. Use the pinned requirements; this
CAD adapter requires ezdxf, while the subsequent one-map build remains stdlib.

The first combined test run passes 33 methods, but the historical qualification
replay correctly rejects its changed frozen test-module hash. That refusal is
retained in [replay](replay/). The original test module is restored; five new
projection methods live separately in scripts/test_cad_projection.py and the
normal suite includes them. Historical method freezes and acceptance stay exact.
The separated five-method module, 19 runner controls and full original
21-candidate/native/context revision replay pass. A first comparison to committed
fixtures finds the CSV register's checkout line endings differ. Actual old and
repaired producers in the same environment emit six byte-identical files for
both valid before/after projections; the committed CSV records also match.
[Exact and record-level results](UNCHANGED-PROJECTIONS.json) retain that distinction.

```sh
python scripts/test_cad_projection.py -v
python scripts/test_cad_handoff.py -v
```

These checks establish local projection integrity. Fields remain draft drawing
references: installed identity, company source authority, accepted corrections,
reverse synchronization and engineering approval are separate.
