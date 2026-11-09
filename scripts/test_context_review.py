"""Delivered field/source fidelity, packet-bound edits, stale/mutated proposals and unsafe text."""
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
import context_components as cc
import context_packet as cp
import context_review as cr
from test_context_packet import FIXTURE, KEY, PUMP, OTHER, FIC, FT, FV, contributions

ROOT = Path(__file__).resolve().parents[1]


class ReviewWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="component-review-")
        self.root = Path(self.temp.name)
        self.contribution = self.root / "contributions.csv"
        self.contribution.write_bytes(contributions())
        self.calls = []
        self.packet = cp.prepare(FIXTURE / "development/rev1", self.root / "r1", KEY["site"], KEY["plant"],
                                 contribution=self.contribution)

    def tearDown(self):
        evidence = os.environ.get("CONTEXT_TEST_EVIDENCE")
        if evidence:
            target = Path(evidence) / self.id().rsplit(".", 1)[-1]
            shutil.copytree(self.root, target)
            (target / "calls.json").write_bytes(cp.encode(self.calls))
        self.temp.cleanup()

    def cli(self, *args, code=0, reason=None):
        run = subprocess.run([sys.executable, "-B", "-S", str(ROOT / "scripts/context_workflow.py"),
                              *map(str, args)], cwd=self.root, capture_output=True, timeout=60)
        self.calls.append({"args": list(map(str, args)), "exit": run.returncode,
                           "stdout": run.stdout.decode("utf-8"), "stderr": run.stderr.decode("utf-8")})
        self.assertEqual(run.returncode, code, run.stderr.decode("utf-8"))
        if reason:
            self.assertIn(reason, run.stderr.decode("utf-8"))
        return json.loads(run.stdout if code == 0 else run.stderr)

    def request(self, opened=None, field="draft_review_note"):
        opened = opened or cp.open_packet(self.packet)
        item = next(row for row in cr.payload(opened)["items"] if row["id"] == PUMP)
        f = item["edit_fields"][field]
        return {"schema": cr.SCHEMA, "basis_sha256": cb.digest(opened["basis"]),
                "receipt_sha256": opened["receipt_sha256"], "subject": PUMP, "field": field,
                "value": KEY["manual_edit_control"]["value"],
                "rationale": "Awaiting permitted nameplate evidence",
                "expected_content_fingerprint": f["content_fingerprint"],
                "expected_evidence_fingerprint": f["evidence_fingerprint"], "roots": f["roots"]}

    def test_delivered_views_keep_literal_source_conflicts_gaps_and_links(self):
        opened = cp.open_packet(self.packet)
        data = cr.payload(opened)
        pump = next(row for row in data["items"] if row["id"] == PUMP)
        other = next(row for row in data["items"] if row["id"] == OTHER)
        for target in cc.TARGETS[:2]:
            field = pump["targets"][target]["fields"]["rated_flow"]
            self.assertEqual(field["state"], "disputed")
            self.assertCountEqual([r["value_text"] for r in field["evidence"]],
                                  [cb.canonical(v) for v in KEY["revisions"][0]["flow_alternatives"]])
            self.assertEqual({r["source_id"] for r in field["evidence"]}, {"EQ", "DS"})
            self.assertEqual({r["unit_text"] for r in field["evidence"]}, {'"m3/h"'})
        self.assertEqual(pump["targets"][cc.TARGETS[1]]["fields"]["operating_limits"]["state"], "unknown")
        serial = other["targets"][cc.TARGETS[0]]["fields"]["serial_number"]["evidence"]
        self.assertEqual([r["value_text"] for r in serial], ['"OTHER-101"'])
        control = next(row for row in data["items"] if row["id"] == FIC)["targets"][cc.TARGETS[2]]["fields"]
        for name, target in (("reads", FT), ("commands", FV)):
            self.assertIn(target, control[name]["evidence"][0]["value_text"])
            self.assertEqual(control[name]["evidence"][0]["source_id"], "NOTE")
        html = self.root / "review.html"
        self.cli("review", self.packet, "--out", html)
        self.cli("verify-review", self.packet, html)
        html.write_bytes(html.read_bytes().replace(b"Choose a scoped item", b"Choose an unscoped item"))
        self.cli("verify-review", self.packet, html, code=2, reason="review HTML differs")

    def test_fresh_process_apply_reopen_preserves_sources_and_previous_note(self):
        request = self.root / "edit.json"
        request.write_bytes(cp.encode(self.request()))
        target = self.root / "edited"
        self.cli("apply-review", self.packet, "--edit", request, "--out", target)
        self.cli("verify", target)
        opened, old = cp.open_packet(target), cp.open_packet(self.packet)
        self.assertEqual(opened["basis"]["claims"], old["basis"]["claims"])
        self.assertEqual(opened["basis"]["sources"], old["basis"]["sources"])
        self.assertEqual(opened["basis"]["corrections"][0]["value"], KEY["manual_edit_control"]["value"])
        rendered = cr.payload(opened)
        self.assertEqual(next(r for r in rendered["items"] if r["id"] == PUMP)["notes"][0]["state"],
                         "proposed_editorial")
        # A new proposal on the edited packet must carry that first note, too.
        second = self.request(opened, field="manufacturer")
        second["value"] = "Request permitted nameplate photo"
        request.write_bytes(cp.encode(second))
        self.cli("apply-review", target, "--edit", request, "--out", self.root / "twice")
        self.assertEqual(len(cp.open_packet(self.root / "twice")["basis"]["corrections"]), 2)

    def test_stale_or_changed_dependencies_and_scope_refuse_specifically(self):
        request = self.request(field="rated_flow")
        path = self.root / "edit.json"
        path.write_bytes(cp.encode(request))
        r2 = cp.prepare(FIXTURE / "development/rev2", self.root / "r2", KEY["site"], KEY["plant"],
                        contribution=self.contribution, previous=self.packet)
        self.cli("apply-review", r2, "--edit", path, "--out", self.root / "stale",
                 code=2, reason="packet changed")
        for key, value in (("roots", []), ("expected_content_fingerprint", "0" * 64),
                           ("expected_evidence_fingerprint", "0" * 64)):
            changed = {**request, key: value}
            path.write_bytes(cp.encode(changed))
            self.cli("apply-review", self.packet, "--edit", path, "--out", self.root / key,
                     code=2, reason="source dependencies differ")
        selected = cp.prepare(FIXTURE / "development/rev1", self.root / "selected", KEY["site"], KEY["plant"],
                              contribution=self.contribution, item=OTHER)
        opened = cp.open_packet(selected)
        changed = {**request, "receipt_sha256": opened["receipt_sha256"],
                   "basis_sha256": cb.digest(opened["basis"])}
        path.write_bytes(cp.encode(changed))
        self.cli("apply-review", selected, "--edit", path, "--out", self.root / "wrong-scope",
                 code=2, reason="subject outside selected draft")

    def test_inactive_sources_and_numeric_lexemes_stay_display_text(self):
        r3 = cp.prepare(FIXTURE / "development/rev3", self.root / "r3", KEY["site"], KEY["plant"],
                        contribution=self.contribution, previous=self.packet)
        item = next(r for r in cr.payload(cp.open_packet(r3))["items"] if r["id"] == PUMP)
        flow = item["targets"][cc.TARGETS[1]]["fields"]["rated_flow"]["evidence"]
        self.assertFalse(next(r for r in flow if r["source_id"] == "DS")["active"])
        basis = cp.open_packet(self.packet)["basis"]
        view = cb.View(basis)
        field = view.field(PUMP, "serial_number")
        for value in (9007199254740993, 1.0, -0.0, False, None, [1.0, False], {"x": 9007199254740993}):
            changed = copy.deepcopy(field)
            changed["alternatives"][0]["value"] = value
            self.assertEqual(cr.field_payload(changed)["evidence"][0]["value_text"], cb.canonical(value))

    def test_untrusted_text_is_embedded_as_data_and_output_never_overwritten(self):
        from context_review_html import render
        hostile = "</script><img src=x onerror=alert(1)> & \u2028"
        html = render({"hostile": hostile})
        self.assertNotIn(hostile, html)
        self.assertIn("\\u003c/script\\u003e", html)
        self.assertNotIn("innerHTML", html)
        path = self.root / "review.html"
        cr.write(self.packet, path)
        original = path.read_bytes()
        with self.assertRaises(FileExistsError):
            cr.write(self.packet, path)
        self.assertEqual(path.read_bytes(), original)

    def test_absent_controller_preserves_component_prerequisite_gap(self):
        records = self.root / "without-controller"
        shutil.copytree(FIXTURE / "development/rev1", records)
        instrument = records / "instruments.csv"
        with instrument.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            names, rows = reader.fieldnames, list(reader)
        controller = next(row for row in rows if row["Tag"] == "FIC-101")
        self.assertEqual(controller["Type"], "controller")
        controller["Type"] = "instrument"
        with instrument.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=names, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        packet = cp.prepare(records, self.root / "no-controller", KEY["site"], KEY["plant"],
                            contribution=self.contribution)
        opened = cp.open_packet(packet)
        self.assertEqual(opened["draft"]["components"][cc.TARGETS[2]]["items"], {})
        expected = "No sourced controller class in selected context; outline only."
        for item in cr.payload(opened)["items"]:
            target = item["targets"][cc.TARGETS[2]]
            self.assertEqual(target["fields"], {})
            self.assertIn(expected, [gap.get("reason") for gap in target["gaps"]])
        self.assertIn(expected.encode("utf-8"), cr.render(opened))


if __name__ == "__main__":
    unittest.main()
