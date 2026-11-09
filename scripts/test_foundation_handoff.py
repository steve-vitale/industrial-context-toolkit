"""Actual separate-process handoff/revision plus typed-loss, identity and authority controls."""
import copy
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import foundation_handoff as f

ROOT = Path(__file__).resolve().parents[1]


class Foundation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='foundation-tests-')
        cls.root = Path(cls.temp.name)
        spec = importlib.util.spec_from_file_location('foundation_rehearsal', ROOT / 'examples/foundation-cycle/reproduce.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.worked = cls.root / 'worked'
        module.run(cls.worked)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def copy(self, name='delivery-1'):
        folder = self.root / self._testMethodName / name
        shutil.copytree(self.worked / name, folder)
        return folder

    def rehash(self, packet):
        receipt = f.load(packet / 'receipt.json')
        receipt['files'] = f.inventory(packet)
        receipt['files'].pop('receipt.json')
        (packet / 'receipt.json').write_bytes(f.raw(receipt))

    def test_complete_process_cycle_and_limits(self):
        summary = f.load(self.worked / 'summary.json')
        self.assertEqual(summary['passed'], summary['checks'])
        self.assertGreaterEqual(summary['cli_calls'], 23)
        self.assertFalse(summary['company_acceptance'])
        self.assertFalse(summary['independent_review'])
        change = f.load(self.worked / 'delivery-2/changes.json')
        self.assertTrue(change['mapping_changes'])
        self.assertEqual(change['unavailable'][0]['id'], 'OPTIONAL')

    def test_cross_unit_identity_and_wrong_revision_refuse(self):
        folder = self.copy('first')
        profile = f.load(folder / 'profile.json')
        profile['history']['mappings'][0]['node'] = 'U2/P-101'
        (folder / 'bad.json').write_bytes(f.raw(profile))
        with self.assertRaisesRegex(ValueError, 'Scoped identity'):
            f.prepare(folder / 'bad.json', folder / 'bad-output')
        self.assertFalse((folder / 'bad-output').exists())
        profile = f.load(folder / 'profile.json')
        profile['drawing']['mappings'][0]['returned_revision'] = 'C'
        (folder / 'bad.json').write_bytes(f.raw(profile))
        with self.assertRaisesRegex(ValueError, 'revision association'):
            f.prepare(folder / 'bad.json', folder / 'bad-output')

    def test_type_collapse_and_partial_receiver_are_not_full_transfer(self):
        packet = self.copy()
        saved = f.load(packet / 'readback.json')
        attr = next(a for a in saved['nodes'][0]['attributes'] if a['name'] == 'typed.0')
        self.assertIs(attr['value'], False)
        attr['value'] = 0
        (packet / 'readback.json').write_bytes(f.raw(saved))
        self.rehash(packet)
        with self.assertRaisesRegex(ValueError, 'Saved readback'):
            f.verify_delivery(packet)
        original = f.Snapshot.decisions
        def partial(reader, *args, **kwargs):
            result = original(reader, *args, **kwargs)
            result['result']['decisions'] = []
            result['result']['next_offset'] = None
            return result
        with patch.object(f.Snapshot, 'decisions', partial), self.assertRaisesRegex(ValueError, 'Incomplete receiver pagination'):
            f.readback(self.worked / 'delivery-1/graph.json', self.worked / 'delivery-1/context.json')

    def test_missing_original_and_replaced_same_revision_bytes_refuse(self):
        packet = self.copy()
        target = packet / 'prepared/originals/documents/0.txt'
        target.write_text('Replaced bytes, unchanged declared revision', encoding='utf-8')
        self.rehash(packet / 'prepared')
        self.rehash(packet)
        with self.assertRaisesRegex(ValueError, 'sha256|reproduce|bindings'):
            f.verify_delivery(packet)
        target.unlink()
        with self.assertRaises(ValueError):
            f.verify_delivery(packet)

    def test_dropped_node_field_or_relationship_refuses_after_inventory_rehash(self):
        for label in ('attribute', 'relationship'):
            packet = self.copy('delivery-2') if label == 'attribute' else self.root / self._testMethodName / 'second-mutation'
            if label != 'attribute':
                shutil.copytree(self.worked / 'delivery-2', packet)
            graph = f.load(packet / 'graph.json')
            if label == 'attribute':
                graph['nodes'][0]['attributes'].pop()
            else:
                graph['edges'].pop()
            (packet / 'graph.json').write_bytes(f.raw(graph))
            self.rehash(packet)
            with self.assertRaises(ValueError):
                f.verify_delivery(packet)

    def test_company_acceptance_and_hidden_mapping_change_refuse(self):
        packet = self.copy()
        receipt = f.load(packet / 'receipt.json')
        receipt['company_acceptance'] = True
        (packet / 'receipt.json').write_bytes(f.raw(receipt))
        with self.assertRaisesRegex(ValueError, 'Company acceptance'):
            f.verify_delivery(packet)
        prepared = packet / 'prepared'
        profile = f.load(prepared / 'profile.json')
        profile['history']['mappings'][0]['reviewer'] = 'Changed authority declaration'
        (prepared / 'profile.json').write_bytes(f.raw(profile))
        self.rehash(prepared)
        with self.assertRaisesRegex(ValueError, 'do not reproduce'):
            f.verify_preparation(prepared)

    def test_prior_history_cannot_be_reset_with_fresh_graph_binding(self):
        packet = self.copy('delivery-2')
        prepared = packet / 'prepared'
        graph, qdoc, qs = f.context.load_inputs(prepared / 'graph.json', prepared / 'questions.json')
        sources, choices, _ = f.context.load_sources(prepared / 'sources.json', qs, prepared)
        register = f.context.reconcile(f.context.empty_register(), qs, sources, choices, [])
        files = f.context.outputs(graph, qdoc, register, choices)
        (packet / 'graph.json').write_text(files['enriched_graph.json'], encoding='utf-8', newline='')
        (packet / 'context.json').write_text(files['context.json'], encoding='utf-8', newline='')
        (packet / 'readback.json').write_bytes(f.raw(f.readback(packet / 'graph.json', packet / 'context.json')))
        self.rehash(packet)
        with self.assertRaisesRegex(ValueError, 'history was dropped'):
            f.verify_delivery(packet)

    def test_escape_alias_and_stale_base_refuse(self):
        folder = self.copy('first')
        profile = f.load(folder / 'profile.json')
        profile['graph'] = '../escape.json'
        (folder / 'bad.json').write_bytes(f.raw(profile))
        with self.assertRaisesRegex(ValueError, 'escapes'):
            f.prepare(folder / 'bad.json', folder / 'bad-output')
        with self.assertRaisesRegex(ValueError, 'aliases'):
            f.prepare(folder / 'profile.json', folder / 'history/new-output')
        with self.assertRaisesRegex(ValueError, 'expected base'):
            f.receive(self.worked / 'delivery-2', folder / 'wrong-base', None)
        self.assertFalse((folder / 'wrong-base').exists())


if __name__ == '__main__':
    unittest.main(verbosity=1)
