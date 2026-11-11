"""Synthetic drawing-set intake controls; no public data, installed extras or model calls."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

import deliverable_report
import import_drawing_set as dset
import offpage_pairing

try:
    import cv2  # noqa: F401
    HAVE_CV2 = True
except ImportError:
    HAVE_CV2 = False


def png(width=200, height=100):
    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress((b'\0' + b'\xff' * width * 3) * height)) + chunk(b'IEND', b''))


def sheet_pred(prefix, connectors):
    symbols = [{'id': 'tank', 'class': 'tank', 'tag': f'{prefix}-TK-101', 'box': [100, 100, 200, 200], 'confidence': .9},
               {'id': 'valve', 'class': 'valve', 'tag': f'{prefix}-V-1', 'box': [400, 100, 450, 150], 'confidence': .9}]
    links = [{'from': 'tank', 'to': 'valve'}]
    for i, text in enumerate(connectors):
        symbols.append({'id': f'op{i}', 'class': 'inlet/outlet', 'tag': text,
                        'box': [800, 100 + 100 * i, 950, 150 + 100 * i], 'confidence': .9})
        links.append({'from': 'valve', 'to': f'op{i}'})
    return {'symbols': symbols, 'connections': links}


class DrawingSetIntake(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = self.root / 'set-bundle'

    def write(self, rows, **overrides):
        entries = []
        for i, (number, title, connectors) in enumerate(rows):
            (self.root / f'{i}.png').write_bytes(png())
            (self.root / f'{i}.json').write_text(json.dumps(sheet_pred(f'U{i}', connectors)), encoding='utf-8')
            entry = {'drawing_id': f'DWG-{i}', 'revision': 'A', 'page': i + 1, 'image': f'{i}.png', 'extraction': f'{i}.json'}
            if number:
                entry['drawing_number'] = number
            if title:
                entry['title'] = title
            entries.append(entry)
        manifest = {'schema_version': dset.SCHEMA, 'set_id': 'Synthetic set', 'extraction_format': 'prediction',
                    'producer': {'method': 'authored synthetic test', 'tool': 'manual', 'model': None},
                    'sheets': entries, **overrides}
        path = self.root / 'set.json'
        path.write_text(json.dumps(manifest), encoding='utf-8')
        return path

    def model(self):
        return json.loads((self.out / 'plant_model.json').read_text(encoding='utf-8'))

    def test_reciprocal_sheet_references_pair_across_sheets(self):
        path = self.write([('P-204', 'Permeate collection', ['TO EQUALIZATION REF SHT P-401']),
                           ('P-401', 'Equalization tank', ['FROM PERMEATE COLLECTION REF SHT P-204'])])
        result = dset.import_set(path, self.out)
        self.assertEqual(result['pairs_from_supplied_numbers'], 1)
        model = self.model()
        self.assertEqual([p['method'] for p in model['offpage_pairs']], ['reciprocal_supplied_numbers'])
        self.assertTrue(all(c['pair_status'] == 'paired' for c in model['offpage_connectors']))
        self.assertEqual({c['refers_to_drawing'] for c in model['offpage_connectors']}, {'P-204', 'P-401'})
        self.assertTrue(any(s['kind'] == 'cross_sheet' for s in model['streams']))
        self.assertEqual(model['summary']['offpage_pairs'], 1)
        self.assertEqual([s['name'] for s in model['systems']], ['Permeate collection', 'Equalization tank'])
        self.assertEqual(sorted(p.name for p in (self.out / 'svg').glob('sheet_*.svg')), ['sheet_0.svg', 'sheet_1.svg'])
        self.assertEqual(sorted(p.name for p in (self.out / 'source').glob('*.png')), ['0.png', '1.png'])

    def test_one_way_reference_pairs_only_with_the_sheet_title(self):
        path = self.write([('P-401', 'Irrigation Equalization Tank P&ID', ['TO EFFLUENT DISPOSAL REF SHT P-501']),
                           ('P-501', 'Effluent disposal', ['IRRIGATION EQUALIZATION TANK', 'DRIP ZONE 1'])])
        dset.import_set(path, self.out)
        model = self.model()
        self.assertEqual([p['method'] for p in model['offpage_pairs']], ['one_way_number_plus_sheet_title'])
        unpaired = [c for c in model['offpage_connectors'] if not c['pair']]
        self.assertEqual([c['text'] for c in unpaired], ['DRIP ZONE 1'])

    def test_one_way_reference_without_a_title_match_stays_unpaired_and_says_why(self):
        path = self.write([('P-401', 'Irrigation tank', ['TO DISPOSAL REF SHT P-501']),
                           ('P-501', 'Effluent disposal', ['DRIP ZONE 1'])])
        dset.import_set(path, self.out)
        model = self.model()
        self.assertEqual(model['offpage_pairs'], [])
        status = {c['text']: c['pair_status'] for c in model['offpage_connectors']}
        self.assertEqual(status['TO DISPOSAL REF SHT P-501'],
                         'unpaired: target sheet is in this set but no matching connector was found')

    def test_drawing_numbers_match_literally_with_separators_but_not_inside_longer_numbers(self):
        pattern = offpage_pairing.number_pattern("P-204")
        for text in ('REF SHT P-204', 'P 204', 'SEE P204.', '(P-204)'):
            self.assertTrue(pattern.search(text.upper()), text)
        for text in ('P-2045', 'XP-204', 'P-20', 'P-2041'):
            self.assertFalse(pattern.search(text.upper()), text)

    def test_set_report_shows_every_sheet_and_the_cross_sheet_pairs(self):
        path = self.write([('P-204', None, ['REF SHT P-401']), ('P-401', None, ['REF SHT P-204'])])
        dset.import_set(path, self.out)
        page = deliverable_report.build(self.out)
        self.assertIn('Draft asset model: Synthetic set', page)
        self.assertIn('Sheet 0: DWG-0', page)
        self.assertIn('Sheet 1: DWG-1', page)
        self.assertIn('Across sheets (1 pair)', page)
        self.assertIn("each names the other&#x27;s drawing number", page)
        self.assertEqual(page.count('<figure>'), 2)

    def test_invalid_sets_are_refused_without_writing(self):
        for sheets, overrides in (
                ([('P-1', None, ['A']), ('P 1', None, ['B'])], {}),          # same number twice
                ([('P-1', None, ['A'])], {'schema_version': 'site-drawing-intake-1'}),
                ([('P-1', None, ['A'])], {'sheets': []})):
            path = self.write(sheets, **overrides)
            with self.assertRaises((ValueError, TypeError)):
                dset.import_set(path, self.out)
            self.assertFalse(self.out.exists())
            self.assertFalse(list(self.root.glob('.site-set-intake-*')))
        path = self.write([('P-1', None, ['A'])])
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest['sheets'][0]['colour'] = 'blue'
        path.write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaises(ValueError):
            dset.import_set(path, self.out)

    def test_line_layers_skip_is_recorded_and_the_bundle_is_still_written(self):
        path = self.write([('P-1', None, ['REF SHT P-2']), ('P-2', None, ['REF SHT P-1'])])
        result = dset.import_set(path, self.out)  # blank synthetic images: the links can't be re-traced
        self.assertEqual(result['line_layers']['status'], 'skipped')
        self.assertTrue(result['line_layers']['reason'])
        model = self.model()
        self.assertEqual(model['meta']['line_layers_status']['status'], 'skipped')
        self.assertNotIn('line_layers', model)
        self.assertIn('Drawn line layers not added', deliverable_report.build(self.out))

    def test_line_layers_can_be_turned_off(self):
        path = self.write([('P-1', None, ['A'])])
        result = dset.import_set(path, self.out, line_layers=False)
        self.assertEqual(result['line_layers'], {'status': 'not requested'})

    @unittest.skipUnless(HAVE_CV2, 'needs OpenCV (requirements.txt)')
    def test_committed_open100_set_gets_pipe_and_instrument_layers(self):
        manifest = Path(__file__).resolve().parent.parent / 'examples' / 'own-drawing' / 'set-manifest.json'
        result = dset.import_set(manifest, self.out)
        layers = result['line_layers']
        self.assertEqual(layers['status'], 'added', layers)
        self.assertGreater(layers['pipe_segments'], 300)
        self.assertGreater(layers['instrument_connections'], 0)
        self.assertEqual(layers['dropped_inconsistent_lines'], 0)
        import graph_export
        graph = graph_export.build(self.out / 'plant_model.json')
        types = {e['type'] for e in graph['edges']}
        self.assertTrue({'piped_to', 'instrument_connection'} <= types)
        self.assertEqual(graph_export.problems(graph), [])
        # Flow direction (round 6 increment 2): only drawn evidence directs a segment; the rest stay as written
        flow = result['flow_direction']
        self.assertEqual(flow['status'], 'added', flow)
        self.assertEqual(flow['directed'] + flow['undirected'] + flow['conflict'], layers['pipe_segments'])
        self.assertGreater(flow['directed'], 50)
        self.assertGreater(flow['undirected'], flow['directed'])  # most segments show no drawn direction
        model = self.model()
        for s in model['line_layers']['segments']:
            if 'direction' in s:
                ev = s['direction_evidence']
                self.assertEqual(s['direction'], 'forward')
                self.assertIn(ev['basis'], ('first_hand', 'valve_chain'))
                self.assertTrue(ev['kinds'] and set(ev['kinds']) <= set(dset.FLOW_SOURCES), s)
                self.assertTrue(0 < ev['confidence'] <= 1)
                self.assertTrue(all(f['kind'] in ev['kinds'] for f in ev['found']))
            else:
                self.assertNotIn('direction_evidence', s)
                self.assertEqual('direction_conflict' in s, s['id'] in model['meta']['flow_direction_status']['conflict_segments'])
        directed = {e['id']: e for e in graph['edges'] if e['type'] == 'piped_to'}
        self.assertEqual(sum(e['direction'] == 'forward' for e in directed.values()), flow['directed'])
        self.assertEqual(sum(e['direction'] == 'unknown' for e in directed.values()),
                         flow['undirected'] + flow['conflict'])
        # turned off, every segment is exactly the line layers' own (the increment-1 bundle)
        off = Path(self.tmp.name) / 'no-flow'
        dset.import_set(manifest, off, flow_direction=False)
        plain = json.loads((off / 'plant_model.json').read_text(encoding='utf-8'))
        self.assertNotIn('flow_direction_status', plain['meta'])
        by_id = {s['id']: s for s in plain['line_layers']['segments']}
        for s in model['line_layers']['segments']:
            o = by_id[s['id']]
            if 'direction_conflict' in s:  # a disagreement is recorded beside the untouched segment
                self.assertNotIn('direction', s)
                s = {k: v for k, v in s.items() if k != 'direction_conflict'}
            if 'direction' in s:
                self.assertEqual({s['from'], s['to']}, {o['from'], o['to']})
                s = {k: v for k, v in s.items() if k not in ('direction', 'direction_evidence', 'from', 'to')}
                o = {k: v for k, v in o.items() if k not in ('from', 'to')}
            self.assertEqual(s, o)

    def test_check_only_writes_nothing(self):
        path = self.write([('P-1', None, ['A']), ('P-2', None, ['B'])])
        result = dset.import_set(path, self.out, check_only=True)
        self.assertTrue(result['inputs_valid'])
        self.assertEqual([d['drawing_id'] for d in result['drawings']], ['DWG-0', 'DWG-1'])
        self.assertFalse(self.out.exists())


def layered(segments, junctions):
    """A minimal model: sheet 0, items A..E (symbol ids a..e), the given pipe segments and junction ids."""
    items = [{'id': x, 'class': 'valve', 'provenance': [{'sheet': '0', 'symbol': x.lower(), 'class': 'valve',
                                                          'box_0_1000': [0, 0, 1, 1]}]} for x in 'ABCDE']
    return {'units': [], 'instruments': [], 'line_items': items, 'offpage_connectors': [],
            'line_layers': {'junctions': [{'id': j} for j in junctions],
                            'segments': [{'id': f'S0-PS{n:03d}', 'from': a, 'to': b, 'sheet': '0'}
                                         for n, (a, b) in enumerate(segments, 1)]}}


def sheet(arrows=(), flags=None, pumps=None):
    return {'0': {'size_px': (1000, 1000), 'arrows': list(arrows), 'flags': flags or {}, 'pumps': pumps or {}}}


def arrow(behind, ahead, near_behind, near_ahead):
    return {'status': 'orients links', 'behind': behind, 'ahead': ahead, 'near_behind': near_behind,
            'near_ahead': near_ahead, 'box_px': [10, 10, 20, 20], 'dir': 1, 'axis': 'x'}


def _walk_relations(o):
    if isinstance(o, dict):
        if isinstance(o.get('relations'), list):
            yield from o['relations']
        for v in o.values():
            yield from _walk_relations(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk_relations(v)


@unittest.skipUnless(HAVE_CV2, 'needs OpenCV (requirements.txt): flow_direction.py imports it')
class SegmentFlowEvidence(unittest.TestCase):
    """Drawn evidence lands on the one segment it is drawn on, or nowhere; never on a segment from layout."""

    def test_an_arrow_behind_a_tee_orients_only_the_segment_it_is_on(self):
        model = layered([('A', 'J1'), ('J1', 'B'), ('C', 'J1')], ['J1'])
        ev = dset.segment_flow_evidence(model, sheet([arrow(['a'], ['b', 'c'], ['a'], [])]))
        self.assertEqual(list(ev), ['S0-PS001'])
        self.assertEqual([e[:2] for e in ev['S0-PS001']], [(1, 'arrowhead')])  # A -> J1, the segment's own order

    def test_an_arrow_between_two_items_counts_once_and_points_the_drawn_way(self):
        model = layered([('B', 'A')], [])
        ev = dset.segment_flow_evidence(model, sheet([arrow(['a'], ['b'], ['a'], ['b'])]))
        self.assertEqual([e[:2] for e in ev['S0-PS001']], [(-1, 'arrowhead')])  # flow A -> B is to -> from here

    def test_an_item_with_two_segments_toward_what_lies_ahead_gets_nothing(self):
        model = layered([('A', 'J1'), ('A', 'J2'), ('J1', 'B'), ('J2', 'B')], ['J1', 'J2'])
        self.assertEqual(dset.segment_flow_evidence(model, sheet([arrow(['a'], ['b'], ['a'], [])])), {})

    def test_a_segment_whose_far_side_reaches_back_behind_the_arrow_gets_nothing(self):
        model = layered([('A', 'J1'), ('J1', 'B'), ('J1', 'C')], ['J1'])
        self.assertEqual(dset.segment_flow_evidence(model, sheet([arrow(['c'], ['b'], ['a'], [])])), {})

    def test_flags_and_pumps_orient_their_own_segments(self):
        model = layered([('A', 'B'), ('C', 'D'), ('C', 'E')], [])
        flags = {'a': {'role': 'source', 'tip': 'right', 'box_px': [0, 0, 5, 5]},
                 'b': {'role': None, 'tip': None, 'box_px': [0, 0, 5, 5]}}
        pumps = {'c': {'fires': True, 'discharge_to': ['d'], 'suction_from': ['e'], 'box_px': [0, 0, 5, 5]}}
        ev = dset.segment_flow_evidence(model, sheet(flags=flags, pumps=pumps))
        self.assertEqual({k: [e[:2] for e in v] for k, v in ev.items()},
                         {'S0-PS001': [(1, 'offpage_flag')], 'S0-PS002': [(1, 'pump_ports')],
                          'S0-PS003': [(-1, 'pump_ports')]})

    def conflicted_bundle(self, pairs, extra_valves=()):
        """A real one-sheet bundle (valve with two off-page flags) given pipe segments `pairs` (symbol ids) and two
        source flags; returns (model, graph, context-map relations) after the bundle's own flow step."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / '0.png').write_bytes(png())
        pred = sheet_pred('U0', ['FROM A', 'FROM C'])
        for n, v in enumerate(extra_valves):
            pred['symbols'].append({'id': v, 'class': 'valve', 'tag': f'U0-V-{n + 2}',
                                    'box': [500 + 60 * n, 300, 540 + 60 * n, 340], 'confidence': .9})
        (root / '0.json').write_text(json.dumps(pred), encoding='utf-8')
        (root / 'set.json').write_text(json.dumps({
            'schema_version': dset.SCHEMA, 'set_id': 'Conflict control', 'extraction_format': 'prediction',
            'producer': {'method': 'authored synthetic test', 'tool': 'manual', 'model': None},
            'sheets': [{'drawing_id': 'DWG-0', 'revision': 'A', 'page': 1, 'image': '0.png',
                        'extraction': '0.json'}]}), encoding='utf-8')
        dset.import_set(root / 'set.json', root / 'bundle', line_layers=False)
        model = json.loads((root / 'bundle' / 'plant_model.json').read_text(encoding='utf-8'))
        asset = {p['symbol']: it['id'] for k in ('units', 'line_items', 'offpage_connectors', 'instruments')
                 for it in model[k] for p in it['provenance']}
        model['line_layers'] = {'junctions': [], 'networks': [], 'segments': [
            {'id': f'S0-PS{n:03d}', 'from': asset[a], 'to': asset[b], 'sheet': '0'}
            for n, (a, b) in enumerate(pairs, 1)]}
        flags = {f: {'role': 'source', 'tip': 'right', 'box_px': [0, 0, 5, 5]} for f in ('op0', 'op1')}
        ev = dset.segment_flow_evidence(model, sheet(flags=flags))
        valves = [x['id'] for x in model['line_items'] if x['class'] == 'valve']
        counts, _, _, conflicts = dset.apply_flow(model['line_layers']['segments'], ev, valves)
        path = root / 'bundle' / 'plant_model.json'
        path.write_text(json.dumps(model), encoding='utf-8')
        import context_map
        import graph_export
        graph = graph_export.build(path)
        self.assertEqual(graph_export.problems(graph), [])
        cmap = context_map.from_twin_graph_1(graph)
        cmap = cmap[0] if isinstance(cmap, tuple) else cmap
        self.assertEqual(context_map.check(cmap), [])
        rels = [r for u in cmap['plant']['units'] for r in u.get('relations', [])] if 'units' in cmap['plant']             else []
        rels = rels or [r for r in _walk_relations(cmap) if r['type'] == 'piped_to']
        return model, counts, conflicts, graph, rels

    def test_opposite_flow_into_a_two_port_valve_is_a_conflict_on_both_segments(self):
        # A -> valve <- C, each from a source flag: continuity through the valve contradicts both
        model, counts, conflicts, graph, rels = self.conflicted_bundle([('op0', 'valve'), ('op1', 'valve')])
        self.assertEqual(counts, {'directed': 0, 'undirected': 0, 'conflict': 2})
        for s in model['line_layers']['segments']:
            self.assertNotIn('direction', s)
            c = s['direction_conflict']
            self.assertEqual(c['kinds'], ['offpage_flag', 'valve_chain'])
            self.assertEqual(len({(f['flow_from'], f['flow_to']) for f in c['found']}), 2)  # both ways kept
        edges = [e for e in graph['edges'] if e['type'] == 'piped_to']
        self.assertEqual({e['direction'] for e in edges}, {'unknown'})
        for e in edges:
            self.assertTrue(any(a['name'].startswith('direction_conflict.found') for a in e['attributes']))
        self.assertEqual(len(rels), 2)
        for r in rels:
            self.assertIs(r['directed'], False)
            self.assertIn('direction_conflict.qualification', r['attributes'])

    def test_continuity_from_both_ends_meeting_at_a_middle_valve_is_withdrawn_with_its_cause(self):
        # A -> V1 -> V2 <- V3 <- B: each outer flag directs its own segment, continuity carries each one valve on,
        # and the two propagated directions both flow into V2. No direction may survive, and each record names V2.
        model, counts, conflicts, graph, rels = self.conflicted_bundle(
            [('op0', 'valve'), ('valve', 'v2'), ('v2', 'v3'), ('v3', 'op1')], extra_valves=['v2', 'v3'])
        self.assertEqual(counts, {'directed': 0, 'undirected': 0, 'conflict': 4})
        v2 = next(x['id'] for x in model['line_items'] if x['tag'] == 'U0-V-2')
        for s in model['line_layers']['segments']:
            c = s['direction_conflict']
            self.assertEqual(c['status'], 'withdrawn')  # each segment's own observations agree
            self.assertNotIn('points both ways', c['qualification'])
            self.assertEqual(len(c['caused_by']), 1)
            self.assertIn(v2, c['caused_by'][0]['valves'])
            self.assertEqual(c['caused_by'][0]['run'], 'path')
            self.assertEqual(len(c['caused_by'][0]['seeds']), 2)
            self.assertTrue(all('flow_from' in o and 'segment' in o for o in c['caused_by'][0]['observations']))
        self.assertEqual({e['direction'] for e in graph['edges'] if e['type'] == 'piped_to'}, {'unknown'})
        self.assertEqual(len(rels), 4)
        for r in rels:
            self.assertIs(r['directed'], False)
            self.assertEqual(r['attributes']['direction_conflict.status']['value'], 'withdrawn')
            self.assertIn(v2, r['attributes']['direction_conflict.caused_by[0].valves']['value'])

    def test_opposing_marks_on_one_segment_keep_both_observations(self):
        model, counts, conflicts, graph, rels = self.conflicted_bundle([('op0', 'op1')])
        self.assertEqual(counts['conflict'], 1)
        c = model['line_layers']['segments'][0]['direction_conflict']
        self.assertEqual(c['kinds'], ['offpage_flag'])
        self.assertEqual(len(c['found']), 2)
        self.assertNotEqual(c['found'][0]['flow_from'], c['found'][1]['flow_from'])
        self.assertIs(rels[0]['directed'], False)
        self.assertIn('direction_conflict.qualification', rels[0]['attributes'])

    def test_consistent_flow_through_a_valve_stays_directed(self):
        sheet_flags = {'op0': {'role': 'source', 'tip': 'right', 'box_px': [0, 0, 5, 5]},
                       'op1': {'role': 'sink', 'tip': 'left', 'box_px': [0, 0, 5, 5]}}
        model = layered([('A', 'B'), ('B', 'C')], [])
        for x, sym in (('A', 'op0'), ('C', 'op1')):
            model['line_items'][ord(x) - 65]['provenance'][0]['symbol'] = sym
        ev = dset.segment_flow_evidence(model, sheet(flags=sheet_flags))
        counts, _, _, _ = dset.apply_flow(model['line_layers']['segments'], ev, ['B'])
        self.assertEqual(counts, {'directed': 2, 'undirected': 0, 'conflict': 0})
        self.assertEqual([(s['from'], s['to']) for s in model['line_layers']['segments']], [('A', 'B'), ('B', 'C')])

    def run_case(self, segs, ev, valves, label):
        """Apply the flow step to a copy and check it with an oracle independent of valve_runs: runs are the segments
        joined through valves with exactly two segments, each oriented by walking it; along each run every emitted
        direction, and every own mark it rests on, must agree with one sense of travel (one rotation on a ring), so
        the emitted directions admit a consistent completion. When every run's marks agree, nothing may be a
        conflict and every marked segment is directed. Returns the counts."""
        orig = {s['id']: (s['from'], s['to']) for s in segs}
        segs = [dict(s) for s in segs]
        counts, _, _, _ = dset.apply_flow(segs, ev, valves)
        ends = {}
        for sid, (a, b) in orig.items():
            for node in {a, b}:
                ends.setdefault(node, []).append(sid)
        two = {v for v in valves if len(ends.get(v, [])) == 2}
        sense, run_of = {}, {}
        for start in orig:
            if start in sense:
                continue
            sense[start], run_of[start], todo = 1, start, [start]
            while todo:
                x = todo.pop()
                a, b = orig[x]
                exit_node, entry_node = (b, a) if sense[x] > 0 else (a, b)
                for node, leaving in ((exit_node, True), (entry_node, False)):
                    if node not in two:
                        continue
                    y = next(i for i in ends[node] if i != x)
                    if y in sense:
                        continue
                    ya, yb = orig[y]
                    sense[y] = (1 if ya == node else -1) if leaving else (1 if yb == node else -1)
                    run_of[y] = start
                    todo.append(y)
        emitted, marks = {}, {}
        for s in segs:
            r = run_of[s['id']]
            if s.get('direction') == 'forward':
                same = (s['from'], s['to']) == orig[s['id']]
                emitted.setdefault(r, set()).add(sense[s['id']] * (1 if same else -1))
                for e in ev.get(s['id'], []):  # a directed segment never contradicts its own mark
                    self.assertEqual(e[0], 1 if same else -1, label)
            for e in ev.get(s['id'], []):
                marks.setdefault(r, set()).add(e[0] * sense[s['id']])
        for r, senses in emitted.items():
            self.assertEqual(len(senses), 1, ('no consistent completion', label))
            self.assertLessEqual(marks.get(r, set()), senses, ('emitted against a mark on its run', label))
        if all(len(v) == 1 for v in marks.values()):
            self.assertEqual(counts['conflict'], 0, label)
            self.assertTrue(all(s.get('direction') == 'forward' for s in segs if s['id'] in ev), label)
        return counts

    def test_reviewer_reproduction_a_gap_between_two_valves_hides_no_contradiction(self):
        # A -> V1 -> V2 - V3 <- V4 <- B, marks on the outer segments only: the middle segment would have to point
        # both ways, so nothing on the run may be directed
        nodes = ['A', 'V1', 'V2', 'V3', 'V4', 'B']
        segs = [{'id': str(i), 'from': a, 'to': b, 'sheet': '0'} for i, (a, b) in enumerate(zip(nodes, nodes[1:]))]
        ev = {sid: [(sign, 'arrowhead', .886, {'kind': 'arrowhead'})] for sid, sign in (('0', 1), ('4', -1))}
        counts, _, _, _ = dset.apply_flow(segs, ev, nodes[1:-1])
        self.assertEqual(counts, {'directed': 0, 'undirected': 1, 'conflict': 4})
        c = segs[0]['direction_conflict']
        self.assertEqual(c['status'], 'withdrawn')
        self.assertEqual(c['caused_by'][0]['segments'], ['0', '1', '2', '3', '4'])
        self.assertEqual(c['caused_by'][0]['valves'], ['V1', 'V2', 'V3', 'V4'])
        self.assertEqual(c['caused_by'][0]['seeds'], ['0', '4'])
        self.assertEqual({o['along_run'] for o in c['caused_by'][0]['observations']}, {1, -1})
        self.assertNotIn('direction', segs[2])
        self.assertNotIn('direction_conflict', segs[2])  # no evidence reached it: untouched

    def test_exhaustive_chains_and_rings_emit_only_directions_with_a_consistent_completion(self):
        """Chains of 1-8 segments (inner nodes two-port valves) and rings of 3-8 valves, every mark pattern (none,
        one way, the other); every stored orientation up to 5 segments, then all forward, alternating and two fixed
        mixed patterns."""
        import itertools
        cases = 0
        for ring, n in [(False, k) for k in range(1, 9)] + [(True, k) for k in range(3, 9)]:
            nodes = [f'N{i}' for i in range(n if ring else n + 1)]
            valves = nodes if ring else nodes[1:-1]
            flips = (list(itertools.product((False, True), repeat=n)) if n <= 5 else
                     [tuple([False] * n), tuple(i % 2 == 1 for i in range(n)), tuple(i % 3 == 0 for i in range(n)),
                      tuple(i in (1, 2, 5) for i in range(n))])
            for flip in flips:
                segs = [{'id': f'S{i}', 'sheet': '0',
                         'from': nodes[(i + 1) % len(nodes)] if flip[i] else nodes[i],
                         'to': nodes[i] if flip[i] else nodes[(i + 1) % len(nodes)]} for i in range(n)]
                for marks in itertools.product((0, 1, -1), repeat=n):
                    ev = {f'S{i}': [(m * (-1 if flip[i] else 1), 'arrowhead', .8,
                                     {'kind': 'arrowhead', 'box_0_1000': [i, 0, i + 1, 1]})]
                          for i, m in enumerate(marks) if m}
                    self.run_case(segs, ev, valves, (ring, n, flip, marks))
                    cases += 1
        self.assertEqual(cases, 94434)

    def test_three_port_valves_and_other_items_split_runs(self):
        """A valve with three segments, or an item that is not a valve, ends a run: marks on different arms never
        contradict each other, and continuity is never carried through them."""
        import itertools
        for middle in ('V', 'P'):  # arm 0 passes a valve, or a pump (not a valve)
            segs = []
            for i in range(3):
                inner = f'{middle if i == 0 else "V"}{i}'
                segs += [{'id': f'S{i}a', 'from': f'A{i}', 'to': inner, 'sheet': '0'},
                         {'id': f'S{i}b', 'from': inner, 'to': 'T', 'sheet': '0'}]
            valves = ['T', 'V1', 'V2'] + (['V0'] if middle == 'V' else [])
            for marks in itertools.product((0, 1, -1), repeat=6):
                ev = {s['id']: [(m, 'arrowhead', .8, {'kind': 'arrowhead', 'box_0_1000': [k, 0, k + 1, 1]})]
                      for k, (s, m) in enumerate(zip(segs, marks)) if m}
                counts = self.run_case(segs, ev, valves, (middle, marks))
                if middle == 'V' and marks == (1, 0, 1, 0, 1, 0):
                    self.assertEqual(counts, {'directed': 6, 'undirected': 0, 'conflict': 0})  # all arms into T
                if middle == 'P' and marks == (1, -1, 0, 0, 0, 0):
                    self.assertEqual(counts['conflict'], 0)  # A0 -> pump <- T: no continuity through a pump

    def test_a_contradiction_in_the_middle_withdraws_the_whole_run_and_names_it(self):
        segs = [{'id': 'S0', 'from': 'A', 'to': 'V1', 'sheet': '0'}, {'id': 'S1', 'from': 'V1', 'to': 'V2', 'sheet': '0'},
                {'id': 'S2', 'from': 'V2', 'to': 'B', 'sheet': '0'}]
        mark = lambda s: [(s, 'arrowhead', 0.8, {'kind': 'arrowhead', 'sheet': '0'})]  # noqa: E731
        counts, _, _, _ = dset.apply_flow(segs, {'S0': mark(1), 'S2': mark(-1)}, ['V1', 'V2'])  # A -> V1 - V2 <- B
        self.assertEqual(counts['conflict'], 3)
        for s in segs:
            c = s['direction_conflict']
            self.assertEqual(c['status'], 'withdrawn')  # no segment's own marks disagree
            self.assertEqual(c['caused_by'][0]['segments'], ['S0', 'S1', 'S2'])
            self.assertEqual(c['caused_by'][0]['seeds'], ['S0', 'S2'])
        self.assertEqual({o.get('through') for o in segs[1]['direction_conflict']['caused_by'][0]['observations']},
                         {None, 'V1', 'V2'})
        one = [{'id': 'S0', 'from': 'A', 'to': 'B', 'sheet': '0'}]
        dset.apply_flow(one, {'S0': mark(1) + [(-1, 'offpage_flag', .8, {'kind': 'offpage_flag'})]}, [])
        self.assertEqual(one[0]['direction_conflict']['status'], 'local_disagreement')

    def test_no_evidence_no_direction(self):
        model = layered([('A', 'B'), ('B', 'C')], [])
        self.assertEqual(dset.segment_flow_evidence(model, sheet()), {})


if __name__ == '__main__':
    unittest.main()
