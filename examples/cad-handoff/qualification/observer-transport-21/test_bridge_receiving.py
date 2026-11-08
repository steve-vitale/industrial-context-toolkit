"""Challenge complete method2 packets after rehashing their inner/outer inventories."""
import json
import unittest
from recheck_evidence import HERE, digest, unpack
from recheck_bridge import check_files


def put(files, name, value):
    files['attempt/' + name] = (json.dumps(value, ensure_ascii=True, separators=(',', ':')) + '\n').encode('utf-8')


def reindex(files):
    path = 'attempt/INVENTORY.json'; row = json.loads(files[path])
    row['files'] = {n.removeprefix('attempt/'): dict(bytes=len(v), sha256=digest(v)) for n, v in files.items()
                    if n.startswith('attempt/') and n != path}
    put(files, 'INVENTORY.json', row)


class CompleteBridgeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = json.loads((HERE / 'BRIDGE-FROZEN-INPUTS-2.json').read_bytes())
        cls.packets = {label: unpack(HERE / 'bridge-2' / label) for label in catalog}

    def test_every_original_normal_and_failed_attempt_receives(self):
        self.assertEqual(len(self.packets), 13)
        for label, files in self.packets.items():
            with self.subTest(label=label): self.assertFalse(check_files(files, label)['whole_cad_qualified'])

    def test_missing_extra_or_changed_normal_reply_refuses(self):
        for variant in ('missing', 'extra', 'sequence', 'wire'):
            with self.subTest(variant=variant):
                files = self.packets['normal-air'].copy(); path = 'mailbox/replies/00000001.json'
                if variant == 'missing': del files['attempt/' + path]
                elif variant == 'extra': files['attempt/mailbox/replies/00009999.json'] = files['attempt/' + path]
                else:
                    row = json.loads(files['attempt/' + path])
                    if variant == 'sequence': row['seq'] = 999
                    else: row['request_wire'] = '{}\n'
                    put(files, path, row)
                reindex(files)
                with self.assertRaises((ValueError, FileNotFoundError)): check_files(files, 'normal-air')

    def test_lost_error_export_refuses(self):
        files = self.packets['fault-malformed'].copy()
        name = next(n for n in files if n.startswith('attempt/mailbox/errors/'))
        del files[name]; reindex(files)
        with self.assertRaises((ValueError, FileNotFoundError)): check_files(files, 'fault-malformed')

    def test_changed_input_or_method_cannot_repin_itself(self):
        for name in ('source.dxf', 'observe_case.js'):
            with self.subTest(name=name):
                files = self.packets['normal-air'].copy(); path = 'attempt/job/' + name
                files[path] += b'\nCHANGED\n'
                freeze = json.loads(files['attempt/job/JOB-FREEZE.json']); freeze['files'][name] = digest(files[path])
                put(files, 'job/JOB-FREEZE.json', freeze); reindex(files)
                with self.assertRaisesRegex(ValueError, 'Original event-driven'): check_files(files, 'normal-air')

    def test_removed_seal_refuses(self):
        files = self.packets['normal-template'].copy(); path = 'attempt/job/native/stdout.txt'
        lines = files[path].decode('utf-8').splitlines()
        files[path] = ('\n'.join(line for line in lines if not line.startswith('ICT_IO_SEALED ')) + '\n').encode('utf-8'); reindex(files)
        with self.assertRaisesRegex(ValueError, 'seal'): check_files(files, 'normal-template')

    def test_lost_or_unbound_client_observation_refuses(self):
        for variant in ('missing', 'changed-frame-reply'):
            with self.subTest(variant=variant):
                files = self.packets['normal-air'].copy(); actions = json.loads(files['attempt/job/ui/actions.json'])
                if variant == 'missing':
                    index = next(i for i, row in enumerate(actions) if row['kind'] == 'native_observation'); del actions[index]
                else:
                    row = next(r for r in actions if r['kind'] == 'native_observation' and r['reply']['request']['action'] == 'frame')
                    row['reply']['view']['factor'] += 1
                for i, row in enumerate(actions, 1): row['event'] = i
                put(files, 'job/ui/actions.json', actions); reindex(files)
                with self.assertRaisesRegex(ValueError, 'observation relationship'): check_files(files, 'normal-air')

    def test_failed_host_exit_cannot_be_promoted(self):
        files = self.packets['fault-wrong-run'].copy(); files['execution/EXIT.json'] = b'{"exit":0}\n'
        with self.assertRaisesRegex(ValueError, 'host exit'): check_files(files, 'fault-wrong-run')


if __name__ == '__main__': unittest.main()
