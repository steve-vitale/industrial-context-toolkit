"""Substantive own-input, relationship, ledger and retained-history controls."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import maintenance_history as mh

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('history_fixture_author', ROOT / 'examples/maintenance-history/fixtures.py')
fixtures = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixtures)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.data = fixtures.records()

    def run_packet(self, name='packet', layout='comma', data=None, rev='1', previous=None, edit=None):
        profile = fixtures.write(self.root / (name + '-inputs'), layout, data or self.data, rev)
        if edit:
            p = json.loads(profile.read_bytes()); edit(p); mh.dump(profile, p)
        return mh.run(profile, self.root / name, previous)

    def asset(self, result, scope='U1', identity='P-101'):
        return next(d for d in result['assets'] if d['key'] == [scope, identity])

    def test_authored_key_scoped_identity_signed_ledger_and_quarantine(self):
        r = self.run_packet(); a = self.asset(r)
        self.assertEqual(r['counts'], dict(assets=3, work_orders=7, transactions=4, details=5, labor=6))
        self.assertEqual([x['record']['id'] for x in a['work_orders']], ['W1', 'W2', 'W3'])
        self.assertEqual(a['booked_hours']['value'], '2.5')
        self.assertEqual(self.asset(r, 'U2')['booked_hours']['value'], '3')
        self.assertEqual(self.asset(r, identity='PARK')['booked_hours']['state'], 'no_rows_supplied')
        self.assertIsNone(self.asset(r, identity='PARK')['booked_hours']['value'])
        self.assertEqual([g['orders'] for g in a['recurring_work']], [['W1', 'W2']])
        self.assertEqual(self.asset(r, identity='PARK')['recurring_work'][0]['orders'], ['W6', 'W7'])
        self.assertEqual(sum(len(d['recurring_work']) for d in r['assets']), 2)
        w1, w2, _ = a['work_orders']
        self.assertEqual(w1['booked_hours']['value'], '1.5')
        self.assertEqual([d['quantity'] for d in w1['details']], ['2', '-1'])
        self.assertEqual(w2['transactions'], [])
        self.assertEqual(w2['details'], [])
        self.assertEqual({k: v['unlinked'] for k, v in r['relationship_coverage'].items()}, dict(work_orders=1, transactions=1, details=2, labor=1))
        self.assertFalse(r['company_acceptance']); self.assertEqual(r['authorized_decision'], 'pending')
        self.assertEqual(w1['record']['origin']['record'], 2)
        self.assertEqual(w1['record']['origin']['end_line'], 3)

    def test_three_transport_layouts_have_same_substantive_result(self):
        results = [self.run_packet(layout, layout=layout) for layout in ('comma', 'semicolon', 'json')]
        def facts(r):
            return [(d['key'], [w['record']['id'] for w in d['work_orders']], d['booked_hours'], d['recurring_work'][0]['orders'] if d['recurring_work'] else []) for d in r['assets']]
        self.assertEqual(facts(results[0]), facts(results[1])); self.assertEqual(facts(results[0]), facts(results[2]))
        for layout in ('comma', 'semicolon', 'json'):
            root = self.root / layout
            original = self.root / (layout + '-inputs') / ('work_orders.json' if layout == 'json' else 'work_orders.csv')
            self.assertEqual((root / 'originals/work_orders/001' ).with_suffix(original.suffix).read_bytes(), original.read_bytes())

    def test_unknown_flags_and_dates_remain_unknown(self):
        r = self.run_packet(); w2 = self.asset(r)['work_orders'][1]
        self.assertEqual(w2['record']['_flags']['reopened'], 'unknown')
        self.assertEqual(w2['labor'][0]['_flags']['correction'], 'unknown')
        row = next(x for x in r['all_records']['work_orders'] if x['id'] == 'W5')
        self.assertEqual(row['_dates']['created']['state'], 'unparsed')
        self.assertEqual(row['created'], '03/04/2024')
        self.assertIn('unparsed_date', {x['code'] for x in r['issues']})

    def test_zero_hours_is_known_but_invalid_or_missing_hours_is_unavailable(self):
        for raw, expected, value in [('0', 'known', '0'), ('not recorded', 'unavailable', None), ('', 'unavailable', None)]:
            with self.subTest(raw=raw):
                data = fixtures.records(); data['labor'] = [dict(data['labor'][0], hours=raw)]
                r = self.run_packet('hour-' + str(len(list(self.root.iterdir()))), data=data)
                self.assertEqual(self.asset(r)['booked_hours']['state'], expected)
                self.assertEqual(self.asset(r)['booked_hours']['value'], value)
                if expected == 'unavailable':
                    self.assertTrue(any(i['field'] == 'hours' for i in r['issues']))

    def test_no_ledger_policy_never_sums_hours(self):
        r = self.run_packet(edit=lambda p: p.pop('labor_ledger'))
        self.assertEqual(self.asset(r)['booked_hours']['state'], 'not_authorized')

    def test_duplicate_scoped_ids_refuse_without_output_or_source_mutation(self):
        for table in fixtures.records():
            with self.subTest(table=table):
                data = fixtures.records(); data[table].append(dict(data[table][0]))
                profile = fixtures.write(self.root / ('dup-' + table), data=data)
                before = {p.name: p.read_bytes() for p in profile.parent.iterdir()}
                with self.assertRaisesRegex(ValueError, 'duplicate scoped primary identity'):
                    mh.run(profile, self.root / ('out-' + table))
                self.assertFalse((self.root / ('out-' + table)).exists())
                self.assertEqual(before, {p.name: p.read_bytes() for p in profile.parent.iterdir()})

    def test_missing_optional_exports_and_empty_labor_are_explicit(self):
        for table_absent in (True, False):
            data = fixtures.records()
            if table_absent:
                data.pop('labor')
            else:
                data['labor'] = []
            def edit(p):
                if table_absent:
                    p.pop('labor_ledger')
            r = self.run_packet('missing-' + str(table_absent), data=data, edit=edit)
            self.assertEqual('labor' in r['sources'], not table_absent)
            self.assertIsNone(self.asset(r)['booked_hours']['value'])

    def test_revisions_preserve_omission_and_portable_history(self):
        self.run_packet('initial'); prior = self.root / 'initial'; before = mh.inventory(prior)
        data = fixtures.records(); data['work_orders'][1]['completed'] = '2024-01-08'
        r = self.run_packet('corrected', data=data, rev='2', previous=prior)
        self.assertEqual(mh.inventory(prior), before)
        rev = json.loads((self.root / 'corrected/revision.json').read_bytes())
        self.assertEqual([(x['table'], x['identity'], x['state']) for x in rev['records']], [('work_orders', ['U1', 'W2'], 'changed')])
        self.assertIn('no_longer_detected_needs_reconciliation', {x['state'] for x in rev['prior_issues']})
        data['work_orders'] = [w for w in data['work_orders'] if w['id'] != 'W2']
        self.run_packet('omitted', data=data, rev='3', previous=self.root / 'corrected')
        omission = json.loads((self.root / 'omitted/revision.json').read_bytes())
        self.assertTrue(any(x['state'] == 'omitted' and x['identity'] == ['U1', 'W2'] for x in omission['records']))
        current = json.loads((self.root / 'omitted/result.json').read_bytes())
        replay = mh.run(self.root / 'omitted/job.json', self.root / 'relocated')
        self.assertEqual(current, replay)
        self.assertTrue((self.root / 'relocated/previous/previous/originals/work_orders/001.csv').exists())

    def test_unchanged_revision_with_changed_bytes_refuses(self):
        self.run_packet('initial'); data = fixtures.records(); data['work_orders'][1]['completed'] = '2024-01-08'
        with self.assertRaisesRegex(ValueError, 'changed under unchanged document revision'):
            self.run_packet('wrong', data=data, previous=self.root / 'initial')
        self.assertFalse((self.root / 'wrong').exists())

    def test_changed_mapping_is_a_basis_change_not_an_accepted_correction(self):
        self.run_packet('initial')
        self.run_packet('changed', rev='2', previous=self.root / 'initial', edit=lambda p: p['sources']['work_orders'].update(flags=dict(reopened=dict(true=['?'], false=['N']))))
        r = json.loads((self.root / 'changed/revision.json').read_bytes())
        self.assertIn('work_orders: flags', r['basis_changes'])
        self.assertTrue(all('accepted' not in x['state'] for x in r['prior_issues']))

    def test_prior_tampering_and_occupied_outputs_refuse(self):
        self.run_packet(); root = self.root / 'packet'; mh.verify_packet(root)
        (root / 'originals/labor/001.csv').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            mh.verify_packet(root)
        before = (root / 'REPORT.html').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Output exists'):
            mh.run(self.root / 'packet-inputs/profile.json', root)
        self.assertEqual((root / 'REPORT.html').read_bytes(), before)

    def test_html_escapes_source_and_code_text(self):
        self.data['assets'][0]['description'] = '<script>bad()</script>'
        self.data['work_orders'][0]['description'] = '<img src=x onerror=bad()>'
        r = self.run_packet()
        page = (self.root / 'packet' / self.asset(r)['page']).read_text()
        self.assertNotIn('<img src=x', page); self.assertIn('&lt;img', page)
        self.assertNotIn('<script>bad()', page); self.assertIn('&lt;script&gt;', page)

    def test_nested_revision_recomputed_even_with_updated_inventory(self):
        self.run_packet('initial')
        self.run_packet('second', rev='2', previous=self.root / 'initial')
        root = self.root / 'second'
        history = json.loads((root / 'revision.json').read_bytes())
        history['records'] = [{'state': 'invented'}]
        mh.dump(root / 'revision.json', history)
        receipt = json.loads((root / 'receipt.json').read_bytes())
        receipt['files'] = mh.inventory(root); mh.dump(root / 'receipt.json', receipt)
        with self.assertRaisesRegex(ValueError, 'revision findings do not reproduce'):
            mh.verify_packet(root)

    def test_retained_history_path_cannot_escape_packet(self):
        self.run_packet('initial')
        root = self.root / 'initial'; job = json.loads((root / 'job.json').read_bytes())
        job['previous_packet'] = '../outside'; mh.dump(root / 'job.json', job)
        receipt = json.loads((root / 'receipt.json').read_bytes())
        receipt['files'] = mh.inventory(root); mh.dump(root / 'receipt.json', receipt)
        with self.assertRaisesRegex(ValueError, 'history escapes'):
            mh.verify_packet(root)

    def test_unknown_columns_and_json_duplicate_keys_refuse(self):
        profile = fixtures.write(self.root / 'unknown')
        path = profile.parent / 'assets.csv'; path.write_text(path.read_text(encoding='utf-8-sig').replace('id,scope', 'surprise,scope'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'headers differ'):
            mh.run(profile, self.root / 'bad')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
            mh.strict_json('[{"id":"a","id":"b"}]')

    def test_dates_are_explicit_and_missing_creation_has_action(self):
        self.assertEqual(mh.parse_date('03/04/2024', 'dmy_date'), '2024-04-03')
        self.assertEqual(mh.parse_date('03/04/2024', 'mdy_date'), '2024-03-04')
        self.assertEqual(mh.parse_date('Jan  9 2024 12:50AM', 'english_datetime'), '2024-01-09T00:50:00')
        self.assertEqual(mh.parse_date('2024-01-09T01:00:00+02:00', 'iso_utc'), '2024-01-08T23:00:00+00:00')
        with self.assertRaises(ValueError):
            mh.parse_date('2024-01-09T01:00:00Z', 'iso_datetime')
        self.data['work_orders'][0]['created'] = ''
        self.data['work_orders'][1]['completed'] = '2024-02-01'
        r = self.run_packet()
        self.assertTrue({'missing_creation_date', 'date_after_cutoff'} <= {x['code'] for x in r['issues']})

    def test_output_input_alias_and_missing_exact_foreign_key(self):
        profile = fixtures.write(self.root / 'inputs')
        with self.assertRaisesRegex(ValueError, 'Output exists'):
            mh.run(profile, profile.parent)
        self.data['work_orders'][0]['asset_id'] = ' P-101'
        r = self.run_packet()
        self.assertEqual(len(self.asset(r)['work_orders']), 2)
        self.assertTrue(any(x['record'] == ['U1', 'W1'] for x in r['unlinked']['work_orders']))


    def no_id_export(self, name, rows, edit=None):
        """A one-file work-order export without an ID column (as in the Nestor excavator records)."""
        profile = fixtures.write(self.root / (name + '-inputs'))
        folder = profile.parent
        with (folder / 'work_orders.csv').open('w', encoding='utf-8', newline='') as stream:
            stream.write('Date,Asset,Text,Type\n')
            for row in rows:
                stream.write(','.join(row) + '\n')
        p = json.loads(profile.read_bytes())
        p['recurring_fields'] = ['work_class']
        p['sources'] = {k: v for k, v in p['sources'].items() if k in ('assets', 'work_orders')}
        p.pop('labor_ledger')
        p['sources']['work_orders'] = dict(id='FIX-orders', revision='1', owner='Records owner', coverage='Authored no-ID export',
                                          files=[dict(path='work_orders.csv')], constants=dict(scope='U1'), identity='record',
                                          columns=dict(Date='created', Asset='asset_id', Text='description', Type='order_type'),
                                          date_formats=dict(created='iso_date'), time_basis='Dates only')
        if edit:
            edit(p)
        mh.dump(profile, p)
        return profile

    ROWS = [('2024-01-02', 'P-101', 'Replace seal'), ('2024-01-03', 'P-101', 'SEAL leaking again'),
            ('2024-01-04', 'PARK', 'mow grass'), ('2024-01-05', 'P-101', 'sealant on cover'),
            ('2024-01-06', 'P-101', 'pump seal and bearing'), ('2024-01-07', 'PARK', 'Bearing noise')]
    RULES = [dict(value='seal', terms=['SEAL']), dict(value='bearing', terms=['BEARING', 'BRG'])]

    def derive(self, p, rules=None):
        p['sources']['work_orders']['derive'] = dict(work_class=dict(source='description', rules=rules or self.RULES,
                                                     basis='Authored test vocabulary; not source codes'))

    def test_record_identity_uses_the_source_record_number(self):
        profile = self.no_id_export('ordinal', [r + ('CM',) for r in self.ROWS])
        r = mh.run(profile, self.root / 'ordinal')
        ids = [w['id'] for w in r['all_records']['work_orders']]
        self.assertEqual(ids, ['2', '3', '4', '5', '6', '7'])
        self.assertTrue(all(w['origin']['record'] == int(w['id']) for w in r['all_records']['work_orders']))
        mh.verify_packet(self.root / 'ordinal')
        def both(p):
            p['sources']['work_orders']['columns']['Type'] = 'id'
        with self.assertRaisesRegex(ValueError, 'record identity'):
            mh.run(self.no_id_export('both', [r + ('CM',) for r in self.ROWS], both), self.root / 'both')

    def test_selection_keeps_declared_values_counts_the_rest_and_keeps_locators(self):
        def select(p):
            p['sources']['work_orders']['select'] = dict(asset_id=['PARK'])
        r = mh.run(self.no_id_export('select', [x + ('CM',) for x in self.ROWS], select), self.root / 'select')
        self.assertEqual([w['id'] for w in r['all_records']['work_orders']], ['4', '7'])
        self.assertEqual(r['counts']['work_orders'], 2)
        self.assertEqual(r['selection'], dict(work_orders=dict(field='asset_id', values=['PARK'], kept=2, excluded=4)))
        self.assertEqual(r['relationship_coverage']['work_orders']['unlinked'], 0)
        self.assertNotIn('selection', self.run_packet('plain'))
        def bad(p):
            p['sources']['work_orders']['select'] = dict(status=['open'])
        with self.assertRaisesRegex(ValueError, 'select'):
            mh.run(self.no_id_export('bad-select', [x + ('CM',) for x in self.ROWS], bad), self.root / 'bad-select')

    def test_derived_class_from_declared_description_terms_is_marked_and_grouped(self):
        r = mh.run(self.no_id_export('derive', [x + ('CM',) for x in self.ROWS], self.derive), self.root / 'derive')
        rows = {w['id']: w for w in r['all_records']['work_orders']}
        # Whole words, case-insensitive, first declared rule wins; 'sealant' is not 'seal'.
        self.assertEqual({k: v.get('work_class', '') for k, v in rows.items()},
                         {'2': 'seal', '3': 'seal', '4': '', '5': '', '6': 'seal', '7': 'bearing'})
        self.assertEqual(rows['3']['_derived']['work_class'], dict(value='seal', rule=1, term='SEAL', source='description'))
        self.assertNotIn('work_class', rows['4']['_derived'])
        pump = self.asset(r)
        self.assertEqual([(g['fields'], g['orders']) for g in pump['recurring_work']], [(dict(work_class='seal'), ['2', '3', '6'])])
        self.assertEqual(pump['recurring_work'][0]['derived_fields'], ['work_class'])
        self.assertEqual(pump['unclassified_orders'], ['5'])
        page = (self.root / 'derive' / pump['page']).read_text(encoding='utf-8')
        self.assertIn('derived from description', page)
        def mapped(p):
            self.derive(p); p['sources']['work_orders']['columns']['Type'] = 'work_class'
        with self.assertRaisesRegex(ValueError, 'derive'):
            mh.run(self.no_id_export('mapped', [x + ('CM',) for x in self.ROWS], mapped), self.root / 'mapped')
        with self.assertRaisesRegex(ValueError, 'derive'):
            mh.run(self.no_id_export('empty', [x + ('CM',) for x in self.ROWS], lambda p: self.derive(p, [dict(value='seal', terms=[])])), self.root / 'empty')

    def test_unmapped_completion_is_not_a_per_record_issue(self):
        r = mh.run(self.no_id_export('nocompletion', [x + ('CM',) for x in self.ROWS]), self.root / 'nocompletion')
        self.assertNotIn('missing_completion_value', {i['code'] for i in r['issues']})
        self.assertIn('missing_completion_value', {i['code'] for i in self.run_packet('mapped-completion')['issues']})

if __name__ == '__main__':
    unittest.main()
