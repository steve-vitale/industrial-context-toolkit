# A tested equipment-data route that does not need a CAD UI

The [separate acceptance contract](../EXCHANGE-6-PLAN.md) was committed with all six fresh authored inputs/keys
at `179c32d`, before implementation. The exchange tool and test/runner methods were frozen at `da9f427` before
the first case ran. That run stopped after the protective library wrapper correctly refused its R12 baseline;
[the failure receipt](FIRST-ATTEMPT.json) is retained. `0915eaf` changed only baseline capture to retain the raw
library save. The exchange tool, source-preserving writer, strict comparator, input cases and keys stayed exact.
Case 1 is exposed development evidence; the other five first ran in the complete cohort. None is a blind model
test, independently authored plant drawing or new public source family.

The design keeps an immutable DXF plus source-bound equipment-data catalog/form, accepts a returned JSON proposal
and patches only declared attribute spans. It qualifies that file-layer operation, not the unfinished native
UI/visual/full-save gates in the [original protocol](../PROTOCOL.md). Use the [review guide](../../data-review/README.md)
for your own inputs or an agent. A full native CAD return is not an input to this route.

## Results

| Authored case | Coverage | Assets / edits | Sidecar unexpected strict differences | Library-save differences | Unplanned candidate bytes |
|---|---|---:|---:|---:|---:|
| 1 | R12 / cp1252 / CRLF | 1 / 1 | 0 | 77 | 0 |
| 2 | R2000 / transformed blocks / LF | 2 / 2 | 0 | 0 | 0 |
| 3 | R2004 / cp1251 Cyrillic / CRLF | 1 / 1 | 0 | 0 | 0 |
| 4 | R2007 / UTF-8 / tag revision / LF | 3 / 4 | 0 | 0 | 0 |
| 5 | R2013 / paper viewport and label / CRLF | 1 / 1 | 0 | 0 | 0 |
| 6 | R2018 / HTML-special foreign text / long replacement / LF | 1 / 1 | 0 | 0 | 0 |

All six library saves differ from independent raw source-plus-plan reconstruction, including the five with
decoded strict zero. Each saved candidate, raw library baseline and complete strict comparison is retained in
`results/`, alongside response and separate byte-check receipt. [INPUTS.json](INPUTS.json) binds exact source/key
hashes; [summary](results/summary.json) records every case. No geometry tolerance or handle/default waiver is used.

Nine focused tests include actual CLI application, exact downloaded-byte retention, stale/current-catalog checks,
competing revisions, malformed/extra/duplicate/identity/foreign edits, wrong before values, multiline/overlong
values, duplicate identities, binary input, destination collisions and planted geometry/layer/foreign/XDATA loss.
These are same-author software checks; the second byte checker is a separate implementation, not a human reviewer.

The [browser observation](browser/OBSERVATION.json) retains two actual downloaded responses, resulting candidate
files, plans, hashes and mobile screenshots. The fictional valve's three edits survive CLI application and a
freshly prepared form after tab close/reopen. Empty/missing-reason forms refuse. The second input's hostile text
stays literal/read-only and a 190-character value survives. The connector blocked `file:` and its explicit new-tab
call failed; normal loopback navigation succeeded after close. Those failures remain in the receipt. Instrumented
case-6 reload/download made only its local HTML request. No CAD geometry/layout rendering is claimed by this form.

## Reproduce offline

```sh
python scripts/test_cad_exchange.py
python examples/cad-handoff/qualification/check_exchange6.py

# Optional: execute both routes again, preserving a new complete result directory.
python examples/cad-handoff/qualification/run_exchange6.py --out out/my-exchange-six-results
```

The check binds frozen methods/inputs, rebuilds all six sidecar candidates exactly, independently reconstructs
their bytes and re-scores retained library baselines. It also regenerates the sample form/catalog and replays
both actual browser downloads against their retained candidate files. CI does **not** rerun the interactive
browser. Existing 21-candidate and 42-native-return evidence and failures remain untouched. Native CAD visual
acceptance, UI drafting, engineering correctness and authenticated company release are separate, unfinished claims.
