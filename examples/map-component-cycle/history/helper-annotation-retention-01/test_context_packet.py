"""Fresh-process record intake, fixed-source answers, edits, revisions and tamper controls."""
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import context_basis as cb
import context_packet as cp
import context_components as cc

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/map-component-cycle/inputs"
KEY = json.loads((FIXTURE / "EXPECTED.json").read_bytes())
PUMP, OTHER, TANK, FT, FIC, FV = KEY["subjects"]


def load(path):
    return json.loads(Path(path).read_bytes())


def contributions(reads=FT):
    """Explicit supplied reading of the frozen NOTE; no interpretation accuracy claim."""
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=["Subject", "Predicate", "Source", "Locator", "Quote", "Target"],
                            lineterminator="\n")
    writer.writeheader()
    for predicate, target in (("reads", reads), ("commands", FV)):
        writer.writerow({"Subject": FIC, "Predicate": predicate, "Source": "NOTE", "Locator": "line 4",
                         "Quote": "FIC-101 reads " + reads.rsplit("/", 1)[-1] + " and adjusts FV-101.", "Target": target})
    return text.getvalue().encode("utf-8")


class PacketWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="context-packet-tests-")
        self.folder = Path(self.temp.name)
        self.contribution = self.folder / "contributions.csv"
        self.contribution.write_bytes(contributions())
        self.calls = []

    def tearDown(self):
        evidence = os.environ.get("CONTEXT_TEST_EVIDENCE")
        if evidence:
            target = Path(evidence) / self.id().rsplit(".", 1)[-1]
            target.mkdir(parents=True, exist_ok=False)
            (target / "calls.json").write_bytes(cp.encode(self.calls))
            for child in self.folder.iterdir():
                destination = target / child.name
                if child.is_dir():
                    shutil.copytree(child, destination)
                else:
                    shutil.copyfile(child, destination)
        self.temp.cleanup()

    def run_cli(self, *args, code=0, message=None):
        command = [sys.executable, "-B", "-S", str(ROOT / "scripts/context_workflow.py"), *map(str, args)]
        run = subprocess.run(command, cwd=self.folder, capture_output=True, timeout=60)
        stdout, stderr = run.stdout.decode("utf-8"), run.stderr.decode("utf-8")
        self.calls.append({"command": command, "exit_code": run.returncode,
                           "stdout": stdout, "stderr": stderr})
        self.assertEqual(run.returncode, code, stderr)
        if message:
            self.assertIn(message, stderr)
        return json.loads(stdout if code == 0 else stderr)

    def prepare(self, revision, name, previous=None, records=None, extra=()):
        target = self.folder / name
        args = ["prepare", "--records", records or FIXTURE / "development" / ("rev" + str(revision)),
                "--site", KEY["site"], "--plant", KEY["plant"], "--out", target,
                "--contributions", self.contribution, *extra]
        if previous:
            args += ["--previous", previous]
        self.run_cli(*args)
        return target

    def test_prepare_replays_original_column_order_in_new_process(self):
        packet = self.prepare(1, "r1")
        result = self.run_cli("verify", packet)
        self.assertTrue(result["verified"])
        self.assertEqual(result["history_depth"], 0)
        for original in (FIXTURE / "development/rev1").iterdir():
            self.assertEqual((packet / "originals" / original.name).read_bytes(), original.read_bytes())

    def test_first_result_and_three_drafts_use_frozen_source_facts(self):
        packet = self.prepare(1, "r1")
        serial = self.run_cli("query", packet, "--item", PUMP, "--field", "serial_number")
        self.assertEqual(serial["state"], "disputed")
        self.assertCountEqual([r["value"] for r in serial["alternatives"]], ["OLD-101", "NEW-101"])
        self.assertNotIn("FUTURE-101", json.dumps(serial))
        flow = self.run_cli("query", packet, "--item", PUMP, "--field", "rated_flow")
        self.assertCountEqual([r["value"] for r in flow["alternatives"]], KEY["revisions"][0]["flow_alternatives"])
        self.assertEqual({r["unit"] for r in flow["alternatives"]}, {"m3/h"})
        self.run_cli("query", packet, "--item", "P-101", code=2, message="ambiguous item")
        other = self.run_cli("query", packet, "--item", OTHER, "--field", "serial_number")
        self.assertEqual([r["value"] for r in other["alternatives"]], ["OTHER-101"])
        draft = load(packet / "drafts.json")["components"]
        fields = [draft[name]["items"][PUMP]["fields"]["rated_flow"]
                  for name in ("equipment_instrument_list", "item_datasheet_scaffold")]
        self.assertEqual(fields[0], fields[1])
        loop = draft["loop_control_narrative_outline"]["items"][FIC]["fields"]
        for field, target in (("reads", FT), ("commands", FV)):
            self.assertEqual([r["object"] for r in loop[field]["relationships"]], [target])
            self.assertEqual(loop[field]["relationships"][0]["roots"], ["NOTE"])
        self.assertEqual(loop["trip_settings"]["state"], "unknown")
        self.assertEqual(loop["fail_position"]["state"], "unknown")

    def test_three_revisions_edit_reopen_and_reimport_keep_basis(self):
        r1 = self.prepare(1, "r1")
        edit = KEY["manual_edit_control"]
        edited = self.folder / "edited"
        self.run_cli("edit", r1, "--item", edit["subject"], "--field", edit["field"],
                     "--value", edit["value"], "--rationale", "Awaiting permitted nameplate evidence", "--out", edited)
        initial = load(r1 / "drafts.json")["components"]
        self.assertEqual(load(edited / "drafts.json")["components"], initial)
        r2 = self.prepare(2, "r2", edited)
        impact = self.run_cli("compare", edited, r2)
        content = {(r["component"], r["subject"], r["field"]) for r in impact["changes"]
                   if r["change"] == "content_changed"}
        self.assertEqual(content, {("equipment_instrument_list", PUMP, "rated_flow"),
                                   ("item_datasheet_scaffold", PUMP, "rated_flow")})
        self.assertTrue(any(r["field"] == "design_temperature" and r["change"] == "basis_changed"
                            for r in impact["changes"]))
        self.assertFalse(any(r["subject"] in (OTHER, FT, FIC, FV) for r in impact["changes"]))
        self.assertEqual(load(r1 / "mappings.json"), load(r2 / "mappings.json"))
        r3 = self.prepare(3, "r3", r2)
        flow = self.run_cli("query", r3, "--item", PUMP, "--field", "rated_flow")
        self.assertEqual([r["value"] for r in flow["alternatives"] if r["active_source"]], ["40"])
        self.assertEqual([r["value"] for r in flow["alternatives"] if not r["active_source"]], ["50"])
        self.assertEqual(next(r for r in flow["alternatives"] if r["source"] == "DS")["source_record"]["status"], "withdrawn")
        annotations = load(r3 / "drafts.json")["annotations"]
        self.assertEqual(annotations[0]["annotation"]["value"], edit["value"])
        again = self.folder / "reimported"
        self.run_cli("reimport", r3, "--draft", r3 / "drafts.json", "--out", again)
        self.assertEqual(load(again / "basis.json")["claims"], load(r3 / "basis.json")["claims"])
        self.assertEqual(load(again / "basis.json")["sources"], load(r3 / "basis.json")["sources"])
        self.assertEqual(len(load(again / "basis.json")["corrections"]), 1)
        relocated = self.folder / "relocated"
        shutil.copytree(again, relocated)
        self.run_cli("verify", relocated)
        self.run_cli("query", relocated, "--item", PUMP, "--field", "rated_flow")

    def rehash(self, packet):
        receipt = load(packet / "RECEIPT.json")
        receipt["files"] = {name: value for name, value in cp.inventory(packet).items() if name != "RECEIPT.json"}
        (packet / "RECEIPT.json").write_bytes(cp.encode(receipt))

    def test_raw_tampering_and_rehashed_derived_fact_have_specific_refusals(self):
        packet = self.prepare(1, "r1")
        raw = (packet / "originals/equipment.csv").read_bytes()
        (packet / "originals/equipment.csv").write_bytes(raw.replace(b"OLD-101", b"BAD-101"))
        self.run_cli("verify", packet, code=2, message="file inventory differs")
        self.rehash(packet)
        self.run_cli("verify", packet, code=2, message="raw-byte binding mismatch")
        (packet / "originals/equipment.csv").write_bytes(raw)
        draft = load(packet / "drafts.json")
        draft["components"]["item_datasheet_scaffold"]["items"][PUMP]["fields"]["rated_flow"]["state"] = "known"
        (packet / "drafts.json").write_bytes(cp.encode(draft))
        self.rehash(packet)
        self.run_cli("verify", packet, code=2, message="component views do not reproduce")

    def test_rehashed_impact_or_unknown_artifact_is_not_silently_accepted(self):
        r1 = self.prepare(1, "r1")
        r2 = self.prepare(2, "r2", r1)
        (r2 / "changes.json").write_bytes(cp.encode({"changes": []}))
        self.rehash(r2)
        self.run_cli("verify", r2, code=2, message="revision impact does not reproduce")
        (r1 / "unaccounted.txt").write_bytes(b"Not part of the declared receiving contract")
        self.rehash(r1)
        self.run_cli("verify", r1, code=2, message="unaccounted packet artifact")

    def test_existing_output_and_receiving_size_limit_refuse_without_replacement(self):
        packet = self.prepare(1, "r1")
        before = (packet / "RECEIPT.json").read_bytes()
        self.run_cli("prepare", "--records", FIXTURE / "development/rev1", "--site", "CF", "--plant", "P1",
                     "--out", packet, code=2, message="output exists")
        self.assertEqual(before, (packet / "RECEIPT.json").read_bytes())
        destination = self.folder / "too-large.json"
        self.run_cli("bundle", packet, "--out", destination, "--max-bytes", 100,
                     code=2, message="exceeds declared receiving byte limit")
        self.assertFalse(destination.exists())
        delivery = self.folder / "delivery.json"
        bundled = self.run_cli("bundle", packet, "--out", delivery)
        reopened = self.folder / "reopened"
        # The old path disappears before decoding/replay; no external reference is needed.
        packet.rename(self.folder / "old-packet-path-no-longer-exists")
        self.run_cli("unbundle", delivery, "--out", reopened, "--expected-sha256", bundled["sha256"])
        verified = self.run_cli("verify", reopened)
        self.assertEqual(verified["receipt_sha256"], bundled["packet_receipt_sha256"])

    def test_delivery_path_escape_and_changed_file_are_specific_refusals(self):
        packet = self.prepare(1, "r1")
        delivery = self.folder / "delivery.json"
        self.run_cli("bundle", packet, "--out", delivery)
        original = load(delivery)
        changed = copy.deepcopy(original)
        changed["files"][0]["path"] = "../escaped.txt"
        delivery.write_bytes(cp.encode(changed))
        self.run_cli("unbundle", delivery, "--out", self.folder / "escape-result", code=2,
                     message="unsafe packet path")
        self.assertFalse((self.folder / "escaped.txt").exists())
        changed = copy.deepcopy(original)
        changed["files"][0]["data"] = "YWx0ZXJlZA=="
        delivery.write_bytes(cp.encode(changed))
        self.run_cli("unbundle", delivery, "--out", self.folder / "changed-result", code=2,
                     message="delivery raw-byte binding mismatch")

    def test_fabricated_correction_cannot_be_emitted_as_verified_packet(self):
        packet = self.prepare(1, "r1")
        old = cp.open_packet(packet)
        basis = copy.deepcopy(old["basis"])
        edit = cc.new_annotation(basis, PUMP, "manufacturer", "Fabricated", "Supplied proposal")
        edit["roots"] = ["NONEXISTENT"]
        edit["id"] = "edit-" + cb.digest({k: v for k, v in edit.items() if k != "id"})[:24]
        basis["corrections"].append(edit)
        target = self.folder / "forged"
        with self.assertRaisesRegex(cb.ContextError, "editorial correction lineage"):
            cp.emit(target, basis, cp.source_bytes(packet), load(packet / "mappings.json"), old["config"],
                    contribution=self.contribution.read_bytes(), previous=old)
        self.assertFalse(target.exists())

    def test_relationship_edit_rebases_after_real_source_and_link_revision(self):
        r1 = self.prepare(1, "r1")
        edited = self.folder / "edited"
        self.run_cli("edit", r1, "--item", FIC, "--field", "reads", "--value", "Verify the input",
                     "--rationale", "Read the returned note", "--out", edited)
        row = load(edited / "basis.json")["corrections"][0]
        self.assertEqual(row["roots"], ["NOTE"])
        self.assertEqual(row["field_kind"], "relationship")
        records = self.folder / "revised-records"
        shutil.copytree(FIXTURE / "development/rev2", records)
        note = records / "engineering-note.txt"
        note.write_bytes(note.read_bytes().replace(b"FIC-101 reads FT-101", b"FIC-101 reads FV-101"))
        register = records / "source-register.csv"
        with register.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        next(r for r in rows if r["DocumentID"] == "NOTE")["Revision"] = "2"
        with register.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader(); writer.writerows(rows)
        self.contribution.write_bytes(contributions(FV))
        revised = self.prepare(2, "revised", edited, records=records)
        wrapped = load(revised / "drafts.json")["annotations"][0]
        self.assertEqual(wrapped["state"], "needs_rebase")
        self.assertEqual(wrapped["annotation"], row)
        self.run_cli("verify", revised)

    def test_selection_hides_other_note_without_losing_private_edit_on_regeneration(self):
        r1 = self.prepare(1, "r1")
        edited = self.folder / "edited"
        self.run_cli("edit", r1, "--item", OTHER, "--field", "private_note", "--value", "OTHER UNIT DETAIL",
                     "--rationale", "Applies to another unit", "--out", edited)
        selected = self.prepare(2, "selected", edited, extra=("--item", PUMP))
        self.assertNotIn("OTHER UNIT DETAIL", (selected / "drafts.json").read_text(encoding="utf-8"))
        self.assertNotIn("OTHER UNIT DETAIL", (selected / "datasheets.md").read_text(encoding="utf-8"))
        self.assertIn("OTHER UNIT DETAIL", (selected / "basis.json").read_text(encoding="utf-8"))
        all_items = self.prepare(3, "all-items", selected)
        self.assertEqual(load(all_items / "drafts.json")["annotations"][0]["annotation"]["value"], "OTHER UNIT DETAIL")
        self.run_cli("verify", all_items)

    def test_valid_api_annotations_survive_ordinary_edit_and_reimport(self):
        packet = self.prepare(1, "r1")
        old = cp.open_packet(packet)
        note = cc.new_annotation(old["basis"], PUMP, "manufacturer", "Check permitted nameplate", "Not supplied")
        annotated = self.folder / "api-annotated"
        cp.emit(annotated, old["basis"], cp.source_bytes(packet), load(packet / "mappings.json"), old["config"],
                annotations=[note], contribution=self.contribution.read_bytes())
        self.run_cli("verify", annotated)
        edited = self.folder / "edited"
        self.run_cli("edit", annotated, "--item", PUMP, "--field", "model", "--value", "Check model",
                     "--rationale", "Await evidence", "--out", edited)
        with self.subTest(path="ordinary edit"):
            self.assertEqual({a["annotation"]["field"] for a in load(edited / "drafts.json")["annotations"]},
                             {"manufacturer", "model"})
            self.assertEqual(len(load(edited / "basis.json")["corrections"]), 2)
        reimported = self.folder / "reimported"
        self.run_cli("reimport", annotated, "--draft", annotated / "drafts.json", "--out", reimported)
        with self.subTest(path="own draft reimport"):
            self.assertEqual(load(reimported / "drafts.json")["annotations"][0]["annotation"], note)


if __name__ == "__main__":
    unittest.main()
