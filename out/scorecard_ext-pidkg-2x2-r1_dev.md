# Extraction scorecard: `ext-pidkg-2x2-r1` (split: dev)

Scored against PID2Graph OPEN100 answer keys with `scripts/score_pid2graph.py` (rules fixed before any run; controls in `scripts/test_scorer_controls.py`). F1 with precision/recall.

| Tool | Model | Drawings (failed) | **Review load** (per 100, lower=better) | Rough: found | Rough: found + right class | Strict (IoU≥0.5): found + right class | Connections | Avg s/drawing | Cost |
|---|---|---|---|---|---|---|---|---|---|
| pid-to-kg | claude-opus-5-5[1m] | 6 (0) | **107.7** | 0.75 (P 0.95 / R 0.62) | 0.69 (P 0.87 / R 0.57) | 0.45 (P 0.57 / R 0.37) | 0.35 (P 0.34 / R 0.36) | 284.7 | $0.00 |

## Rough match by class (F1)

| Tool | tank | pump | valve | instrumentation | inlet/outlet | general |
|---|---|---|---|---|---|---|
| pid-to-kg | 0.65 (16) | 0.48 (11) | 0.80 (139) | 0.80 (160) | 0.99 (48) | 0.16 (126) |

Numbers in parentheses in the class table are how many of that class the answer keys contain.
Subscription tools show $0.00; their cost is a flat subscription, not per call.
