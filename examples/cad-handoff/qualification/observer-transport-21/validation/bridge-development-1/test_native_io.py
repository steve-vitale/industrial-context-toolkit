"""Actual private-file helper controls, distinct from native QCAD execution."""
import json
from pathlib import Path
import tempfile
import unittest

from mailbox import publish, wire
from native_io import Runner, IO_PROTOCOL, FOLDERS, sha


class NativeIOControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'mailbox'; self.root.mkdir()
        (self.root / 'staging').mkdir()
        for role in FOLDERS:
            (self.root / role).mkdir(); (self.root / 'staging' / role).mkdir()
        self.config = self.root.parent / 'transport.json'
        self.run_id = 'a' * 32
        self.config.write_bytes(wire(dict(protocol='ict-native-mailbox/1', io_protocol=IO_PROTOCOL, run_id=self.run_id)))
        self.call_id = 0

    def call(self, operation, seq=1, seen=None, **kw):
        self.call_id += 1
        value = dict(io_protocol=IO_PROTOCOL, call_id=self.call_id, operation=operation,
                     seq=seq, seen=seen or {}, run_id=None if operation == 'initialize' else self.run_id, **kw)
        return Runner(self.root, self.config).run(wire(value).decode('ascii').rstrip('\n'))

    def request(self, data=None):
        value = dict(protocol='ict-native-mailbox/1', run_id=self.run_id, seq=1, body=dict(action='status'))
        data = wire(value) if data is None else data
        publish(self.root / 'requests/00000001.json', data)
        return data

    def initialize(self): self.assertTrue(self.call('initialize')['ok'])

    def test_real_files_roundtrip_and_contiguous_event_hashes(self):
        self.initialize(); self.assertEqual(self.call('poll')['status'], 'idle')
        data = self.request(); message = self.call('poll')
        self.assertEqual(message['request_wire'].encode('ascii'), data)
        out = self.call('publish', request_wire=data.decode('ascii'), observation=dict(request=dict(seq=1, action='status'), value='µ valve'))
        self.assertTrue(out['ok'])
        reply = json.loads((self.root / 'replies/00000001.json').read_bytes())
        self.assertEqual(reply['observation']['value'], 'µ valve')
        previous = None
        for index in range(1, self.call_id + 1):
            path = self.root / 'events' / f'{index:08d}.json'; raw = path.read_bytes()
            row = json.loads(raw); self.assertEqual(row['previous_event_sha256'], previous); previous = sha(raw)
            self.assertEqual((self.root / 'staging/events' / path.name).read_bytes(), raw)

    def test_malformed_wrong_sequence_run_or_nonfinite_messages_fail(self):
        # Separate helper instances/directories retain each failure independently.
        self.initialize(); self.request(b'{bad\n'); out = self.call('poll')
        self.assertFalse(out['ok']); self.assertEqual(out['error']['exception'], 'JSONDecodeError')
        self.assertEqual(len(list((self.root / 'errors').iterdir())), 1)

    def test_nonfinite_and_duplicate_argument_fields_refuse(self):
        for value in ('{"call_id":1,"call_id":2}', '{"number":NaN}'):
            out = Runner(self.root, self.config).run(value)
            self.assertFalse(out['ok']); self.assertEqual(out['error']['exception'], 'ValueError')

    def test_envelope_run_mismatch_refuses(self):
        self.initialize(); self.request(wire(dict(protocol='ict-native-mailbox/1', run_id='b'*32, seq=1, body={})))
        out=self.call('poll'); self.assertFalse(out['ok']); self.assertIn('run/sequence',out['error']['message'])

    def test_helper_has_no_arbitrary_path_operation(self):
        self.initialize(); out=self.call('read', path='/arbitrary')
        self.assertFalse(out['ok']); self.assertEqual(out['error']['stage'],'call-envelope')

    def test_reply_collision_keeps_original_and_records_actual_errno(self):
        self.initialize(); data=self.request(); self.assertTrue(self.call('poll')['ok'])
        target=self.root/'replies/00000001.json'; target.write_bytes(b'ORIGINAL\n')
        out=self.call('publish',request_wire=data.decode(),observation=dict(request=dict(seq=1,action='status')))
        self.assertFalse(out['ok']); self.assertEqual(out['error']['exception'],'FileExistsError')
        self.assertNotEqual(out['error']['errno'],0); self.assertEqual(out['error']['stage'],'publish-link')
        self.assertEqual(target.read_bytes(),b'ORIGINAL\n')

    def test_error_publication_failure_preserves_primary_and_secondary(self):
        self.initialize(); self.request(b'{bad\n'); (self.root/'errors/00000002.json').mkdir()
        out=self.call('poll'); self.assertFalse(out['ok'])
        self.assertEqual(out['error']['exception'],'JSONDecodeError')
        self.assertEqual(out['error_publication_error']['exception'],'FileExistsError')
        event=json.loads((self.root/'events/00000002.json').read_bytes())
        self.assertIn('error_publication_error',event['result'])

    def test_changed_request_after_read_refuses_publication(self):
        self.initialize(); data=self.request(); self.assertTrue(self.call('poll')['ok'])
        path=self.root/'requests/00000001.json'; path.chmod(0o644)
        changed=json.loads(data); changed['body']['action']='seal'; path.write_bytes(wire(changed))
        out=self.call('publish',request_wire=data.decode(),observation=dict(request=dict(seq=1,action='status')))
        self.assertFalse(out['ok']); self.assertIn('wire changed',out['error']['message'])

    def test_lost_invocation_history_refuses_next_call(self):
        self.initialize(); (self.root/'events/00000001.json').unlink()
        out=self.call('poll'); self.assertFalse(out['ok']); self.assertIn('history',out['error']['message'])

    def test_native_observation_error_keeps_its_owner(self):
        self.initialize(); data=self.request(); self.call('poll')
        out=self.call('publish',request_wire=data.decode(),native_error=dict(message='Unsupported read-only action',stage='native-observation'))
        self.assertFalse(out['ok']); self.assertEqual(out['error']['owner'],'qcad-observer')
        self.assertIsNone(out['error']['errno'])

    def test_cleanup_marker_stops_before_consuming_abandoned_request(self):
        self.initialize(); self.request(b'{abandoned\n')
        publish(self.root/'controls/stop.json',wire(dict(protocol=IO_PROTOCOL,run_id=self.run_id,scope='cleanup-only')))
        out=self.call('poll'); self.assertTrue(out['ok']); self.assertEqual(out['status'],'stopped')
        self.assertFalse(list((self.root/'replies').iterdir()))

    def test_argument_bound_refuses_without_truncation(self):
        out=Runner(self.root,self.config).run('x'*60001)
        self.assertFalse(out['ok']); self.assertIn('bound',out['error']['message'])
        self.assertFalse(list((self.root/'replies').iterdir()))


if __name__ == '__main__': unittest.main()
