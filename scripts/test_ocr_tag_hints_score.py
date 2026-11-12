"""Scorer and controls for ocr_tag_hints_score.py; no OCR program, public data or model calls."""
import random
import unittest

import ocr_tag_hints_score as s

TRUTH = {"LI401": [{"tag": "LI 401", "box_0_1000": [100, 100, 120, 120]}],
         "FIC101": [{"tag": "FIC 101", "box_0_1000": [500, 500, 530, 520]}]}


class Scoring(unittest.TestCase):
    def test_text_and_located_matches_are_counted_apart(self):
        hints = {"LI401": {"box_0_1000": [102, 102, 118, 118], "confidence": 90},
                 "FIC101": {"box_0_1000": [800, 800, 820, 820], "confidence": 50},   # right text, wrong place
                 "XX999": {"box_0_1000": [0, 0, 5, 5], "confidence": 95}}
        r = s.score(hints, TRUTH)
        self.assertEqual((r["truth"], r["hints"], r["text_tp"], r["located_tp"]), (2, 3, 2, 1))
        self.assertEqual((r["confident_hints"], r["confident_text_tp"]), (2, 1))

    def test_controls_behave_as_designed(self):
        hints = {"LI401": {"box_0_1000": [102, 102, 118, 118]}, "FIC101": {"box_0_1000": [505, 505, 525, 515]}}
        c = s.controls(hints, TRUTH, random.Random(1))
        self.assertEqual(s.prf(c["perfect"])["located_recall"], 1.0)
        self.assertIsNone(s.prf(c["empty"])["text_precision"])
        self.assertEqual(c["random"]["text_tp"], 0)
        self.assertEqual(c["shifted"]["text_tp"], 2)        # the text still matches
        self.assertEqual(c["shifted"]["located_tp"], 0)     # but nowhere near the truth

    def test_held_out_sets_are_refused(self):
        with self.assertRaises(SystemExit) as e:
            s.main(["--sets", "open100-holdout", "--out", "unused"])
        self.assertEqual(e.exception.code, 2)
        self.assertEqual(s.OPEN100_DEV, (0, 1, 2, 3, 4, 5))
        self.assertEqual(sorted(s.PAHALA_PAGES), ["P-401", "P-501"])


if __name__ == "__main__":
    unittest.main()
