# Extraction scorecard: `ext-pidkg-2x2-r2` (split: dev)

Scored against PID2Graph OPEN100 answer keys with `scripts/score_pid2graph.py` (rules fixed before any run; controls in `scripts/test_scorer_controls.py`). F1 with precision/recall.

| Tool | Model | Drawings (failed) | **Review load** (per 100, lower=better) | Rough: found | Rough: found + right class | Strict (IoU≥0.5): found + right class | Connections | Avg s/drawing | Cost |
|---|---|---|---|---|---|---|---|---|---|
| pid-to-kg | claude-opus-5-5[1m] | 6 (0) | **89.1** | 0.79 (P 0.96 / R 0.67) | 0.72 (P 0.88 / R 0.61) | 0.42 (P 0.51 / R 0.36) | 0.46 (P 0.45 / R 0.47) | 267.5 | $0.00 |

## Rough match by class (F1)

| Tool | tank | pump | valve | instrumentation | inlet/outlet | general |
|---|---|---|---|---|---|---|
| pid-to-kg | 0.65 (16) | 0.48 (11) | 0.93 (139) | 0.79 (160) | 0.99 (48) | 0.13 (126) |

Numbers in parentheses in the class table are how many of that class the answer keys contain.
Subscription tools show $0.00; their cost is a flat subscription, not per call.
