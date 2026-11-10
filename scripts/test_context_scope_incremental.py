"""Causal local scoped revisions; exact prior bytes, no managed receiving claim."""
import copy
import json
import os
from pathlib import Path
import shutil
import unittest

import context_basis as cb
import context_packet as cp
import context_scope as cs
import test_context_scope_identity as fixture


class IncrementalScopeTests(unittest.TestCase):
    setUp = fixture.ScopedIdentityTests.setUp
    full = fixture.ScopedIdentityTests.full
    cli = fixture.ScopedIdentityTests.cli
    repair = fixture.ScopedIdentityTests.repair

    def tearDown(self):
        evidence = os.environ.get("SCOPE_INCREMENTAL_TEST_EVIDENCE")
        if evidence:
            target = Path(evidence) / self.id().split(".")[-1]
            shutil.copytree(self.root, target)
            (target / "calls.json").write_bytes(cp.encode(self.calls))
        self.temp.cleanup()

    def scoped(self, full, name, previous=None, unit=None):
        args = ["--scope", unit] if unit else ["--item", fixture.PUMP]
        if previous: args += ["--previous-scoped", previous]
        preview = self.root / (name + ".preview.json")
        result = self.cli("scope-preview", full, *args, "--out", preview)
        out = self.root / name
        self.cli("package-scope", full, *args, "--permit-whole-files-preview", result["preview_sha256"], "--out", out)
        return out, json.loads(preview.read_bytes())

    def assert_marker(self, current, prior):
        opened, old = cp.open_packet(current), cp.open_packet(prior)
        self.assertEqual(opened["receipt"]["previous_receipt_sha256"], old["receipt_sha256"])
        self.assertEqual(opened["scope"]["incremental_history"], {
            "schema": "engineering-context-incremental-history-1",
            "previous_scoped_receipt_sha256": old["receipt_sha256"],
            "previous_original_receipt_sha256": old["scope"]["source_packet_receipt_sha256"]})
        self.assertEqual(cp.inventory(prior), cp.inventory(current / "previous"))
        for name in cp.inventory(prior):
            self.assertEqual((prior / name).read_bytes(), (current / "previous" / name).read_bytes())

    def test_causal_r1_then_r2_then_r3_preserves_delivered_bytes_and_withdrawal(self):
        r1 = self.full(); s1, p1 = self.scoped(r1, "s1")
        self.cli("bundle", s1, "--out", self.root / "sent-r1.json")
        old = cp.inventory(s1)
        # R2 inputs are prepared only after R1 has been independently delivered.
        r2 = self.full(2, "r2", r1); s2, p2 = self.scoped(r2, "s2", s1)
        self.assert_marker(s2, s1)
        self.assertEqual(cp.inventory(s1), old)
        self.assertNotEqual(p1, p2)
        self.assertEqual(p2["previous_scoped_anchor"], cp.open_packet(s2)["scope"]["incremental_history"])
        self.assertEqual(self.cli("query", s2, "--item", "P-201", "--field", "class")["subject"], fixture.PUMP)
        self.cli("bundle", s2, "--out", self.root / "sent-r2.json")
        r3 = self.full(3, "r3", r2); s3, _ = self.scoped(r3, "s3", s2)
        self.assert_marker(s3, s2)
        self.cli("query", s3, "--item", "P-201", code=2, message="item not found")
        self.assertEqual(self.cli("query", s3 / "previous", "--item", "P-201", "--field", "class")["subject"], fixture.PUMP)
        wire = self.root / "sent-r3.json"; result = self.cli("bundle", s3, "--out", wire)
        self.cli("unbundle", wire, "--expected-sha256", result["sha256"], "--out", self.root / "fresh")
        self.assertEqual(cp.inventory(s3), cp.inventory(self.root / "fresh"))

    def test_wrong_ancestor_policy_and_changed_original_commitment_refuse(self):
        r1 = self.full(); s1, _ = self.scoped(r1, "s1")
        r2 = self.full(2, "r2", r1)
        records = self.root / "alternate-records"; shutil.copytree(fixture.FIXTURE / "rev1", records)
        path = records / "equipment.csv"; path.write_bytes(path.read_bytes().replace(b"Feed pump", b"Changed feed pump"))
        alt = self.full(name="alt", records=records); wrong, _ = self.scoped(alt, "wrong")
        self.cli("scope-preview", r2, "--item", fixture.PUMP, "--previous-scoped", wrong,
                 "--out", self.root / "bad-ancestor.json", code=2, message="original ancestor")
        self.cli("scope-preview", r2, "--scope", "IX/P1/U1", "--previous-scoped", s1,
                 "--out", self.root / "bad-policy.json", code=2, message="selection policy")
        elsewhere = self.root / "elsewhere"
        self.cli("prepare", "--records", fixture.FIXTURE / "rev1", "--site", "ELSE", "--plant", "P1",
                 "--identity-crosswalk", "identity-crosswalk.csv", "--out", elsewhere)
        other_preview = self.cli("scope-preview", elsewhere, "--item", "ELSE/P1/U1/FP-1001", "--out", self.root / "else-preview.json")
        other_scope = self.root / "else-scope"
        self.cli("package-scope", elsewhere, "--item", "ELSE/P1/U1/FP-1001", "--permit-whole-files-preview",
                 other_preview["preview_sha256"], "--out", other_scope)
        self.cli("scope-preview", r2, "--item", fixture.PUMP, "--previous-scoped", other_scope,
                 "--out", self.root / "bad-namespace.json", code=2, message="namespace or selection policy")
        forged = self.root / "forged"; shutil.copytree(s1, forged)
        manifest = cb.read_json(forged / "scope.json"); manifest["source_basis_sha256"] = "0" * 64
        (forged / "scope.json").write_bytes(cp.encode(manifest)); self.repair(forged)
        self.cli("scope-preview", r2, "--item", fixture.PUMP, "--previous-scoped", forged,
                 "--out", self.root / "bad-original.json", code=2, message="prior scoped projection")

    def test_same_unit_policy_may_add_real_source_identity_without_rewriting_old_selection(self):
        r1 = self.full(); s1, _ = self.scoped(r1, "s1", unit="IX/P1/U1")
        records = self.root / "new-records"; shutil.copytree(fixture.FIXTURE / "rev2", records)
        path = records / "equipment.csv"
        rows = path.read_text(encoding="utf-8").splitlines()
        rows.append(rows[1].replace("FP-1001", "FP-1002"))
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        r2 = self.full(2, "r2", r1, records)
        s2, _ = self.scoped(r2, "s2", s1, unit="IX/P1/U1")
        self.assert_marker(s2, s1)
        self.assertNotIn("IX/P1/U1/FP-1002", cp.open_packet(s1)["scope"]["selected_entities"])
        self.assertIn("IX/P1/U1/FP-1002", cp.open_packet(s2)["scope"]["selected_entities"])

    def test_intervening_edit_frame_and_original_correction_are_retained(self):
        r1 = self.full(); s1, _ = self.scoped(r1, "s1")
        edited = self.root / "edited"
        self.cli("edit", r1, "--item", fixture.PUMP, "--field", "description", "--value", "Check seal source",
                 "--rationale", "Retained selected correction", "--out", edited)
        r2 = self.full(2, "r2", edited); s2, preview = self.scoped(r2, "s2", s1)
        self.assert_marker(s2 / "previous", s1)
        self.assert_marker(s2, s2 / "previous")
        self.assertEqual(cp.open_packet(s2)["receipt"]["history_depth"], 2)
        self.assertEqual(cp.open_packet(s2)["basis"]["corrections"], cp.open_packet(r2)["basis"]["corrections"])
        self.assertEqual(preview["previous_scoped_anchor"]["previous_scoped_receipt_sha256"], cp.open_packet(s1)["receipt_sha256"])
        self.assertEqual(cp.inventory(s1), cp.inventory(s2 / "previous" / "previous"))
        # A forged selected-field witness refuses before it can act as a prior anchor.
        bad = self.root / "bad-witness"; shutil.copytree(s2, bad)
        manifest = cb.read_json(bad / "scope.json"); manifest["correction_witnesses"][0]["original_basis_sha256"] = "f" * 64
        (bad / "scope.json").write_bytes(cp.encode(manifest)); self.repair(bad)
        self.cli("verify", bad, code=2, message="correction witness")

    def test_marker_exact_types_omission_forgery_and_depth_zero_refuse(self):
        r1 = self.full(); s1, _ = self.scoped(r1, "s1")
        r2 = self.full(2, "r2", r1); s2, _ = self.scoped(r2, "s2", s1)
        marker = cb.read_json(s2 / "scope.json")["incremental_history"]
        variants = [None, False, {}, {**marker, "extra": True}, {**marker, "schema": "wrong"},
                    {**marker, "previous_scoped_receipt_sha256": 1},
                    {**marker, "previous_original_receipt_sha256": None},
                    {**marker, "previous_original_receipt_sha256": False},
                    {**marker, "previous_scoped_receipt_sha256": "0" * 64},
                    {**marker, "previous_original_receipt_sha256": "0" * 64}, "OMIT"]
        for i, value in enumerate(variants):
            with self.subTest(marker=value):
                bad = self.root / ("bad" + str(i)); shutil.copytree(s2, bad)
                manifest = cb.read_json(bad / "scope.json")
                if value == "OMIT": manifest.pop("incremental_history")
                else: manifest["incremental_history"] = copy.deepcopy(value)
                (bad / "scope.json").write_bytes(cp.encode(manifest)); self.repair(bad)
                self.cli("verify", bad, code=2)
        bad = self.root / "zero"; shutil.copytree(s1, bad)
        manifest = cb.read_json(bad / "scope.json"); manifest["incremental_history"] = marker
        (bad / "scope.json").write_bytes(cp.encode(manifest)); self.repair(bad)
        self.cli("verify", bad, code=2, message="incremental history needs a predecessor")

    def test_preserved_boundary_missing_repeated_and_missing_segment_markers_refuse(self):
        # Pure verifier boundary controls isolate the invariant from packet hash failures.
        def frame(permission, root, original, receipt, marker=True):
            manifest = {"whole_file_permission_sha256": permission,
                        "permission_root_source_receipt_sha256": root,
                        "source_packet_receipt_sha256": original}
            if marker: manifest["incremental_history"] = cs.history_binding("a" * 64, "b" * 64)
            return {"scope": manifest, "receipt_sha256": receipt}
        new = frame("1" * 64, "2" * 64, "3" * 64, "4" * 64)
        old = frame("5" * 64, "6" * 64, "7" * 64, "8" * 64, False)
        self.assertEqual(cs.incremental_anchor([new, old]), cs.history_binding("8" * 64, "7" * 64))
        for chain in ([new], [new, old, new], [frame("1" * 64, "2" * 64, "3" * 64, "4" * 64, False), old]):
            with self.subTest(chain=chain), self.assertRaises(cb.ContextError):
                cs.incremental_anchor(chain)


if __name__ == "__main__":
    unittest.main()
