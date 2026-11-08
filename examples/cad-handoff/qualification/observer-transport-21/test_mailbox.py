"""Loss-sensitive offline transport controls; independent of native Qt execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from mailbox import Mailbox, PROTOCOL, audit, publish, validate_reply, wire


class MailboxControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('requests', 'replies', 'errors', 'staging'): (self.root / name).mkdir()
        self.run = '1' * 32
        self.body = dict(action='status')
        self.request = wire(dict(protocol=PROTOCOL, run_id=self.run, seq=1, body=self.body))
        self.reply = dict(protocol=PROTOCOL, run_id=self.run, seq=1, request_wire=self.request.decode(),
                          observation=dict(request=dict(seq=1, action='status'), filename='', modified=False))

    def packet(self):
        publish(self.root / 'requests/00000001.json', self.request)
        publish(self.root / 'replies/00000001.json', wire(self.reply))

    def test_normal_exact_wire_and_complete_history(self):
        self.packet()
        self.assertEqual(audit(self.root, self.run, [self.body])['requests'], 1)

    def test_publication_collision_retains_original(self):
        p = self.root / 'requests/00000001.json'
        p.write_bytes(b'original')
        with self.assertRaises(FileExistsError): publish(p, self.request)
        self.assertEqual(p.read_bytes(), b'original')

    def test_staging_collision_retains_original(self):
        p = self.root / 'staging/requests-00000001.json'; p.write_bytes(b'original')
        with self.assertRaises(FileExistsError): publish(self.root / 'requests/00000001.json', self.request)
        self.assertEqual(p.read_bytes(), b'original')

    def test_binding_changes_are_not_repaired_by_valid_json(self):
        for key, value in [('seq', 2), ('seq', True), ('run_id', '2' * 32), ('protocol', 'other'),
                           ('request_wire', self.request.decode().replace('status', 'save')),
                           ('observation', dict(request=dict(seq=1, action='save')))]:
            with self.subTest(key=key, value=value):
                reply = copy.deepcopy(self.reply); reply[key] = value
                with self.assertRaises(ValueError): validate_reply(wire(reply), self.request, self.run, 1)

    def test_wrong_intended_action_still_fails_with_consistent_wire(self):
        self.packet()
        with self.assertRaises(ValueError): audit(self.root, self.run, [dict(action='save')])

    def test_missing_extra_and_staging_loss_refuse(self):
        self.packet()
        for folder, name in [('replies', '00000001.json'), ('requests', '00000001.json'),
                             ('staging', 'replies-00000001.json')]:
            p = self.root / folder / name; kept = p.with_suffix('.kept'); p.rename(kept)
            with self.assertRaises(ValueError): audit(self.root, self.run, [self.body])
            kept.rename(p)
        (self.root / 'replies/00000002.json').write_bytes(wire(self.reply))
        with self.assertRaises(ValueError): audit(self.root, self.run, [self.body])

    def test_errors_always_prevent_normal_receiving(self):
        self.packet()
        (self.root / 'errors/00000001.json').write_bytes(wire(dict(error='native read failed')))
        with self.assertRaisesRegex(ValueError, 'errors present'): audit(self.root, self.run, [self.body])

    def test_client_dead_process_stops_before_publication(self):
        events = []
        client = Mailbox(self.root, self.run, lambda: False, lambda *a, **k: events.append((a, k)), self.root / 'console')
        with self.assertRaisesRegex(ValueError, 'exited'): client.request(self.body)
        self.assertFalse(list((self.root / 'requests').iterdir()))
        self.assertTrue(client.failed)

    def test_console_only_fatal_prevents_clean_client(self):
        console = self.root / 'console'; console.write_bytes(b'ICT_MAILBOX_FATAL {"error":"read failed"}\n')
        client = Mailbox(self.root, self.run, lambda: True, lambda *a, **k: None, console)
        with self.assertRaisesRegex(ValueError, 'console'): client.request(self.body)

    def test_missing_reply_times_out_and_stays_failed(self):
        client = Mailbox(self.root, self.run, lambda: True, lambda *a, **k: None, self.root / 'console', timeout=0)
        with self.assertRaisesRegex(ValueError, 'deadline'): client.request(self.body)
        with self.assertRaisesRegex(ValueError, 'already failed'): client.request(self.body)
        self.assertEqual(len(list((self.root / 'requests').iterdir())), 1)

    def test_changed_request_stops_even_when_reply_is_valid(self):
        publish(self.root / 'replies/00000001.json', wire(self.reply))
        def change(client, path):
            path.chmod(0o644); path.write_bytes(b'changed')
        client = Mailbox(self.root, self.run, lambda: True, lambda *a, **k: None, self.root / 'console')
        with self.assertRaisesRegex(ValueError, 'changed'): client.request(self.body, after_publish=change)


if __name__ == '__main__': unittest.main()
