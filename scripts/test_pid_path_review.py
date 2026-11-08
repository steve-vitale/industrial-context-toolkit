"""Policy, source, revision and receiving controls for prepared cross-sheet graph questions."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import pid_path_review as p

BASE = Path(__file__).resolve().parents[1] / 'examples/pid-path-review'


class PathReviewTests(unittest.TestCase):
    def graph(self, name='prepared-initial'):
        return json.loads((BASE / 'inputs' / (name + '.json')).read_bytes())

    def query(self, identity='remote', policy='reviewed'):
        q = next(q for q in json.loads((BASE / 'QUERIES.json').read_bytes()) if q['id'] == identity)
        q.pop('id')
        return dict(q, policy=policy)

    def test_frozen_policy_baseline_and_revision_exercise(self):
        spec = importlib.util.spec_from_file_location('path_case', BASE / 'reproduce.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as root:
            result = module.reproduce(Path(root) / 'new')
        self.assertEqual(result, json.loads((BASE / 'worked/replay.json').read_bytes()))
        self.assertEqual(len(result['policy_cases']), 10)
        self.assertEqual(result['revisions'][0]['prior_answer'], 'unchanged')
        self.assertEqual(result['revisions'][1]['prior_answer'], 'reopened')
        self.assertFalse(result['engineering_acceptance'])

    def test_all_published_packets_reproduce_with_current_methods(self):
        folders = [p for p in (BASE / 'worked').iterdir() if p.is_dir()]
        self.assertEqual(len(folders), 14)
        for folder in folders:
            with self.subTest(folder=folder.name):
                saved = p.receive(folder)
                self.assertEqual(saved['tool_bindings'], p.bindings())

    def test_edge_confirmation_cannot_override_open_endpoint_conflict(self):
        g = self.graph()
        result = p.evaluate(g, self.query())
        self.assertEqual(result['answer']['status'], 'not_established')
        self.assertTrue(any(q.get('conflict') == 'DEMO/CONFLICT/C-size' for b in result['boundaries'] for q in b.get('qualifications', [])))
        explored = p.evaluate(g, self.query(policy='exploratory'))
        self.assertEqual(explored['answer']['status'], 'qualified')
        row = next(r for r in explored['register'] if r['id'].endswith('/V-301'))
        self.assertEqual(row['item_status'], 'confirmed')
        self.assertEqual(row['association_status'], 'qualified')

    def test_network_membership_and_logical_streams_are_not_physical_adjacency(self):
        query = dict(self.query('local'), basis='physical')
        result = p.evaluate(self.graph(), query)
        self.assertEqual(result['answer']['status'], 'not_established')
        self.assertTrue(any(b['reason'] == 'relation_outside_selected_network_or_basis' for b in result['boundaries']))
        g = self.graph()
        e = g['edges'][0]
        e.update(type='piped_to')
        e.pop('layer')
        self.assertEqual(p.evaluate(g, query)['answer']['status'], 'supported')

    def test_known_reverse_never_becomes_an_exploratory_forward_path(self):
        for policy in ('reviewed', 'exploratory'):
            result = p.evaluate(self.graph(), self.query('reverse', policy))
            self.assertEqual(result['answer']['status'], 'not_established')
            self.assertTrue(any(b['edge'] == 'REVERSE' and b['reason'] == 'known_reverse_direction' for b in result['boundaries']))

    def test_unknown_offpage_medium_remains_qualified_and_known_signal_is_excluded_from_process(self):
        original = p.evaluate(self.graph('initial'), self.query(policy='exploratory'))
        self.assertTrue(any(q['reason'] == 'offpage_network_kind_unknown' for q in original['answer']['qualifications']))
        g = self.graph()
        e = next(e for e in g['edges'] if e['id'] == 'PAIR12')
        next(a for a in e['attributes'] if a['name'] == 'network_kind')['value'] = 'signal'
        self.assertEqual(p.evaluate(g, self.query(policy='exploratory'))['answer']['status'], 'not_established')

    def test_rejected_and_unresolvable_are_not_exploration_candidates(self):
        for status in ('rejected', 'unresolvable'):
            g = self.graph()
            g['edges'][0]['status'] = status
            self.assertEqual(p.evaluate(g, self.query('local', 'exploratory'))['answer']['status'], 'not_established')

    def test_missing_source_and_unreviewed_edge_attribute_stop_reviewed_trace(self):
        for change in ('source', 'claim'):
            g = self.graph()
            if change == 'source':
                g['edges'][0]['source'].pop('locator')
            else:
                g['edges'][0]['attributes'] = [dict(name='size', value='3 in', status='unverified', source=g['edges'][0]['source'])]
            self.assertEqual(p.evaluate(g, self.query('local'))['answer']['status'], 'not_established')
            self.assertEqual(p.evaluate(g, self.query('local', 'exploratory'))['answer']['status'], 'qualified')

    def test_starting_record_qualification_is_visible_in_report(self):
        g = self.graph()
        start = self.query('local')['from']
        next(n for n in g['nodes'] if n['id'] == start)['status'] = 'unverified'
        r = p.evaluate(g, self.query('local', 'exploratory'))
        r['comparison'] = p.compare(r)
        self.assertEqual(r['answer']['status'], 'qualified')
        for name in ('REPORT.md', 'REPORT.html'):
            self.assertIn(b'Starting record review: review status unverified', p.render(r)[name])

    def test_new_incident_edge_and_new_conflict_reopen_prior_answer(self):
        q = self.query('local')
        old = p.evaluate(self.graph(), q)
        for kind in ('edge', 'conflict'):
            g = self.graph()
            if kind == 'edge':
                e = copy.deepcopy(g['edges'][0])
                e['id'] = 'new-parallel'
                g['edges'].append(e)
            else:
                c = next(n for n in g['nodes'] if n['kind'] == 'conflict')
                c['conflict']['subject'] = q['to']
            new = p.evaluate(g, q)
            self.assertEqual(p.compare(new, old)['prior_answer'], 'reopened')

    def test_identity_and_vocabulary_refusals(self):
        for kind in ('duplicate_node', 'duplicate_edge', 'unknown_status', 'unknown_direction', 'unknown_medium', 'duplicate_claim', 'dangling_conflict'):
            g = self.graph()
            if kind == 'duplicate_node':
                g['nodes'].append(copy.deepcopy(g['nodes'][0]))
            elif kind == 'duplicate_edge':
                g['edges'].append(copy.deepcopy(g['edges'][0]))
            elif kind == 'unknown_status':
                g['edges'][0]['status'] = 'HOLD'
            elif kind == 'unknown_direction':
                g['edges'][0]['direction'] = 'probably'
            elif kind == 'unknown_medium':
                next(a for e in g['edges'] if e['id'] == 'PAIR12' for a in e['attributes'] if a['name'] == 'network_kind')['value'] = True
            elif kind == 'duplicate_claim':
                g['nodes'][1]['attributes'] *= 2
            else:
                next(n['conflict'] for n in g['nodes'] if n['kind'] == 'conflict')['subject'] = 'foreign'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                p.evaluate(g, self.query())
        with self.assertRaises(ValueError):
            p.evaluate(self.graph(), dict(self.query(), **{'from': 'P-101'}))

    def test_typed_json_input_and_work_bounds(self):
        for data in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.assertRaises(ValueError):
                p.parse(data)
        g = self.graph()
        g['nodes'] *= p.MAX_NODES
        with self.assertRaisesRegex(ValueError, 'bounded scope'):
            p.evaluate(g, self.query())

    def test_packet_history_tamper_existing_destination_and_nested_output_refuse(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'one'
            p.run(BASE / 'inputs/prepared-initial.json', self.query('local'), out)
            self.assertEqual(p.receive(out)['answer']['status'], 'supported')
            with self.assertRaisesRegex(ValueError, 'existing'):
                p.run(BASE / 'inputs/prepared-initial.json', self.query('local'), out)
            with self.assertRaisesRegex(ValueError, 'outside'):
                p.run(BASE / 'inputs/prepared-initial.json', self.query('local'), out / 'nested', out)
            (out / 'REPORT.html').write_text('tampered', encoding='utf8')
            with self.assertRaisesRegex(ValueError, 'altered'):
                p.run(BASE / 'inputs/prepared-corrected.json', self.query('local'), root / 'new', out)
            self.assertFalse((root / 'new').exists())

    def test_changed_query_or_method_cannot_inherit_a_prior_answer(self):
        old = p.evaluate(self.graph(), self.query())
        for kind in ('query', 'method'):
            changed = copy.deepcopy(old)
            if kind == 'query':
                changed['query']['policy'] = 'exploratory'
            else:
                changed['tool_bindings']['pid_path_review.py'] = '0' * 64
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                p.compare(old, changed)

    def test_rehashed_false_answer_and_projection_still_refuse(self):
        for name in ('result.json', 'REPORT.html'):
            with tempfile.TemporaryDirectory() as temp:
                out = Path(temp) / 'packet'
                p.run(BASE / 'inputs/prepared-initial.json', self.query(), out)
                if name == 'result.json':
                    r = json.loads((out / name).read_bytes())
                    r['answer']['status'] = 'supported'
                    (out / name).write_bytes(p.dump(r))
                else:
                    (out / name).write_text('False supported route', encoding='utf8')
                receipt = json.loads((out / 'receipt.json').read_bytes())
                data = (out / name).read_bytes()
                receipt['files'][name] = dict(bytes=len(data), sha256=p.sha(data))
                (out / 'receipt.json').write_bytes(p.dump(receipt))
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'reproduce'):
                    p.receive(out)

    def test_same_tag_in_another_scope_does_not_merge_identity(self):
        g = self.graph()
        n = copy.deepcopy(g['nodes'][1])
        n['id'] = 'DEMO/P2/U2/P-101'
        g['nodes'].append(n)
        result = p.evaluate(g, dict(self.query(), **{'to': n['id']}))
        self.assertEqual(result['answer']['status'], 'not_established')
        self.assertNotIn(n['id'], [r['id'] for r in result['register']])

    def test_historical_retired_conflict_is_retained_without_blocking_current_local_facts(self):
        g = self.graph()
        c = next(n['conflict'] for n in g['nodes'] if n['kind'] == 'conflict')
        c.update(subject='removed-item', detected=False)
        result = p.evaluate(g, self.query('local'))
        self.assertEqual(result['answer']['status'], 'supported')
        self.assertEqual(c['subject'], 'removed-item')

    def test_html_escapes_supplied_text_and_csv_retains_json_cells(self):
        g = self.graph()
        g['nodes'][1]['tag'] = '=bad<script>'
        r = p.evaluate(g, self.query('local'))
        r['comparison'] = p.compare(r)
        out = p.render(r)
        self.assertNotIn(b'<script>', out['REPORT.html'])
        import csv, io
        row = next(row for row in csv.DictReader(io.StringIO(out['REGISTER.csv'].decode())) if row['id'] == json.dumps('DEMO/P1/U1/P-101', separators=(',', ':')))
        self.assertEqual(json.loads(row['tag']), '=bad<script>')


if __name__ == '__main__':
    unittest.main()
