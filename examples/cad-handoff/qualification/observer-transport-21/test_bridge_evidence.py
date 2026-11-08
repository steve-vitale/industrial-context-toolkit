"""Semantic loss controls after recomputing inventories, independent of outer hashes."""
import copy
import json
import unittest
from recheck_evidence import HERE, digest, unpack
from recheck_bridge_development import check_files as check_bridge
from recheck_async import check_files as check_async


def replace(files, name, value):
    files['attempt/' + name] = (json.dumps(value, separators=(',', ':'), ensure_ascii=True) + '\n').encode('utf-8')


def reindex(files):
    name = 'attempt/INVENTORY.json'; row = json.loads(files[name])
    row['files'] = {n.removeprefix('attempt/'): dict(bytes=len(v), sha256=digest(v)) for n, v in files.items() if n != name}
    replace(files, 'INVENTORY.json', row)


class BridgeEvidenceControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = unpack(HERE / 'bridge-development-1')
        cls.probes = {n: unpack(HERE / f'probes/async-probe-{n}') for n in (1, 2)}

    def test_original_outcomes_remain_distinct(self):
        self.assertFalse(check_bridge(self.bridge)['whole_cad_qualified'])
        self.assertEqual(check_async(self.probes[1], 1)['status'], 'original-ambiguous-signal-failure-retained')
        self.assertEqual(check_async(self.probes[2], 2)['native_timer_ticks'], 1107)

    def test_lost_helper_event_refuses_with_recomputed_inventory(self):
        files = self.bridge.copy(); del files['attempt/mailbox/events/00001000.json']; reindex(files)
        with self.assertRaisesRegex(ValueError, 'invocation events'): check_bridge(files)

    def test_failed_attempt_or_cleanup_cannot_be_promoted(self):
        for path in ('job/native/PROCESS.json', 'inspection/CANCEL-AND-CLEANUP.json'):
            with self.subTest(path=path):
                files = self.bridge.copy(); row = json.loads(files['attempt/' + path])
                row['controller_exit' if 'PROCESS' in path else 'exit'] = 0
                replace(files, path, row); reindex(files)
                with self.assertRaises(ValueError): check_bridge(files)

    def test_frozen_source_cannot_be_replaced_with_its_own_new_hash(self):
        files = self.probes[2].copy(); path = 'job/observe_case.js'
        files['attempt/' + path] += b'\n// changed method\n'
        freeze = json.loads(files['attempt/job/JOB-FREEZE.json']); freeze['files']['observe_case.js'] = digest(files['attempt/' + path])
        replace(files, 'job/JOB-FREEZE.json', freeze); reindex(files)
        with self.assertRaisesRegex(ValueError, 'Original probe freeze'): check_async(files, 2)

    def test_jointly_false_schedule_reports_refuse(self):
        files = self.probes[2].copy(); report = json.loads(files['attempt/job/native/ASYNC.json'])
        report['ticks_at_finish'] = report['ticks_at_start']; replace(files, 'job/native/ASYNC.json', report)
        client = json.loads(files['attempt/job/ui/RESULT.json']); client['report'] = report; replace(files, 'job/ui/RESULT.json', client)
        lines = files['attempt/job/native/stdout.txt'].decode('utf-8').splitlines()
        files['attempt/job/native/stdout.txt'] = ('\n'.join('ICT_ASYNC_FINISHED ' + json.dumps(report, ensure_ascii=False) if line.startswith('ICT_ASYNC_FINISHED ') else line for line in lines) + '\n').encode('utf-8')
        reindex(files)
        with self.assertRaisesRegex(ValueError, 'scheduling'): check_async(files, 2)

    def test_failed_signal_probe_cannot_lose_its_error(self):
        files = self.probes[1].copy(); row = json.loads(files['attempt/job/native/ASYNC-FAILURE.json']); row['error'] = 'no error'
        replace(files, 'job/native/ASYNC-FAILURE.json', row); reindex(files)
        with self.assertRaisesRegex(ValueError, 'signal failure'): check_async(files, 1)


if __name__ == '__main__': unittest.main()
