# Control loops and signals, read from the drawing-set bundle (round 6, increment 3)

Development sets only. Every number is read from the `control_loops` block of the `plant_model.json` that `scripts/import_drawing_set.py` wrote (`scripts/loop_score.py`), against `data/te_control_loops.json` (19 running loops: 11 valve loops, 8 cascades). A loop counts when a confirmed loop has the key's controller, measurement and output; P = share of confirmed loops that are a key loop. TE sheets are drawn by this repository from its own model, so TE scores are upper bounds for clean drawings.

| Set | Run | Confirmed / loops | Valve loops | Cascades | Loop P | Sensor P / R | Final element P / R | Cascade P / R | Shuffled roles, 10 seeds (loop R; P mean, range) | Tag-only (loop R / P) | Empty | Rest of bundle unchanged |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| te-a | key symbols + tracer | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r1/claude | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r1/codex | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r2/claude | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r2/codex | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r3/claude | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r3/codex | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r4/claude | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r4/codex | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r5/claude | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-a | te-clean-trace-r5/codex | 0 / 1 | 0/11 | 0/8 | - | - / 0.0 | - / 0.0 | - / 0.0 | 0.0 (0.0-0.0); none asserted | 0.0 / - | 0.0 | True |
| te-d | key symbols + tracer | 10 / 20 | 7/11 | 3/8 | 1.0 | 1.0 / 0.526 | 1.0 / 0.636 | 1.0 / 0.375 | 0.037 (0.0-0.105); 0.643 (0.0-1.0, 7 of 10 seeds assert any) | 0.579 / 0.55 | 0.0 | True |
| open100 | r2-tiles-trace/claude | 0 / 0 | no key | no key | - | - | - | - | - | - | - | True |
| open100 | r2-tiles-trace/codex | 0 / 0 | no key | no key | - | - | - | - | - | - | - | True |
| open100 | r2-tiles-trace/gemini | 0 / 0 | no key | no key | - | - | - | - | - | - | - | True |

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
   "mean": 0.526,
   "min": 0.526,
   "max": 0.526,
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
   "mean": 0.526,
   "min": 0.526,
   "max": 0.526,
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
   "mean": 0.636,
   "min": 0.636,
   "max": 0.636,
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
   "mean": 0.375,
   "min": 0.375,
   "max": 0.375,
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
   "mean": 0.526,
   "min": 0.526,
   "max": 0.526,
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
   "mean": 0.546,
   "min": 0.333,
   "max": 0.75,
   "sd": 0.209
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
     "mean": 0.037,
     "min": 0.0,
     "max": 0.105,
     "sd": 0.036
    },
    "loop_precision": {
     "n": 7,
     "mean": 0.643,
     "min": 0.0,
     "max": 1.0,
     "sd": 0.378
    },
    "loops_asserted": {
     "n": 10,
     "mean": 1.1,
     "min": 0,
     "max": 2,
     "sd": 0.876
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
    "mean": 1.0,
    "min": 1.0,
    "max": 1.0,
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
