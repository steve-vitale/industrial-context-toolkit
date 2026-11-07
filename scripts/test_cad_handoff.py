"""DXF edit/readback, foreign attributes/geometry, stale plans and destructive-return controls."""
import copy
import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

import ezdxf
import cad_handoff as ch


def drawing(path):
    doc = ezdxf.new("R2000")
    doc.layers.new("PROCESS", dxfattribs={"color": 3})
    block = doc.blocks.new("VALVE")
    block.add_circle((0, 0), 2)
    for i, key in enumerate(("ICT_ID", "TAG", "MODEL", "SERIAL", "SIZE", "VENDOR_PRIVATE")):
        block.add_attdef(key, (3, -i), height=0.7)
    ref = doc.modelspace().add_blockref("VALVE", (10, 20), dxfattribs={"layer": "PROCESS"})
    ref.add_auto_attribs(dict(ICT_ID="fixture/valve-01", TAG="FV-101", MODEL="A", SERIAL="123", SIZE="DN50",
                             VENDOR_PRIVATE="retain me"))
    line = doc.modelspace().add_line((0, 20), (8, 20), dxfattribs={"layer": "PROCESS"})
    doc.appids.new("VENDOR_TEST")
    line.set_xdata("VENDOR_TEST", [(1000, "do not flatten"), (1040, 1.25)])
    doc.saveas(path)


class Handoff(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "original.dxf"
        drawing(self.source)
        self.before = ch.snapshot(self.source)
        self.plan = {"schema": "cad-edit-plan-1", "source_sha256": ch.digest(self.source), "changes": [
            {"id": "fixture/valve-01", "attribute": "SIZE", "before": "DN50", "after": "DN65",
             "reason": "Fictional reviewed replacement note; not installed-state evidence"}]}

    def test_edit_round_trip_retains_source_foreign_data_and_context_identity(self):
        source_bytes = self.source.read_bytes()
        out = self.root / "proposal"
        report = ch.apply(self.source, self.plan, out)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(self.source.read_bytes(), source_bytes)
        self.assertEqual((out / "source.dxf").read_bytes(), source_bytes)
        after = ch.snapshot(out / "candidate.dxf")
        self.assertEqual(after["assets"][0]["id"], "fixture/valve-01")
        self.assertEqual(after["assets"][0]["attributes"]["VENDOR_PRIVATE"], "retain me")
        self.assertEqual(after["assets"][0]["attributes"]["SIZE"], "DN65")
        self.assertEqual(ch.compare(self.before, after, self.plan)["unexpected"], [])
        self.assertTrue(ch.compare(self.before, after)["unexpected"])
        proposed = json.loads((out / "candidate-context/cad_context.json").read_text())
        self.assertEqual(proposed["nodes"][0]["attributes"]["SIZE"], "DN65")
        self.assertEqual(proposed["relationships"], [])

    def test_stale_source_before_value_duplicate_and_identity_edits_refused(self):
        for mutate in (lambda p: p.update(source_sha256="0" * 64),
                       lambda p: p["changes"][0].update(before="DN40"),
                       lambda p: p["changes"].append(p["changes"][0]),
                       lambda p: p["changes"][0].update(attribute="ICT_ID")):
            with self.subTest(mutate=mutate):
                plan = copy.deepcopy(self.plan)
                mutate(plan)
                with self.assertRaises(ch.InputError):
                    ch.apply(self.source, plan, self.root / "refused")
                self.assertFalse((self.root / "refused").exists())

    def test_geometry_layer_foreign_field_and_xdata_loss_are_detected(self):
        mutations = [lambda d: setattr(d.modelspace().query("LINE")[0].dxf, "end", (9, 20, 0)),
                     lambda d: setattr(d.layers.get("PROCESS").dxf, "color", 1),
                     lambda d: setattr(d.modelspace().query("INSERT")[0].get_attrib("VENDOR_PRIVATE").dxf, "text", "lost"),
                     lambda d: d.modelspace().query("LINE")[0].discard_xdata("VENDOR_TEST")]
        for i, mutate in enumerate(mutations):
            doc = ch.load(self.source)
            mutate(doc)
            returned = self.root / f"wrong-{i}.dxf"
            doc.saveas(returned)
            with self.subTest(i=i):
                self.assertTrue(ch.compare(self.before, ch.snapshot(returned))["unexpected"])

    def test_empty_flattened_and_duplicate_ids_are_not_accepted_as_assets(self):
        for i in range(3):
            doc = ch.load(self.source)
            ref = doc.modelspace().query("INSERT")[0]
            if i == 0:
                ref.delete_attrib("ICT_ID")
            elif i == 1:
                doc.modelspace().delete_entity(ref)
            else:
                doc.modelspace().add_entity(ref.copy())
            path = self.root / f"invalid-{i}.dxf"
            doc.saveas(path)
            with self.subTest(i=i), self.assertRaises(ch.InputError):
                ch.snapshot(path)

    def test_existing_output_is_not_overwritten(self):
        ch.apply(self.source, self.plan, self.root / "proposal")
        with self.assertRaises(ch.InputError):
            ch.apply(self.source, self.plan, self.root / "proposal")

    def test_explicit_map_projection_retains_identity_and_rejects_a_guessed_match(self):
        spec = importlib.util.spec_from_file_location("cad_projection", Path(__file__).resolve().parents[1] /
                                                    "examples/cad-handoff/project_to_map.py")
        projection = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(projection)
        packet = self.root / "packet"
        ch.apply(self.source, self.plan, packet)
        mapping = {"site": "S", "plant": "P", "unit": "U", "assets": [
            {"id": "fixture/valve-01", "tag": "FV-101", "section": "instruments"}]}
        projection.project(packet / "candidate-context", mapping, self.root / "projection")
        sheet = json.loads((self.root / "projection/sheet.json").read_text())
        self.assertEqual(sheet["instruments"][0]["attributes"]["cad_size"], "DN65")
        self.assertEqual(sheet["lines"], [])
        mapping["assets"][0]["tag"] = "FV-102"
        with self.assertRaises(ValueError):
            projection.project(packet / "candidate-context", mapping, self.root / "wrong-match")
        self.assertFalse((self.root / "wrong-match").exists())


class ReceivingReview(unittest.TestCase):
    setUp = Handoff.setUp
    def test_native_return_is_explained_without_changing_the_strict_gate(self):
        root = Path(__file__).resolve().parents[1]
        source = root / "examples/cad-handoff/source/valve.dxf"
        returned = root / "examples/cad-handoff/native/qcad/returned.dxf"
        plan = json.loads(source.with_name("edit-plan.json").read_text(encoding="utf-8"))
        report = ch.review(source, returned, plan, self.root / "review")
        self.assertEqual(report["strict_status"], "differences")
        self.assertEqual(report["strict_difference_count"], 335)
        self.assertEqual(sum(report["entity_partitions"].values()), 333)
        self.assertEqual(len(report["header_changes"]), 54)
        self.assertEqual([x["status"] for x in report["asset_attributes"]].count("planned edit observed"), 3)
        self.assertFalse(any(x["status"] == "unexpected" for x in report["asset_attributes"]))
        style = [x for x in report["drawing_changes"] if "style" in x.get("fields", {})]
        self.assertTrue(any(x["fields"]["style"]["after"]["value"] == "textstyle3" for x in style))
        self.assertTrue(any(x["after_type"] == "VIEWPORT" and x["category"] == "added handle" for x in report["drawing_changes"]))
        self.assertEqual(report["acceptance"], "not performed")
        self.assertEqual(json.loads((self.root / "review/strict-comparison.json").read_text(encoding="utf-8")),
                         ch.compare(ch.snapshot(source), ch.snapshot(returned), plan))

    def test_planted_geometry_layer_and_foreign_attribute_remain_visible(self):
        doc = ch.load(self.source)
        doc.modelspace().query("LINE")[0].dxf.end = (999, 20, 0)
        doc.modelspace().query("INSERT")[0].get_attrib("VENDOR_PRIVATE").dxf.text = "unplanned"
        doc.layers.get("PROCESS").dxf.color = 1
        returned = self.root / "changed.dxf"
        doc.saveas(returned)
        report = ch.review(self.source, returned, None, self.root / "review")
        self.assertTrue(any("end" in x.get("fields", {}) for x in report["drawing_changes"]))
        self.assertTrue(any(x["attribute"] == "VENDOR_PRIVATE" and x["status"] == "unexpected" for x in report["asset_attributes"]))
        self.assertTrue(any(x["before_type"] == "LAYER" for x in report["entity_changes"]))
        self.assertEqual(report["strict_status"], "differences")

    def test_existing_destination_and_stale_plan_preserve_originals(self):
        original = self.source.read_bytes()
        out = self.root / "review"
        out.mkdir()
        (out / "keep.txt").write_text("retained", encoding="utf-8")
        with self.assertRaises(ch.InputError):
            ch.review(self.source, self.source, None, out)
        self.assertEqual((out / "keep.txt").read_text(), "retained")
        stale = copy.deepcopy(self.plan)
        stale["source_sha256"] = "0" * 64
        with self.assertRaises(ch.InputError):
            ch.review(self.source, self.source, stale, self.root / "stale")
        self.assertFalse((self.root / "stale").exists())
        self.assertEqual(self.source.read_bytes(), original)

    def test_identical_pair_and_escaped_attribute_do_not_imply_acceptance(self):
        doc = ch.load(self.source)
        doc.modelspace().query("INSERT")[0].get_attrib("VENDOR_PRIVATE").dxf.text = "<script>bad</script>"
        doc.saveas(self.source)
        out = self.root / "review"
        report = ch.review(self.source, self.source, None, out)
        self.assertEqual(report["strict_status"], "pass")
        self.assertEqual(report["acceptance"], "not performed")
        self.assertNotIn("<script>", (out / "REPORT.html").read_text(encoding="utf-8"))
        self.assertIn("&lt;script&gt;", (out / "REPORT.html").read_text(encoding="utf-8"))
        self.assertEqual((out / "originals/before.dxf").read_bytes(), self.source.read_bytes())

    def test_xdata_loss_stays_in_the_strict_queue_even_without_a_drawing_field_change(self):
        doc = ch.load(self.source)
        doc.modelspace().query("LINE")[0].discard_xdata("VENDOR_TEST")
        returned = self.root / "lost-xdata.dxf"
        doc.saveas(returned)
        report = ch.review(self.source, returned, None, self.root / "review")
        self.assertEqual(report["drawing_changes"], [])
        self.assertEqual(report["strict_status"], "differences")
        self.assertTrue(any("1000" in e["changed_groups"] for e in report["entity_changes"]))
        self.assertIn("XDATA", report["boundary"])

    def test_reassigned_handle_is_not_matched_by_geometry(self):
        doc = ch.load(self.source)
        line = doc.modelspace().query("LINE")[0]
        old = line.dxf.handle
        self.assertTrue(doc.entitydb.reset_handle(line, "FFF0"))
        returned = self.root / "renumbered.dxf"
        doc.saveas(returned)
        report = ch.review(self.source, returned, None, self.root / "review")
        queue = {x["handle"]: x for x in report["entity_changes"]}
        self.assertEqual(queue[old]["category"], "removed handle")
        self.assertEqual(queue["FFF0"]["category"], "added handle")
        self.assertEqual(report["strict_status"], "differences")
        self.assertIn("not added/removed physical objects", report["boundary"])

    def test_missing_planned_edit_and_cli_difference_exit_are_not_success(self):
        import subprocess
        import sys
        out = self.root / "review"
        run = subprocess.run([sys.executable, str(Path(ch.__file__)), "review", str(self.source), str(self.source),
                              "--plan", str(self.root / "plan.json"), "--out", str(out)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)  # missing input plan, no partial packet
        self.assertFalse(out.exists())
        (self.root / "plan.json").write_text(json.dumps(self.plan), encoding="utf-8")
        run = subprocess.run([sys.executable, str(Path(ch.__file__)), "review", str(self.source), str(self.source),
                              "--plan", str(self.root / "plan.json"), "--out", str(out)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        report = json.loads((out / "review.json").read_text(encoding="utf-8"))
        size = next(x for x in report["asset_attributes"] if x["attribute"] == "SIZE")
        self.assertEqual(size["status"], "planned edit missing or different")

    def test_malformed_plan_shapes_are_input_errors_before_packet_creation(self):
        cases = [[], None, dict(self.plan, changes=[None]), dict(self.plan, changes=[{"id": []}]),
                 dict(self.plan, changes=[dict(self.plan["changes"][0], reason=None)])]
        for i, plan in enumerate(cases):
            if plan is None:
                continue  # None means review without a plan; explicitly supported.
            with self.subTest(i=i), self.assertRaises(ch.InputError):
                ch.review(self.source, self.source, plan, self.root / "refused")
            self.assertFalse((self.root / "refused").exists())


if __name__ == "__main__":
    unittest.main()
