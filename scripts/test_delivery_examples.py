"""Check retained public-source/OCR identities and the published CAD proposal against its own declared scope."""
import csv
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DeliveryEvidence(unittest.TestCase):
    def test_public_original_attribution_and_exact_source_identity(self):
        folder = ROOT / "examples/photo-to-record"
        for manifest, name, author, license_name in (
                ("PROVENANCE.json", "motor-nameplate.jpg", "tony_duell", "CC BY 2.0"),
                ("industrial-PROVENANCE.json", "industrial-motor.jpg", "Denis Apel", "CC BY-SA 2.0 Germany")):
            with self.subTest(name=name):
                pin = read(folder / "source" / manifest)
                source = folder / "source" / name
                self.assertEqual(sha(source), pin["sha256"])
                self.assertEqual(source.stat().st_size, pin["bytes"])
                self.assertEqual(pin["author"], author)
                self.assertEqual(pin["license"], license_name)
                self.assertFalse(pin["original_modified"])

    def test_every_ocr_attempt_is_retained_including_empty_failure(self):
        folder = ROOT / "examples/photo-to-record/worked/public-cases"
        receipt = read(folder / "receipt.json")
        self.assertEqual([r["label"] for r in receipt["runs"]],
                         ["whole-psm3", "crop-psm3", "crop-psm6", "crop-psm11", "industrial-psm3", "industrial-psm6"])
        original = ROOT / "examples/photo-to-record/source/motor-nameplate.jpg"
        self.assertEqual(receipt["source_sha256"], sha(original))
        for run in receipt["runs"]:
            source = (folder / run["input_name"] if run["input_name"] == "nameplate-crop.png"
                      else ROOT / "examples/photo-to-record/source" / run["input_name"])
            self.assertEqual(run["input_sha256"], sha(source))
            output = folder / (run["label"] + ".txt")
            self.assertEqual(run["output_sha256"], sha(output))
            self.assertEqual(run["bytes_out"], output.stat().st_size)
            self.assertTrue((folder / (run["label"] + ".stderr.txt")).is_file())
        self.assertEqual(receipt["runs"][0]["bytes_out"], 0)

    def test_photo_readings_are_candidates_without_an_invented_plant_identity(self):
        with (ROOT / "examples/photo-to-record/candidate-fields.csv").open(encoding="utf-8", newline="") as f:
            fields = {r["field"]: r for r in csv.DictReader(f)}
        for key in ("plant_tag", "site_unit", "capture_to_asset_link"):
            self.assertEqual((fields[key]["candidate"], fields[key]["status"]), ("", "unknown"))
        self.assertEqual(fields["voltage"]["units"], "V")
        self.assertIn("unresolved", fields["plate_number"]["interpretation_limit"])
        self.assertTrue(all(r["status"] == "needs independent review" for k, r in fields.items()
                            if k not in {"plant_tag", "site_unit", "capture_to_asset_link"}))

    def test_native_cad_diagnostic_retains_failures_and_exact_bytes(self):
        folder = ROOT / "examples/cad-handoff/native/diagnostic"
        receipt = read(folder / "receipt.json")
        for name, expected in receipt["files"].items():
            with self.subTest(name=name):
                self.assertEqual(sha(folder / name), expected)
        self.assertEqual([r["exit_code"] for r in receipt["runs"]], [0] * 5)
        self.assertIn("failed", receipt["rasterization"]["initial_attempt"])
        ui = read(folder / "ui-retry.json")
        self.assertIsNone(ui["returned_dxf"])
        self.assertIn("not completed", ui["acceptance"])
        self.assertIn("remains unqualified", (folder / "README.md").read_text(encoding="utf-8"))

    def test_comparison_basis_examples_keep_disappeared_findings_open(self):
        import maintenance_intake as mi
        folder = ROOT / "examples/maintenance-intake/basis-worked"
        replay = read(folder / "replay.json")
        self.assertTrue(all(replay["checks"].values()))
        for name in ("ignored-serial", "omitted-history"):
            packet = folder / name
            mi.verify_packet(packet)
            basis = read(packet / "comparison-basis.json")
            finding = read(packet / "findings.json")
            self.assertEqual(basis["status"], "needs_review")
            self.assertIn("maintenance_intake.py", basis["changed_methods"])
            self.assertEqual(finding["findings"], [])
            self.assertEqual(finding["history"]["no_longer_detected"][0]["status"], "open")
        removed = read(folder / "omitted-history/comparison-basis.json")["sources"][1]["removed_records"]
        self.assertEqual((removed[0]["values"]["work_order"], removed[0]["origin"]["original_record"]), ("WO-801", 2))

    def test_qcad_native_readback_does_not_override_preservation_failure(self):
        import cad_handoff as cad
        folder = ROOT / "examples/cad-handoff/native/qcad"
        receipt = read(folder / "receipt.json")
        for name, expected in receipt["files"].items():
            self.assertEqual(sha(folder / name), expected, name)
        source = ROOT / "examples/cad-handoff/source/valve.dxf"
        plan = read(source.with_name("edit-plan.json"))
        comparison = cad.compare(cad.snapshot(source), cad.snapshot(folder / "returned.dxf"), plan)
        self.assertEqual(comparison, read(folder / "comparison.json"))
        self.assertEqual(len(comparison["unexpected"]), 335)
        actual = read(folder / "readback.json")["after"][0]["attributes"]
        for c in plan["changes"]:
            self.assertEqual(actual[c["attribute"]], c["after"])
        self.assertEqual(actual["VENDOR_NOTE"], "retain this unfamiliar attribute")
        self.assertEqual(receipt["interactive_acceptance"], "not performed")

    def test_r15_native_return_and_review_packet_reproduce_without_waivers(self):
        import cad_handoff as cad
        folder = ROOT / "examples/cad-handoff/native/qcad-r15"
        receipt = read(folder / "receipt.json")
        for name, expected in receipt["files"].items():
            self.assertEqual(sha(folder / name), expected, name)
        source = ROOT / "examples/cad-handoff/source/valve.dxf"
        before, after = cad.snapshot(source), cad.snapshot(folder / "returned.dxf")
        comparison = cad.compare(before, after, read(source.with_name("edit-plan.json")))
        self.assertEqual((before["dxfversion"], after["dxfversion"]), ("AC1015", "AC1015"))
        expected = dict(before["assets"][0]["attributes"])
        for change in read(source.with_name("edit-plan.json"))["changes"]:
            expected[change["attribute"]] = change["after"]
        self.assertEqual(after["assets"][0]["attributes"], expected)
        self.assertEqual(read(folder / "readback.json")["after"][0]["attributes"], expected)
        self.assertEqual((comparison["status"], len(comparison["unexpected"])), ("differences", 344))
        packet = ROOT / "examples/cad-handoff/receiving-review/worked"
        receipt = read(packet / "receipt.json")
        for name, expected in receipt["files"].items():
            self.assertEqual(sha(packet / name), expected, name)
        self.assertEqual((packet / "originals/before.dxf").read_bytes(), source.read_bytes())
        self.assertEqual(read(packet / "strict-comparison.json"), read(ROOT / "examples/cad-handoff/native/qcad/comparison.json"))
        report = read(packet / "review.json")
        self.assertEqual((report["strict_status"], report["strict_difference_count"], report["acceptance"]), ("differences", 335, "not performed"))
        self.assertEqual(sum(report["entity_partitions"].values()), 333)

    def test_saved_cad_proposal_retains_original_and_separate_context(self):
        folder = ROOT / "examples/cad-handoff"
        plan = read(folder / "source/edit-plan.json")
        self.assertEqual(plan["source_sha256"], sha(folder / "source/valve.dxf"))
        self.assertEqual((folder / "worked/source.dxf").read_bytes(), (folder / "source/valve.dxf").read_bytes())
        report = read(folder / "worked/comparison.json")
        self.assertEqual(report["before_sha256"], plan["source_sha256"])
        self.assertEqual(report["after_sha256"], sha(folder / "worked/candidate.dxf"))
        self.assertEqual((report["status"], report["unexpected"]), ("pass", []))
        self.assertEqual(report["expected_edits"], plan["changes"])
        old = read(folder / "worked/cad_context.json")["nodes"][0]
        after = read(folder / "worked/candidate-context/cad_context.json")["nodes"][0]
        self.assertEqual(old["id"], after["id"])
        self.assertEqual((old["attributes"]["SIZE"], after["attributes"]["SIZE"]), ("DN50", "DN65"))
        self.assertEqual(old["attributes"]["VENDOR_NOTE"], after["attributes"]["VENDOR_NOTE"])
        for version, size, source in (("before", "DN50", "source/valve.dxf"),
                                      ("after", "DN65", "worked/candidate.dxf")):
            graph = read(folder / f"worked/map-{version}/map/graph.json")
            node = next(n for n in graph["nodes"] if n["id"] == old["id"])
            attributes = {a["name"]: a for a in node["attributes"]}
            self.assertEqual(attributes["cad_size"]["value"], size)
            self.assertEqual(attributes["cad_source_sha256"]["value"], sha(folder / source))
            self.assertEqual(node["status"], "unverified")
            self.assertFalse(any(e["type"] in {"connects", "controls", "measures"} for e in graph["edges"]))


if __name__ == "__main__":
    unittest.main()
