# Why five native paper-layout views were blank

The original sources contain display viewports. Read-only QCAD Professional trial 3.33.1 Qt5 import exposes
zero entities in those five authored layout blocks. Both retained native save formats contain different
paper/main viewport settings instead of the original display viewport. This is real lost layout information,
not merely an informational save-metadata flag or a blank source drawing. Original strict failures remain failures.

All 12 replacement source/candidate pairs were probed. The six public-adapted cases include the working
`text_in_viewports` paper example; this is not a claim that every QCAD layout fails. Source/candidate hashes remain
exact. `evidence.zip` retains 36 records with individual pins in `INVENTORY.json`, including native probe receipts,
raw logs, viewport comparisons and all ten new native PNGs.

The exposed cp1251 source was then used for six **predeclared diagnostic revisions**, with methods and exact
input copies committed before native execution. These are deliberate source changes, not preservation candidates:

| Revision | Native imported display viewport | Actual paper image |
|---|---|---|
| Exact original | Absent | Blank apart from trial-mark fragment |
| Ordinary library save | Absent | Blank apart from trial-mark fragment |
| Add main viewport | Original display bounds `[15, 5, 115, 75]` exposed | Drawing visible through viewport |
| Add main viewport, restore original current handle | Same display bounds exposed | Drawing visible through viewport |
| Change current handle only | Absent | Blank apart from trial-mark fragment |
| Activate layout only | Absent | Blank apart from trial-mark fragment |

This isolates a main-viewport compatibility dependency **among these tested revisions of one exposed source**.
It does not prove a universal CAD rule, general QCAD defect, independently validated repair or a safe automatic
source modification. The primary ezdxf [layout internals](https://ezdxf.readthedocs.io/en/stable/dxfinternals/layout_management.html)
and [API documentation](https://ezdxf.readthedocs.io/en/stable/layouts/layouts.html) differ in how strongly they
state the need for a main viewport. The original frozen fixtures/generator remain unchanged. All failures and
working copies stay available; a future preparation method needs its own declared scope and fresh validation.

The other display experiment also stays failed. Two equal-scale translated long-label source/candidate pairs
retain trial-mark overlap in both positions. The bounds were obtained before font substitution; the long
substituted candidate also reaches the right frame edge, so complete label containment is unproved. All ten
native commands exited zero with unchanged inputs, and all ten images were directly inspected. This is not a
complete readable visual pass. No marks were removed, masked or suppressed; no output pixels were edited.

The fresh UI attempt closed the old expired process and launched a new one. The startup dialog remains.
Two capture attempts failed with `window capture timed out: timed out waiting on channel`; two freshly observed
startup-button clicks failed with `element 6 is not available in cached app state for qcad.exe`. No drawing edit,
save, close or reopen was observed. See `UI-OBSERVATION.json`; no API/render result substitutes for that gate.

From the repository root, with the pinned ezdxf dependency:

```sh
python examples/cad-handoff/qualification/check_diagnosis4.py
```

This offline check verifies both evidence archives, frozen inputs/methods, all 12 saved source/candidate/native
viewport comparisons, five retained losses, six native hypothesis observations and ten original PNGs. An omitted
variant control must fail. It does not run the native editor or establish human/engineering acceptance.
