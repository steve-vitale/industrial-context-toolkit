# Crossing evaluator scorecard (development)

Judge: claude / claude-opus-5-5; bar 0.8; prompt sha256 df3e18650ae9. assert_enabled: **False**.

| Run | Set | n | answered at bar | correct | accuracy | can't tell or below bar | supported 'continues' |
|---|---|---|---|---|---|---|---|
| 1 | true_crossings_te_d | 13 | 4 | 4 | 1.0 | 9 | 4 |
| 1 | false_merges_sweep | 10 | 3 | 0 | 0.0 | 7 | 3 |
| 1 | fixtures_true | 1 | 0 | 0 | None | 1 | 0 |
| 1 | fixtures_false | 0 | 0 | 0 | None | 0 | 0 |
| 2 | true_crossings_te_d | 13 | 4 | 4 | 1.0 | 9 | 4 |
| 2 | false_merges_sweep | 10 | 3 | 0 | 0.0 | 7 | 3 |
| 2 | fixtures_true | 1 | 0 | 0 | None | 1 | 0 |
| 2 | fixtures_false | 0 | 0 | 0 | None | 0 | 0 |

| Run | Calls | Seconds | Errors | Controls (verdict, confidence) |
|---|---|---|---|---|
| 1 | 4 | 139.2 | 0 | obvious_separate_ends: cannot_tell 0.45; blank: cannot_tell 0.95; obvious_crossing: continues 0.8 |
| 2 | 4 | 129.0 | 0 | obvious_separate_ends: continues 0.45; blank: cannot_tell 0.95; obvious_crossing: continues 0.75 |
