"""Frozen connection-intent controls, stale-source refusals and exact terminal distinctions."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import check_pid_connections as tool
import check_pid_markups as markup

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/pid-port-review'
spec = importlib.util.spec_from_file_location('port_replay', EXAMPLE / 'replay.py')
replay = importlib.util.module_from_spec(spec); spec.loader.exec_module(replay)
KEY = json.loads((EXAMPLE / 'ACCEPTANCE.json').read_text(encoding='utf-8'))


class Connections(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = replay.prepare(self.root / 'input')

    def edit(self, field, change):
        manifest = json.loads(self.manifest.read_text(encoding='utf-8'))
        path = self.manifest.parent / manifest[field]['path']
        data = json.loads(path.read_text(encoding='utf-8'))
        change(data); tool.write(path, data)
        manifest[field]['sha256'] = tool.sha(path.read_bytes()); tool.write(self.manifest, manifest)

    def run_tool(self, name='packet'):
        return tool.run(self.manifest, self.root / name)

    def test_prior_key_and_corrected_revision_preserve_sources(self):
        before = {p.relative_to(self.manifest.parent).as_posix(): p.read_bytes()
                  for p in self.manifest.parent.rglob('*') if p.is_file()}
        initial = self.run_tool()
        self.assertEqual({r['id']: r['status'] for r in initial['requirements']}, KEY['initial_requirements'])
        self.assertEqual([r['id'] for r in initial['other_connections']], KEY['initial_other_connections'])
        self.assertEqual(before, {p.relative_to(self.manifest.parent).as_posix(): p.read_bytes()
                                 for p in self.manifest.parent.rglob('*') if p.is_file()})
        corrected = tool.run(replay.prepare(self.root / 'corrected-input', True), self.root / 'corrected')
        self.assertEqual({r['id']: r['status'] for r in corrected['requirements']}, KEY['corrected_requirements'])
        self.assertEqual(corrected['other_connections'], [])
        for result in (initial, corrected):
            self.assertFalse(result['engineering_accepted']); self.assertFalse(result['cad_qualified'])
            self.assertFalse(result['automatic_drawing_reading'])

    def test_port_fact_runs_through_existing_markup_packet(self):
        # Exercise the actual old CLI packet route, not only an isolated new predicate.
        fixture_spec = importlib.util.spec_from_file_location('old_fixture', ROOT/'examples/pid-markup-review/build_fixture.py')
        fixture = importlib.util.module_from_spec(fixture_spec); fixture_spec.loader.exec_module(fixture)
        folder = self.root / 'markup'; fixture.build(folder)
        manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        for field in ('requests', 'readings'):
            path = folder / manifest[field]['path']; data = json.loads(path.read_text(encoding='utf-8'))
            rows = [c['key'] for m in data['markups'] for c in m['checks']] if field == 'requests' else [r['key'] for r in data['observations']]
            for key in rows:
                if key['kind'] == 'connection' and key['relation'] == 'signal':
                    key.update(kind='port_connection', port='OUT', to_port='PV', medium='electric')
            tool.write(path, data); manifest[field]['sha256'] = tool.sha(path.read_bytes())
        tool.write(folder/'manifest.json', manifest)
        result = markup.run(folder/'manifest.json', self.root/'markup-out')
        self.assertEqual(next(m for m in result['markups'] if m['id']=='M04')['status'], 'not_supported')
        self.assertIn('PT-101.OUT', (self.root/'markup-out/REPORT.html').read_text(encoding='utf-8'))
        wrong = replay.matched_baseline()
        self.assertEqual(wrong['tag_only_wrong_input_supported'], KEY['tag_only_wrong_input_supported'])
        self.assertEqual(wrong['port_aware_wrong_input_supported'], KEY['port_aware_wrong_input_supported'])
        with self.assertRaises(markup.InputError):
            markup.value_check(wrong['requested'], 'true')

    def test_direction_relation_medium_and_missing_port_are_findings(self):
        variants = [({'from': {'tag': 'PIC-102', 'port': 'PV'}}, 'from_direction_incompatible'),
                    ({'to': {'tag': 'PIC-102', 'port': 'OUT'}}, 'to_direction_incompatible'),
                    ({'relation': 'process'}, 'from_relation_incompatible'),
                    ({'medium': 'pneumatic'}, 'from_medium_incompatible'),
                    ({'to': {'tag': 'PIC-102', 'port': 'NOPE'}}, 'to_port_missing')]
        for i, (patch, code) in enumerate(variants):
            with self.subTest(code=code):
                self.edit('records', lambda v: v['connections'][1].update(patch))
                result = self.run_tool('variant-' + str(i))
                self.assertIn(code, result['connections'][1]['validation']['issues'])
                # Restore the complete original case before next mutation.
                self.manifest = replay.prepare(self.root / ('input-' + str(i)))

    def test_unknown_types_identity_and_unknown_observation_cannot_be_supported(self):
        self.edit('catalog', lambda v: v['symbols'][0]['ports'][0].update(medium=None))
        result = self.run_tool('null')
        self.assertTrue(all(r['status']=='unknown' for r in result['requirements']))
        self.manifest = replay.prepare(self.root/'new')
        self.edit('records', lambda v: v['connections'].append(dict(copy.deepcopy(v['connections'][1]), id='UNCLEAR', state='unknown', reason='Unreadable line')))
        self.assertEqual(self.run_tool('unclear')['requirements'][0]['status'], 'unknown')
        self.edit('records', lambda v: v.update(identity='uncertain'))
        self.assertTrue(all(r['status']=='unknown' for r in self.run_tool('identity')['requirements']))

    def test_incomplete_or_conflicting_coverage_does_not_prove_absence(self):
        self.edit('records', lambda v: v['coverage'][1].update(complete=False))
        self.assertEqual(self.run_tool('incomplete')['requirements'][1]['status'], 'unknown')
        self.edit('records', lambda v: v['coverage'].append(dict(copy.deepcopy(v['coverage'][1]),complete=True)))
        self.assertEqual(self.run_tool('conflict')['requirements'][1]['status'], 'unknown')

    def test_duplicate_tags_and_connections_remain_ambiguous(self):
        self.edit('records', lambda v: v['assets'].append(copy.deepcopy(v['assets'][2])))
        result = self.run_tool('tags')
        self.assertEqual(result['requirements'][0]['status'], 'unknown')
        self.assertIn({'tag': 'PT-102', 'code': 'ambiguous_tag'}, result['inventory_issues'])
        self.manifest = replay.prepare(self.root/'new')
        self.edit('records', lambda v: v['connections'].append(dict(copy.deepcopy(v['connections'][1]),id='DUP')))
        self.assertEqual(self.run_tool('duplicate')['requirements'][0]['status'], 'ambiguous')

    def test_stale_source_and_rebound_old_observations_refuse(self):
        manifest = json.loads(self.manifest.read_text(encoding='utf-8'))
        doc = manifest['documents'][2]; path = self.manifest.parent / doc['path']
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaisesRegex(tool.InputError, 'Stale file binding'): self.run_tool()
        doc['sha256'] = tool.sha(path.read_bytes()); tool.write(self.manifest, manifest)
        with self.assertRaisesRegex(tool.InputError, 'Stale observation'): self.run_tool()
        self.assertFalse((self.root/'packet').exists())

    def test_invalid_inputs_refuse_before_any_packet(self):
        cases = [('records', lambda v: v['requirements'][0].pop('medium')),
                 ('records', lambda v: v['coverage'][0].update(complete='true')),
                 ('records', lambda v: v['requirements'].append(copy.deepcopy(v['requirements'][0]))),
                 ('records', lambda v: v['connections'][0]['evidence'][0].update(document='markup')),
                 ('records', lambda v: v['connections'][0]['evidence'][0].update(box_0_1000=[0,0,1001,100])),
                 ('records', lambda v: v['allowed_connections'].append(dict(copy.deepcopy(v['requirements'][2]), id='STALE', to={'tag':'PIC-103','port':'PV'}, evidence=copy.deepcopy(v['allowed_connections'][0]['evidence'])))),
                 ('catalog', lambda v: v['symbols'][0]['ports'].append(copy.deepcopy(v['symbols'][0]['ports'][0])))]
        for i, (field, change) in enumerate(cases):
            with self.subTest(i=i):
                self.edit(field, change)
                with self.assertRaises((tool.InputError, KeyError)): self.run_tool()
                self.assertFalse((self.root/'packet').exists())
                self.manifest = replay.prepare(self.root/('new-' + str(i)))

    def test_path_escape_output_collision_and_html_escaping(self):
        self.edit('records', lambda v: v['requirements'][0].update(id='<script>alert(1)</script>'))
        self.run_tool()
        rendered = (self.root/'packet/REPORT.html').read_text(encoding='utf-8')
        self.assertNotIn('<script>', rendered); self.assertIn('&lt;script&gt;', rendered)
        with self.assertRaisesRegex(tool.InputError, 'Output exists'): self.run_tool()
        manifest = json.loads(self.manifest.read_text(encoding='utf-8'))
        manifest['records']['path'] = '../escape.json'; tool.write(self.manifest, manifest)
        with self.assertRaisesRegex(tool.InputError, 'inside manifest'): self.run_tool('escape')

    def test_portable_replay_and_receipt_integrity(self):
        initial = self.run_tool()
        again = tool.run(self.root/'packet/manifest.json', self.root/'replayed')
        self.assertEqual(initial, again)
        receipt = json.loads((self.root/'packet/receipt.json').read_text(encoding='utf-8'))
        for rel, pin in receipt['files'].items():
            self.assertEqual(tool.sha((self.root/'packet'/rel).read_bytes()), pin)

    def test_committed_results_match_prior_key_and_actual_execution(self):
        result = replay.run(self.root/'replay')
        expected = json.loads((EXAMPLE/'worked/replay.json').read_text(encoding='utf-8'))
        self.assertEqual(result, expected)
        self.assertEqual(result['initial']['requirements'], KEY['initial_requirements'])
        self.assertEqual(result['corrected']['requirements'], KEY['corrected_requirements'])
        for label in ('initial', 'corrected'):
            packet = EXAMPLE/'worked'/label
            receipt = json.loads((packet/'receipt.json').read_text(encoding='utf-8'))
            for rel, pin in receipt['files'].items():
                self.assertEqual(tool.sha((packet/rel).read_bytes()), pin)
            for name, pin in receipt['code'].items():
                self.assertEqual(tool.sha((ROOT/'scripts'/name).read_bytes().replace(b'\r\n', b'\n')), pin)


if __name__ == '__main__': unittest.main()
