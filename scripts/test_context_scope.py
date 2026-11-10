"""Frozen literal-source scoped-package controls; fictional exposed records, no plant evidence."""
import copy
import csv
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

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "examples/map-component-cycle/inputs/development"
PUMP, OTHER, FIC, FT, FV = ["CF/P1/" + s for s in ("U1/P-101", "U2/P-101", "U1/FIC-101", "U1/FT-101", "U1/FV-101")]


class ScopedPacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="context-scope-")
        self.folder = Path(self.temp.name)
        self.calls = []
        self.contribution = self.folder / "contributions.csv"
        self.contribution.write_bytes(("Subject,Predicate,Source,Locator,Quote,Target\n" +
            f"{FIC},reads,NOTE,line 4,FIC-101 reads FT-101 and adjusts FV-101.,{FT}\n" +
            f"{FIC},commands,NOTE,line 4,FIC-101 reads FT-101 and adjusts FV-101.,{FV}\n").encode())

    def tearDown(self):
        evidence = os.environ.get("SCOPE_TEST_EVIDENCE")
        if evidence:
            dest = Path(evidence) / self.id().split(".")[-1]
            shutil.copytree(self.folder, dest)
            (dest / "calls.json").write_bytes(cp.encode(self.calls))
        self.temp.cleanup()

    def cli(self, *args, code=0, message=None):
        call = [sys.executable, "-B", "-S", str(ROOT / "scripts/context_workflow.py"), *map(str, args)]
        run = subprocess.run(call, cwd=self.folder, capture_output=True, timeout=60)
        self.calls.append({"args": list(map(str, args)), "code": run.returncode,
                           "stdout": run.stdout.decode(), "stderr": run.stderr.decode()})
        self.assertEqual(run.returncode, code, run.stderr.decode())
        if message:
            self.assertIn(message, run.stderr.decode())
        return json.loads(run.stdout if code == 0 else run.stderr)

    def full(self, name="full", revision=1, previous=None):
        out = self.folder / name
        args = ["prepare", "--records", RECORDS / ("rev" + str(revision)), "--site", "CF", "--plant", "P1",
                "--contributions", self.contribution, "--out", out]
        if previous:
            args += ["--previous", previous]
        self.cli(*args)
        return out

    def scope(self, source, item=PUMP, name="scoped"):
        preview = self.folder / (name + ".preview.json")
        result = self.cli("scope-preview", source, "--item", item, "--out", preview)
        out = self.folder / name
        self.cli("package-scope", source, "--item", item, "--permit-whole-files-preview", result["preview_sha256"], "--out", out)
        return out, json.loads(preview.read_bytes())

    def repair(self, packet):
        receipt = json.loads((packet / "RECEIPT.json").read_bytes())
        receipt["files"] = {k: v for k, v in cp.inventory(packet).items() if k != "RECEIPT.json"}
        (packet / "RECEIPT.json").write_bytes(cp.encode(receipt))

    def test_pump_actual_projection_omits_other_content_but_discloses_exact_mixed_whole_bytes(self):
        full = self.full()
        scoped, preview = self.scope(full)
        opened = cp.open_packet(scoped)
        basis = opened["basis"]
        self.assertNotIn(OTHER, [r["id"] for r in basis["entities"]])
        self.assertFalse(any(r["subject"] == OTHER for r in basis["claims"]))
        self.assertEqual({p.name for p in (scoped / "originals").iterdir()}, {"equipment.csv", "work-orders.csv", "datasheet.csv"})
        self.assertEqual((scoped / "originals/equipment.csv").read_bytes(), (RECORDS / "rev1/equipment.csv").read_bytes())
        self.assertIn(b"OTHER-101", (scoped / "originals/equipment.csv").read_bytes())
        self.assertEqual({r["value"] for r in basis["claims"] if r["subject"] == PUMP and r["predicate"] == "serial_number"}, {"OLD-101", "NEW-101"})
        self.assertEqual({r["value"] for r in basis["claims"] if r["subject"] == PUMP and r["predicate"] == "rated_flow"}, {"40", "45"})
        self.assertEqual(opened["draft"]["selection"]["entities"], [PUMP])
        self.assertTrue(preview["whole_files"])
        self.assertTrue(all(r["contains_unfiltered_whole_file_content"] for r in preview["whole_files"]))
        self.assertIn("unrelated", preview["qualification"])
        self.assertEqual(opened["scope"]["schema"], "engineering-context-scope-1")

    def test_whole_file_permission_is_exact_and_required_before_publication(self):
        full = self.full()
        out = self.folder / "denied"
        self.cli("package-scope", full, "--item", PUMP, "--permit-whole-files-preview", "0" * 64, "--out", out,
                 code=2, message="whole-file preview permission")
        self.assertFalse(out.exists())

    def test_outgoing_boundaries_and_incoming_subject_refs_retain_exact_edges_without_expansion(self):
        full = self.full()
        source = cp.open_packet(full)["basis"]
        controller, _ = self.scope(full, FIC, "controller")
        opened = cp.open_packet(controller)
        self.assertEqual({r["id"] for r in opened["basis"]["boundaries"]}, {FT, FV})
        edges = [r for r in source["relationships"] if r["subject"] == FIC]
        self.assertEqual(opened["basis"]["relationships"], edges)
        meter, _ = self.scope(full, FT, "meter")
        opened = cp.open_packet(meter)
        self.assertEqual(opened["scope"]["external_subject_references"], [FIC])
        self.assertFalse(any(r["subject"] == FIC for r in opened["basis"]["claims"]))
        self.assertEqual(opened["draft"]["selection"]["entities"], [FT])
        self.cli("query", meter, "--item", FIC, code=2, message="external_subject_reference")
        self.cli("materialize", meter, "--item", FIC, "--out", self.folder / "bad.json", code=2, message="external_subject_reference")
        result = self.cli("query", meter, "--item", FT)
        self.assertEqual(result["scope_coverage"]["external_subject_reference_count"], 1)
        review = self.folder / "review.html"
        self.cli("review", meter, "--out", review)
        self.assertIn("external_subject_reference", review.read_text(encoding="utf-8"))
        self.assertIn("unexpanded", review.read_text(encoding="utf-8"))

    def test_selected_original_mutation_and_structured_leak_refuse_specific_replay(self):
        full = self.full()
        packet, _ = self.scope(full)
        target = packet / "originals/equipment.csv"
        target.write_bytes(target.read_bytes().replace(b"OLD-101", b"BAD-101"))
        self.repair(packet)
        self.cli("verify", packet, code=2, message="source raw-byte binding mismatch")
        intact, _ = self.scope(full, name="intact")
        basis = json.loads((intact / "basis.json").read_bytes())
        leaked = next(r for r in cp.open_packet(full)["basis"]["claims"] if r["subject"] == OTHER)
        basis["claims"].append(leaked)
        (intact / "basis.json").write_bytes(cp.encode(basis))
        receipt = json.loads((intact / "RECEIPT.json").read_bytes());receipt["basis_sha256"] = cb.digest(basis)
        (intact / "RECEIPT.json").write_bytes(cp.encode(receipt));self.repair(intact)
        self.cli("verify", intact, code=2, message="scoped basis replay differs")

    def test_relocation_bundle_and_fresh_process_reopen_preserve_literal_scope(self):
        full = self.full();packet, _ = self.scope(full)
        delivery = self.folder / "delivery.json"
        result = self.cli("bundle", packet, "--out", delivery)
        shutil.rmtree(full);shutil.rmtree(packet)
        reopened = self.folder / "reopened"
        self.cli("unbundle", delivery, "--expected-sha256", result["sha256"], "--out", reopened)
        self.cli("verify", reopened)
        facts = self.cli("query", reopened, "--item", PUMP, "--field", "rated_flow")
        self.assertEqual({r["value"] for r in facts["alternatives"]}, {"40", "45"})
        self.assertFalse((reopened / "originals/instruments.csv").exists())

    def test_scoped_history_retains_original_selected_correction_and_field_only_qualification(self):
        full = self.full()
        edited = self.folder / "edited"
        self.cli("edit", full, "--item", PUMP, "--field", "draft_review_note", "--value", "Confirm nameplate.",
                 "--rationale", "Selected original proposal", "--out", edited)
        unrelated = self.folder / "unrelated"
        self.cli("edit", edited, "--item", FT, "--field", "draft_review_note", "--value", "PRIVATE OTHER NOTE",
                 "--rationale", "Out of selected scope", "--out", unrelated)
        revision = self.full("revision", 2, unrelated)
        packet, _ = self.scope(revision)
        opened = cp.open_packet(packet)
        original = next(r for r in cp.open_packet(revision)["basis"]["corrections"] if r["subject"] == PUMP)
        self.assertEqual(opened["basis"]["corrections"], [original])
        self.assertEqual(opened["draft"]["annotations"][0]["annotation"], original)
        self.assertIn("field", opened["scope"]["correction_qualification"])
        self.assertIn("not", opened["scope"]["correction_qualification"])
        for path in packet.rglob("basis.json"):
            self.assertNotIn("PRIVATE OTHER NOTE", path.read_text(encoding="utf-8"))
            self.assertNotIn(OTHER, path.read_text(encoding="utf-8"))
        self.assertFalse(any(p.name == "instruments.csv" for p in packet.rglob("*")))
        self.cli("verify", packet)


    def test_unselected_source_declaration_cannot_hide_in_scoped_manifest(self):
        packet, _ = self.scope(self.full())
        metadata = json.loads((packet / "scope.json").read_bytes())
        with (RECORDS / "rev1/source-register.csv").open(encoding="utf-8", newline="") as source:
            row = next(r for r in csv.DictReader(source) if r["DocumentID"] == "NOTE")
        metadata["source_input"]["declarations"].append(row)
        (packet / "scope.json").write_bytes(cp.encode(metadata));self.repair(packet)
        self.cli("verify", packet, code=2, message="scoped declaration closure differs")

    def test_scope_counts_distinguish_false_from_zero_before_component_digest_checks(self):
        packet, _ = self.scope(self.full())
        metadata = json.loads((packet / "scope.json").read_bytes())
        self.assertEqual(metadata["counts"]["external_subject_reference_count"], 0)
        metadata["counts"]["external_subject_reference_count"] = False
        (packet / "scope.json").write_bytes(cp.encode(metadata));self.repair(packet)
        self.cli("verify", packet, code=2, message="scoped coverage differs")

    def test_missing_selected_original_and_dropped_boundary_refuse_with_intact_positive(self):
        full = self.full();packet, _ = self.scope(full)
        self.cli("verify", packet)
        (packet / "originals/equipment.csv").unlink();self.repair(packet)
        self.cli("verify", packet, code=2, message="source raw-byte binding mismatch")
        controller, _ = self.scope(full, FIC, "controller")
        basis = json.loads((controller / "basis.json").read_bytes());basis["boundaries"].pop()
        (controller / "basis.json").write_bytes(cp.encode(basis));self.repair(controller)
        self.cli("verify", controller, code=2, message="scoped basis replay differs")

    def test_changed_selected_correction_fingerprint_cannot_relabel_an_original_proposal(self):
        full = self.full();edited = self.folder / "edited"
        self.cli("edit", full, "--item", PUMP, "--field", "draft_review_note", "--value", "Nameplate needed",
                 "--rationale", "Retained source limit", "--out", edited)
        packet, _ = self.scope(edited)
        basis = json.loads((packet / "basis.json").read_bytes());annotation = basis["corrections"][0]
        annotation["expected_content_fingerprint"] = "0" * 64
        annotation["id"] = "edit-" + cb.digest({k: v for k, v in annotation.items() if k != "id"})[:24]
        (packet / "basis.json").write_bytes(cp.encode(basis))
        manifest = json.loads((packet / "scope.json").read_bytes());manifest["correction_witnesses"][0]["annotation_id"] = annotation["id"]
        (packet / "scope.json").write_bytes(cp.encode(manifest))
        receipt = json.loads((packet / "RECEIPT.json").read_bytes());receipt["basis_sha256"] = cb.digest(basis)
        (packet / "RECEIPT.json").write_bytes(cp.encode(receipt));self.repair(packet)
        self.cli("verify", packet, code=2, message="selected correction field witness differs")

    def test_scoped_review_keeps_retained_proposals_visible_while_disabling_new_edits(self):
        full = self.full(); edited = self.folder / "edited"
        self.cli("edit", full, "--item", PUMP, "--field", "draft_review_note", "--value", "Retained value",
                 "--rationale", "Selected original rationale", "--out", edited)
        packet, _ = self.scope(edited)
        review = self.folder / "review.html"
        self.cli("review", packet, "--out", review)
        html = review.read_text(encoding="utf-8")
        self.assertIn("Selected original rationale", html)
        self.assertNotIn("byId('edit-section').hidden=true;", html,
                         "retained proposals share this section and must remain visible")
        self.assertIn("#edit-section label,#edit-section select,#edit-section textarea,#edit-section button", html)
        self.assertIn("Retained editorial proposals", html)
        self.cli("edit", packet, "--item", PUMP, "--field", "draft_review_note", "--value", "Denied",
                 "--rationale", "No unsupported scoped editing", "--out", self.folder / "denied-edit",
                 code=2, message="original permitted whole packet")

    def test_multi_hop_traversal_refuses_expanding_identity_only_external_subject(self):
        self.contribution.write_bytes(self.contribution.read_bytes() +
            f"{FT},reads,NOTE,line 4,FIC-101 reads FT-101 and adjusts FV-101.,{FIC}\n".encode())
        full = self.full(); packet, _ = self.scope(full, FT)
        self.cli("query", packet, "--item", FT, "--relation", "reads", "--depth", 1)
        self.cli("query", packet, "--item", FT, "--relation", "reads", "--depth", 2,
                 code=2, message="external_subject_reference")

    def test_explicit_retained_dependency_materializes_actual_versioned_supporting_evidence(self):
        dep = "CF/P1/U1/record:WO-801"
        full = self.full(); edited = self.folder / "edited"
        self.cli("edit", full, "--item", dep, "--field", "draft_review_note", "--value", "Check work-order close date",
                 "--rationale", "Retained dependency original rationale", "--out", edited)
        packet, _ = self.scope(edited)
        opened = cp.open_packet(packet); inventory = cp.inventory(packet)
        expected_note = next(a for a in opened["basis"]["corrections"] if a["subject"] == dep)
        default = self.folder / "default.json"
        self.cli("materialize", packet, "--out", default)
        self.assertEqual(default.read_bytes(), cp.encode(opened["draft"]))
        self.assertEqual(opened["draft"]["selection"]["entities"], [PUMP])
        actual = self.folder / "supporting.json"
        result = self.cli("materialize", packet, "--item", dep, "--out", actual)
        artifact = json.loads(actual.read_bytes())
        self.assertEqual(result["schema"], "engineering-scoped-component-materialization-1")
        self.assertEqual(artifact["schema"], result["schema"])
        self.assertEqual(artifact["selection"]["entities"], [dep])
        self.assertEqual(artifact["supporting_context"], [cb.View(opened["basis"]).inspect(dep)])
        self.assertEqual(artifact["supporting_context"][0]["entity"]["identity_role"], "maintenance_record")
        draft = artifact["component_draft"]
        self.assertEqual(draft["selection"], artifact["selection"])
        self.assertEqual(draft["annotations"][0]["annotation"], expected_note)
        self.assertIn("selected_field_source_replay_only", draft["annotations"][0]["verification"])
        self.assertTrue(all(not c["items"] and c["gaps"] for c in draft["components"].values()))
        self.assertIn("WO-801", artifact["readable_supporting_context"])
        self.assertIn("Closed order records replacement", artifact["readable_supporting_context"])
        self.assertIn("record 2", artifact["readable_supporting_context"])
        self.assertIn("not the omitted whole parent basis", artifact["qualification"])
        self.assertEqual(cp.inventory(packet), inventory)
        self.assertEqual(cp.open_packet(packet)["draft"]["selection"]["entities"], [PUMP])

    def test_full_legacy_and_compact_replay_bytes_stay_unchanged(self):
        compact = self.full()
        old_files = {n: (compact / n).read_bytes() for n in cp.inventory(compact)}
        self.scope(compact)
        cp.open_packet(compact)
        self.assertEqual({n: (compact / n).read_bytes() for n in cp.inventory(compact)}, old_files)
        legacy = self.folder / "legacy";shutil.copytree(compact, legacy)
        opened = cp.open_packet(legacy)
        (legacy / "drafts.json").write_bytes(cp.encode(opened["draft"]))
        self.repair(legacy)
        before = {n: (legacy / n).read_bytes() for n in cp.inventory(legacy)}
        self.scope(legacy, name="legacy-scoped")
        cp.open_packet(legacy)
        self.assertEqual({n: (legacy / n).read_bytes() for n in cp.inventory(legacy)}, before)


if __name__ == "__main__":
    unittest.main()
