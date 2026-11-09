"""Map explorer: source/identity/typed receiving controls, independent of browser appearance."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_explorer as tool
import ontology

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/one-map/inputs'
GRAPH = ROOT / 'examples/one-map/expected/start/graph.json'
ITEM = 'S1/P1/200/P-101'


class MapExplorerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.g = tool.graph(GRAPH)

    def packet(self, **kw):
        dest = self.root / 'packet'
        tool.export(GRAPH, dest, sources=SOURCE, item=ITEM, **kw)
        return dest

    def reseal(self, packet):
        (packet / 'RECEIPT.json').write_bytes(tool.encoded({'schema': tool.SCHEMA, 'method': tool.method(), 'files': tool.files_at(packet)}))

    def test_complete_records_questions_and_separate_same_tag(self):
        p = self.packet()
        r = tool.load(p / 'exploration.json')
        view = r['views']['current'][ITEM]
        node = next(n for n in self.g['nodes'] if n['id'] == ITEM)
        self.assertEqual(tool.encoded(view['node']), tool.encoded(node))
        self.assertEqual(view['edges'], [e for e in self.g['edges'] if ITEM in (e['from'], e['to'])])
        for k in ontology.QUESTION_KINDS:
            self.assertEqual(view['answers'][k], ontology.ask(self.g, k, ITEM))
        self.assertIn('S1/P2/300/P-101', r['views']['current'])
        self.assertNotEqual(view['node']['scope'], r['views']['current']['S1/P2/300/P-101']['node']['scope'])
        conflicts = [n['conflict'] for n in self.g['nodes'] if n['kind'] == 'conflict' and n['conflict']['subject'] == ITEM]
        self.assertEqual(view['conflicts'], conflicts)
        self.assertEqual((p / 'current.json').read_bytes(), GRAPH.read_bytes())

    def test_ambiguous_and_unknown_refused_before_any_output(self):
        for item in ('P-101', 'NO-SUCH-TAG'):
            target = self.root / item
            with self.assertRaises(tool.InputError):
                tool.export(GRAPH, target, item=item)
            self.assertFalse(target.exists())

    def test_new_directory_only_and_no_source_writes(self):
        before = {p: p.read_bytes() for p in SOURCE.rglob('*') if p.is_file()}
        p = self.packet()
        with self.assertRaisesRegex(tool.InputError, 'already exists'):
            tool.export(GRAPH, p)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_retained_source_bytes_and_missing_unbound(self):
        p = self.packet()
        rows = tool.load(p / 'evidence.json')
        self.assertTrue(any(r['status'] == 'retained' for r in rows))
        self.assertTrue(any(r['status'] == 'unbound' for r in rows))
        for r in rows:
            if r['status'] == 'retained':
                self.assertEqual((p / r['retained']).read_bytes(), (SOURCE / r['source']['path']).read_bytes())
        retained = {}
        minimal = {'a': {'path': 'absent.txt', 'sha256': 'a'*64}, 'b': {'path': 'x'}}
        self.assertEqual([r['status'] for r in tool.evidence(minimal, 'current', SOURCE, retained)], ['missing', 'unbound'])
        self.assertEqual(tool.evidence(minimal, 'current', None, {})[0]['status'], 'not_supplied')

    def test_mismatch_and_unsafe_paths_not_substituted(self):
        (self.root / 'x.txt').write_bytes(b'new')
        g = {'a': {'path': 'x.txt', 'sha256': tool.sha(b'old')}}
        saved = {}
        self.assertEqual(tool.evidence(g, 'current', self.root, saved)[0]['status'], 'hash_mismatch')
        self.assertEqual(saved, {})
        for name in ('../outside', '/etc/passwd', 'C:/secret', 'https://example.org/x', 'a\\b', 'a/./b', 'a//b'):
            g['a']['path'] = name
            self.assertEqual(tool.evidence(g, 'current', self.root, {})[0]['status'], 'unsafe_path')

    def test_copy_reopen_and_external_receipt_binding(self):
        p = self.packet()
        digest = tool.sha((p / 'RECEIPT.json').read_bytes())
        dest = self.root / 'received'
        shutil.copytree(p, dest)
        self.assertTrue(tool.verify(dest, digest)['verified'])
        with self.assertRaisesRegex(tool.InputError, 'independently retained'):
            tool.verify(dest, '0'*64)

    def test_altered_source_and_added_file_refused(self):
        p = self.packet()
        source = next((p / 'evidence').iterdir())
        source.write_bytes(b'altered')
        with self.assertRaisesRegex(tool.InputError, 'inventory/hash'):
            tool.verify(p)
        self.reseal(p)
        with self.assertRaisesRegex(tool.InputError, 'source hash'):
            tool.verify(p)

    def test_partial_projection_refused_even_with_rehashed_inventory(self):
        p = self.packet()
        r = tool.load(p / 'exploration.json')
        r['views']['current'][ITEM]['conflicts'] = []
        (p / 'exploration.json').write_bytes(tool.encoded(r))
        self.reseal(p)
        with self.assertRaisesRegex(tool.InputError, 'complete retained snapshots'):
            tool.verify(p)

    def test_typed_values_and_history_preserved(self):
        g = copy.deepcopy(self.g)
        n = next(n for n in g['nodes'] if n['id'] == ITEM)
        for name, value in [('false', False), ('zero', 0), ('decimal', 1.0), ('literal', '001')]:
            n['attributes'].append({'name': name, 'value': value, 'status': 'unverified', 'source': n['source']})
        c = next(n for n in g['nodes'] if n['kind'] == 'conflict')['conflict']
        c['history'] = [{'ruling': 'earlier disputed value', 'who': 'fictional reviewer', 'reason': 'not authenticated'}]
        r = tool.derived(g, None, ITEM)
        self.assertEqual(tool.encoded(r['views']['current'][ITEM]['node']), tool.encoded(n))
        self.assertIn(c, tool.inspect(g, c['subject'])['conflicts'])

    def test_snapshot_comparison_keeps_complete_before_after_and_direction(self):
        old = copy.deepcopy(self.g)
        old['nodes'][0]['name'] = 'Prior name'
        r = tool.derived(self.g, old, ITEM)
        self.assertIsNotNone(r['changes'])
        d = next(x for x in r['node_changes'] if x['id'] == old['nodes'][0]['id'])
        self.assertEqual(d['before'], old['nodes'][0])
        self.assertEqual(d['after'], self.g['nodes'][0])
        self.assertEqual(r['views']['current'][ITEM]['edges'], tool.inspect(self.g, ITEM)['edges'])

    def test_foreign_site_and_schema_refused(self):
        old = copy.deepcopy(self.g)
        old['site'] = 'OTHER'
        with self.assertRaisesRegex(tool.InputError, 'same site'):
            tool.derived(self.g, old, ITEM)
        p = self.root / 'graph.json'
        old['schema'] = 'twin-graph-1'
        p.write_bytes(tool.encoded(old))
        with self.assertRaisesRegex(tool.InputError, 'twin-graph-2'):
            tool.graph(p)

    def test_escaped_html_uses_text_and_no_external_requests(self):
        value = '</script><script>alert(1)</script><img src="https://example.org">'
        html = tool.map_explorer_html.render({'test': value})
        self.assertNotIn(value, html)
        self.assertIn('\\u003c/script', html)
        self.assertNotIn('innerHTML', html)
        self.assertNotIn('fetch(', html)
        self.assertIn("default-src 'none'", html)

    def test_separate_cli_export_verify_and_refusal(self):
        cli = [sys.executable, '-B', '-S', str(ROOT / 'scripts/map_explorer.py')]
        p = self.root / 'cli'
        a = subprocess.run(cli + ['export', '--map', str(GRAPH), '--item', ITEM, '--out', str(p)], capture_output=True, text=True)
        self.assertEqual(a.returncode, 0, a.stderr)
        b = subprocess.run(cli + ['verify', str(p)], capture_output=True, text=True)
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertTrue(json.loads(b.stdout)['verified'])
        bad = subprocess.run(cli + ['export', '--map', str(GRAPH), '--item', 'P-101', '--out', str(self.root / 'bad')], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertIn('give the qualified id', bad.stderr)


if __name__ == '__main__':
    unittest.main()
