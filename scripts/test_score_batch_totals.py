"""The frozen feed-total scorer and the industrial-yeast case runner: known answers, refusals, no key leak."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import batch_analysis
import industrial_yeast_case as case
import score_batch_totals as sbt

ROOT = Path(__file__).resolve().parents[1]


def key(level="batch", items=None):
    return {"schema": sbt.KEY_SCHEMA, "source": "test", "split": "development", "level": level, "signal": "F",
            "unit": "kg", "tolerance_kg": 0.5,
            "items": items or [{"id": "A", "batch_id": "A", "start_s": 0, "end_s": 7200, "logged_delta_kg": 6},
                               {"id": "B", "batch_id": "B", "start_s": 0, "end_s": 7200, "logged_delta_kg": 9}]}


def plan(interpolation="next", unit="kg/h"):
    return {"schema": "batch-analysis-2",
            "context": {k: "test" for k in ("site_id", "asset_id", "model_revision", "recipe_id", "recipe_revision")},
            "max_gap_s": 3600,
            "signals": {"F": {"unit": unit, "asset_id": "feed", "source_ref": "test", "interpolation": interpolation,
                              "quality": None}},
            "windows": [{"id": b, "batch_id": b, "phase": "all", "start_s": 0, "end_s": 7200, "source_ref": "t"}
                        for b in ("A", "B")]}


# An hourly-total log: hour 0 blank, then the feed of the hour that just ended. A: 2 + 4 = 6 kg; B: 4 + 5 = 9 kg.
CSV = b"batch_id,time_s,F\nA,0,\nA,3600,2\nA,7200,4\nB,0,\nB,3600,4\nB,7200,5\n"


def report(interpolation="next", unit="kg/h"):
    return batch_analysis.analyze(CSV, json.dumps(plan(interpolation, unit)).encode())


class Scorer(unittest.TestCase):
    def test_next_hold_report_matches_the_logged_cumulative(self):
        s = sbt.score(key(), report())
        self.assertEqual((s["matched"], s["answered"], s["items"]), (2, 2, 2))
        self.assertEqual(s["mean_abs_error_kg"], 0)

    def test_wrong_methods_and_units_do_not_match(self):
        self.assertEqual(sbt.score(key(), report("linear"))["answered"], 0)    # hour 0 blank: incomplete
        self.assertEqual(sbt.score(key(), report("previous"))["answered"], 0)
        wrong = sbt.score(key(), report("next", "kg/s"))
        self.assertEqual((wrong["matched"], wrong["answered"]), (0, 2))
        energy = sbt.score(key(), report("next", "kW"))                       # kWh is not the key's kg
        self.assertEqual(energy["answered"], 0)

    def test_tolerance_is_half_a_kilogram_inclusive(self):
        for delta, ok in ((0.5, True), (-0.5, True), (0.5001, False)):
            k = key()
            k["items"][0]["logged_delta_kg"] = 6 + delta
            self.assertEqual(sbt.score(k, report())["rows"][0]["matched"], ok, delta)

    def test_a_window_must_match_its_key_item_exactly(self):
        r = report()
        r["windows"][0]["end_s"] = 3600
        self.assertIsNone(sbt.answers(key(), r)["A"])
        r = report()
        r["windows"][1]["batch_id"] = "A"
        self.assertIsNone(sbt.answers(key(), r)["B"])
        r = report()
        r["windows"].append(copy.deepcopy(r["windows"][0]))
        with self.assertRaises(ValueError):
            sbt.score(key(), r)

    def test_controls_known_answers_and_named_weaknesses(self):
        c = sbt.controls(key())
        self.assertEqual(list(c), list(sbt.CONTROL_ORDER))
        self.assertEqual(c["perfect"]["match_rate"], 1)
        self.assertEqual((c["empty"]["matched"], c["empty"]["answered"]), (0, 0))
        self.assertEqual([r["answer_kg"] for r in c["shuffled"]["rows"]], [9, 6])
        self.assertEqual([r["answer_kg"] for r in c["recipe_constant"]["rows"]], [22700, 22700])
        hourly = key("hourly", [{"id": f"A-h{k}", "batch_id": "A", "start_s": (k - 1) * 3600, "end_s": k * 3600,
                                 "logged_delta_kg": 1} for k in (1, 2)])
        self.assertEqual([r["answer_kg"] for r in sbt.controls(hourly)["recipe_constant"]["rows"]], [11350, 11350])

    def test_key_and_input_refusals(self):
        bad = []
        for field, value in (("schema", "x"), ("level", "daily"), ("tolerance_kg", 5), ("unit", "g"), ("items", [])):
            k = key(); k[field] = value; bad.append(k)
        k = key(); k["items"][1]["id"] = "A"; bad.append(k)
        k = key(); k["items"][0]["logged_delta_kg"] = float("nan"); bad.append(k)
        k = key(); k["items"][0]["end_s"] = 0; bad.append(k)
        k = key(); k["items"][0]["extra"] = 1; bad.append(k)
        for k in bad:
            with self.subTest(key=k), self.assertRaises(ValueError):
                sbt.validate_key(k)
        p = plan(); p["windows"].pop()
        with self.assertRaises(ValueError):
            sbt.check_input(key(), p)
        p = plan(); p["signals"]["total_fermentable_sugar_kg"] = p["signals"]["F"]
        with self.assertRaisesRegex(ValueError, "withheld"):
            sbt.check_input(key(), p)

    def test_decision_rule(self):
        def level(m, others):
            return {"method": {"match_rate": m}, "controls": {n: {"match_rate": v} for n, v in others.items()}}
        kept, why = sbt.decide({"batch": level(1.0, {"perfect": 1.0, "recipe_constant": 0.6}),
                                "hourly": level(0.96, {"perfect": 1.0, "shuffled": 0.0})})
        self.assertTrue(kept, why)
        kept, why = sbt.decide({"batch": level(0.6, {"recipe_constant": 0.6}), "hourly": level(1.0, {})})
        self.assertFalse(kept)
        self.assertEqual(len(why), 2)
        kept, _ = sbt.decide({"batch": level(1.0, {}), "hourly": level(0.94, {})})
        self.assertFalse(kept)

    def test_benchmark_counts(self):
        counts, diag = sbt.benchmark_counts(key(), report("next", "kg/s"))
        self.assertEqual(counts, {"batch_feed_totals": {"tp": 0, "predicted": 2, "truth": 2}})
        self.assertEqual(len(diag["mismatched_or_unanswered"]), 2)


class CaseRunner(unittest.TestCase):
    ROWS = {"B01": [{"batch_id": "B01", "time_h": "0", case.FEED: "", case.KEY_COLUMN: "300"},
                    {"batch_id": "B01", "time_h": "1", case.FEED: "389", case.KEY_COLUMN: "689"},
                    {"batch_id": "B01", "time_h": "2", case.FEED: "560.5", case.KEY_COLUMN: "1249.5"}]}

    def test_tool_input_never_carries_the_key_column(self):
        raw = case.tool_csv(self.ROWS)
        self.assertEqual(raw.decode().splitlines()[0], f"batch_id,time_s,{case.FEED}")
        self.assertNotIn(b"1249.5", raw)
        self.assertNotIn(b"689", raw)
        self.assertEqual(raw.decode().splitlines()[1], "B01,0,")
        self.assertEqual(case.tool_csv(self.ROWS, zero_start=True).decode().splitlines()[1], "B01,0,0")

    def test_windows_keys_and_logged_sums(self):
        k = case.key(self.ROWS, "batch", "development")
        self.assertEqual(k["items"], [{"id": "B01", "batch_id": "B01", "start_s": 0, "end_s": 7200,
                                       "logged_delta_kg": 949.5}])
        h = case.key(self.ROWS, "hourly", "development")
        self.assertEqual([i["logged_delta_kg"] for i in h["items"]], [389, 560.5])
        self.assertEqual(case.logged_sum(self.ROWS, "batch"), {"B01": 949.5})
        p = case.plan(self.ROWS, "hourly", "next", "kg/h")
        sbt.check_input(h, p)
        report = batch_analysis.analyze(case.tool_csv(self.ROWS), json.dumps(p).encode())
        self.assertEqual(sbt.score(h, report)["matched"], 2)

    def test_fractional_hours_and_blank_key_refuse(self):
        with self.assertRaises(ValueError):
            case.seconds("0.0001", "B01")
        rows = copy.deepcopy(self.ROWS)
        rows["B01"][2][case.KEY_COLUMN] = ""
        with self.assertRaises(ValueError):
            case.key(rows, "batch", "development")

    def test_split_comes_from_the_dated_plan(self):
        self.assertEqual(case.split_batches("development"), ["B01", "B02", "B03", "B04", "B05"])
        self.assertEqual(case.split_batches("held-out"), ["B06", "B07", "B08", "B09", "B10"])

    def test_changed_original_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in (case.SERIES, case.META):
                (Path(tmp) / name).write_bytes(b"batch_id\n")
            with self.assertRaisesRegex(ValueError, "corpus_pins"):
                case.pinned(tmp)

    @unittest.skipUnless((case.EXTERNAL / case.SERIES).is_file(), "industrial-yeast originals not fetched "
                         "(python scripts/fetch_corpus.py industrial-yeast)")
    def test_development_rerun_matches_committed_results(self):
        if not (case.RESULTS / "development").is_dir():
            self.skipTest("no committed development results")
        done = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/industrial_yeast_case.py"), "--split",
                               "development", "--check"], capture_output=True, text=True, timeout=300)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
