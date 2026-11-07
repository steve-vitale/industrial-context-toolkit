# How much of a native return is demonstrably handle renaming?

The frozen diagnostic audits **all 42 retained native default/R15 returns**, beside their 21 source-preserving
candidates. It proves a limited exact decoded correspondence for some records; it does **not** establish that
the full native differences are only handle churn. All 42 native failures and every strict difference remain.

The [plan](../CORRESPONDENCE-5-PLAN.md) and 39 authored decoded-graph controls were committed at `e62e8d1`
before implementation. The [matcher/checker/runner freeze](../CORRESPONDENCE-5-FREEZE.json) was committed at
`e89ad4b` before this whole retained cohort ran. Inputs were already exposed; this is failure diagnosis, not a
fresh validation or a new CAD-preservation method. The original protocol, strict comparator, value patcher,
sources and returned DXFs are unchanged. No native application or model was called.

## Reproduce

From the repository root, with the pinned ezdxf dependency:

```sh
python examples/cad-handoff/qualification/check_correspondence5.py

# Optional: new complete report directory, including verified prior inputs.
python examples/cad-handoff/qualification/run_correspondence5.py --out out/cad-correspondence-local
```

The check verifies both archives and frozen methods, runs all 39 authored controls, reproduces all 63 reports,
and inspects every reported pair directly without calling the matcher's signature/pruning functions. Its own
code is separate, but both are agent-authored software checks, not independent engineering review. Fabricated
pair and omitted-report controls must refuse. It does not launch a CAD application or fill a UI/visual gate.

## What “correspondence” establishes

Every literal ordered tag value must match after applying only the supplied attribute plan. Only own handles
and declared pointer values may be renamed. A candidate body must be unique on both sides, and every nonzero
pointer must target another verified pair. Ambiguity, identical dangling references, changed defaults, geometry,
style names, foreign fields and unknown data remain unpaired. XDATA 1005 and arbitrary 320–329 handles remain
literal; this diagnostic does not claim their application semantics or physical identity are preserved.

The result retains all source/return handles and reasons for unpaired records. Every original strict index gets
separate before/after-side evidence, so a reused handle cannot conceal two different records. No strict row is
marked resolved, removed or subtracted. Headers/version differences remain exact. See the
[summary](summary.json) and [per-report archive inventory](INVENTORY.json); `evidence.zip` contains every full
report. Reports link by SHA to the original source/return/plan and retained strict comparison in round 2.

| Retained route | Cases | Strict differences, still retained | Unique literal-body seeds | Closed exact decoded pairs |
|---|---:|---:|---:|---:|
| Source-preserving candidate | 21 | 0 | 1,820 | 586 |
| Native default save | 21 | 7,991 | 558 | 307 |
| Native R15 save | 21 | 8,218 | 509 | 276 |

Counts aggregate record occurrences across related cases/routes, not independent equipment, plants or trials.
The rule leaves **1,719 before-side records unpaired even in the exact source-preserving controls**: duplicate
bodies and dependent reference ambiguity prevent unique proof. Unpaired therefore means *not proved by this
diagnostic*, not automatically lost/changed engineering content. The frozen rule was not relaxed to raise coverage.

## Follow one source to its changes

The original valve's default return still has **335 strict differences**. Thirteen records have a closed exact
decoded correspondence: nine TABLE, two LTYPE, one STYLE and one APPID record. These limited results explain
some identifier rewriting; they do not qualify the asset, drawing or full save. The R15 return retains 344
differences and fourteen corresponding records.

The same stable asset's MODEL attribute retains handle `3E` and the planned `SRC-2 -> SRC-3` value. Its decoded
return also removes explicit alignment-point codes 11/21/31 (`26.0/28.0/0.0`) and adds text-style code 7
`textstyle3` and code 280 `0`. Its unchanged ICT_ID attribute shows the same non-value changes. These are
explicit serialization/content differences, beyond handle rewriting. Their visual/engineering implications
are not waived as defaults. Original data and strict rows remain in the
[round-2 evidence](../round-2/README.md) and the existing
[receiving review](../../receiving-review/README.md).

## Qualification remains incomplete

The [current UI observation](UI-OBSERVATION.json) records two capture timeouts and two failed clicks on a freshly
observed trial-expiry button. The same window remains live with no document and disabled Save; an observation
timeout was not treated as a terminal process. There is no observed native edit/save/close/reopen or retained
UI-saved return. Earlier trial-mark/readability and native layout failures also remain. The diagnostic advances
explanation of the saved files; it does not fill those original acceptance gates or establish company acceptance.
