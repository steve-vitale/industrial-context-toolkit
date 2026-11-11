# Flow direction on `piped_to`, read from the drawing-set bundle (round 6, increment 2)

Development sets only. Every number is read from the `plant_model.json` that `scripts/import_drawing_set.py` wrote (`scripts/flow_direction_score.py`). Share = pipe segments with a direction / all pipe segments. Precision = directed segments pointing the truth's way / directed segments the truth directs (TE only). A drawn flow direction is review evidence, not isolation or lockout guidance.

| Set | Run | Pipe segments | Directed | Conflicts | Share | Precision (scored) | Reversed control | Layout control | Arrow detection P / R |
|---|---|---|---|---|---|---|---|---|---|
| open100 | r2-tiles-trace/claude | 295 | 76 | 4 | 0.258 | no truth | - | - | 0.682 / 0.491 |
| open100 | r2-tiles-trace/codex | 400 | 106 | 1 | 0.265 | no truth | - | - | 0.79 / 0.467 |
| open100 | r2-tiles-trace/gemini | 297 | 78 | 4 | 0.263 | no truth | - | - | 0.636 / 0.491 |
| te-a | key symbols + tracer | 41 | 32 | 0 | 0.78 | 1.0 (22/22) | 0.0 | 0.88 | - |
| te-a | te-clean-trace-r1/claude | 42 | 32 | 0 | 0.762 | 1.0 (22/22) | 0.0 | 0.92 | - |
| te-a | te-clean-trace-r1/codex | 42 | 32 | 0 | 0.762 | 1.0 (22/22) | 0.0 | 0.92 | - |
| te-a | te-clean-trace-r2/claude | 42 | 32 | 0 | 0.762 | 1.0 (22/22) | 0.0 | 0.92 | - |
| te-a | te-clean-trace-r2/codex | 42 | 32 | 0 | 0.762 | 1.0 (22/22) | 0.0 | 0.92 | - |
| te-a | te-clean-trace-r3/claude | 42 | 32 | 0 | 0.762 | 1.0 (22/22) | 0.0 | 0.92 | - |
| te-a | te-clean-trace-r3/codex | 42 | 32 | 0 | 0.762 | 1.0 (22/22) | 0.0 | 0.92 | - |
| te-a | te-clean-trace-r4/claude | 42 | 32 | 0 | 0.762 | 1.0 (22/22) | 0.0 | 0.92 | - |
| te-a | te-clean-trace-r4/codex | 42 | 32 | 0 | 0.762 | 1.0 (22/22) | 0.0 | 0.92 | - |
| te-a | te-clean-trace-r5/claude | 42 | 32 | 0 | 0.762 | 1.0 (22/22) | 0.0 | 0.92 | - |
| te-a | te-clean-trace-r5/codex | 42 | 32 | 0 | 0.762 | 1.0 (22/22) | 0.0 | 0.92 | - |
| te-d | key symbols + tracer | 101 | 22 | 0 | 0.218 | 1.0 (16/16) | 0.0 | 0.943 | - |
| pahala | claude reading | 20 | 6 | 0 | 0.3 | no truth | - | - | - |

Diagnostic, TE only: the same directed segments against every drawn route in the drawer's own order (cooling water, steam, the reactor header and the spill-back included; self-generated, not a model truth).

| Set | Run | Directed and scorable | Correct | Precision |
|---|---|---|---|---|
| te-a | key symbols + tracer | 32 | 32 | 1.0 |
| te-a | te-clean-trace-r1/claude | 32 | 32 | 1.0 |
| te-a | te-clean-trace-r1/codex | 32 | 32 | 1.0 |
| te-a | te-clean-trace-r2/claude | 32 | 32 | 1.0 |
| te-a | te-clean-trace-r2/codex | 32 | 32 | 1.0 |
| te-a | te-clean-trace-r3/claude | 32 | 32 | 1.0 |
| te-a | te-clean-trace-r3/codex | 32 | 32 | 1.0 |
| te-a | te-clean-trace-r4/claude | 32 | 32 | 1.0 |
| te-a | te-clean-trace-r4/codex | 32 | 32 | 1.0 |
| te-a | te-clean-trace-r5/claude | 32 | 32 | 1.0 |
| te-a | te-clean-trace-r5/codex | 32 | 32 | 1.0 |
| te-d | key symbols + tracer | 22 | 22 | 1.0 |

Runs per set: open100 3 scored of 3 attempted, 0 refused; te-a 11 scored of 11 attempted, 0 refused; te-d 1 scored of 1 attempted, 0 refused; pahala 1 scored of 1 attempted, 0 refused

## Spread (runs, then sheets)

```
{
 "open100": {
  "runs_attempted": 3,
  "runs_scored": 3,
  "runs_refused_by_intake": 0,
  "share_directed": {
   "n": 3,
   "mean": 0.262,
   "min": 0.258,
   "max": 0.265,
   "sd": 0.004
  },
  "share_directed_by_sheet": {
   "n": 18,
   "mean": 0.272,
   "min": 0.083,
   "max": 0.476,
   "sd": 0.095
  },
  "arrow_detection_precision": {
   "n": 3,
   "mean": 0.703,
   "min": 0.636,
   "max": 0.79,
   "sd": 0.079
  },
  "arrow_detection_recall": {
   "n": 3,
   "mean": 0.483,
   "min": 0.467,
   "max": 0.491,
   "sd": 0.014
  }
 },
 "te-a": {
  "runs_attempted": 11,
  "runs_scored": 11,
  "runs_refused_by_intake": 0,
  "share_directed": {
   "n": 11,
   "mean": 0.764,
   "min": 0.762,
   "max": 0.78,
   "sd": 0.005
  },
  "share_directed_by_sheet": {
   "n": 33,
   "mean": 0.801,
   "min": 0.667,
   "max": 1.0,
   "sd": 0.145
  },
  "precision": {
   "n": 11,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "precision_by_sheet": {
   "n": 33,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "controls_precision": {
   "perfect": {
    "n": 11,
    "mean": 1.0,
    "min": 1.0,
    "max": 1.0,
    "sd": 0.0
   },
   "reversed": {
    "n": 11,
    "mean": 0.0,
    "min": 0.0,
    "max": 0.0,
    "sd": 0.0
   },
   "layout": {
    "n": 11,
    "mean": 0.916,
    "min": 0.88,
    "max": 0.92,
    "sd": 0.012
   }
  }
 },
 "te-d": {
  "runs_attempted": 1,
  "runs_scored": 1,
  "runs_refused_by_intake": 0,
  "share_directed": {
   "n": 1,
   "mean": 0.218,
   "min": 0.218,
   "max": 0.218,
   "sd": 0.0
  },
  "share_directed_by_sheet": {
   "n": 3,
   "mean": 0.22,
   "min": 0.195,
   "max": 0.242,
   "sd": 0.024
  },
  "precision": {
   "n": 1,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "precision_by_sheet": {
   "n": 3,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "controls_precision": {
   "perfect": {
    "n": 1,
    "mean": 1.0,
    "min": 1.0,
    "max": 1.0,
    "sd": 0.0
   },
   "reversed": {
    "n": 1,
    "mean": 0.0,
    "min": 0.0,
    "max": 0.0,
    "sd": 0.0
   },
   "layout": {
    "n": 1,
    "mean": 0.943,
    "min": 0.943,
    "max": 0.943,
    "sd": 0.0
   }
  }
 },
 "pahala": {
  "runs_attempted": 1,
  "runs_scored": 1,
  "runs_refused_by_intake": 0,
  "share_directed": {
   "n": 1,
   "mean": 0.3,
   "min": 0.3,
   "max": 0.3,
   "sd": 0.0
  },
  "share_directed_by_sheet": {
   "n": 2,
   "mean": 0.309,
   "min": 0.286,
   "max": 0.333,
   "sd": 0.033
  }
 }
}
```
