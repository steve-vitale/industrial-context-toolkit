"""Compact specifications, actual materialized artifacts and retained legacy packet parity."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import context_basis as cb
import context_components as cc
import context_packet as cp
from test_context_packet import FIXTURE, KEY, PUMP, OTHER, contributions, load

ROOT = Path(__file__).resolve().parents[1]
SPEC = "engineering-component-view-specification-1"


class CompactViewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="compact-context-")
        self.root = Path(self.temp.name)
        self.contribution = self.root / "contributions.csv"
        self.contribution.write_bytes(contributions())
        self.packet = cp.prepare(FIXTURE / "development/rev1", self.root / "packet", KEY["site"], KEY["plant"],
                                 contribution=self.contribution)

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, "-B", "-S", str(ROOT / "scripts/context_workflow.py"),
                                 *map(str, args)], capture_output=True, timeout=60)
        self.assertEqual(result.returncode, code, result.stderr.decode())
        return json.loads(result.stdout if code == 0 else result.stderr)

    def resign(self):
        receipt = load(self.packet / "RECEIPT.json")
        receipt["files"] = {k: v for k, v in cp.inventory(self.packet).items() if k != "RECEIPT.json"}
        (self.packet / "RECEIPT.json").write_bytes(cp.encode(receipt))

    def test_default_spec_is_explicit_compact_bound_and_not_a_full_draft(self):
        stored = load(self.packet / "drafts.json")
        self.assertEqual(stored["schema"], SPEC)
        self.assertNotIn("components", stored)
        opened = cp.open_packet(self.packet)
        self.assertEqual(stored["full_draft_sha256"], cb.digest(opened["draft"]))
        self.assertEqual(stored["basis_sha256"], cb.digest(opened["basis"]))
        self.assertEqual(stored["method_sha256_lf"], opened["receipt"]["method_sha256_lf"])
        self.assertLess((self.packet / "drafts.json").stat().st_size, len(cp.encode(opened["draft"])) // 4)

    def test_streamed_digest_matches_existing_canonical_typed_values(self):
        values = [False, 0, True, 1, 1.0, -0.0, 0.0, 10**80, {"unit": "°C", "nested": [None, "é", "\\\""]}]
        for value in values:
            with self.subTest(value=repr(value)):
                self.assertEqual(cc.draft_digest(value), cb.digest(value))
        self.assertEqual(len({cc.draft_digest(v) for v in values[:7]}), 7)

    def test_materialize_cli_delivers_exact_full_typed_artifact_for_own_reimport(self):
        destination = self.root / "full-draft.json"
        result = self.cli("materialize", self.packet, "--out", destination)
        opened = cp.open_packet(self.packet)
        self.assertEqual(destination.read_bytes(), cp.encode(opened["draft"]))
        self.assertEqual(result["sha256"], cb.raw_sha(destination.read_bytes()))
        self.assertEqual(load(destination)["schema"], cc.SCHEMA)
        again = self.root / "again"
        self.cli("reimport", self.packet, "--draft", destination, "--out", again)
        self.assertEqual(cp.open_packet(again)["basis"], opened["basis"])

    def test_materialize_exact_selection_retains_basis_and_no_other_item_view(self):
        destination = self.root / "selected.json"
        self.cli("materialize", self.packet, "--item", PUMP, "--out", destination)
        draft = load(destination)
        self.assertEqual(draft["selection"]["entities"], [PUMP])
        self.assertNotIn(OTHER, draft["components"]["item_datasheet_scaffold"]["items"])
        self.assertEqual(draft["basis_sha256"], cp.open_packet(self.packet)["receipt"]["basis_sha256"])
        self.cli("reimport", self.packet, "--draft", destination, "--out", self.root / "selected-edited")

    def test_reimport_spec_has_clear_materialize_instruction(self):
        result = self.cli("reimport", self.packet, "--draft", self.packet / "drafts.json", "--out", self.root / "bad", code=2)
        self.assertIn("materialize", result["error"])
        self.assertFalse((self.root / "bad").exists())

    def test_rehashed_spec_mutations_refuse_without_changing_retained_facts(self):
        original = (self.packet / "drafts.json").read_bytes()
        for key, value in [("full_draft_sha256", "0" * 64), ("basis_sha256", "0" * 64),
                           ("selection", {"scope": None, "item": OTHER, "entities": [OTHER]}),
                           ("method_sha256_lf", {}), ("targets", []), ("unexpected", "instruction")]:
            with self.subTest(key=key):
                stored = json.loads(original)
                stored[key] = value
                (self.packet / "drafts.json").write_bytes(cp.encode(stored))
                self.resign()
                with self.assertRaisesRegex(cb.ContextError, "component view specification"):
                    cp.open_packet(self.packet)
                (self.packet / "drafts.json").write_bytes(original)
                self.resign()

    def test_rehashed_readable_change_still_refuses(self):
        (self.packet / "datasheets.md").write_bytes(b"Invented replacement")
        self.resign()
        with self.assertRaisesRegex(cb.ContextError, "readable component differs"):
            cp.open_packet(self.packet)

    def test_materialize_size_limit_and_existing_file_refuse_without_replacement(self):
        destination = self.root / "too-large.json"
        opened = cp.open_packet(self.packet)
        # Isolate the output guard; lowering the shared bound must not instead fail source intake.
        with patch.object(cp, "open_packet", return_value=opened), patch.object(cb, "MAX_BYTES", 1):
            with self.assertRaisesRegex(cb.ContextError, "materialized draft exceeds"):
                cp.materialize(self.packet, destination)
        self.assertFalse(destination.exists())
        destination.write_bytes(b"Keep engineer work")
        self.cli("materialize", self.packet, "--out", destination, code=2)
        self.assertEqual(destination.read_bytes(), b"Keep engineer work")
        self.cli("materialize", self.packet, "--out", self.packet / "unaccounted.json", code=2)
        self.assertFalse((self.packet / "unaccounted.json").exists())

    def test_legacy_full_draft_three_revision_archive_opens_without_rewriting(self):
        archive = ROOT / "examples/map-component-cycle/development/complete-run.zip"
        manifest = load(archive.parent / "MANIFEST.json")
        self.assertEqual(cb.raw_sha(archive.read_bytes()), manifest["sha256"])
        prefix = "commands-and-artifacts/test_three_revisions_edit_reopen_and_reimport_keep_basis/r3/"
        destination = self.root / "legacy"
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if name.startswith(prefix) and not name.endswith("/"):
                    relative = cp.safe_name(name[len(prefix):])
                    target = destination / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(z.read(name))
        before = cp.inventory(destination)
        full = load(destination / "drafts.json")
        self.assertEqual(full["schema"], cc.SCHEMA)
        opened = cp.open_packet(destination)
        self.assertEqual(opened["draft"], full)
        self.assertEqual(opened["receipt"]["history_depth"], 3)
        self.assertEqual(cp.inventory(destination), before)
        copied = self.root / "legacy-export.json"
        self.cli("materialize", destination, "--out", copied)
        self.assertEqual(copied.read_bytes(), cp.encode(full))

    def test_delivery_refusal_does_not_claim_draft_selection_filters_source_scope(self):
        result = self.cli("bundle", self.packet, "--out", self.root / "no.json", "--max-bytes", 1, code=2)
        self.assertIn("does not filter retained basis or originals", result["error"])
        self.assertFalse((self.root / "no.json").exists())


if __name__ == "__main__":
    unittest.main()
