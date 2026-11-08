"""Requested-change review controls: source freshness, negative coverage, topology and later returns."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import check_pid_markups as tool

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/pid-markup-review'
spec = importlib.util.spec_from_file_location('markup_fixture', EXAMPLE / 'build_fixture.py')
fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
KEY = json.loads((EXAMPLE / 'ACCEPTANCE.json').read_text(encoding='utf-8'))


class MarkupReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / 'inputs'; fixture.build(self.inputs)

    def edit(self, name, change):
        path = self.inputs / name
        value = json.loads(path.read_text(encoding='utf-8'))
        change(value); fixture.write(path, value)
        if name != 'manifest.json':
            manifest = json.loads((self.inputs / 'manifest.json').read_text(encoding='utf-8'))
            manifest[name.removesuffix('.json')]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            fixture.write(self.inputs / 'manifest.json', manifest)

    def run_review(self, name='out'):
        return tool.run(self.inputs / 'manifest.json', self.root / name)

    def test_imperfect_return_against_prior_acceptance_and_unchanged_sources(self):
        original = {p.name: p.read_bytes() for p in self.inputs.iterdir()}
        result = self.run_review()
        self.assertEqual({m['id']: m['status'] for m in result['markups']}, KEY['markup_statuses'])
        self.assertEqual(result['counts'], KEY['counts'])
        self.assertEqual(len(result['other_observed_changes']), KEY['other_observed_changes'])
        self.assertEqual(result['other_observed_changes'][0]['key']['name'], 'fail_action')
        self.assertEqual(len(result['other_fact_coverage_gaps']), KEY['other_fact_coverage_gaps'])
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.inputs.iterdir()})
        queue = (self.root / 'out/review_queue.csv').read_text(encoding='utf-8').splitlines()
        self.assertTrue(queue[1].startswith('M02,safety,'))
        self.assertTrue(any(row.startswith('OTHER-001,needs_assessment,') for row in queue))
        self.assertTrue(any(row.startswith('COVERAGE-001,normal,') for row in queue))
        self.assertFalse(result['release_accepted']); self.assertFalse(result['automatic_drawing_reading'])
        replay = tool.run(self.root/'out/manifest.json', self.root/'portable-replay')
        self.assertEqual(replay['counts'], result['counts'])
        receipt = json.loads((self.root/'out/receipt.json').read_text(encoding='utf-8'))
        for path, pin in receipt['files'].items():
            self.assertEqual(hashlib.sha256((self.root/'out'/path).read_bytes()).hexdigest(), pin)

    def test_missing_absence_evidence_does_not_verify_removal(self):
        self.edit('readings.json', lambda v: v.update(observations=[o for o in v['observations']
                  if not (o['role']=='returned' and o['key']['kind']=='symbol' and o['key']['subject']=='HV-102')]))
        item = next(m for m in self.run_review()['markups'] if m['id']=='M02')
        self.assertEqual(item['status'], 'not_verifiable')
        self.assertEqual(item['checks'][0]['returned']['state'], 'unknown')

    def test_tag_presence_or_reversed_connection_is_not_requested_signal(self):
        def change(value):
            row = next(o for o in value['observations'] if o['role']=='returned' and o['key']['kind']=='connection'
                       and o['key']['relation']=='signal')
            row['key']['subject'], row['key']['to'] = row['key']['to'], row['key']['subject']
            row['value'] = True
        self.edit('readings.json', change)
        item = next(m for m in self.run_review()['markups'] if m['id']=='M04')
        self.assertEqual(item['status'], 'not_verifiable')

    def test_conflicting_readings_and_unconfirmed_identity_stay_open(self):
        def conflict(value):
            row = copy.deepcopy(next(o for o in value['observations'] if o['role']=='returned'
                                     and o['key'].get('name')=='size'))
            row['value'] = 'DN100'; value['observations'].append(row)
        self.edit('readings.json', conflict)
        item = next(m for m in self.run_review()['markups'] if m['id']=='M01')
        self.assertEqual(item['checks'][0]['status'], 'ambiguous')
        self.edit('manifest.json', lambda v: v['documents'][2]['pages'][0].update(identity='uncertain'))
        self.assertFalse(any(m['status']=='supported' for m in self.run_review('uncertain')['markups']))

    def test_stale_source_and_rebound_file_with_old_observations_refuse(self):
        path = self.inputs / 'returned.svg'; path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaisesRegex(tool.InputError, 'Stale file binding'):
            self.run_review()
        self.edit('manifest.json', lambda v: v['documents'][2].update(sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        with self.assertRaisesRegex(tool.InputError, 'Stale observation'):
            self.run_review()
        self.assertFalse((self.root / 'out').exists())

    def test_locators_roles_and_duplicate_sheet_identity_refuse(self):
        original = (self.inputs / 'readings.json').read_bytes()
        for field, value in [('page', 2), ('box_0_1000', [0,0,1001,100]), ('document','markup')]:
            with self.subTest(field=field):
                (self.inputs / 'readings.json').write_bytes(original)
                self.edit('readings.json', lambda v: v['observations'][0]['evidence'][0].update({field:value}))
                with self.assertRaises(tool.InputError):self.run_review()
        self.edit('manifest.json', lambda v: v['documents'][0]['pages'].append(dict(v['documents'][0]['pages'][0],page=2)))
        with self.assertRaisesRegex(tool.InputError, 'Ambiguous repeated sheet'):
            self.run_review()

    def test_typed_values_conflicting_requests_and_path_escape_refuse_or_remain_unmatched(self):
        self.edit('requests.json', lambda v: v['markups'][0]['checks'][0].update(after=80))
        item = next(m for m in self.run_review()['markups'] if m['id']=='M01')
        self.assertEqual(item['checks'][0]['status'], 'different_from_request')
        self.edit('requests.json', lambda v: v['markups'].append(dict(copy.deepcopy(v['markups'][0]),id='M08',checks=[dict(v['markups'][0]['checks'][0],after='DN125')])))
        with self.assertRaisesRegex(tool.InputError, 'Conflicting markup requests'):
            self.run_review('conflicting')
        outside=self.root/'outside.svg';outside.write_text('<svg/>',encoding='utf-8')
        self.edit('manifest.json', lambda v:v['documents'][0].update(path='../outside.svg',sha256=hashlib.sha256(outside.read_bytes()).hexdigest()))
        with self.assertRaisesRegex(tool.InputError, 'inside the manifest folder'):
            self.run_review('outside')

    def test_collision_html_escaping_and_revised_return_are_separate_packets(self):
        self.edit('requests.json', lambda v: v['markups'][0].update(text='<script>alert("x")</script>'))
        result=self.run_review()
        html=(self.root/'out/REPORT.html').read_text(encoding='utf-8')
        self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html)
        before=(self.root/'out/result.json').read_bytes()
        with self.assertRaisesRegex(tool.InputError,'Output exists'):self.run_review()
        fixture.build(self.root/'corrected',corrected=True)
        corrected=tool.run(self.root/'corrected/manifest.json',self.root/'later')
        self.assertEqual({m['id']:m['status'] for m in corrected['markups']},KEY['corrected_return_statuses'])
        self.assertEqual(before,(self.root/'out/result.json').read_bytes())
        self.assertNotEqual(result['documents'][2]['sha256'],corrected['documents'][2]['sha256'])
        self.assertEqual(corrected['other_observed_changes'],[])
        self.assertTrue(all(m['review_required'] for m in corrected['markups']))

    def test_committed_packets_reproduce_and_receipts_bind_every_retained_file(self):
        for label in ('worked','corrected'):
            with self.subTest(packet=label):
                packet=EXAMPLE/label
                expected=json.loads((packet/'result.json').read_text(encoding='utf-8'))
                result=tool.run(packet/'manifest.json',self.root/label)
                self.assertEqual(result,expected)
                receipt=json.loads((packet/'receipt.json').read_text(encoding='utf-8'))
                for path,pin in receipt['files'].items():
                    self.assertEqual(hashlib.sha256((packet/path).read_bytes()).hexdigest(),pin)


if __name__=='__main__':unittest.main()
