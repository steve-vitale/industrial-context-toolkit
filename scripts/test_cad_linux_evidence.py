"""Offline retained Linux CAD UI evidence and bounded archive receiving controls."""
import importlib.util
import copy
import json
from pathlib import Path
import tempfile
import unittest

import cad_handoff as ch


class RetainedLinuxNativeEvidence(unittest.TestCase):
    def records_module(self):
        path = Path(__file__).resolve().parents[1] / 'examples/cad-handoff/qualification/check_records15.py'
        spec = importlib.util.spec_from_file_location('cad_records15_receiver', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_crossed_records_retain_failed_routes_and_dangling_links(self):
        result = self.records_module().check()
        self.assertEqual(result['attempted_final_exports'], 48)
        self.assertEqual(result['completed_final_exports'], 46)
        self.assertEqual(result['fresh_public_inventory_repeats'], 46)
        self.assertEqual(result['retained_earlier_exports'], 26)
        self.assertEqual(result['final_statuses'], dict(differences=12, refused=34, native_failed=2))
        self.assertEqual(result['final_returns_with_dangling_links'], 12)
        self.assertEqual(result['dxflib_imported_attributes_parented_to_modelspace'], 72)
        self.assertEqual(result['dxflib_returns_without_attribute_sequence_markers'], 24)
        self.assertFalse(result['whole_cad_qualified'])

    def test_record_paths_keep_full_order_and_dangling_reference(self):
        receiving = self.records_module()
        doc = ch.ezdxf.new('R2010')
        dictionary = doc.rootdict.add_new_dict('FOREIGN')
        record = dictionary.add_xrecord('payload')
        record.extend([(1, 'retain'), (90, 123), (40, 4.5)])
        rows = receiving.a.records(doc)
        payload = next(r for r in rows if r['path'] == ['FOREIGN', 'payload'])
        self.assertEqual(payload['ordered_tags'], [[1, 'retain'], [90, 123], [40, 4.5]])
        dictionary.add('broken', 'FFFFFF')
        missing = next(r for r in receiving.a.records(doc) if r['path'] == ['FOREIGN', 'broken'])
        self.assertEqual(missing['type'], 'dangling-reference')
        self.assertEqual(missing['handle'], 'FFFFFF')
        self.assertIsNone(missing['ordered_tags'])
        forged = copy.deepcopy(payload)
        forged['ordered_tags'] = [[40, 4.5]]
        with self.assertRaisesRegex(ValueError, 'exact re-score'):
            receiving.equal(payload, forged)

    def test_failed_native_job_cannot_disappear_from_manifest(self):
        receiving = self.records_module()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'native.stdout'
            profile = dict(configuration_file='/home/cad/.config/QCAD/QCAD3.conf', qt_version='5.14.2',
                           importer_filters=['DXF Files [dxflib] (*.dxf)'],
                           exporter_filters=['R15 [2000/LT2000] DXF Drawing [OpenDesign] (*.dxf)'])
            row = dict(id='failed', error='native export failure', import_filter=profile['importer_filters'][0],
                       export_filter=profile['exporter_filters'][0])
            path.write_text('ICT_RECORD15_PROFILE ' + json.dumps(profile) + '\nICT_RECORD15 ' + json.dumps(row) + '\n', encoding='utf-8')
            job = dict(id='failed', importer='dxflib', exporter='OpenDesign', version='R15')
            receiving.a.native_rows(path, [job], allow_errors=True)
            with self.assertRaisesRegex(ValueError, 'coverage/error'):
                receiving.a.native_rows(path, [])
            with self.assertRaisesRegex(ValueError, 'coverage/error'):
                receiving.a.native_rows(path, [job])

    def boundaries_module(self):
        path = Path(__file__).resolve().parents[1] / 'examples/cad-handoff/qualification/check_boundaries14.py'
        spec = importlib.util.spec_from_file_location('cad_boundaries14_receiver', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_save_boundaries_keep_metadata_losses_and_seed_control_separate(self):
        result = self.boundaries_module().check()
        self.assertEqual(result['native_exports'], 63)
        self.assertEqual(result['fresh_public_inventory_repeats'], 63)
        self.assertEqual(result['strict_reports'], 65)
        self.assertEqual(result['seed_repeat_strict_differences'], [0] * 6)
        self.assertEqual(result['unseeded_to_seeded_differences'], [53] * 6)
        self.assertEqual(result['valid_integer_controls'], 17)
        self.assertEqual(result['missing_xrecord_controls'], 17)
        self.assertEqual(result['missing_unused_registration_controls'], 17)
        self.assertTrue(result['retained_incomplete_probe'])
        self.assertTrue(all(n > 0 for n in result['source_to_original_differences']))
        self.assertFalse(result['whole_cad_qualified'])

    def test_boundary_receiver_refuses_placeholder_missing_job_and_forged_pass(self):
        receiving = self.boundaries_module()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'native.stdout'
            manifest = dict(jobs=[dict(id='one'), dict(id='two')])
            path.write_text('placeholder\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                receiving.b.native_rows(path, manifest)
            path.write_text('ICT_BOUND14_PROFILE ' + json.dumps(dict(configuration_file='/home/cad/.config/QCAD/QCAD3.conf'))
                            + '\nICT_BOUND14 {"id":"one"}\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'coverage'):
                receiving.b.native_rows(path, manifest)
        with self.assertRaisesRegex(ValueError, 'exact re-score'):
            receiving.equal(dict(status='differences', unexpected=[dict(kind='entity')]), dict(status='pass', unexpected=[]))

    def test_empty_native_diagnostic_keeps_literal_zero_creation_time(self):
        import tarfile
        receiving = self.boundaries_module()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'empty.dxf'
            with tarfile.open(receiving.BASE / 'evidence.tar.xz', 'r:xz') as archive:
                path.write_bytes(archive.extractfile('raw/attempt-1/empty/default.dxf').read())
            first = receiving.b.diagnostic_inventory(path)
            second = receiving.b.diagnostic_inventory(path)
            self.assertEqual(first, second)
            header = bytes.fromhex(first['raw_header_hex'])
            self.assertIn(b'$TDCREATE', header)
            self.assertIn(header, path.read_bytes())
            self.assertNotIn('header', first)

    def scene_module(self):
        path = Path(__file__).resolve().parents[1] / 'examples/cad-handoff/qualification/check_scene13.py'
        spec = importlib.util.spec_from_file_location('cad_scene13_receiver', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_actual_gui_replay_explains_every_original_delta_pixel(self):
        result = self.scene_module().check()
        self.assertEqual(result['original_gui_delta_pixels'], 1978)
        self.assertEqual(result['original_outside_geometric_bounds_pixels'], 62)
        self.assertEqual(result['whole_canvas_delta_mismatches'], 0)
        self.assertEqual(result['outside_color_mismatches'], 0)
        self.assertEqual(result['ablations']['lines']['outside_changed_pixels'], 0)
        self.assertEqual(result['ablations']['stroke']['outside_color_mismatches'], 0)
        self.assertEqual(result['incomplete_trace_delta_mismatches'], 857)
        self.assertFalse(result['whole_cad_qualified'])

    def test_gui_replay_refuses_wrong_explicit_pen_and_viewport(self):
        import tarfile
        receiving = self.scene_module()
        base = receiving.BASE
        with tarfile.open(base/'evidence.tar.xz', 'r:xz') as packed:
            block = packed.extractfile('raw/build/control4-chunks/000.part').read()
        rows = [json.loads(line) for line in block.splitlines()]
        stroke = next(r for r in rows if r['kind'] == 'stroke')
        receiving.s.replay_input.tokens([stroke])
        wrong = copy.deepcopy(stroke)
        wrong['stroke_pen']['width'] = 2
        with self.assertRaisesRegex(ValueError, 'explicit stroke pen'):
            receiving.s.replay_input.tokens([wrong])
        wrong = copy.deepcopy(stroke)
        wrong['viewport'][0] = 1
        with self.assertRaisesRegex(ValueError, 'viewport/window'):
            receiving.s.replay_input.tokens([wrong])

    def test_gui_delta_check_cannot_hide_a_pixel_outside_model_bounds(self):
        from PIL import Image
        receiving = self.scene_module().s
        black = Image.new('RGB', (1533, 1032))
        changed = black.copy()
        changed.putpixel((0, 0), (255, 255, 0))
        self.assertEqual(receiving.compare_pixels([black, changed], [black, black]), 1)

    def root_module(self):
        path = Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification/check_root12.py"
        spec = importlib.util.spec_from_file_location("cad_root12_receiver", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_causal_controls_retain_full_save_and_pixel_failures(self):
        result = self.root_module().check()
        self.assertEqual(result['native_exports'], 144)
        self.assertEqual(result['fresh_process_fields'], 432)
        self.assertEqual(result['original_noedit_strict_rows'], 4650)
        self.assertEqual(result['second_noedit_strict_rows'], 6138)
        self.assertEqual(result['fixed_default_matched_differences'], [0] * 6)
        self.assertEqual(result['fixed_r15_matched_differences'], [1] * 6)
        self.assertTrue(result['before_load_count_vectors_equal'])
        self.assertEqual(result['original_outside_text_pixels'], 62)
        self.assertEqual(result['raster_profiles_with_exact_gui_delta'], 0)
        self.assertFalse(result['whole_cad_qualified'])

    def test_causal_receiver_refuses_omitted_jobs_and_unplanned_layer_changes(self):
        receiving = self.root_module().analyze
        before = [dict(parent='7', tag='ICT_ID', text='asset', layer_id='11'),
                  dict(parent='7', tag='MODEL', text='before', layer_id='11')]
        after = copy.deepcopy(before)
        after[1]['text'] = 'after'
        plan = dict(changes=[dict(id='asset', attribute='MODEL', before='before', after='after')])
        receiving.operation_state(before, after, plan)
        after[1]['layer_id'] = '0'
        with self.assertRaisesRegex(ValueError, 'unplanned observed property'):
            receiving.operation_state(before, after, plan)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'native.stdout'
            path.write_text('ICT_ROOT12_PROFILE ' + json.dumps(dict(configuration_file=receiving.CONFIG)) + '\n'
                            + 'ICT_ROOT12 ' + json.dumps(dict(id='one')) + '\n', encoding='utf-8')
            receiving.native_rows(path, ['one'])
            with self.assertRaisesRegex(ValueError, 'omitted'):
                receiving.native_rows(path, ['one', 'two'])

    def test_causal_comparison_detects_geometry_and_refuses_a_forged_zero(self):
        receiver = self.root_module()
        source = Path(__file__).resolve().parents[1] / 'examples/cad-handoff/qualification/validation-2/authored/validation-long.dxf'
        before = ch.snapshot(source)
        after = copy.deepcopy(before)
        circle = next(r for r in after['entities'].values() if r['type'] == 'CIRCLE')
        next(t for t in circle['tags'] if t[0] == 40)[1] += 0.25
        report = receiver.analyze.comparison(before, after)
        self.assertGreater(report['strict_differences'], 0)
        forged = dict(report, strict_differences=0, strict_status='pass')
        with self.assertRaisesRegex(ValueError, 'exact re-score'):
            receiver.equal_report(report, forged)

    def public_module(self, name):
        folder = Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification/public-validation-11"
        spec = importlib.util.spec_from_file_location("cad_public11_" + name, folder / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_bitmap_window_contract_uses_size_instead_of_maximum(self):
        convert = self.public_module("window").xywh
        for bounds in ([-10, -14, 46, 10], [10, 20, 30, 50], [-30, -40, -10, -20], [0, 0, 1, 1]):
            x, y, width, height = convert(bounds)
            self.assertEqual([x, y, x + width, y + height], bounds)
        for bounds in ([0, 0, 0, 1], [0, 0, 1, -1], [0, 0, float('inf'), 1], [True, 0, 1, 1]):
            with self.assertRaises(ValueError):
                convert(bounds)

    def test_public_native_receiving_rejects_missing_case_and_wrong_profile(self):
        import json
        receiving = self.public_module("receive")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'native.stdout'
            profile = {'configuration_file': '/home/cad/.config/QCAD/QCAD3.conf'}
            path.write_text('ICT_TRANSFER11_PROFILE ' + json.dumps(profile) + '\nICT_QUAL_NATIVE {"id":"one"}\n', encoding='utf-8')
            self.assertEqual(len(receiving.native_rows(path, 'ICT_QUAL_NATIVE ', ['one'])), 1)
            with self.assertRaisesRegex(ValueError, 'coverage'):
                receiving.native_rows(path, 'ICT_QUAL_NATIVE ', ['one', 'omitted'])
            profile['configuration_file'] = '/work/installed-but-unselected.conf'
            path.write_text('ICT_TRANSFER11_PROFILE ' + json.dumps(profile) + '\nICT_QUAL_NATIVE {"id":"one"}\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'profile'):
                receiving.native_rows(path, 'ICT_QUAL_NATIVE ', ['one'])

    def test_public_native_receiving_checks_every_stored_field(self):
        receiving = self.public_module("receive")
        rows = [{'attributes': {'ICT_ID': 'asset', 'MODEL': 'expected', 'FOREIGN': 'keep'}}]
        expected = {'asset': dict(rows[0]['attributes'])}
        self.assertEqual(receiving.native_fields(rows, expected), 3)
        rows[0]['attributes']['FOREIGN'] = 'lost'
        with self.assertRaisesRegex(ValueError, 'fields'):
            receiving.native_fields(rows, expected)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            receiving.fields(rows + rows)

    def test_public_candidates_native_returns_and_retained_failures(self):
        path = Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification/check_public11.py"
        spec = importlib.util.spec_from_file_location("cad_public11_full", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.check()
        self.assertEqual(result['exact_candidates'], 6)
        self.assertEqual(result['source_exposure'], {'newly_inspected': 4, 'exposed_regression': 2})
        self.assertEqual(result['native_fields'], 72)
        self.assertEqual(result['fresh_process_fields'], 72)
        self.assertEqual(result['corrected_images'], 24)
        self.assertEqual(result['source_revision_loss_controls'], 36)
        self.assertTrue(all(r['strict_differences'] > 0 for r in result['native_strict']))
        self.assertFalse(result['whole_cad_qualified'])

    def module(self):
        path = Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification/check_linux7.py"
        spec = importlib.util.spec_from_file_location("cad_linux_native_replay", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_returned_files_observations_and_receiving_controls(self):
        summary = self.module().check()
        self.assertFalse(summary["whole_cad_qualified"])

    def test_pointer_states_and_neutral_source_candidate_replay(self):
        path = Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification/check_receiver8.py"
        spec = importlib.util.spec_from_file_location("cad_pointer_state_replay", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.check()
        self.assertEqual(result["neutral_source_candidate_different_pixels"], 0)
        self.assertEqual(result["pointer_neutral_views"], 9)
        self.assertEqual(len(result["receiving_refusals"]), 5)
        self.assertFalse(result["whole_cad_qualified"])

    def test_font_profiles_complete_frames_and_planted_receiving_errors(self):
        path = Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification/check_font9.py"
        spec = importlib.util.spec_from_file_location("cad_font_frame_replay", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.check()
        self.assertEqual(result["native_views"], 36)
        self.assertEqual(result["unique_native_attributes"], 144)
        self.assertEqual(result["default_long_overview_pixels_outside_exact_model_bounds"], 62)
        self.assertEqual(len(result["receiving_refusals"]), 7)
        self.assertFalse(result["whole_cad_qualified"])

    def test_minimal_layout_revisions_native_paper_and_foreign_bytes(self):
        path = Path(__file__).resolve().parents[1] / "examples/cad-handoff/qualification/check_layout10.py"
        spec = importlib.util.spec_from_file_location("cad_layout_preparation_replay", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.check()
        self.assertEqual(result["minimal_proposals"], 5)
        self.assertEqual(result["verified_profile_paper_images"], 25)
        self.assertEqual(result["semantic_input_controls"], 17)
        self.assertFalse(result["whole_cad_qualified"])

    def test_evidence_extraction_rejects_paths_links_and_omission(self):
        import hashlib
        import io
        import tarfile
        module = self.module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, (name, kind) in enumerate((("raw/note.txt", "valid"), ("raw/../../escape", "path"),
                                                 ("raw/note:alternate", "path"), ("raw/link", "link"),
                                                 ("raw/note.txt", "omitted"))):
                base = root / str(index)
                base.mkdir()
                archive = base / "evidence.tar.xz"
                data = b"original evidence"
                with tarfile.open(archive, "w:xz") as packed:
                    if kind != "omitted":
                        entry = tarfile.TarInfo(name)
                        entry.size = len(data)
                        if kind == "link":
                            entry.type, entry.linkname = tarfile.SYMTYPE, "../../escape"
                        packed.addfile(entry, io.BytesIO(data))
                ch.write_json(base / "INVENTORY.json", dict(raw_bytes=len(data),
                    archive=dict(path=archive.name, bytes=archive.stat().st_size, sha256=ch.digest(archive)),
                    files={name: dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())}))
                with self.subTest(kind=kind, name=name):
                    if kind == "valid":
                        extracted = module.unpack(base, base / "out")
                        self.assertEqual((extracted / "note.txt").read_bytes(), data)
                    else:
                        with self.assertRaises(ValueError):
                            module.unpack(base, base / "out")
                    self.assertFalse((root / "escape").exists())



if __name__ == "__main__":
    unittest.main()
