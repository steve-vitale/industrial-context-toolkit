"""Offline retained Linux CAD UI evidence and bounded archive receiving controls."""
import importlib.util
import copy
import json
from pathlib import Path
import tempfile
import unittest

import cad_handoff as ch


class RetainedLinuxNativeEvidence(unittest.TestCase):
    def open_module(self):
        path = Path(__file__).resolve().parents[1] / 'examples/cad-handoff/qualification/check_open18.py'
        spec = importlib.util.spec_from_file_location('cad_open18_receiver', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_normal_application_does_not_repair_native_plot_storage(self):
        result = self.open_module().check()
        self.assertEqual(result['document_jobs'], 84)
        self.assertEqual(result['inventory_comparisons'], 546)
        self.assertEqual(sum(r['calls'] for r in result['constructors'].values()), 426)
        for route in ('bare', 'mdi'):
            for stage in ('opened', 'noop', 'after_print'):
                self.assertEqual(result['attribution'][route][stage],
                                 dict(observations=372, follows_presets=192, equal_across_presets=180))
        for kind in ('noop', 'print'):
            self.assertEqual(result['differences'][kind], dict(comparisons=84, target=0, non_target=0))
        self.assertEqual(result['print_value_changed_leaves'], 0)
        self.assertEqual(result['mdi_closes_accepted'], 42)
        self.assertEqual(result['mdi_wrappers_still_counted'], 42)
        self.assertFalse(result['strict_comparison_run'])
        self.assertFalse(result['whole_cad_qualified'])

    def test_open_receiving_refuses_missing_or_altered_native_evidence(self):
        receiver = self.open_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = receiver.old.unpack(receiver.BASE, Path(temporary))
            path = root / 'attempt-1/native/mdi-preset-a.stdout'
            original = path.read_bytes()
            for kind in ('missing_job', 'missing_getter', 'wrong_filter', 'no_view', 'lost_close', 'unrelated_change'):
                lines = original.decode('utf-8').splitlines()
                index = next(i for i, line in enumerate(lines) if line.startswith('ICT_OPEN18_JOB '))
                row = json.loads(lines[index].split(' ', 1)[1])
                if kind == 'missing_getter':
                    row['after_print']['headers']['layouts'][0]['properties'].pop()
                elif kind == 'wrong_filter':
                    row['filter'] = 'DXF Files [dxflib] (*.dxf)'
                elif kind == 'no_view':
                    row['has_view'] = False
                elif kind == 'lost_close':
                    row['close_result'] = False
                elif kind == 'unrelated_change':
                    row['after_print']['file_version'] = 'an unrelated changed value'
                if kind == 'missing_job':
                    lines.pop(index)
                else:
                    lines[index] = 'ICT_OPEN18_JOB ' + json.dumps(row)
                path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    receiver.receive(root)
                path.write_bytes(original)

    def test_open_analysis_preserves_unrelated_changes_in_full_comparison(self):
        receiver = self.open_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = receiver.old.unpack(receiver.BASE, Path(temporary)) / 'attempt-1'
            path = root / 'native/mdi-preset-a.stdout'
            lines = path.read_text(encoding='utf-8').splitlines()
            index = next(i for i, line in enumerate(lines) if line.startswith('ICT_OPEN18_JOB '))
            row = json.loads(lines[index].split(' ', 1)[1])
            row['after_print']['file_version'] = 'unexpected version'
            lines[index] = 'ICT_OPEN18_JOB ' + json.dumps(row)
            path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            result, detail = receiver.analysis.analyze(root)
            self.assertGreater(result['differences']['print']['non_target'], 0)
            self.assertTrue(any(c['path'] == '/file_version' for r in detail['comparisons'] for c in r['changes']))
            self.assertFalse(result['whole_cad_qualified'])

    def test_open_receiving_keeps_controller_and_cleanup_failures(self):
        receiver = self.open_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = receiver.old.unpack(receiver.BASE, Path(temporary))
            for name, replacement in [('MDI-CLOSE-ACTIONS.json', []), ('STARTUP-ACTIONS.json', []),
                                      ('CONTROLLER-STATUS.json', {'native_process_restarts': 1})]:
                path = root / 'attempt-1' / name
                original = path.read_bytes()
                path.write_text(json.dumps(replacement), encoding='utf-8')
                with self.subTest(name=name), self.assertRaises(ValueError):
                    receiver.receive(root)
                path.write_bytes(original)
            path = root / 'attempt-1/native/bare-observe.stderr'
            path.write_text(path.read_text(encoding='utf-8').replace("'QCoreApplication.quit' [undefined] is not a function", 'omitted'), encoding='utf-8')
            with self.assertRaises(ValueError):
                receiver.receive(root)

    def layout_module(self):
        path = Path(__file__).resolve().parents[1] / 'examples/cad-handoff/qualification/check_layout17.py'
        spec = importlib.util.spec_from_file_location('cad_layout17_receiver', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_actual_constructor_presets_remain_a_diagnostic(self):
        result = self.layout_module().check()
        self.assertEqual(result['document_jobs'], 56)
        self.assertEqual([r['calls'] for r in result['constructors'].values()], [68] * 4)
        self.assertEqual(result['inventory_comparisons'], 168)
        self.assertEqual(result['target_differences'], 2355)
        self.assertEqual(result['non_target_differences'], 0)
        self.assertEqual(result['follows_presets'], dict(initial=336, imported=192))
        self.assertEqual(result['all_modes_equal'], dict(initial=0, imported=180))
        self.assertTrue(result['constructor_causality_confirmed'])
        self.assertTrue(result['detached_getters_confirmed'])
        self.assertEqual(result['cad_files_saved'], 0)
        self.assertFalse(result['whole_cad_qualified'])
        self.assertFalse(result['strict_comparison_run'])

    def test_constructor_receiving_refuses_lost_or_altered_observations(self):
        receiver = self.layout_module()
        a = receiver.a
        with tempfile.TemporaryDirectory() as temporary:
            root = receiver.old.unpack(receiver.BASE, Path(temporary)) / 'attempt-2'
            fields = a.read(root / 'FIELDS.json')
            rows = a.records(root / 'native/preset-a.stderr', 'ICT_LAYOUT17_CTOR ')
            for kind in ('missing_call', 'missing_field', 'wrong_mode', 'wrong_abi', 'pre_write', 'post_write', 'tab_not_reset'):
                changed = copy.deepcopy(rows)
                if kind == 'missing_call':
                    changed.pop(1)
                elif kind == 'missing_field':
                    changed[0]['fields'].pop()
                elif kind == 'wrong_mode':
                    changed[0]['mode'] = 'observe'
                elif kind == 'wrong_abi':
                    changed[0]['fields'][0]['offset'] += 1
                elif kind == 'tab_not_reset':
                    changed[0]['fields'][-1]['after_library'] = 'd2040000'
                else:
                    changed[0]['fields'][0]['before_library' if kind == 'pre_write' else 'after_library'] = '0000000000000000'
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    a.constructor_rows(changed, fields, 'preset-a')
            detached = a.records(root / 'native/preset-a.stdout', 'ICT_LAYOUT17_DETACHED ')[0]
            for kind in ('missing_getter', 'typed_boolean'):
                changed = copy.deepcopy(detached)
                if kind == 'missing_getter':
                    changed['properties'].pop()
                else:
                    next(p for p in changed['properties'] if p['getter'] == 'getUseStandardScale')['value'] = dict(type='number', value=0)
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    a.detached(changed, fields, a.read(root / 'KEYS.json'), 'preset-a')

    def test_layout_receiving_keeps_non_target_changes_and_failed_imports(self):
        receiver = self.layout_module()
        a = receiver.a
        with tempfile.TemporaryDirectory() as temporary:
            root = receiver.old.unpack(receiver.BASE, Path(temporary)) / 'attempt-2'
            path = root / 'native/observe.stdout'
            original = path.read_text(encoding='utf-8')
            prefix = 'ICT_LAYOUT17_JOB '
            for kind in ('other_change', 'failed_import', 'omitted_variable', 'omitted_job'):
                lines = original.splitlines()
                index = next(i for i, line in enumerate(lines) if line.startswith(prefix))
                row = json.loads(lines[index][len(prefix):])
                if kind == 'other_change':
                    row['initial']['file_version'] = 'unrelated changed version'
                elif kind == 'failed_import':
                    row['import_code'] = 99
                elif kind == 'omitted_variable':
                    row['initial']['headers']['known_variables'].pop()
                if kind == 'omitted_job':
                    lines.pop(index)
                else:
                    lines[index] = prefix + json.dumps(row)
                path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                with self.subTest(kind=kind):
                    if kind == 'other_change':
                        summary, detail = a.analyze(root)
                        self.assertEqual(summary['non_target_differences'], 3)
                        self.assertEqual(sum(c['path'] == '/file_version' for r in detail['comparisons'] for c in r['differences']), 3)
                    else:
                        with self.assertRaises(ValueError):
                            a.analyze(root)
            path.write_text(original, encoding='utf-8')
            completion = a.read(root / 'native/COMPLETE.json')
            completion['whole_cad_qualified'] = True
            ch.write_json(root / 'native/COMPLETE.json', completion)
            with self.assertRaisesRegex(ValueError, 'completion claim'):
                a.analyze(root)

    def headers_module(self):
        path = Path(__file__).resolve().parents[1] / 'examples/cad-handoff/qualification/check_headers16.py'
        spec = importlib.util.spec_from_file_location('cad_headers16_receiver', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_header_controls_retain_fresh_layout_failures(self):
        result = self.headers_module().check()
        self.assertEqual(result['observation_jobs'], 26)
        self.assertEqual(result['observation_exports'], 25)
        self.assertEqual(result['observation_fresh_imports'], 25)
        self.assertEqual(result['observation_exact_public_inventory_repeats'], 17)
        self.assertEqual(len(result['fresh_layout_differences']), 8)
        changes = [r for row in result['fresh_layout_differences'] for r in row['differences']]
        self.assertEqual(len(changes), 46)
        self.assertTrue(all(r['path'].startswith('/headers/layouts/') for r in changes))
        self.assertEqual(result['dimension_exports'], 48)
        self.assertEqual(result['dimension_exact_public_inventory_repeats'], 48)
        self.assertEqual(result['exact_single_cell_operations'], 48)
        self.assertEqual(result['directional_DIMASZ_controls'], 48)
        self.assertEqual(result['dimension_strict_statuses'], dict(differences=24, refused=24))
        self.assertFalse(result['whole_cad_qualified'])

    def test_dimensional_operation_refuses_the_other_store_changing(self):
        operation = self.headers_module().a.operation
        original = dict(objects=[], variables=[], file_version='R24', headers=dict(layouts=[],
            known_variables=[dict(name='DIMASZ', enum_id=24, present=True, value=dict(type='number', value=0.18)),
                             dict(name='USERI5', enum_id=144, present=False, value=dict(type='undefined'))],
            dimension_variables=[dict(name='DIMASZ', has_override=True, value=dict(type='number', value=2.5))]))
        known = copy.deepcopy(original)
        known['headers']['known_variables'][0]['value']['value'] = 9.875
        operation(original, known, 'known')
        style = copy.deepcopy(original)
        style['headers']['dimension_variables'][0]['value']['value'] = 9.875
        operation(original, style, 'style')
        both = copy.deepcopy(known)
        both['headers']['dimension_variables'] = style['headers']['dimension_variables']
        for label in ('known', 'style', 'unchanged'):
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, 'Undeclared recorded change'):
                    operation(original, both, label)

    def test_raw_header_keeps_literal_zero_time_and_line_endings(self):
        analysis = self.headers_module().a
        data = b'  0\r\nSECTION\r\n  2\r\nHEADER\r\n  9\r\n$TDCREATE\r\n 40\r\n0.0\r\n  9\n$DIMASZ\n 40\n9.875\n  0\r\nENDSEC\r\n'
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary) / 'literal.dxf'
            p.write_bytes(data)
            result = analysis.raw_header(p)
            self.assertEqual(bytes.fromhex(result['raw_hex']), data)
            self.assertEqual(analysis.raw_number(result, '$TDCREATE', 40), 0.0)
            self.assertEqual(analysis.raw_number(result, '$DIMASZ', 40), 9.875)
        self.assertEqual(len(analysis.changes({'typed': False}, {'typed': 0})), 1)

    def test_header_reassembly_refuses_escaping_duplicate_and_missing_parts(self):
        import hashlib
        receiving = self.headers_module()
        data = b'exact native observations'
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for mode in ('valid', 'escape', 'duplicate', 'missing', 'wrong_hash', 'unreferenced'):
                root = parent / mode
                (root / 'chunks').mkdir(parents=True)
                (root / 'chunks/one.part').write_bytes(data)
                parts = ['chunks/one.part'] * (2 if mode == 'duplicate' else 1)
                if mode == 'missing':
                    parts = ['chunks/missing.part']
                if mode == 'unreferenced':
                    (root / 'chunks/extra.part').write_bytes(data)
                pin = dict(bytes=len(data) * len(parts), sha256=hashlib.sha256(data * len(parts)).hexdigest(), parts=parts)
                if mode == 'wrong_hash':
                    pin['sha256'] = '0' * 64
                ch.write_json(root / 'REASSEMBLY.json', {'../escape.bin' if mode == 'escape' else 'native.stdout': pin})
                with self.subTest(mode=mode):
                    if mode == 'valid':
                        receiving.reassemble(root)
                        self.assertEqual((root / 'native.stdout').read_bytes(), data)
                    else:
                        with self.assertRaises(ValueError):
                            receiving.reassemble(root)
                self.assertFalse((parent / 'escape.bin').exists())

    def test_header_native_inventory_cannot_drop_a_known_variable(self):
        receiving = self.headers_module()
        keys = receiving.b.read(receiving.BASE / 'KEYS.json')
        state = dict(objects=[], variables=[], headers=dict(layouts=[],
            known_variables=[dict(name=k, enum_id=i, present=False, value=dict(type='undefined'))
                             for i, k in enumerate(keys['known_variables'])],
            dimension_variables=[dict(name=r['name'], has_override=False, value=dict(type='undefined'))
                                 for r in keys['dimension_variables']]))
        profile = dict(configuration_file='/home/cad/.config/QCAD/QCAD3.conf', qt_version='5.14.2',
            importer_filters=['DXF Files [dxflib] (*.dxf)'], exporter_filters=['R15 [2000/LT2000] DXF Drawing [dxflib] (*.dxf)'])
        job = dict(id='failed', importer='dxflib', exporter='dxflib', version='R15')
        row = dict(id='failed', import_filter=profile['importer_filters'][0], export_filter=profile['exporter_filters'][0],
                   initial=state, error='retained failure')
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary) / 'native.stdout'
            def save():
                p.write_text('ICT_HEADER16_PROFILE ' + json.dumps(profile) + '\nICT_HEADER16 ' + json.dumps(row) + '\n', encoding='utf-8')
            save()
            receiving.a.native_rows(p, [job], keys, True)
            state['headers']['known_variables'].pop()
            save()
            with self.assertRaisesRegex(ValueError, 'known-variable observation omitted'):
                receiving.a.native_rows(p, [job], keys, True)

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
        self.assertEqual(result['symbol_controls']['attempted_jobs'], 6)
        self.assertEqual(result['symbol_controls']['target_rename_exported'], 2)
        self.assertEqual(result['symbol_controls']['unchanged_failed'], 2)
        self.assertEqual(result['symbol_controls']['unrelated_rename_failed'], 2)
        self.assertEqual([r['strict_report']['status'] for r in result['symbol_controls']['observations']
                          if 'strict_report' in r], ['refused', 'refused'])
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

    def test_symbol_control_refuses_undeclared_public_changes(self):
        operation = self.records_module().symbols.operation
        before = dict(objects=[dict(id='69', type=4, name='2/2-directional valve', custom=[], handle='45')],
                      variables=[dict(name='retained', value=17)], known={}, file_version='R15')
        rename = dict(before='2/2-directional valve', after='2_2-directional valve')
        after = copy.deepcopy(before)
        after['objects'][0]['name'] = rename['after']
        operation(before, after, rename)
        operation(before, before, None)
        for changed in ('handle', 'variable', 'undeclared', 'duplicate'):
            forged = copy.deepcopy(after)
            if changed == 'handle':
                forged['objects'][0]['handle'] = '46'
            elif changed == 'variable':
                forged['variables'][0]['value'] = 18
            elif changed == 'duplicate':
                forged['objects'].append(copy.deepcopy(forged['objects'][0]))
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    operation(before, forged, None if changed == 'undeclared' else rename)

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
