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
        self.assertNotIn("<script>", (out / "REPORT.md").read_text(encoding="utf-8"))
        self.assertIn("&lt;script&gt;", (out / "REPORT.md").read_text(encoding="utf-8"))
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


class SourcePreservingValues(unittest.TestCase):
    """Development controls only; no reserved qualification fixture is read here."""

    def setUp(self):
        import cad_value_patch
        self.patch = cad_value_patch
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.dxf"
        drawing(self.source)
        self.raw = self.source.read_bytes().replace(b"\r\n", b"\n")
        self.raw = self.raw.replace(b"  0\nEOF", b"999\nUnfamiliar raw comment\n  0\nEOF")
        self.source.write_bytes(self.raw)
        self.plan = {"schema": "cad-edit-plan-1", "source_sha256": ch.digest(self.source), "changes": [
            {"id": "fixture/valve-01", "attribute": "MODEL", "before": "A", "after": "B",
             "reason": "Authored development control"}]}

    def test_exact_literal_replacement_and_unchanged_strict_comparator(self):
        marker = b"  1\nA\n"
        self.assertEqual(self.raw.count(marker), 1)
        out = self.root / "patched"
        report = self.patch.apply(self.source, self.plan, out)
        self.assertEqual(report["unexpected"], [])
        self.assertEqual((out / "candidate.dxf").read_bytes(), self.raw.replace(marker, b"  1\nB\n"))
        self.assertEqual((out / "source.dxf").read_bytes(), self.raw)
        self.assertEqual(self.source.read_bytes(), self.raw)
        self.assertTrue(ch.compare(ch.snapshot(self.source), ch.snapshot(out / "candidate.dxf"))["unexpected"])

    def test_crlf_and_multiple_values_retain_every_other_byte(self):
        raw = self.raw.replace(b"\n", b"\r\n")
        self.source.write_bytes(raw)
        self.plan["source_sha256"] = ch.digest(self.source)
        self.plan["changes"].append(dict(id="fixture/valve-01", attribute="SERIAL", before="123", after="98765",
                                          reason="Second declared development edit"))
        out = self.root / "crlf"
        self.patch.apply(self.source, self.plan, out)
        expected = raw.replace(b"  1\r\nA\r\n", b"  1\r\nB\r\n").replace(b"  1\r\n123\r\n", b"  1\r\n98765\r\n")
        self.assertEqual((out / "candidate.dxf").read_bytes(), expected)

    def test_control_characters_multiline_and_ambiguous_escapes_refuse_without_packet(self):
        for i, text in enumerate(["new\nline", "new\rline", "new\tfield", "bad\0field", r"new\Pline", r"\U+0041"]):
            plan = copy.deepcopy(self.plan)
            plan["changes"][0]["after"] = text
            out = self.root / ("bad-"+str(i))
            with self.subTest(text=text), self.assertRaises(ch.InputError):
                self.patch.apply(self.source, plan, out)
            self.assertFalse(out.exists())

    def test_binary_and_duplicate_raw_primary_text_refuse(self):
        cases = [b"AutoCAD Binary DXF\r\n\x1a\x00", self.raw.replace(b"  1\nA\n", b"  1\nA\n  1\nA\n")]
        for i, raw in enumerate(cases):
            self.source.write_bytes(raw)
            plan = copy.deepcopy(self.plan)
            plan["source_sha256"] = ch.digest(self.source)
            out = self.root / ("ambiguous-"+str(i))
            with self.subTest(i=i), self.assertRaises(ch.InputError):
                self.patch.apply(self.source, plan, out)
            self.assertFalse(out.exists())

    def test_second_revision_old_plan_and_existing_output_refuse(self):
        out = self.root / "first"
        self.patch.apply(self.source, self.plan, out)
        candidate = out / "candidate.dxf"
        with self.assertRaises(ch.InputError):
            self.patch.apply(candidate, self.plan, self.root / "stale")
        with self.assertRaises(ch.InputError):
            self.patch.apply(self.source, self.plan, out)
        second = copy.deepcopy(self.plan)
        second["source_sha256"] = ch.digest(candidate)
        second["changes"][0].update(before="B", after="C")
        self.patch.apply(candidate, second, self.root / "second")
        self.assertEqual((out / "source.dxf").read_bytes(), self.raw)
        self.assertEqual(ch.snapshot(candidate)["assets"][0]["attributes"]["MODEL"], "B")

    def test_source_changed_during_patch_refuses(self):
        from unittest.mock import patch
        original = self.patch.patch_bytes
        def concurrent_edit(raw, spans):
            result = original(raw, spans)
            self.source.write_bytes(raw.replace(b"Unfamiliar raw comment", b"Concurrent manual note"))
            return result
        with patch.object(self.patch, "patch_bytes", side_effect=concurrent_edit), self.assertRaises(ch.InputError):
            self.patch.apply(self.source, self.plan, self.root / "race")
        self.assertFalse((self.root / "race").exists())

    def test_stale_duplicate_identity_and_before_controls_refuse(self):
        for i, mutate in enumerate([lambda p: p.update(source_sha256="0"*64),
                                    lambda p: p["changes"][0].update(before="stale"),
                                    lambda p: p["changes"].append(p["changes"][0]),
                                    lambda p: p["changes"][0].update(attribute="ICT_ID")]):
            plan = copy.deepcopy(self.plan)
            mutate(plan)
            out = self.root / ("refuse-"+str(i))
            with self.subTest(i=i), self.assertRaises(ch.InputError):
                self.patch.apply(self.source, plan, out)
            self.assertFalse(out.exists())

    def test_independent_audit_detects_comment_change_ignored_by_strict_snapshot(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification"))
        from verify_bytes import verify
        out = self.root / "checked"
        self.patch.apply(self.source, self.plan, out)
        candidate = out / "candidate.dxf"
        self.assertEqual(verify(self.source, candidate, self.plan)["status"], "pass")
        raw = candidate.read_bytes()
        self.assertIn(b"Unfamiliar raw comment", raw)
        candidate.write_bytes(raw.replace(b"Unfamiliar raw comment", b"Dropped provenance!!!"))
        self.assertEqual(ch.compare(ch.snapshot(self.source), ch.snapshot(candidate), self.plan)["unexpected"], [])
        with self.assertRaises(ValueError):
            verify(self.source, candidate, self.plan)

    def test_mutated_geometry_layer_foreign_and_xdata_in_candidate_fail(self):
        out = self.root / "mutated"
        self.patch.apply(self.source, self.plan, out)
        candidate = out / "candidate.dxf"
        for i, mutation in enumerate([
            lambda d: setattr(d.modelspace().query("LINE")[0].dxf, "end", (99, 0, 0)),
            lambda d: setattr(d.layers.get("PROCESS").dxf, "color", 1),
            lambda d: setattr(d.modelspace().query("INSERT")[0].get_attrib("VENDOR_PRIVATE").dxf, "text", "lost"),
            lambda d: d.modelspace().query("LINE")[0].discard_xdata("VENDOR_TEST")]):
            doc = ch.load(candidate)
            mutation(doc)
            returned = self.root / ("loss-"+str(i)+".dxf")
            doc.saveas(returned)
            self.assertTrue(ch.compare(ch.snapshot(self.source), ch.snapshot(returned), self.plan)["unexpected"])


class QualificationPreparation(unittest.TestCase):
    """Development controls for retaining the full attempted cohort and authored profiles."""
    def adapter(self):
        path = Path(__file__).resolve().parents[1] / 'examples/cad-handoff/qualification/adapt_public.py'
        spec = importlib.util.spec_from_file_location('cad_public_fixture_adapter', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_adapter_preserves_existing_attributes_and_adds_only_declared_test_values(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, target = root / 'original.dxf', root / 'adapted.dxf'
            drawing(source)
            original = source.read_bytes()
            before = ch.snapshot(source)['assets'][0]
            plan, recipe = self.adapter().adapt(source, 'development', target)
            after = ch.snapshot(target)['assets'][0]
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(after['id'], before['id'])
            for key, value in before['attributes'].items():
                self.assertEqual(after['attributes'][key], value)
            self.assertEqual(plan['changes'][0]['attribute'], 'MANUFACTURER')
            self.assertEqual(after['attributes']['MANUFACTURER'], 'QUAL-BEFORE')
            self.assertFalse(recipe['authored_anchor'])
            self.assertEqual(recipe['additions'][0]['attributes'], {'MANUFACTURER': 'QUAL-BEFORE'})

    def test_adapter_empty_geometry_anchor_and_ambiguous_original_are_distinct(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'geometry.dxf'
            doc = ezdxf.new('R2000')
            doc.modelspace().add_line((0, 0), (10, 20))
            doc.saveas(source)
            plan, recipe = self.adapter().adapt(source, 'geometry-development', root / 'adapted.dxf')
            self.assertTrue(recipe['authored_anchor'])
            self.assertTrue(plan['changes'][0]['id'].startswith('AUTHORED-QUAL/'))
            drawing(source)
            doc = ch.load(source)
            doc.modelspace().query('INSERT')[0].add_attrib('TAG', 'DUPLICATE')
            doc.saveas(source)
            with self.assertRaisesRegex(ch.InputError, 'Duplicate original attribute'):
                self.adapter().adapt(source, 'bad-development', root / 'refused.dxf')
            self.assertFalse((root / 'refused.dxf').exists())

    def test_runner_retains_failed_case_then_runs_next_case_and_refuses_empty_cohort(self):
        import subprocess
        import sys
        runner = Path(__file__).resolve().parents[1] / 'examples/cad-handoff/qualification/run_cases.py'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'good.dxf'
            drawing(source)
            bad = root / 'bad.dxf'
            bad.write_bytes(b'not a DXF\n')
            plan = dict(schema='cad-edit-plan-1', source_sha256=ch.digest(source), changes=[
                dict(id='fixture/valve-01', attribute='MODEL', before='A', after='B', reason='development')])
            planpath = root / 'plan.json'
            ch.write_json(planpath, plan)
            cases = [dict(id=p.stem, split='development', source=p.name, source_sha256=ch.digest(p),
                          plan=planpath.name, plan_sha256=ch.digest(planpath)) for p in (bad, source)]
            manifest = root / 'MANIFEST.json'
            ch.write_json(manifest, dict(cases=cases))
            command = [sys.executable, str(runner), '--split', 'exposed-regression', '--manifest', str(manifest)]
            result = subprocess.run(command + ['--out', str(root / 'results')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            records = json.loads((root / 'results/results.json').read_bytes())['results']
            self.assertEqual([r['case'] for r in records], ['bad', 'good'])
            self.assertIn('error', records[0])
            self.assertEqual(records[1]['routes']['value-spans']['byte_check']['status'], 'pass')
            ch.write_json(manifest, dict(cases=[]))
            result = subprocess.run(command + ['--out', str(root / 'empty')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('empty cohort is not a pass', result.stderr)
            self.assertFalse((root / 'empty').exists())

    def test_public_runner_requires_bound_adaptation_and_the_complete_selected_cohort(self):
        import hashlib
        import subprocess
        import sys
        repo = Path(__file__).resolve().parents[1]
        here = repo / 'examples/cad-handoff/qualification'
        digest = lambda p: hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        # A disposable development selection; no reserved public drawing is read by this test.
        with tempfile.TemporaryDirectory(prefix='cad-public-guard-', dir=repo) as folder:
            root = Path(folder)
            source = root / 'original.dxf'
            drawing(source)
            selection = root / 'selection.json'
            ch.write_json(selection, dict(cases=[dict(id='guard-development', source=source.name,
                                                    source_sha256=ch.digest(source))]))
            methods = ['scripts/cad_value_patch.py', 'scripts/cad_handoff.py',
                       'examples/cad-handoff/qualification/verify_bytes.py',
                       'examples/cad-handoff/qualification/run_cases.py',
                       'examples/cad-handoff/qualification/adapt_public.py']
            freeze = root / 'freeze.json'
            ch.write_json(freeze, dict(methods={p: digest(repo / p) for p in methods},
                manifests={selection.relative_to(repo).as_posix(): digest(selection)}))
            adapted = root / 'adapted'
            result = subprocess.run([sys.executable, str(here / 'adapt_public.py'), '--selection', str(selection),
                '--freeze', str(freeze), '--out', str(adapted)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = adapted / 'MANIFEST.json'
            admission = root / 'admission.json'
            command = [sys.executable, str(here / 'run_cases.py'), '--split', 'public-adapted',
                       '--manifest', str(manifest), '--freeze', str(freeze), '--admission', str(admission)]
            ch.write_json(admission, dict(freeze_sha256_lf=digest(freeze), manifest_sha256_lf='0' * 64))
            result = subprocess.run(command + ['--out', str(root / 'unbound')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('does not bind', result.stderr)
            self.assertFalse((root / 'unbound').exists())
            ch.write_json(admission, dict(freeze_sha256_lf=digest(freeze), manifest_sha256_lf=digest(manifest)))
            result = subprocess.run(command + ['--out', str(root / 'good')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(manifest.read_bytes())
            data['cases'] = []
            ch.write_json(manifest, data)
            ch.write_json(admission, dict(freeze_sha256_lf=digest(freeze), manifest_sha256_lf=digest(manifest)))
            result = subprocess.run(command + ['--out', str(root / 'omitted')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('omits, adds or changes', result.stderr)
            self.assertFalse((root / 'omitted').exists())


class R12Inspection(unittest.TestCase):
    """Exposed round-1 R12 failure is now development, not fresh validation."""
    def test_r12_retains_virtual_records_and_detects_planted_losses(self):
        import cad_value_patch
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "legacy.dxf"
            doc = ezdxf.new("R12")
            doc.layers.new("PIPE", dxfattribs={"color": 3})
            doc.appids.new("VENDOR")
            block = doc.blocks.new("PUMP")
            block.add_circle((0, 0), 2)
            for i, tag in enumerate(("ICT_ID", "TAG", "MODEL", "FOREIGN")):
                block.add_attdef(tag, (3, -i), height=0.7)
            ref = doc.modelspace().add_blockref("PUMP", (5, 9))
            ref.add_auto_attribs(dict(ICT_ID="r12-development/pump", TAG="P-01", MODEL="A", FOREIGN="keep"))
            line = doc.modelspace().add_line((0, 0), (20, 5), dxfattribs={"layer": "PIPE"})
            line.set_xdata("VENDOR", [(1000, "foreign")])
            doc.saveas(source)
            before = ch.snapshot(source)
            virtual = [v for v in before["entities"].values() if v["type"] == "BLOCK_RECORD"]
            self.assertTrue(virtual)
            self.assertTrue(all(v["tags"] for v in virtual))
            plan = dict(schema="cad-edit-plan-1", source_sha256=ch.digest(source), changes=[
                dict(id="r12-development/pump", attribute="MODEL", before="A", after="B", reason="development control")])
            cad_value_patch.apply(source, plan, root / "candidate")
            candidate = root / "candidate/candidate.dxf"
            self.assertEqual(ch.compare(before, ch.snapshot(candidate), plan)["unexpected"], [])
            self.assertIn(b"AC1009", candidate.read_bytes())
            for i, mutation in enumerate([
                lambda d: setattr(d.modelspace().query("LINE")[0].dxf, "end", (99, 0, 0)),
                lambda d: setattr(d.layers.get("PIPE").dxf, "color", 1),
                lambda d: setattr(d.styles.get("Standard").dxf, "width", 1.5),
                lambda d: setattr(d.modelspace().query("INSERT")[0].get_attrib("FOREIGN").dxf, "text", "lost"),
                lambda d: d.modelspace().query("LINE")[0].discard_xdata("VENDOR"),
                lambda d: setattr(d.blocks.get("PUMP").query("CIRCLE")[0].dxf, "radius", 3),
            ]):
                changed = ch.load(candidate)
                mutation(changed)
                returned = root / ("loss-" + str(i) + ".dxf")
                changed.saveas(returned)
                with self.subTest(loss=i):
                    self.assertTrue(ch.compare(before, ch.snapshot(returned), plan)["unexpected"])


if __name__ == "__main__":
    unittest.main()
