# Control loops and signals, read from the drawing-set bundle (round 6, increment 3)

Development sets only. Every number is read from the `control_loops` block of the `plant_model.json` that `scripts/import_drawing_set.py` wrote (`scripts/loop_score.py`), against `data/te_control_loops.json` (19 running loops: 11 valve loops, 8 cascades). A loop counts when a confirmed loop has the key's controller, measurement and output; P = share of confirmed loops that are a key loop. TE sheets are drawn by this repository from its own model, so TE scores are upper bounds for clean drawings.

Each scored run has two rows: **strict** first (the default consumer filter: relations and loops at tier `traced_through_crossing` dropped), then **every tier** (everything asserted, crossing tier included).

| Set | Run | View | Confirmed / loops | Valve loops | Cascades | Loop P | Sensor P / R | Final element P / R | Cascade P / R | Shuffled roles, 10 seeds (loop R; P mean, range) | Tag-only (loop R / P) | Empty | Rest of bundle unchanged |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| te-a | key symbols + tracer | strict | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | key symbols + tracer | every tier | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r1/claude | strict | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r1/claude | every tier | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r1/codex | strict | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r1/codex | every tier | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r2/claude | strict | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r2/claude | every tier | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r2/codex | strict | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r2/codex | every tier | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r3/claude | strict | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r3/claude | every tier | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r3/codex | strict | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r3/codex | every tier | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r4/claude | strict | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r4/claude | every tier | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r4/codex | strict | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r4/codex | every tier | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r5/claude | strict | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r5/claude | every tier | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r5/codex | strict | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r5/codex | every tier | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-d | key symbols + tracer | strict | 10 / 20 | 7/11 | 3/8 | 1.0 | 1.0 / 0.526 | 1.0 / 0.636 | 1.0 / 0.375 | 0.069 (0.0-0.158); 0.625 (0.0-1.0, 10 of 10 seeds assert any) | 0.579 / 0.55 | 0.0 | True |
| te-d | key symbols + tracer | every tier | 19 / 20 | 11/11 | 8/8 | 1.0 | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 1.0 | 0.069 (0.0-0.158); 0.625 (0.0-1.0, 10 of 10 seeds assert any) | 0.579 / 0.55 | 0.0 | True |
| open100 | r2-tiles-trace/claude | - | 0 / 0 | no key | no key | - | - | - | - | - | - | - | True |
| open100 | r2-tiles-trace/codex | - | 0 / 0 | no key | no key | - | - | - | - | - | - | - | True |
| open100 | r2-tiles-trace/gemini | - | 0 / 0 | no key | no key | - | - | - | - | - | - | - | True |

Recall at four levels (loop R / P): strictly traced (asserted, dropping tier `traced_through_crossing`); asserted (confirmed loops, every tier); asserted plus every review candidate (`candidate_loops`) counted as if confirmed; the tag-only control.

| Set | Run | Strictly traced | Asserted | Asserted + candidates | Tag-only |
|---|---|---|---|---|---|
| te-a | key symbols + tracer | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / 0.0 |
| te-a | te-clean-trace-r1/claude | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / 0.0 |
| te-a | te-clean-trace-r1/codex | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / 0.0 |
| te-a | te-clean-trace-r2/claude | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / 0.0 |
| te-a | te-clean-trace-r2/codex | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / 0.0 |
| te-a | te-clean-trace-r3/claude | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / 0.0 |
| te-a | te-clean-trace-r3/codex | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / 0.0 |
| te-a | te-clean-trace-r4/claude | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / 0.0 |
| te-a | te-clean-trace-r4/codex | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / 0.0 |
| te-a | te-clean-trace-r5/claude | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / 0.0 |
| te-a | te-clean-trace-r5/codex | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / None (0/11, 0/8) | 0.0 / 0.0 |
| te-d | key symbols + tracer | 0.526 / 1.0 (7/11, 3/8) | 1.0 / 1.0 (11/11, 8/8) | 1.0 / 1.0 (11/11, 8/8) | 0.579 / 0.55 |

Diagnostic, TE revision D: `signal_to` pairs against the drawn signal lines of the key (`signal_edges`, cross-sheet flags followed), unordered, by tag.

| Run | Asserted | Correct | Drawn | P | R |
|---|---|---|---|---|---|
| key symbols + tracer | 38 | 38 | 38 | 1.0 | 1.0 |

## Spread (runs, then sheets)

```
{
 "te-a": {
  "runs_attempted": 11,
  "runs_scored": 11,
  "bundle_identical_without_loops": true,
  "controller_recall": {
   "n": 11,
   "mean": 0.0,
   "min": 0.0,
   "max": 0.0,
   "sd": 0.0
  },
  "controller_precision": null,
  "sensor_recall": {
   "n": 11,
   "mean": 0.0,
   "min": 0.0,
   "max": 0.0,
   "sd": 0.0
  },
  "sensor_precision": null,
  "final_recall": {
   "n": 11,
   "mean": 0.0,
   "min": 0.0,
   "max": 0.0,
   "sd": 0.0
  },
  "final_precision": null,
  "cascade_recall": {
   "n": 11,
   "mean": 0.0,
   "min": 0.0,
   "max": 0.0,
   "sd": 0.0
  },
  "cascade_precision": null,
  "loop_recall": {
   "n": 11,
   "mean": 0.0,
   "min": 0.0,
   "max": 0.0,
   "sd": 0.0
  },
  "loop_precision": null,
  "loop_recall_by_sheet": null,
  "controls_shuffled_roles_over_seeds": [
   {
    "seeds": [
     0,
     1,
     2,
     3,
     4,
     5,
     6,
     7,
     8,
     9
    ],
    "loop_recall": {
     "n": 10,
     "mean": 0.0,
     "min": 0.0,
     "max": 0.0,
     "sd": 0.0
    },
    "loop_precision": null,
    "loops_asserted": {
     "n": 10,
     "mean": 0,
     "min": 0,
     "max": 0,
     "sd": 0.0
    }
   },
   {
    "seeds": [
     0,
     1,
     2,
     3,
     4,
     5,
     6,
     7,
     8,
     9
    ],
    "loop_recall": {
     "n": 10,
     "mean": 0.0,
     "min": 0.0,
     "max": 0.0,
     "sd": 0.0
    },
    "loop_precision": null,
    "loops_asserted": {
     "n": 10,
     "mean": 0,
     "min": 0,
     "max": 0,
     "sd": 0.0
    }
   },
   {
    "seeds": [
     0,
     1,
     2,
     3,
     4,
     5,
     6,
     7,
     8,
     9
    ],
    "loop_recall": {
     "n": 10,
     "mean": 0.0,
     "min": 0.0,
     "max": 0.0,
     "sd": 0.0
    },
    "loop_precision": null,
    "loops_asserted": {
     "n": 10,
     "mean": 0,
     "min": 0,
     "max": 0,
     "sd": 0.0
    }
   },
   {
    "seeds": [
     0,
     1,
     2,
     3,
     4,
     5,
     6,
     7,
     8,
     9
    ],
    "loop_recall": {
     "n": 10,
     "mean": 0.0,
     "min": 0.0,
     "max": 0.0,
     "sd": 0.0
    },
    "loop_precision": null,
    "loops_asserted": {
     "n": 10,
     "mean": 0,
     "min": 0,
     "max": 0,
     "sd": 0.0
    }
   },
   {
    "seeds": [
     0,
     1,
     2,
     3,
     4,
     5,
     6,
     7,
     8,
     9
    ],
    "loop_recall": {
     "n": 10,
     "mean": 0.0,
     "min": 0.0,
     "max": 0.0,
     "sd": 0.0
    },
    "loop_precision": null,
    "loops_asserted": {
     "n": 10,
     "mean": 0,
     "min": 0,
     "max": 0,
     "sd": 0.0
    }
   },
   {
    "seeds": [
     0,
     1,
     2,
     3,
     4,
     5,
     6,
     7,
     8,
     9
    ],
    "loop_recall": {
     "n": 10,
     "mean": 0.0,
     "min": 0.0,
     "max": 0.0,
     "sd": 0.0
    },
    "loop_precision": null,
    "loops_asserted": {
     "n": 10,
     "mean": 0,
     "min": 0,
     "max": 0,
     "sd": 0.0
    }
   },
   {
    "seeds": [
     0,
     1,
     2,
     3,
     4,
     5,
     6,
     7,
     8,
     9
    ],
    "loop_recall": {
     "n": 10,
     "mean": 0.0,
     "min": 0.0,
     "max": 0.0,
     "sd": 0.0
    },
    "loop_precision": null,
    "loops_asserted": {
     "n": 10,
     "mean": 0,
     "min": 0,
     "max": 0,
     "sd": 0.0
    }
   },
   {
    "seeds": [
     0,
     1,
     2,
     3,
     4,
     5,
     6,
     7,
     8,
     9
    ],
    "loop_recall": {
     "n": 10,
     "mean": 0.0,
     "min": 0.0,
     "max": 0.0,
     "sd": 0.0
    },
    "loop_precision": null,
    "loops_asserted": {
     "n": 10,
     "mean": 0,
     "min": 0,
     "max": 0,
     "sd": 0.0
    }
   },
   {
    "seeds": [
     0,
     1,
     2,
     3,
     4,
     5,
     6,
     7,
     8,
     9
    ],
    "loop_recall": {
     "n": 10,
     "mean": 0.0,
     "min": 0.0,
     "max": 0.0,
     "sd": 0.0
    },
    "loop_precision": null,
    "loops_asserted": {
     "n": 10,
     "mean": 0,
     "min": 0,
     "max": 0,
     "sd": 0.0
    }
   },
   {
    "seeds": [
     0,
     1,
     2,
     3,
     4,
     5,
     6,
     7,
     8,
     9
    ],
    "loop_recall": {
     "n": 10,
     "mean": 0.0,
     "min": 0.0,
     "max": 0.0,
     "sd": 0.0
    },
    "loop_precision": null,
    "loops_asserted": {
     "n": 10,
     "mean": 0,
     "min": 0,
     "max": 0,
     "sd": 0.0
    }
   },
   {
    "seeds": [
     0,
     1,
     2,
     3,
     4,
     5,
     6,
     7,
     8,
     9
    ],
    "loop_recall": {
     "n": 10,
     "mean": 0.0,
     "min": 0.0,
     "max": 0.0,
     "sd": 0.0
    },
    "loop_precision": null,
    "loops_asserted": {
     "n": 10,
     "mean": 0,
     "min": 0,
     "max": 0,
     "sd": 0.0
    }
   }
  ],
  "controls_loop_recall": {
   "perfect": {
    "n": 11,
    "mean": 1.0,
    "min": 1.0,
    "max": 1.0,
    "sd": 0.0
   },
   "empty": {
    "n": 11,
    "mean": 0.0,
    "min": 0.0,
    "max": 0.0,
    "sd": 0.0
   },
   "shuffled_roles": {
    "n": 11,
    "mean": 0.0,
    "min": 0.0,
    "max": 0.0,
    "sd": 0.0
   },
   "tag_only": {
    "n": 11,
    "mean": 0.0,
    "min": 0.0,
    "max": 0.0,
    "sd": 0.0
   }
  },
  "controls_loop_precision": {
   "perfect": {
    "n": 11,
    "mean": 1.0,
    "min": 1.0,
    "max": 1.0,
    "sd": 0.0
   },
   "empty": null,
   "shuffled_roles": null,
   "tag_only": {
    "n": 11,
    "mean": 0.0,
    "min": 0.0,
    "max": 0.0,
    "sd": 0.0
   }
  }
 },
 "te-d": {
  "runs_attempted": 1,
  "runs_scored": 1,
  "bundle_identical_without_loops": true,
  "controller_recall": {
   "n": 1,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "controller_precision": {
   "n": 1,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "sensor_recall": {
   "n": 1,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "sensor_precision": {
   "n": 1,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "final_recall": {
   "n": 1,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "final_precision": {
   "n": 1,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "cascade_recall": {
   "n": 1,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "cascade_precision": {
   "n": 1,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "loop_recall": {
   "n": 1,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "loop_precision": {
   "n": 1,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "loop_recall_by_sheet": {
   "n": 3,
   "mean": 1.0,
   "min": 1.0,
   "max": 1.0,
   "sd": 0.0
  },
  "controls_shuffled_roles_over_seeds": [
   {
    "seeds": [
     0,
     1,
     2,
     3,
     4,
     5,
     6,
     7,
     8,
     9
    ],
    "loop_recall": {
     "n": 10,
     "mean": 0.069,
     "min": 0.0,
     "max": 0.158,
     "sd": 0.056
    },
    "loop_precision": {
     "n": 10,
     "mean": 0.625,
     "min": 0.0,
     "max": 1.0,
     "sd": 0.403
    },
    "loops_asserted": {
     "n": 10,
     "mean": 2,
     "min": 1,
     "max": 4,
     "sd": 1.155
    }
   }
  ],
  "controls_loop_recall": {
   "perfect": {
    "n": 1,
    "mean": 1.0,
    "min": 1.0,
    "max": 1.0,
    "sd": 0.0
   },
   "empty": {
    "n": 1,
    "mean": 0.0,
    "min": 0.0,
    "max": 0.0,
    "sd": 0.0
   },
   "shuffled_roles": {
    "n": 1,
    "mean": 0.105,
    "min": 0.105,
    "max": 0.105,
    "sd": 0.0
   },
   "tag_only": {
    "n": 1,
    "mean": 0.579,
    "min": 0.579,
    "max": 0.579,
    "sd": 0.0
   }
  },
  "controls_loop_precision": {
   "perfect": {
    "n": 1,
    "mean": 1.0,
    "min": 1.0,
    "max": 1.0,
    "sd": 0.0
   },
   "empty": null,
   "shuffled_roles": {
    "n": 1,
    "mean": 0.667,
    "min": 0.667,
    "max": 0.667,
    "sd": 0.0
   },
   "tag_only": {
    "n": 1,
    "mean": 0.55,
    "min": 0.55,
    "max": 0.55,
    "sd": 0.0
   }
  }
 },
 "open100": {
  "runs_attempted": 3,
  "runs_scored": 3,
  "bundle_identical_without_loops": true,
  "confirmed_loops": {
   "n": 3,
   "mean": 0,
   "min": 0,
   "max": 0,
   "sd": 0.0
  },
  "signal_to": {
   "n": 3,
   "mean": 0,
   "min": 0,
   "max": 0,
   "sd": 0.0
  }
 }
}
```
