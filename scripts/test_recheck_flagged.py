"""A412 re-check: only flagged symbols can change, nothing is added, every change is recorded, links are diffed."""
import unittest

import recheck_flagged as rf


def sym(i, cls="valve", box=(0, 0, 10, 10), conf=0.9):
    return {"id": i, "class": cls, "tag": None, "bbox": {"x_min": box[0], "y_min": box[1], "x_max": box[2],
                                                         "y_max": box[3]}, "confidence": conf}


def with_box(symbols):
    return rf.symbols_with_box({"symbols": symbols})


class ApplyAnswers(unittest.TestCase):
    def setUp(self):
        self.syms = with_box([sym("a"), sym("b", box=(100, 100, 110, 110)), sym("c", box=(200, 200, 210, 210)),
                              sym("d", box=(1, 1, 11, 11), conf=0.5), sym("e", box=(300, 300, 310, 310))])

    def test_unflagged_symbols_are_untouched_even_if_answered(self):
        out, recs = rf.apply_answers(self.syms, {"b": ["tier red"]},
                                     {"a": {"verdict": "reject", "confidence": 1.0},
                                      "b": {"verdict": "confirm", "confidence": 1.0}})
        self.assertEqual([s["id"] for s in out], ["a", "b", "c", "d", "e"])
        self.assertEqual([r["id"] for r in recs], ["b"])
        self.assertTrue(all("box" not in s for s in out))

    def test_confident_changes_apply_and_are_recorded(self):
        flags = {"b": ["x"], "c": ["x"], "e": ["x"]}
        answers = {"b": {"verdict": "correct", "class": "instrumentation", "confidence": 0.9},
                   "c": {"verdict": "reject", "confidence": 0.95},
                   "e": {"verdict": "reject", "confidence": 0.5}}
        out, recs = rf.apply_answers(self.syms, flags, answers)
        by_id = {s["id"]: s for s in out}
        self.assertEqual(by_id["b"]["class"], "instrumentation")
        self.assertNotIn("c", by_id)
        self.assertIn("e", by_id)  # below the threshold: unchanged
        rec = {r["id"]: r for r in recs}
        self.assertEqual((rec["b"]["before"]["class"], rec["b"]["after"]["class"], rec["b"]["applied"]),
                         ("valve", "instrumentation", True))
        self.assertEqual((rec["c"]["after"]["kept"], rec["c"]["applied"]), (False, True))
        self.assertFalse(rec["e"]["applied"])

    def test_invalid_or_missing_answers_change_nothing(self):
        flags = {"b": ["x"], "c": ["x"], "e": ["x"]}
        answers = {"b": {"verdict": "correct", "class": "spaceship", "confidence": 1.0},
                   "c": {"verdict": "add", "confidence": 1.0}}
        out, recs = rf.apply_answers(self.syms, flags, answers)
        self.assertEqual(out, [{k: v for k, v in s.items() if k != "box"} for s in self.syms])
        self.assertFalse(any(r["applied"] for r in recs))
        self.assertEqual({r["id"] for r in recs}, set(flags))

    def test_a_duplicate_pair_never_loses_both(self):
        flags = {"a": ["dup_box"], "d": ["dup_box"]}
        answers = {"a": {"verdict": "duplicate", "confidence": 0.9}, "d": {"verdict": "duplicate", "confidence": 0.9}}
        out, recs = rf.apply_answers(self.syms, flags, answers)
        ids = {s["id"] for s in out}
        self.assertEqual(len(ids & {"a", "d"}), 1)
        self.assertIn("a", ids)  # the less sure detection (d, 0.5) goes first


class LinkChanges(unittest.TestCase):
    def test_links_added_by_retrace_are_reported(self):
        before = [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}, {"from": "c", "to": "d"}]
        after = [{"from": "c", "to": "d"}, {"from": "a", "to": "d"}]
        lc = rf.link_changes(before, after, ["b"])
        self.assertEqual(lc["dropped_with_removed_symbols"], [["a", "b"], ["b", "c"]])
        self.assertEqual(lc["added"], [["a", "d"]])
        self.assertEqual(lc["lost_otherwise"], [])

    def test_held_out_sheets_refused(self):
        with self.assertRaises(SystemExit):
            rf.check_sheets(["6"])


if __name__ == "__main__":
    unittest.main()
