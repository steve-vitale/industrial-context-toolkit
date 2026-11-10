"""Synthetic drawing-set intake controls; no public data, installed extras or model calls."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

import deliverable_report
import import_drawing_set as dset


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
        pattern = dset.number_pattern('P-204')
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

    def test_check_only_writes_nothing(self):
        path = self.write([('P-1', None, ['A']), ('P-2', None, ['B'])])
        result = dset.import_set(path, self.out, check_only=True)
        self.assertTrue(result['inputs_valid'])
        self.assertEqual([d['drawing_id'] for d in result['drawings']], ['DWG-0', 'DWG-1'])
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
