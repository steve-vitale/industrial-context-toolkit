"""Source-known equipment bridge controls; actual existing generator CPU execution."""
import copy
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import context_basis as cb
import context_components as cc
import context_generator as cg
import context_packet as cp

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "examples/map-component-cycle/inputs/development/rev1"
P1, P2, TANK = "CF/P1/U1/P-101", "CF/P1/U2/P-101", "CF/P1/U1/TK-101"
ORACLE = {P1: ("pump", "Feed pump"), P2: ("pump", "Other unit pump"), TANK: ("tank", "Water feed tank")}


class GeneratorBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.packet = cp.prepare(RECORDS, self.root / "packet", "CF", "P1")
        self.opened = cp.open_packet(self.packet)

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, "-B", "-S", str(ROOT / "scripts/context_workflow.py"), *map(str,args)],
                                capture_output=True, timeout=60)
        self.assertEqual(result.returncode, code, result.stderr.decode("utf8", "replace"))
        return json.loads(result.stdout if code == 0 else result.stderr)

    def altered(self, change):
        opened = copy.deepcopy(self.opened)
        change(opened["basis"])
        cb.validate(opened["basis"])
        opened["draft"] = cc.generate(opened["basis"])
        return opened

    def test_three_source_known_units_and_reversible_safe_identity_without_facts_added(self):
        model, projection = cg.project(self.opened)
        self.assertEqual(len(model["units"]), 3)
        self.assertEqual({projection["identity_map"][u["id"]]["id"]: (u["type"], u["name"]) for u in model["units"]}, ORACLE)
        self.assertNotEqual(cg.export_id(P1), cg.export_id(P2))
        self.assertEqual(model["streams"], [])
        self.assertEqual(model["instruments"], [])
        self.assertEqual(model["final_elements"], [])
        self.assertTrue(all("layout" not in u and "uom" not in u and u["verification"]["status"] == "unverified" for u in model["units"]))
        self.assertEqual(projection["basis_sha256"], self.opened["draft"]["basis_sha256"])
        self.assertEqual(projection["context"][P1]["fields"]["serial_number"], cb.View(self.opened["basis"]).field(P1,"serial_number"))
        self.assertTrue(any(o["subject"].endswith("FT-101") for o in projection["omissions"]))

    def test_existing_generator_really_runs_and_export_contains_no_measurement_bindings(self):
        before = cp.inventory(self.packet)
        target = self.root / "generated-context"
        answer = self.cli("generate", self.packet, "--out", target)
        self.assertEqual(answer["units"], 3)
        self.assertTrue(self.cli("verify-generated", self.packet, target)["verified"])
        self.assertEqual(cp.inventory(self.packet), before)
        tags = cb.read_json(target / "generated/ignition/tags.json")
        nodes = []
        def walk(node):
            nodes.append(node)
            for child in node.get("tags", []): walk(child)
        walk(tags)
        self.assertEqual(sum(n.get("tagType") == "UdtInstance" for n in nodes), 3)
        self.assertFalse(any(n.get("tagType") == "AtomicTag" for n in nodes))
        sheet = list(csv.DictReader(io.StringIO((target / "generated/pi/pi_builder_af.csv").read_text(encoding="utf-8-sig"))))
        self.assertFalse(any("PI Point" in row.values() or "Attribute" in row.values() for row in sheet))
        svg = (target / "generated/svg/overview.svg").read_text(encoding="utf8")
        self.assertIn("Positions placed in flow order; links are logical, not pipe routes.", svg)
        self.assertNotIn('class="pipe" data-stream=',svg)
        for u in cb.read_json(target / "model.json")["units"]:
            self.assertTrue((target / "generated/svg" / (u["id"]+".svg")).is_file())
        self.assertIn("3 units, 0 streams, 0 instruments, 0 final elements",(target / "generator.stdout.txt").read_text())

    def test_unsupported_class_missing_name_and_missing_unit_scope_omit_without_defaults(self):
        for predicate,value in [("class","unsupported_magic"),("description",None),("description","=UNSAFE()")]:
            with self.subTest(predicate=predicate,value=value):
                def change(basis):
                    for c in basis["claims"]:
                        if c["subject"] == P1 and c["predicate"] == predicate: c["value"] = value
                model, projected = cg.project(self.altered(change))
                self.assertNotIn(cg.export_id(P1), projected["identity_map"])
                self.assertTrue(any(o["subject"] == P1 for o in projected["omissions"]))
                self.assertEqual(len(model["units"]),2)
        def scope(basis):
            entity = next(e for e in basis["entities"] if e["id"] == P1)
            entity["scope"] = basis["namespace"]
        self.assertNotIn(cg.export_id(P1), cg.project(self.altered(scope))[1]["identity_map"])
        with self.assertRaisesRegex(cb.ContextError,"entity tag"):
            self.altered(lambda b: next(e for e in b["entities"] if e["id"] == P1).update(tag=""))

    def test_disputed_rejected_withdrawn_or_proposed_required_facts_are_not_selected(self):
        for fault in ("disputed","rejected","withdrawn","proposed","role"):
            with self.subTest(fault=fault):
                def change(basis):
                    claim = next(c for c in basis["claims"] if c["subject"] == P1 and c["predicate"] == "class")
                    if fault == "disputed":
                        other = copy.deepcopy(claim);other.update(value="tank",locator="independent fixture occurrence")
                        other["id"] = cb.record_id("claim",other);basis["claims"].append(other)
                    elif fault == "withdrawn":
                        next(s for s in basis["sources"] if s["id"] == claim["source"])["status"] = "withdrawn"
                    elif fault == "role": claim.update(role="proposal",id=cb.record_id("claim",{**claim,"role":"proposal"}))
                    else: claim["review"]["status"] = fault
                _,projection = cg.project(self.altered(change))
                self.assertNotIn(cg.export_id(P1),projection["identity_map"])
                field = projection["context"][P1]["fields"]["class"]
                self.assertTrue(field["alternatives"])

    def test_selection_and_editorial_proposals_keep_source_evidence_without_promoting_edit(self):
        edit = cc.new_annotation(self.opened["basis"],P1,"description","Revised proposed name","Check exact permitted source")
        edited = cp.write_edited(self.packet,self.root/"edited",annotation=edit)
        selected = cp.open_packet(edited)
        selected["draft"] = cc.generate(selected["basis"],item=P1,history_bases=selected["history_bases"])
        model,projected = cg.project(selected)
        self.assertEqual(len(model["units"]),1)
        self.assertEqual(model["units"][0]["name"],"Feed pump")
        self.assertEqual(projected["editorial_proposals"][0]["annotation"],edit)
        evidence = projected["context"][P1]["fields"]["class"]["alternatives"][0]
        self.assertTrue(evidence["source_record"]["sha256"])
        self.assertTrue(evidence["source_lineage"])
        self.assertTrue(evidence["locator"])
        self.assertTrue(evidence["roots"])

    def test_mutated_model_projection_output_source_and_method_refuse(self):
        target=self.root/"exports";cg.write(self.packet,target)
        for relative in ("model.json","projection.json","generated/svg/overview.svg","RECEIPT.json"):
            with self.subTest(relative=relative):
                f=target/relative;before=f.read_bytes()
                if relative.endswith("json"):
                    doc=json.loads(before);doc["mutant"]=True;f.write_bytes(cp.encode(doc))
                else:f.write_bytes(before+b"changed")
                with self.assertRaises(cb.ContextError):cg.verify(self.packet,target)
                f.write_bytes(before)
        with patch.object(cg,"pins",return_value={"different":"method"}):
            with self.assertRaisesRegex(cb.ContextError,"method changed"):cg.verify(self.packet,target)
        original=self.packet/"originals/equipment.csv";before=original.read_bytes();original.write_bytes(before+b"changed")
        with self.assertRaises(cb.ContextError):cg.verify(self.packet,target)

    def test_actual_human_svg_bounds_names_and_placeholder_disclosures(self):
        import xml.etree.ElementTree as ET
        target = self.root / "human-scaffold"
        cg.write(self.packet, target)
        model = cb.read_json(target / "model.json")
        projection = cb.read_json(target / "projection.json")
        tags = cb.read_json(target / "generated/ignition/tags.json")
        types = tags["tags"][0]["tags"]
        instances = {n["name"]: n for n in tags["tags"][1]["tags"]}
        sheet = list(csv.DictReader(io.StringIO((target / "generated/pi/pi_builder_af.csv").read_text(encoding="utf-8-sig"))))
        for u in model["units"]:
            identity = projection["identity_map"][u["id"]]
            self.assertEqual(u["presentation"], {"tag": identity["tag"], "scope": identity["scope"]})
            tree = ET.parse(target / "generated/svg" / (u["id"] + ".svg"))
            texts = [n for n in tree.iter() if n.tag.endswith("text")]
            visible = " ".join(n.text or "" for n in texts)
            for text in (identity["tag"], identity["scope"], u["name"]):
                self.assertIn(text, visible)
                self.assertIn(text, instances[u["id"]]["documentation"])
                self.assertTrue(any(row.get("Name") == u["id"] and text in row.get("Description", "") for row in sheet))
            self.assertNotIn(u["id"], visible)
            height = float(tree.getroot().get("height"))
            for line in texts:
                width = float(line.get("textLength"))
                self.assertLessEqual(width, 240)
                self.assertGreaterEqual(150 - width / 2, 0)
                self.assertLessEqual(150 + width / 2, 300)
                self.assertLessEqual(float(line.get("y")) + 150, height)
            self.assertEqual(instances[u["id"]]["parameters"]["BasePath"]["value"],
                             "ns=1;s=" + model["meta"]["model_id"] + "." + u["id"])
        for t in types:
            self.assertEqual(t["parameters"]["BasePath"]["value"], "")
            self.assertEqual(t["parameters"]["OPCServer"]["value"], "Ignition OPC UA Server")
            self.assertEqual(t["tags"], [])
        readme = (target / "README.md").read_text(encoding="utf8")
        self.assertNotIn("Empty Ignition UDT BasePath/OPCServer", readme)
        self.assertIn("Ignition OPC UA Server", readme)
        self.assertIn("ns=1;s=context_", readme)

    def test_optional_presentation_wraps_long_source_text_without_discarding_original(self):
        import generate
        model, projection = cg.project(self.opened)
        model["units"][0]["name"] = "Long source name " * 30
        prepared = generate._auto_layout(generate._mark_finals(model))
        self.assertEqual(generate.validate(prepared), [])
        svg = generate.unit_svg(prepared, prepared["units"][0])
        self.assertIn(model["units"][0]["name"], svg)
        self.assertTrue(all(len(line) <= 28 for line in generate._presentation_lines(model["units"][0])))
        self.assertGreater(prepared["units"][1]["layout"]["y"] - prepared["units"][0]["layout"]["y"],260)
        for bad in ({"tag":"P", "scope":"U", "extra":"invented"}, {"tag":"", "scope":"U"}, {"tag":"P", "scope":False}):
            mutated = copy.deepcopy(prepared);mutated["units"][0]["presentation"] = bad
            self.assertTrue(any("presentation" in error for error in generate.validate(mutated)))

    def test_existing_output_input_packet_and_zero_eligible_refuse_before_publish(self):
        target=self.root/"existing";target.mkdir();(target/"user.txt").write_text("retain")
        with self.assertRaisesRegex(cb.ContextError,"output exists"):cg.write(self.packet,target)
        self.assertEqual((target/"user.txt").read_text(),"retain")
        with self.assertRaisesRegex(cb.ContextError,"outside input packet"):cg.write(self.packet,self.packet/"nested")
        empty=self.altered(lambda b: b["claims"].clear())
        with self.assertRaisesRegex(cb.ContextError,"no supported"):
            cg.expected_files(empty,self.root)
        self.assertFalse((self.root/"model.json").exists())


if __name__ == "__main__":
    unittest.main()
