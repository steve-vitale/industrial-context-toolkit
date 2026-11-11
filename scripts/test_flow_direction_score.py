"""The round-6 flow-direction scorer's reporting: refused readings are rows, not crashes; held-out sets refuse."""
import contextlib
import io
import unittest

import flow_direction_score as fds


def scored(share, precision=None):
    run = {"line_layers": "added", "flow_direction": {"conflict": 1}, "pipe_segments": 10, "directed": int(share * 10),
           "share": share, "per_sheet": {"0": {"pipe_segments": 10, "directed": int(share * 10), "share": share}}}
    if precision is not None:
        controls = {c: {"precision": v} for c, v in (("perfect", 1.0), ("reversed", 1 - precision), ("layout", 0.5))}
        total = {"precision": precision, "correct": 2, "directed": 2, "controls": controls}
        run["direction_vs_truth"] = {"total": total, "sheets": {"101": total}}
    return run


class Reporting(unittest.TestCase):
    def doc(self):
        sets = {"open100": {"truth": None, "runs": {"r2-tiles-trace/claude": scored(0.3),
                                                    "r2-tiles-trace/gemini": {"refused_by_intake": "a failed\nrecord"}}},
                "te-a": {"truth": "streams", "runs": {"key": scored(0.8, 1.0)}}}
        return {"sets": sets, "summary": fds.summarize(sets)}

    def test_mixed_scored_and_refused_runs_render_and_are_counted(self):
        doc = self.doc()
        s = doc["summary"]["open100"]
        self.assertEqual((s["runs_attempted"], s["runs_scored"], s["runs_refused_by_intake"]), (2, 1, 1))
        self.assertEqual(s["refused"], ["r2-tiles-trace/gemini"])
        self.assertEqual(s["share_directed"]["n"], 1)  # the refused run is not averaged in as a zero
        page = fds.markdown(doc)
        self.assertIn("| open100 | r2-tiles-trace/gemini | refused by the intake: a failed record |", page)
        self.assertIn("open100 1 scored of 2 attempted, 1 refused", page)
        self.assertIn("| te-a | key | 10 | 8 | 1 | 0.8 | 1.0 (2/2) |", page)

    def test_held_out_or_unknown_sets_are_refused_before_any_input_is_read(self):
        for name in ("open100-holdout", "dexpi-holdout", "pahala-p204"):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as stop:
                fds.main(["--sets", name, "--out", "unused"])
            self.assertEqual(stop.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
