"""Flowsheet topology task: key extraction from flowsheet source, role alignment, scoring and its wrong controls."""
import json
from pathlib import Path
import tempfile
import textwrap
import unittest

import flowsheet_topology as ft

FLOWSHEET = textwrap.dedent('''
    from pyomo.network import Arc
    from idaes.models.unit_models import (
        Feed, Mixer, Compressor, Heater, StoichiometricReactor, Turbine, Flash, Product, Separator,
    )

    def build_model(m):
        m.fs.props = SomeParameterBlock()
        m.fs.A = Feed(property_package=m.fs.props)
        m.fs.B = Feed(property_package=m.fs.props)
        m.fs.M1 = Mixer(inlet_list=["a", "b"])
        m.fs.C1 = Compressor(compressor=True)
        m.fs.H1 = Heater()
        m.fs.R1 = StoichiometricReactor()
        m.fs.T1 = Turbine()
        m.fs.F1 = Flash()
        m.fs.P1 = Product()
        m.fs.P2 = Product()
        m.fs.f1 = Arc(source=m.fs.A.outlet, destination=m.fs.M1.a)
        m.fs.f2 = Arc(source=m.fs.B.outlet, destination=m.fs.M1.b)
        m.fs.s1 = Arc(source=m.fs.M1.outlet, destination=m.fs.C1.inlet)
        m.fs.s2 = Arc(source=m.fs.C1.outlet, destination=m.fs.H1.inlet)
        m.fs.s3 = Arc(source=m.fs.H1.outlet, destination=m.fs.R1.inlet)
        m.fs.s4 = Arc(source=m.fs.R1.outlet, destination=m.fs.T1.inlet)
        m.fs.s5 = Arc(source=m.fs.T1.outlet, destination=m.fs.F1.inlet)
        m.fs.g = Arc(source=m.fs.F1.vap_outlet, destination=m.fs.P1.inlet)
        m.fs.l = Arc(source=m.fs.F1.liq_outlet, destination=m.fs.P2.inlet)
''')


def cite(n):
    return f'source.txt:L{n}-L{n}'


def model(units, streams):
    return {'meta': {'model_id': 'x'},
            'units': [{'id': i, 'name': n, 'type': t, 'source': cite(line)} for i, n, t, line in units],
            'streams': [{'id': f'S{k}', 'name': 's', 'from': a, 'to': b, 'source': cite(1)}
                        for k, (a, b) in enumerate(streams, 1)]}


GOOD_UNITS = [('MX', 'Feed mixer', 'feed_header', 2), ('K1', 'Feed compressor', 'compressor', 3),
              ('E1', 'Preheater', 'heat_exchanger', 4), ('RX', 'Reactor', 'reactor', 5),
              ('EX', 'Letdown turbine', 'compressor', 6), ('D1', 'Flash drum', 'separator', 7)]
GOOD_STREAMS = [('BL', 'MX'), ('BL', 'MX'), ('MX', 'K1'), ('K1', 'E1'), ('E1', 'RX'), ('RX', 'EX'),
                ('EX', 'D1'), ('D1', 'BL'), ('D1', 'BL')]


class KeyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='flowsheet-key-')
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / 'flowsheet.py'
        self.path.write_text(FLOWSHEET, encoding='utf-8')

    def test_key_reads_units_and_arcs_without_executing(self):
        key = ft.key_from_flowsheet(self.path)
        self.assertEqual(len(key['units']), 10)
        self.assertEqual(len(key['arcs']), 9)
        roles = {u['id']: u['role'] for u in key['units']}
        self.assertEqual(roles, {'A': 'feed', 'B': 'feed', 'M1': 'mixer', 'C1': 'compressor', 'H1': 'heat_exchange',
                                 'R1': 'reactor', 'T1': 'expander', 'F1': 'separator', 'P1': 'product',
                                 'P2': 'product'})
        self.assertIn({'id': 's1', 'from': 'M1', 'from_port': 'outlet', 'to': 'C1', 'to_port': 'inlet'}, key['arcs'])
        # The parameter block is not a unit: only classes imported from the unit model library count.
        self.assertNotIn('props', roles)

    def test_pressure_changer_direction_comes_from_its_compressor_flag(self):
        src = FLOWSHEET.replace('Compressor,', 'Compressor, PressureChanger,').replace(
            'm.fs.T1 = Turbine()', 'm.fs.T1 = PressureChanger(compressor=False)')
        self.path.write_text(src, encoding='utf-8')
        self.assertEqual({u['id']: u['role'] for u in ft.key_from_flowsheet(self.path)['units']}['T1'], 'expander')

    def test_import_alias_records_the_library_class(self):
        """A419 review: the held-out source imports `Separator as Splitter`; the key records Separator, not the alias."""
        src = FLOWSHEET.replace('Separator,', 'Separator as Splitter,').replace(
            'm.fs.P2 = Product()', 'm.fs.P2 = Product()\n    m.fs.S1 = Splitter()')
        self.path.write_text(src, encoding='utf-8')
        units = {u['id']: u for u in ft.key_from_flowsheet(self.path)['units']}
        self.assertEqual((units['S1']['class'], units['S1']['role']), ('Separator', 'splitter'))

    def test_unknown_unit_class_or_dangling_arc_refuses(self):
        self.path.write_text(FLOWSHEET.replace('Separator,', 'Separator, Mystery,').replace(
            'm.fs.H1 = Heater()', 'm.fs.H1 = Mystery()'), encoding='utf-8')
        with self.assertRaises(ValueError):
            ft.key_from_flowsheet(self.path)
        self.path.write_text(FLOWSHEET.replace('destination=m.fs.P2.inlet', 'destination=m.fs.ZZ.inlet'),
                             encoding='utf-8')
        with self.assertRaises(ValueError):
            ft.key_from_flowsheet(self.path)


class ScoreTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='flowsheet-score-')
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / 'flowsheet.py'
        path.write_text(FLOWSHEET, encoding='utf-8')
        self.key = ft.key_from_flowsheet(path)

    def test_a_correct_model_with_different_names_scores_perfectly(self):
        counts, diag = ft.score(self.key, model(GOOD_UNITS, GOOD_STREAMS))
        for metric in ('units', 'boundaries', 'connections'):
            self.assertEqual(counts[metric]['tp'], counts[metric]['truth'], metric)
            self.assertEqual(counts[metric]['tp'], counts[metric]['predicted'], metric)
        self.assertEqual(diag['missing_arcs'], [])
        self.assertEqual(diag['unexpected_streams'], [])

    def test_one_wrong_endpoint_costs_exactly_that_connection(self):
        streams = list(GOOD_STREAMS)
        streams[5] = ('RX', 'D1')  # skips the turbine
        counts, diag = ft.score(self.key, model(GOOD_UNITS, streams))
        self.assertEqual(counts['connections'], {'tp': 8, 'predicted': 9, 'truth': 9})
        self.assertEqual(diag['missing_arcs'], ['s4'])
        self.assertEqual(diag['unexpected_streams'], ['S6'])

    def test_turbine_typed_compressor_needs_a_turbine_name(self):
        units = list(GOOD_UNITS)
        units[4] = ('EX', 'Second compressor', 'compressor', 6)
        counts, _ = ft.score(self.key, model(units, GOOD_STREAMS))
        self.assertEqual(counts['units']['tp'], 5)
        self.assertLess(counts['connections']['tp'], 9)

    def test_empty_and_missing_answers_score_zero(self):
        counts, _ = ft.score(self.key, None)
        self.assertEqual(counts['connections'], {'tp': 0, 'predicted': 0, 'truth': 9})
        self.assertEqual(counts['units'], {'tp': 0, 'predicted': 0, 'truth': 6})

    def test_unknown_stream_endpoint_is_an_invalid_answer(self):
        with self.assertRaises(ValueError):
            ft.score(self.key, model(GOOD_UNITS, GOOD_STREAMS + [('RX', 'NOPE')]))

    def test_internal_arcs_are_reported_apart_from_boundary_credit(self):
        """A419 review: an answer with only feeds and products earns connection credit but no internal arc."""
        boundary_only = [('BL', 'MX'), ('BL', 'MX'), ('D1', 'BL'), ('D1', 'BL')]
        counts, _ = ft.score(self.key, model(GOOD_UNITS, boundary_only))
        self.assertEqual(counts['connections']['tp'], 4)
        self.assertEqual(counts['internal'], {'tp': 0, 'predicted': 0, 'truth': 5})
        counts, _ = ft.score(self.key, model(GOOD_UNITS, GOOD_STREAMS))
        self.assertEqual(counts['internal'], {'tp': 5, 'predicted': 5, 'truth': 5})

    def test_key_controls_separate(self):
        table = ft.key_controls(self.key)
        self.assertEqual(table['reference']['connections']['tp'], 9)
        self.assertEqual(table['reference']['units']['tp'], 6)
        self.assertEqual(table['empty']['connections']['tp'], 0)
        for name in ft.WRONG_KEY_CONTROLS:
            self.assertLessEqual(ft.f1(table[name]['connections']), ft.WRONG_CONTROL_MAX, name)
        self.assertEqual(ft.check_key_controls(table), [])

    def test_prediction_controls_reported_beside_the_answer(self):
        _, diag = ft.score(self.key, model(GOOD_UNITS, GOOD_STREAMS))
        controls = diag['controls']
        self.assertEqual(set(controls), {'reversed', 'shuffled', 'mention_order_chain'})
        self.assertEqual(controls['reversed']['connections']['tp'], 0)
        self.assertLessEqual(ft.f1(controls['shuffled']['connections']), ft.WRONG_CONTROL_MAX)
        # The process is a chain in mention order, so the naive baseline recovers it: that is the point of reporting it.
        self.assertEqual(controls['mention_order_chain']['connections']['tp'], 9)

    def test_alignment_is_role_preserving_only(self):
        # A reactor and a flash drum swapped in the chain cannot be rescued by relabelling across roles.
        units = [(i, n, ('separator' if t == 'reactor' else 'reactor' if t == 'separator' else t), line)
                 for i, n, t, line in GOOD_UNITS]
        counts, _ = ft.score(self.key, model(units, GOOD_STREAMS))
        self.assertLess(counts['connections']['tp'], 9)


class NotebookTests(unittest.TestCase):
    def test_prose_takes_markdown_cells_only_and_stops_at_the_heading(self):
        nb = {'cells': [{'cell_type': 'markdown', 'source': ['# Title  \n', 'Text one.']},
                        {'cell_type': 'code', 'source': ['m.fs.s01 = Arc(source=m.fs.A.outlet)'],
                         'outputs': [{'text': 'M101 outlet'}]},
                        {'cell_type': 'markdown', 'source': ['More text.']},
                        {'cell_type': 'markdown', 'source': ['# 4. Recycle\n', 'Recycle text.']}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'n.ipynb'
            path.write_text(json.dumps(nb), encoding='utf-8')
            dev = ft.notebook_prose(path, stop='# 4.')
            full = ft.notebook_prose(path)
        self.assertEqual(dev, '# Title\nText one.\n\nMore text.\n')
        self.assertNotIn('Arc', full)
        self.assertTrue(full.endswith('# 4. Recycle\nRecycle text.\n'))


if __name__ == '__main__':
    unittest.main()
