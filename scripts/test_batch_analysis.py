"""Analytical oracles and planted failures for recorded phase calculations; stdlib only."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import batch_analysis as tool

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/batch-analysis"


class BatchAnalysis(unittest.TestCase):
    def plan(self, end=3600, unit="kg/h"):
        return {"schema": "batch-analysis-1",
                "context": {key: "test" for key in ("site_id", "asset_id", "model_revision", "recipe_id", "recipe_revision")},
                "max_gap_s": 1800,
                "signals": {"F": {"unit": unit, "asset_id": "vessel", "source_ref": "authored test"}},
                "windows": [{"id": "w", "batch_id": "A", "phase": "feed", "start_s": 0, "end_s": end, "source_ref": "test record"}]}

    def run_case(self, rows, plan=None):
        raw = ("batch_id,time_s,F\n" + rows).encode()
        return tool.analyze(raw, json.dumps(plan or self.plan()).encode())

    def result(self, rows, plan=None):
        return self.run_case(rows, plan)["windows"][0]["signals"]["F"]

    def test_rectangle_and_triangle_oracles(self):
        rectangle = self.result("A,0,2\nA,600,2\nA,1800,2\n", self.plan(end=1800))
        self.assertEqual(rectangle["full_window_integral"], 1)
        self.assertEqual(rectangle["time_weighted_mean_observed"], 2)
        ramp = self.result("A,0,0\nA,1800,2\nA,3600,4\n")
        self.assertEqual(ramp["full_window_integral"], 2)
        self.assertEqual(ramp["covered_s"], 3600)

    def test_power_conversion_and_rate_units(self):
        for unit, value, total in (("W", 1000, 1), ("kW", 1, 1), ("kg/s", 1, 3600),
                                   ("g/h", 2, 2), ("L/h", 2, 2), ("L/s", 1, 3600)):
            with self.subTest(unit=unit):
                r = self.result(f"A,0,{value}\nA,1800,{value}\nA,3600,{value}\n", self.plan(unit=unit))
                self.assertAlmostEqual(r["full_window_integral"], total)

    def test_bad_samples_never_bridge_or_become_zero(self):
        for bad in ("", "Bad", "NaN", "inf", "-Infinity", "1e999"):
            with self.subTest(bad=bad):
                r = self.result(f"A,0,2\nA,1800,{bad}\nA,3600,2\n")
                self.assertEqual(r["bad_sample_lines"], [3])
                self.assertEqual(r["covered_s"], 0)
                self.assertIsNone(r["observed_integral"])
                self.assertIsNone(r["full_window_integral"])
                self.assertIsNone(r["time_weighted_mean_observed"])

    def test_long_gap_and_missing_edges_are_partial(self):
        r = self.result("A,0,2\nA,600,2\nA,3600,2\n")
        self.assertEqual(r["covered_s"], 600)
        self.assertAlmostEqual(r["observed_integral"], 1 / 3)
        self.assertIsNone(r["full_window_integral"])
        r = self.result("A,600,2\nA,1800,2\n")
        self.assertEqual(r["covered_s"], 1200)
        self.assertEqual(r["coverage_status"], "incomplete")
        self.assertIsNone(r["full_window_integral"])

    def test_empty_window_and_measurement_unit(self):
        r = self.result("A,5000,2\n")
        self.assertEqual(r["sample_count"], 0)
        self.assertIsNone(r["sample_min"])
        r = self.result("A,0,28\nA,1800,30\nA,3600,30\n", self.plan(unit="degC"))
        self.assertEqual(r["time_weighted_mean_observed"], 29.5)
        self.assertEqual(r["coverage_status"], "complete")
        self.assertIsNone(r["integral_unit"])
        self.assertIsNone(r["observed_integral"])

    def test_interleaved_batches_and_separate_phase_windows(self):
        p = self.plan()
        p["windows"] += [{**p["windows"][0], "id": "b", "batch_id": "B"},
                         {**p["windows"][0], "id": "a2", "start_s": 3600, "end_s": 7200}]
        r = self.run_case("A,0,2\nB,0,8\nA,1800,2\nB,1800,8\nA,3600,2\nB,3600,8\nA,5400,4\nA,7200,4\n", p)
        self.assertEqual([w["signals"]["F"]["full_window_integral"] for w in r["windows"]], [2, 8, 3.5])

    def test_time_and_csv_refusals(self):
        for rows in ("A,0,2\nA,0,2\n", "A,2,2\nA,1,2\n", "A,NaN,2\n", "A,-1,2\n",
                     "A,bad,2\n", "A,0,2,3\n", "B,0,2\n", "A,0,2\nB,1,2\n", ""):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.run_case(rows)
        with self.assertRaises(ValueError):
            tool.analyze(b"batch_id,time_s,F,F\nA,0,2,2\n", json.dumps(self.plan()).encode())

    def test_configuration_refusals(self):
        variants = []
        for value in (True, 0, -1, float("inf")):
            p = self.plan(); p["max_gap_s"] = value; variants.append(p)
        p = self.plan(); p["signals"]["F"]["unit"] = "lb/hour"; variants.append(p)
        p = self.plan(); p["windows"][0]["end_s"] = 0; variants.append(p)
        p = self.plan(); p["windows"].append(copy.deepcopy(p["windows"][0])); variants.append(p)
        p = self.plan(); p["windows"].append({**p["windows"][0], "id": "overlap"}); variants.append(p)
        p = self.plan(); p["unused"] = True; variants.append(p)
        p = self.plan(); p["signals"]["F"]["quality"] = "invented"; variants.append(p)
        p = self.plan(); p["context"]["asset_id"] = ""; variants.append(p)
        for p in variants:
            with self.subTest(plan=p), self.assertRaises(ValueError):
                self.run_case("A,0,2\n", p)
        with self.assertRaisesRegex(ValueError, "duplicate JSON field"):
            tool.analyze(b"", b'{"schema":1,"schema":2}')

    def test_captured_hashes_and_extreme_value_refusal(self):
        csv_raw = b"batch_id,time_s,F\nA,0,2\nA,1800,2\nA,3600,2\n"
        plan_raw = json.dumps(self.plan()).encode()
        r = tool.analyze(csv_raw, plan_raw)
        self.assertEqual(r["inputs"], {"csv_sha256": hashlib.sha256(csv_raw).hexdigest(),
                                       "plan_sha256": hashlib.sha256(plan_raw).hexdigest()})
        with self.assertRaises((ValueError, OverflowError)):
            self.run_case("A,0,1e308\nA,1800,1e308\nA,3600,1e308\n")

    def test_graph_binding_and_generated_graph_agree(self):
        import graph_export
        graph_raw = (EXAMPLE / "graph.json").read_bytes()
        graph = json.loads(graph_raw)
        rebuilt = graph_export.build(EXAMPLE / "process_model.json")
        self.assertEqual(graph, rebuilt)
        report = tool.analyze((EXAMPLE / "observations.csv").read_bytes(),
                              (EXAMPLE / "plan.json").read_bytes(), graph_raw)
        binding = report["graph_binding"]
        self.assertEqual(binding["graph_sha256"], hashlib.sha256(graph_raw).hexdigest())
        self.assertEqual(len(binding["assets"]), 5)
        self.assertTrue(all(n["status"] == "unverified" for n in binding["assets"]))

    def v2_plan(self, interpolation="previous", quality=True):
        p = self.plan()
        p["schema"] = "batch-analysis-2"
        p["signals"]["F"].update(interpolation=interpolation,
                                quality={"column": "Q", "good_values": ["GOOD"]} if quality else None)
        return p

    def quality_result(self, rows, plan=None):
        report = tool.analyze(("batch_id,time_s,F,Q\n" + rows).encode(), json.dumps(plan or self.v2_plan()).encode())
        return report["windows"][0]["signals"]["F"]

    def test_previous_and_linear_distinct_analytical_oracles(self):
        raw = b"batch_id,time_s,F\nA,0,2\nA,1800,6\nA,3600,6\n"
        for method, expected in (("previous", 4), ("linear", 5)):
            with self.subTest(method=method):
                r = tool.analyze(raw, json.dumps(self.v2_plan(method, quality=False)).encode())
                result = r["windows"][0]["signals"]["F"]
                self.assertEqual(result["full_window_integral"], expected)
                self.assertEqual(result["time_weighted_mean_observed"], expected)
                self.assertEqual(result["interpolation"], method)
                self.assertIn(method, tool.markdown(r))
                self.assertEqual(result["quality_policy"], "no external quality filter selected; quality not checked")

    def test_null_quality_retains_unknown_source_quality_despite_numerical_coverage(self):
        p = self.v2_plan(quality=False)
        p["signals"]["F"]["source_ref"] = "original quality unavailable; published samples may include upstream interpolation"
        r = tool.analyze(b"batch_id,time_s,F\nA,0,2\nA,1800,2\nA,3600,2\n", json.dumps(p).encode())
        result = r["windows"][0]["signals"]["F"]
        self.assertEqual(result["coverage_status"], "complete")
        self.assertEqual(result["full_window_integral"], 2)
        self.assertEqual(result["good_samples"], 3)
        self.assertEqual(result["quality_policy"], "no external quality filter selected; quality not checked")
        self.assertIn("original quality unavailable", r["signal_definitions"]["F"]["source_ref"])
        self.assertIn("Accepted / all samples", tool.markdown(r))
        self.assertNotIn("Good / all samples", tool.markdown(r))

    def test_numeric_bad_quality_excludes_intervals_and_retains_reason(self):
        for method in ("linear", "previous"):
            r = self.quality_result("A,0,2,GOOD\nA,1800,99,FAULT\nA,3600,6,GOOD\n", self.v2_plan(method))
            self.assertEqual(r["covered_s"], 0)
            self.assertIsNone(r["full_window_integral"])
            self.assertEqual(r["excluded_samples"], [{"record_end_line": 3, "raw_value": "99",
                              "reasons": ["quality_not_accepted"], "quality_column": "Q", "quality_value": "FAULT"}])

    def test_quality_tokens_are_exact_and_do_not_override_bad_values(self):
        for token in ("", "good", "GOOD ", "UNKNOWN", "1.0"):
            p = self.v2_plan()
            p["signals"]["F"]["quality"]["good_values"] = ["GOOD", "1"]
            with self.subTest(token=token):
                r = self.quality_result(f"A,0,2,GOOD\nA,1800,6,{token}\nA,3600,6,GOOD\n", p)
                self.assertEqual(r["covered_s"], 0)
                self.assertEqual(r["excluded_samples"][0]["quality_value"], token)
        for token in ("00", "0.0"):
            p = self.v2_plan()
            p["signals"]["F"]["quality"]["good_values"] = ["0"]
            r = self.quality_result(f"A,0,2,0\nA,1800,6,{token}\nA,3600,6,0\n", p)
            self.assertEqual(r["covered_s"], 0)
            self.assertEqual(r["excluded_samples"][0]["quality_value"], token)
        for value, reason in (("Bad", "non_numeric_value"), ("", "non_numeric_value"), ("nan", "non_finite_value")):
            for quality in ("GOOD", "FAULT"):
                with self.subTest(value=value, quality=quality):
                    r = self.quality_result(f"A,0,2,GOOD\nA,1800,{value},{quality}\nA,3600,6,GOOD\n")
                    reasons = [reason] + (["quality_not_accepted"] if quality == "FAULT" else [])
                    self.assertEqual(r["excluded_samples"][0]["reasons"], reasons)
                    self.assertIsNone(r["observed_integral"])

    def test_v2_requires_explicit_valid_semantics_and_real_quality_column(self):
        variants = []
        for field in ("interpolation", "quality"):
            p = self.v2_plan(); del p["signals"]["F"][field]; variants.append(p)
        for method in (None, True, "Next", "nearest", "auto", {}):
            variants.append(self.v2_plan(method))
        for tokens in ([], ["GOOD", "GOOD"], [1], [True], [""], "GOOD", None):
            p = self.v2_plan(); p["signals"]["F"]["quality"]["good_values"] = tokens; variants.append(p)
        for column in ("time_s", "batch_id", "F", "", None):
            p = self.v2_plan(); p["signals"]["F"]["quality"]["column"] = column; variants.append(p)
        for p in variants:
            with self.subTest(plan=p), self.assertRaises(ValueError):
                tool.analyze(b"batch_id,time_s,F,Q\nA,0,2,GOOD\n", json.dumps(p).encode())
        with self.assertRaisesRegex(ValueError, "CSV header"):
            tool.analyze(b"batch_id,time_s,F\nA,0,2\n", json.dumps(self.v2_plan()).encode())

    def test_next_is_an_interval_ending_hold_with_its_own_oracle(self):
        # A log whose value at each time is the rate over the interval it closes (an hourly total): the closing
        # sample's value times the interval. Same series, three distinct oracles.
        raw = b"batch_id,time_s,F\nA,0,2\nA,1800,6\nA,3600,6\n"
        r = tool.analyze(raw, json.dumps(self.v2_plan("next", quality=False)).encode())
        result = r["windows"][0]["signals"]["F"]
        self.assertEqual(result["full_window_integral"], 6)
        self.assertEqual(result["time_weighted_mean_observed"], 6)
        self.assertEqual(result["interpolation"], "next")
        self.assertIn("interval-ending", r["method"]["assumption"])
        self.assertIn("next", tool.markdown(r))
        self.assertIn("closing sample", tool.markdown(r))

    def test_next_uses_only_the_closing_value_so_a_blank_opening_value_does_not_refuse(self):
        # Hour 0 of a fed-batch log is blank (feed not yet started); the first hour's feed is logged at its end.
        r = tool.analyze(b"batch_id,time_s,F\nA,0,\nA,1800,2\nA,3600,4\n",
                         json.dumps(self.v2_plan("next", quality=False)).encode())["windows"][0]["signals"]["F"]
        self.assertEqual(r["coverage_status"], "complete")
        self.assertEqual(r["full_window_integral"], 3)
        self.assertEqual(r["bad_sample_lines"], [2])
        self.assertEqual(r["excluded_samples"][0]["reasons"], ["non_numeric_value"])
        for method in ("linear", "previous"):
            other = tool.analyze(b"batch_id,time_s,F\nA,0,\nA,1800,2\nA,3600,4\n",
                                 json.dumps(self.v2_plan(method, quality=False)).encode())["windows"][0]["signals"]["F"]
            self.assertIsNone(other["full_window_integral"])

    def test_next_refuses_a_bad_closing_value_and_keeps_the_gap_and_edge_rules(self):
        r = self.quality_result("A,0,2,GOOD\nA,1800,99,FAULT\nA,3600,6,GOOD\n", self.v2_plan("next"))
        self.assertEqual(r["covered_s"], 1800)
        self.assertEqual(r["observed_integral"], 3)
        self.assertIsNone(r["full_window_integral"])
        r = self.quality_result("A,0,2,GOOD\nA,600,2,GOOD\nA,3600,6,GOOD\n", self.v2_plan("next"))
        self.assertEqual(r["covered_s"], 600)
        self.assertIsNone(r["full_window_integral"])
        r = self.quality_result("A,600,2,GOOD\nA,3600,6,GOOD\n", self.v2_plan("next"))
        self.assertEqual(r["coverage_status"], "incomplete")
        self.assertIsNone(r["full_window_integral"])

    def test_reports_without_next_keep_their_method_text(self):
        for method in ("linear", "previous"):
            r = tool.analyze(b"batch_id,time_s,F\nA,0,2\nA,1800,6\nA,3600,6\n",
                             json.dumps(self.v2_plan(method, quality=False)).encode())
            self.assertNotIn("interval-ending", r["method"]["assumption"])
            self.assertNotIn("closing sample", tool.markdown(r))

    def test_previous_retains_conservative_edges_and_gap_policy(self):
        for rows in ("A,0,2,GOOD\nA,1800,6,FAULT\n", "A,0,2,GOOD\nA,3600,6,GOOD\n"):
            r = self.quality_result(rows)
            self.assertEqual(r["covered_s"], 0)
            self.assertIsNone(r["observed_integral"])
        r = self.quality_result("A,0,2,GOOD\nA,600,2,GOOD\nA,3600,6,GOOD\n")
        self.assertEqual(r["covered_s"], 600)
        self.assertAlmostEqual(r["observed_integral"], 1 / 3)
        self.assertIsNone(r["full_window_integral"])

    def test_v1_retained_baseline_changes_only_implementation_fingerprints(self):
        r = tool.analyze((EXAMPLE / "observations.csv").read_bytes(), (EXAMPLE / "plan.json").read_bytes(),
                         (EXAMPLE / "graph.json").read_bytes())
        old = json.loads((EXAMPLE / "history/a306/batch_analysis.json").read_bytes())
        self.assertNotEqual(r["method"]["tool_sha256_lf"], old["method"]["tool_sha256_lf"])
        del r["method"]["tool_sha256_lf"]
        del old["method"]["tool_sha256_lf"]
        # The core-export repair also changes the pinned graph validator file.
        # Current pins are checked separately; retain exact equality of all engineering values.
        del r["graph_binding"]["validator_sha256_lf"]
        del old["graph_binding"]["validator_sha256_lf"]
        self.assertEqual(r, old)
        self.assertEqual((EXAMPLE / "expected/batch_analysis.md").read_bytes(),
                         (EXAMPLE / "history/a306/batch_analysis.md").read_bytes())

    def test_both_v2_clis_preserve_sources_and_match_reports(self):
        semantics = EXAMPLE / "semantics"
        for method, expected in (("previous", 4), ("linear", 5)):
            with self.subTest(method=method), tempfile.TemporaryDirectory() as tmp:
                paths = [semantics / "observations.csv", semantics / f"{method}.plan.json", EXAMPLE / "graph.json"]
                before = [p.read_bytes() for p in paths]
                run = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/batch_analysis.py"),
                                      "--csv", str(paths[0]), "--plan", str(paths[1]), "--graph", str(paths[2]), "--out", tmp],
                                     capture_output=True, text=True, timeout=30)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertEqual(before, [p.read_bytes() for p in paths])
                report = json.loads((Path(tmp) / "batch_analysis.json").read_bytes())
                a, b = [w["signals"] for w in report["windows"]]
                self.assertEqual(a["FT-101"]["full_window_integral"], expected)
                self.assertIsNone(b["FT-101"]["full_window_integral"])
                self.assertAlmostEqual(b["POWER-101"]["full_window_integral"], 1)
                for name in ("batch_analysis.json", "batch_analysis.md"):
                    self.assertEqual((Path(tmp) / name).read_bytes(), (semantics / "expected" / method / name).read_bytes())

    def test_measured_public_series_reproduces_independent_key_and_full_reports(self):
        case = EXAMPLE / "public-distillation"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "reproduced"
            run = subprocess.run([sys.executable, "-B", "-S", str(case / "reproduce.py"),
                                  "--check", "--out", str(out)], capture_output=True, text=True, timeout=40)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            result = json.loads((out / "CHECK.json").read_bytes())
            self.assertTrue(result["pass"])
            self.assertTrue(result["complete_expected_match"])
            report = json.loads((out / "reports/batch_analysis.json").read_bytes())
            flow = report["windows"][0]["signals"]["FT703"]
            self.assertAlmostEqual(flow["full_window_integral"], 0.46861319444444444)
            self.assertEqual(flow["sample_count"], 3512)
            self.assertEqual(flow["quality_policy"], "no external quality filter selected; quality not checked")

    def test_public_packet_missing_required_pin_refuses_before_cli(self):
        case = EXAMPLE / "public-distillation"
        spec = importlib.util.spec_from_file_location("distillation_example", case / "reproduce.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = json.loads((case / "PROVENANCE.json").read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for rel in original["files"]:
                dest = folder / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((case / rel).read_bytes())
            for missing in ("KEY.json", "source/anomaly-metadata.yaml"):
                data = copy.deepcopy(original)
                del data["files"][missing]
                (folder / "PROVENANCE.json").write_text(json.dumps(data), encoding="utf-8")
                with self.subTest(missing=missing), patch.object(module, "HERE", folder), \
                     patch.object(module.subprocess, "run", side_effect=AssertionError("CLI must not start")), \
                     self.assertRaisesRegex(ValueError, "exact required runtime files"):
                    module.packet()

    def test_public_case_output_and_cache_must_stay_outside_checkout(self):
        case = EXAMPLE / "public-distillation"
        spec = importlib.util.spec_from_file_location("distillation_paths", case / "reproduce.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            target = folder / "inside-checkout"
            with patch.object(module, "ROOT", folder), \
                 patch.object(module, "urlopen", side_effect=AssertionError("Network must not start")), \
                 self.assertRaisesRegex(ValueError, "outside the checkout"):
                module.fetch(target)
            self.assertFalse(target.exists())
            with patch.object(module, "ROOT", folder), \
                 patch.object(sys, "argv", [str(case / "reproduce.py"), "--out", str(target)]), \
                 patch.object(module.subprocess, "run", side_effect=AssertionError("CLI must not start")), \
                 self.assertRaisesRegex(ValueError, "outside the checkout"):
                module.main()
            self.assertFalse(target.exists())

    def test_analysis_context_handoff_preserves_complete_history_and_readback(self):
        case = EXAMPLE / "context-handoff"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "handoff"
            run = subprocess.run([sys.executable, "-B", "-S", str(case / "reproduce.py"),
                                  "--root", str(ROOT), "--out", str(out)], capture_output=True, text=True, timeout=45)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            result = json.loads((out / "RESULT.json").read_bytes())
            self.assertTrue(result["pass"])
            self.assertEqual([job["exit"] for job in result["jobs"]], [0, 0, 0, 2])
            self.assertTrue(result["no_analytics_execution"])
            self.assertTrue(result["no_transport"])
            self.assertEqual(len(result["pure_Snapshot_pairs"]), 2)
            for stage in ("partial", "refreshed"):
                for name in ("context.json", "enriched_graph.json"):
                    self.assertEqual((out / stage / name).read_bytes(), (case / "expected" / stage / name).read_bytes())
            self.assertEqual((out / "fictional-partial.csv").read_bytes(), (case / "fictional-partial-v2.csv").read_bytes())

    def test_graph_unknown_wrong_kind_rejected_and_malformed_refuse(self):
        plan_raw = (EXAMPLE / "plan.json").read_bytes()
        csv_raw = (EXAMPLE / "observations.csv").read_bytes()
        graph = json.loads((EXAMPLE / "graph.json").read_bytes())
        for change in ("unknown", "wrong-kind", "rejected", "duplicate", "malformed"):
            g = copy.deepcopy(graph)
            if change == "malformed":
                g["nodes"] = ["bad"]
            elif change == "duplicate":
                g["nodes"].append(copy.deepcopy(g["nodes"][0]))
            else:
                n = next(n for n in g["nodes"] if n["id"] == "FT-101")
                if change == "unknown":
                    n["id"] = "foreign-instrument"
                elif change == "wrong-kind":
                    n["kind"] = "equipment"
                else:
                    n["status"] = "rejected"
            with self.subTest(change=change), self.assertRaises(ValueError):
                tool.analyze(csv_raw, plan_raw, json.dumps(g).encode())

    def test_cli_public_example_matches_fixed_oracles_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "reports"
            paths = [EXAMPLE / "observations.csv", EXAMPLE / "plan.json"]
            before = [p.read_bytes() for p in paths]
            run = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/batch_analysis.py"),
                                  "--csv", str(paths[0]), "--plan", str(paths[1]),
                                  "--graph", str(EXAMPLE / "graph.json"), "--out", str(out)],
                                 capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(before, [p.read_bytes() for p in paths])
            report = json.loads((out / "batch_analysis.json").read_text(encoding="utf-8"))
            totals = [w["signals"]["FT-101"]["full_window_integral"] for w in report["windows"]]
            self.assertEqual(totals, [0.5, 3.5, 2, None])
            self.assertEqual(report["windows"][1]["signals"]["DO-101"]["sample_min"], 20)
            for w in report["windows"]:
                self.assertAlmostEqual(w["signals"]["POWER-101"]["full_window_integral"], 1)
            for name in ("batch_analysis.json", "batch_analysis.md"):
                self.assertEqual((out / name).read_bytes(), (EXAMPLE / "expected" / name).read_bytes())

    def test_cli_refuses_existing_and_input_alias_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            csv_path, plan_path = folder / "source.csv", folder / "plan.json"
            csv_path.write_text("batch_id,time_s,F\nA,0,2\n", encoding="utf-8")
            plan_path.write_text(json.dumps(self.plan()), encoding="utf-8")
            report = folder / "batch_analysis.json"
            report.write_bytes(b"keep this report")
            before = {p: p.read_bytes() for p in (csv_path, plan_path, report)}
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(tool.main(["--csv", str(csv_path), "--plan", str(plan_path), "--out", str(folder)]), 2)
            self.assertEqual(before, {p: p.read_bytes() for p in before})
            self.assertFalse((folder / "batch_analysis.md").exists())
            report.unlink()
            os.link(csv_path, report)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(tool.main(["--csv", str(csv_path), "--plan", str(plan_path), "--out", str(folder)]), 2)
            self.assertEqual(csv_path.read_bytes(), before[csv_path])

    def test_invalid_cli_inputs_never_publish_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            csv_path, plan_path = folder / "source.csv", folder / "plan.json"
            for case in ("unit", "order", "graph"):
                p = self.plan()
                csv_path.write_text("batch_id,time_s,F\nA,0,2\nA,1800,2\n", encoding="utf-8")
                if case == "unit":
                    p["signals"]["F"]["unit"] = "unknown-unit"
                elif case == "order":
                    csv_path.write_text("batch_id,time_s,F\nA,1,2\nA,0,2\n", encoding="utf-8")
                plan_path.write_text(json.dumps(p), encoding="utf-8")
                out = folder / case
                args = ["--csv", str(csv_path), "--plan", str(plan_path), "--out", str(out)]
                if case == "graph":
                    graph_path = folder / "graph.json"
                    graph_path.write_text('{"nodes":["malformed"]}', encoding="utf-8")
                    args += ["--graph", str(graph_path)]
                original = [csv_path.read_bytes(), plan_path.read_bytes()]
                with self.subTest(case=case), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(tool.main(args), 2)
                    self.assertFalse(out.exists())
                    self.assertEqual([csv_path.read_bytes(), plan_path.read_bytes()], original)


if __name__ == "__main__":
    unittest.main()
