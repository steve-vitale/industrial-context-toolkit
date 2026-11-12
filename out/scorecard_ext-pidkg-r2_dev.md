# Extraction scorecard: `ext-pidkg-r2` (split: dev)

Scored against PID2Graph OPEN100 answer keys with `scripts/score_pid2graph.py` (rules fixed before any run; controls in `scripts/test_scorer_controls.py`). F1 with precision/recall.

| Tool | Model | Drawings (failed) | **Review load** (per 100, lower=better) | Rough: found | Rough: found + right class | Strict (IoU≥0.5): found + right class | Connections | Avg s/drawing | Cost |
|---|---|---|---|---|---|---|---|---|---|
| pid-to-kg | claude-opus-5-5[1m] | 6 (0) | **112.9** | 0.79 (P 0.94 / R 0.68) | 0.71 (P 0.85 / R 0.62) | 0.46 (P 0.55 / R 0.40) | 0.32 (P 0.30 / R 0.34) | 317.5 | $0.00 |

## Rough match by class (F1)

| Tool | tank | pump | valve | instrumentation | inlet/outlet | general |
|---|---|---|---|---|---|---|
| pid-to-kg | 0.65 (16) | 0.48 (11) | 0.88 (139) | 0.78 (160) | 0.99 (48) | 0.19 (126) |

Numbers in parentheses in the class table are how many of that class the answer keys contain.
Subscription tools show $0.00; their cost is a flat subscription, not per call.
