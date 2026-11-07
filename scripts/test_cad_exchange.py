"""Source-bound sidecar CLI, malformed/stale proposals and exact-byte preservation controls."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cad_exchange as ce
import cad_handoff as ch
from test_cad_handoff import drawing

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("exchange_byte_check", ROOT / "examples/cad-handoff/qualification/verify_bytes.py")
byte_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(byte_check)


class Exchange(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.dxf"
        drawing(self.source)
        self.exchange = ce.prepare(self.source, self.root / "review")
        self.change = {"id": "fixture/valve-01", "attribute": "SIZE", "before": "DN50", "after": "DN65",
                       "reason": "Authored test note; proposed value only"}
        self.response = ce.response_for(self.exchange, [self.change])

    def refused(self, exchange=None, response=None, source=None):
        out = self.root / "refused"
        with self.assertRaises((ch.InputError, ValueError)):
            ce.apply(source or self.source, self.exchange if exchange is None else exchange,
                     self.response if response is None else response, out)
        self.assertFalse(out.exists())

    def test_cli_round_trip_retains_original_response_and_reopens_revised_catalog(self):
        response_path = self.root / "download.json"
        raw = json.dumps(self.response, ensure_ascii=False).encode("utf-8") + b"\r\n"
        response_path.write_bytes(raw)
        out = self.root / "draft"
        result = subprocess.run([sys.executable, str(ROOT / "scripts/cad_exchange.py"), "apply", str(self.source),
                                 str(self.root / "review/exchange.json"), str(response_path), "--out", str(out)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((out / "response-original.json").read_bytes(), raw)
        plan = ce.read_json(out / "plan.json")
        self.assertEqual(byte_check.verify(self.source, out / "candidate.dxf", plan)["unplanned_byte_changes"], 0)
        self.assertEqual((out / "source.dxf").read_bytes(), self.source.read_bytes())
        updated = ce.prepare(out / "candidate.dxf", self.root / "reopened")
        self.assertEqual(updated["assets"][0]["attributes"]["SIZE"], "DN65")
        self.assertEqual(updated["assets"][0]["attributes"]["VENDOR_PRIVATE"], "retain me")
        self.refused(source=out / "candidate.dxf")

    def test_bad_bindings_and_changed_catalog_refuse(self):
        for mutate in (lambda x: x.update(source_sha256="0"*64), lambda x: x.update(exchange_sha256="0"*64),
                       lambda x: x.update(schema="cad-edit-plan-1"), lambda x: x.update(extra="ignored?")):
            response = copy.deepcopy(self.response)
            mutate(response)
            self.refused(response=response)
        for mutate in (lambda x: x["editable"].append("ICT_ID"),
                       lambda x: x["assets"][0]["attributes"].update(SIZE="DN40"),
                       lambda x: x.update(extra="ignored?")):
            exchange = copy.deepcopy(self.exchange)
            mutate(exchange)
            response = ce.response_for(exchange, [self.change])
            self.refused(exchange=exchange, response=response)

    def test_malformed_duplicate_and_forbidden_changes_refuse(self):
        for changes in ([], None, [self.change, self.change], [None], [dict(self.change, extra="ignored?")],
                        [dict(self.change, attribute="ICT_ID")], [dict(self.change, attribute="VENDOR_PRIVATE")],
                        [dict(self.change, id="guessed-id")], [dict(self.change, before="DN40")],
                        [dict(self.change, after="DN50")], [dict(self.change, after="")],
                        [dict(self.change, reason=" ")], [dict(self.change, after=65)],
                        [dict(self.change, after="DN65\nnew record")], [dict(self.change, after="X"*251)],
                        [dict(self.change, after="A\\PB")]):
            with self.subTest(changes=changes):
                self.refused(response=ce.response_for(self.exchange, changes))

    def test_duplicate_json_fields_and_full_dxf_response_refuse(self):
        with self.assertRaises(ch.InputError):
            ce.parse_json('{"changes":[],"changes":[]}')
        with self.assertRaises(ValueError):
            ce.parse_json(self.source.read_text())
        with self.assertRaises(ch.InputError):
            ce.apply(self.source, self.exchange, self.response, self.root / "bad-original", b'{}')
        self.assertFalse((self.root / "bad-original").exists())

    def test_existing_destinations_and_source_revision_are_not_overwritten(self):
        before = self.source.read_bytes()
        with self.assertRaises(ch.InputError):
            ce.prepare(self.source, self.root / "review")
        self.source.write_bytes(before + b"\n\n")
        self.refused()
        self.assertEqual(self.source.read_bytes(), before + b"\n\n")
        self.source.write_bytes(before)
        out = self.root / "draft"
        ce.apply(self.source, self.exchange, self.response, out)
        candidate = (out / "candidate.dxf").read_bytes()
        with self.assertRaises(ch.InputError):
            ce.apply(self.source, self.exchange, self.response, out)
        self.assertEqual((out / "candidate.dxf").read_bytes(), candidate)

    def test_two_competing_proposals_require_explicit_revision(self):
        first, second = self.root / "first", self.root / "second"
        ce.apply(self.source, self.exchange, self.response, first)
        ce.apply(self.source, self.exchange, ce.response_for(self.exchange, [dict(self.change, after="DN80")]), second)
        self.refused(source=first / "candidate.dxf")
        current = ce.prepare(first / "candidate.dxf", self.root / "revision")
        revised = ce.response_for(current, [dict(self.change, before="DN65", after="DN80")])
        ce.apply(first / "candidate.dxf", current, revised, self.root / "revised-draft")

    def test_foreign_payload_cannot_close_script_or_replace_template_markers(self):
        doc = ch.load(self.source)
        foreign = '</script><img src=x onerror="globalThis.injected=1">@FINGERPRINT@ & foreign'
        doc.modelspace().query("INSERT")[0].get_attrib("VENDOR_PRIVATE").dxf.text = foreign
        doc.saveas(self.source)
        data = ce.catalog(self.source)
        html = ce.render(data)
        self.assertNotIn(foreign, html)
        self.assertIn("\\u003c/script\\u003e", html)
        payload = html.split('<script id="catalog" type="application/json">', 1)[1].split('</script>', 1)[0]
        self.assertEqual(json.loads(payload), data)
        self.assertEqual(html.count('</script>'), 2)

    def test_unprofiled_duplicate_assets_and_binary_input_refuse(self):
        for number in range(3):
            doc = ch.load(self.source)
            ref = doc.modelspace().query("INSERT")[0]
            if number == 0:
                ref.delete_attrib("ICT_ID")
            elif number == 1:
                doc.modelspace().add_entity(ref.copy())
            path = self.root / f"bad-{number}.dxf"
            doc.saveas(path)
            if number == 2:
                path.write_bytes(b"AutoCAD Binary DXF\x00")
            with self.assertRaises(ch.InputError):
                ce.prepare(path, self.root / f"refused-{number}")
            self.assertFalse((self.root / f"refused-{number}").exists())

    def test_independent_checker_detects_geometry_layer_foreign_and_xdata_changes(self):
        out = self.root / "draft"
        ce.apply(self.source, self.exchange, self.response, out)
        mutations = [lambda d: setattr(d.modelspace().query("LINE")[0].dxf, "end", (900, 20, 0)),
                     lambda d: setattr(d.layers.get("PROCESS").dxf, "color", 1),
                     lambda d: setattr(d.modelspace().query("INSERT")[0].get_attrib("VENDOR_PRIVATE").dxf, "text", "lost"),
                     lambda d: d.modelspace().query("LINE")[0].discard_xdata("VENDOR_TEST")]
        for i, mutate in enumerate(mutations):
            doc = ch.load(out / "candidate.dxf")
            mutate(doc)
            path = self.root / f"mutated-{i}.dxf"
            doc.saveas(path)
            self.assertTrue(ch.compare(ch.snapshot(self.source), ch.snapshot(path), ce.read_json(out / "plan.json"))["unexpected"])
            with self.assertRaises(ValueError):
                byte_check.verify(self.source, path, ce.read_json(out / "plan.json"))


if __name__ == "__main__":
    unittest.main()
