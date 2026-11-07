# Make a returned drawing reviewable

Use the reusable `cad_handoff.py review` command on your retained original and returned DXFs. This example uses
one fictional drawing and an actual native-engine return. The report explains the failed exchange without waiving
it. All files are local; Python 3.10+ and the pinned ezdxf dependency are sufficient. No CAD account/network is needed.

```sh
python scripts/cad_handoff.py review examples/cad-handoff/source/valve.dxf examples/cad-handoff/native/qcad/returned.dxf --plan examples/cad-handoff/source/edit-plan.json --out out/cad-receiving-review
```

**Expected exit 1** means a complete packet was written with strict differences. Exit 0 means only the existing
strict decoded comparison passed, still not acceptance. Exit 2 is a preparation/input failure. Open REPORT.html
offline, or read [the saved Markdown report](worked/REPORT.md). Keep the whole packet for working source links.

The report separates:

- Supplied stable identities and every attribute value, including the three observed planned edits and foreign fields.
- Layout/block records and explicit drawing fields, showing the new paper-space viewport, changed style references
  and added explicit width/attribute-definition flags in this return. Missing versus present values stay distinct.
- Named layers/styles/table fields and each changed header value.
- Every strict entity difference, partitioned into added handles (262), removed handles (53), same-type changes (17)
  and reused handle/different type (1). These 333 entity differences plus version and header are the original 335.

These are review observations. It does not infer equivalence from geometry or match renamed handles. Explicit
fields omit complex entity payloads and XDATA; those stay in the strict queue. Named table fields do not cover
complete linetype patterns/style behavior. Counts of added/removed handles are not counts of physical assets or
proved engineering losses. No green interpretation/release badge is generated. Rendering, opaque content and native
project databases need their own receiving checks. [All original limits](../README.md) continue to apply.

The packet retains exact before/after drawing bytes, parsed supplied plan values, complete strict comparison,
compact review data, readable reports and a hash receipt with method/Python/ezdxf versions. Hashes are not signatures
or a full environment lock. New runs require unused output folders and cannot overwrite earlier packets or sources.
If the source changes during inspection, the tool refuses publication. Nothing is written into a context map.

The [new controls first failed](before.txt) against the old implementation. The updated module passes 14 test methods,
including moved geometry, changed layer/foreign value, missing planned edit, lost XDATA, renamed handle, malformed
plan, output collision and escaped report text. These are exposed software checks, not an independent engineering
review. CI replays the actual saved native return and the [explicit R2000 attempt](../native/qcad-r15/README.md),
whose 344 differences remain a failed preservation result too. No human effort or company acceptance was measured.

A receiver/reviewer can now point to exact changed fields and original rows before applying the
[interactive checklist](../RECEIVING_CHECK.md). The classification does not complete that checklist.

[Actual two-command replay evidence](replay.json) records both expected failure exits and 15 exposed packet/input conditions. Replay it yourself with `python examples/cad-handoff/receiving-review/reproduce.py --out out/cad-receiving-controls`.
