"""The assistant stand-in sees only the packet, returns check diagnostics for correction, and builds through the tool."""
import json
from pathlib import Path
import tempfile
import unittest

import description_workflow as dw
import run_description_author as ra

ROOT = Path(__file__).resolve().parent.parent


class AuthorRunTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='author-run-')
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.packet = self.tmp / 'packet'
        dw.prepare(ROOT / 'examples/from-description/assisted/source.txt', self.packet)
        self.reference = (self.packet / 'reference_answer.json').read_text(encoding='utf-8')
        self.messages = []

    def caller(self, replies):
        def call(message, model):
            self.messages.append(message)
            return {'text': replies[len(self.messages) - 1], 'model': 'fake-model', 'seconds': 0.1,
                    'cost_usd_notional': 0.0}
        return call

    def test_message_is_the_packet_and_nothing_else(self):
        message = ra.packet_message(self.packet)
        for name in ra.PACKET_FILES:
            self.assertIn((self.packet / name).read_text(encoding='utf-8'), message)
        self.assertNotIn('packet.json', [line.strip('= ') for line in message.splitlines() if line.startswith('=====')])

    def test_check_errors_go_back_and_a_passing_answer_is_built(self):
        broken = json.loads(self.reference)
        broken['model']['meta']['source_sha256'] = '0' * 64
        record = ra.run(self.packet, self.tmp / 'out', rounds=3, caller=self.caller(
            ['no json here', '```json\n' + json.dumps(broken) + '\n```', self.reference]))
        self.assertEqual([r['check']['ok'] for r in record['rounds']], [False, False, True])
        self.assertIn('reply held no JSON object', self.messages[1])
        self.assertIn('source_sha256', self.messages[2])
        self.assertTrue(record['built'])
        self.assertTrue((self.tmp / 'out/result/model.json').is_file())
        self.assertEqual(record['served_model'], 'fake-model')

    def test_an_answer_that_never_passes_is_not_built(self):
        record = ra.run(self.packet, self.tmp / 'out', rounds=2, caller=self.caller(['{"model": {}}', '{}']))
        self.assertFalse(record['built'])
        self.assertFalse((self.tmp / 'out/result').exists())
        self.assertTrue((self.tmp / 'out/answer.json').is_file())


if __name__ == '__main__':
    unittest.main()
