"""Regression controls for mapped originals, refusal boundaries and three successive maintenance packets."""
import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path

import maintenance_intake as mi


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.p = {"schema": mi.SCHEMA, "site": "TEST", "plant": "P1", "units": ["U1", "U2"], "as_of": "2026-11-06",
                  "equipment": {"id": "EQ", "revision": "1", "owner": "Maintenance", "coverage": "Selected two units; supplied export only",
                                "columns": {"Position": "tag", "Area": "unit", "Serial": "serial_number"}, "ignored_columns": ["Note"]},
                  "work_orders": {"id": "WO", "revision": "1", "owner": "Maintenance", "coverage": "Selected two units; supplied history only",
                                  "columns": {"Order": "work_order", "Position": "tag", "Area": "unit", "Closed": "closed_on", "Fitted": "installed_serial_number"}}}
        self.eq = [{"Position": "P-101", "Area": "U1", "Serial": "0001", "Note": "keep\noriginal"},
                   {"Position": "P-101", "Area": "U2", "Serial": "9999", "Note": "other unit"}]
        self.wo = [{"Order": "801", "Position": "P-101", "Area": "U1", "Closed": "2026-11-01", "Fitted": "0002"},
                   {"Order": "802", "Position": "P-101", "Area": "U1", "Closed": "", "Fitted": "9998"}]

    def save(self):
        mi.dump(self.root / "profile.json", self.p)
        for k, rr in (("equipment", self.eq), ("work_orders", self.wo)):
            with (self.root / (k + ".csv")).open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rr[0]), delimiter=self.p[k].get("delimiter", ","))
                w.writeheader()
                w.writerows(rr)

    def run_packet(self, name="packet", previous=None):
        self.save()
        return mi.run(self.root / "profile.json", self.root / "equipment.csv", self.root / "work_orders.csv", self.root / name, previous)

    def test_site_file_claims_no_drawing_register_without_drawings(self):
        a = self.run_packet()
        site = mi.load(a / "prepared/site.json")
        self.assertNotIn("drawing_register", site)  # an empty register would claim drawings the intake never had
        self.assertFalse((a / "prepared/drawings.csv").exists())
        self.assertFalse([n for n in mi.load(a / "map/graph.json")["nodes"] if n["kind"] == "document"
                          and str(n.get("id", "")).startswith("PID-")])

    def test_three_revisions_preserve_identity_history_and_sources(self):
        a = self.run_packet()
        before = mi.inventory(a)
        f = mi.load(a / "findings.json")["findings"]
        self.assertEqual([(x["subject"], x["attribute"]) for x in f], [("TEST/P1/U1/P-101", "serial_number")])
        self.assertEqual({s["says"] for s in f[0]["original_evidence"]}, {"0001", "0002"})
        self.assertTrue(all(s["origin"] for s in f[0]["original_evidence"]))
        self.assertEqual((a / "originals/equipment.csv").read_bytes(), (self.root / "equipment.csv").read_bytes())
        self.assertEqual(mi.load(a / "prepared/row-origins.json")[0]["original_end_line"], 3)
        self.eq[0]["Serial"] = "0002"
        self.p["equipment"]["revision"] = "2"
        b = self.run_packet("returned", a)
        self.assertEqual(mi.load(b / "findings.json")["findings"], [])
        self.assertEqual(len(mi.load(b / "findings.json")["history"]["no_longer_detected"]), 1)
        self.p["work_orders"]["revision"] = "2"
        self.wo.append(dict(self.wo[0], Order="803", Closed="2026-11-05", Fitted="0003"))
        c = self.run_packet("replacement", b)
        fresh = mi.load(c / "findings.json")
        self.assertEqual(fresh["findings"][0]["subject"], f[0]["subject"])
        self.assertEqual({s["says"] for s in fresh["findings"][0]["original_evidence"]}, {"0002", "0003"})
        self.assertEqual(before, mi.inventory(a))
        self.assertEqual(mi.verify_packet(c)["previous_receipt_sha256"], mi.sha(b / "receipt.json"))
        self.assertIn("No field inspection", (c / "REPORT.html").read_text())
        self.assertIn("9998", (c / "originals/work_orders.csv").read_text(encoding="utf-8-sig"))
        self.assertNotIn("9998", json.dumps(fresh["findings"]))

    def test_semicolon_explicit_date_and_html_escaping(self):
        self.p["equipment"]["delimiter"] = ";"
        self.p["work_orders"]["date_format"] = "%d/%m/%Y"
        self.wo[0]["Closed"] = "01/11/2026"
        self.eq[0]["Serial"] = "<script>alert(1)</script>"
        out = self.run_packet()
        page = (out / "REPORT.html").read_text()
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertEqual(mi.load(out / "findings.json")["findings"][0]["original_evidence"][0]["origin"]["original_record"], 2)

    def test_invalid_identity_dates_duplicate_and_unknown_fields_refuse(self):
        variants = [lambda: self.eq[0].update(Area=""), lambda: self.eq.append(dict(self.eq[0])),
                    lambda: self.wo[0].update(Closed="11/01/2026"), lambda: self.wo[0].update(Closed="2026-11-07"),
                    lambda: self.p["equipment"]["columns"].update(Unknown="model"),
                    lambda: self.wo.append(dict(self.wo[0], Order="900", Fitted="different")),
                    lambda: self.wo.append(dict(self.wo[0]))]
        baseline = copy.deepcopy((self.p, self.eq, self.wo))
        for mutate in variants:
            self.p, self.eq, self.wo = copy.deepcopy(baseline)
            mutate()
            with self.subTest(case=variants.index(mutate)), self.assertRaises(ValueError):
                self.run_packet()
            self.assertFalse((self.root / "packet").exists())

    def test_duplicate_headers_wrong_width_and_empty_export(self):
        self.save()
        for content in ("Position,Area,Serial,Serial\nP,U1,1,2\n", "Position,Area,Serial,Note\nP,U1\n", "Position,Area,Serial,Note\n"):
            with self.subTest(content=content), self.assertRaises(ValueError):
                mi.read_rows(content.encode(), "equipment", self.p)

    def test_missing_input_and_existing_destination_preserve_evidence(self):
        a = self.run_packet()
        before = mi.inventory(a)
        with self.assertRaises(ValueError):
            self.run_packet()
        (self.root / "work_orders.csv").unlink()
        with self.assertRaises(OSError):
            mi.run(self.root / "profile.json", self.root / "equipment.csv", self.root / "work_orders.csv", self.root / "missing", a)
        self.assertFalse((self.root / "missing").exists())
        self.assertEqual(before, mi.inventory(a))

    def test_revision_scope_and_tampered_previous_refuse(self):
        a = self.run_packet()
        self.eq[0]["Serial"] = "0002"
        with self.assertRaisesRegex(ValueError, "unchanged revision"):
            self.run_packet("bad", a)
        self.p["equipment"]["revision"] = "2"
        self.p["units"].append("U3")
        with self.assertRaisesRegex(ValueError, "scope/source authority"):
            self.run_packet("bad", a)
        self.p["units"].pop()
        (a / "REPORT.md").write_text("changed")
        with self.assertRaisesRegex(ValueError, "inventory differs"):
            self.run_packet("bad", a)
        self.assertFalse((self.root / "bad").exists())

    def test_changed_headers_are_allowed_with_explicit_mapping_and_revision(self):
        a = self.run_packet()
        self.p["equipment"]["columns"]["Installed serial"] = self.p["equipment"]["columns"].pop("Serial")
        for r in self.eq:
            r["Installed serial"] = r.pop("Serial")
        self.p["equipment"]["revision"] = "2"
        b = self.run_packet("headers", a)
        self.assertEqual(len(mi.load(b / "findings.json")["history"]["still_detected"]), 1)

    def test_malformed_profile_and_removed_history_do_not_claim_acceptance(self):
        for mutate in (lambda p: [], lambda p: dict(p, units=[["U1"]]),
                       lambda p: dict(p, equipment=[]),
                       lambda p: dict(p, equipment=dict(p["equipment"], columns={"X": []}))):
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                mi.profile_check(mutate(copy.deepcopy(self.p)))
        a = self.run_packet()
        # A later export omitted the closed order. This removes the observed disagreement but supplies no correction.
        self.wo = [self.wo[1]]
        self.p["work_orders"]["revision"] = "2-partial"
        b = self.run_packet("omitted-history", a)
        report = mi.load(b / "findings.json")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["history"]["no_longer_detected"][0]["status"], "open")
        self.assertIn("not an accepted correction", report["history"]["meaning"])

    def test_changed_interpretation_of_identical_source_is_explicit(self):
        a = self.run_packet()
        previous = mi.inventory(a)
        # Same bytes and source revision, different declared meaning: no serial disagreement is now possible.
        self.p["equipment"]["columns"]["Serial"] = "model"
        b = self.run_packet("reinterpreted", a)
        self.assertEqual(mi.load(b / "findings.json")["findings"], [])
        basis = mi.load(b / "comparison-basis.json")
        self.assertEqual(basis["status"], "needs_review")
        self.assertEqual(basis["interpretation_changes"][0]["source"], "equipment")
        self.assertFalse(basis["sources"][0]["bytes_changed"])
        self.assertIn("Comparison basis needs review", (b / "REPORT.html").read_text())
        self.assertEqual(previous, mi.inventory(a))

    def test_date_format_change_and_removed_source_rows_are_explained(self):
        self.p["work_orders"]["date_format"] = "%m/%d/%Y"
        self.wo[0]["Closed"] = "02/01/2026"
        a = self.run_packet()
        self.p["work_orders"]["date_format"] = "%d/%m/%Y"
        b = self.run_packet("date-basis", a)
        basis = mi.load(b / "comparison-basis.json")
        self.assertEqual(basis["interpretation_changes"][0]["source"], "work_orders")
        change = basis["sources"][1]["changed_records"][0]
        self.assertEqual((change["before"]["closed_on"], change["after"]["closed_on"]), ("2026-02-01", "2026-01-02"))
        self.wo = [self.wo[1]]
        self.p["work_orders"]["revision"] = "2"
        c = self.run_packet("omitted", b)
        removed = mi.load(c / "comparison-basis.json")["sources"][1]["removed_records"]
        self.assertEqual(removed[0]["values"]["work_order"], "801")
        self.assertEqual(removed[0]["origin"]["original_record"], 2)

    def test_method_drift_and_legacy_missing_pins_are_never_silent(self):
        a = self.run_packet()
        receipt = mi.load(a / "receipt.json")
        receipt["methods_sha256_lf"]["one_map.py"] = "0" * 64
        mi.dump(a / "receipt.json", receipt)  # exposed metadata control, not an actual old engine run
        b = self.run_packet("method-drift", a)
        basis = mi.load(b / "comparison-basis.json")
        self.assertIn("one_map.py", basis["changed_methods"])
        self.assertEqual(basis["status"], "needs_review")
        receipt.pop("methods_sha256_lf")
        mi.dump(a / "receipt.json", receipt)
        c = self.run_packet("legacy", a)
        self.assertTrue(mi.load(c / "comparison-basis.json")["unknown_prior_basis"])

    def test_identical_recorded_basis_is_distinct_from_acceptance(self):
        a = self.run_packet()
        b = self.run_packet("repeat", a)
        basis = mi.load(b / "comparison-basis.json")
        self.assertEqual(basis["status"], "unchanged_recorded_basis")
        self.assertEqual(basis["changed_methods"], [])
        self.assertEqual(basis["interpretation_changes"], [])
        self.assertTrue(all(not s["changed_records"] for s in basis["sources"]))
        self.assertIn("not acceptance", basis["meaning"])

    def test_row_reordering_is_not_a_changed_normalized_record(self):
        a = self.run_packet()
        self.wo.reverse()
        self.p["work_orders"]["revision"] = "2-reordered"
        b = self.run_packet("reordered", a)
        source = mi.load(b / "comparison-basis.json")["sources"][1]
        self.assertTrue(source["bytes_changed"])
        for field in ("changed_records", "removed_records", "added_records"):
            self.assertEqual(source[field], [])


if __name__ == "__main__":
    unittest.main()
