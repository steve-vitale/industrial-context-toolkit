"""Challenge the actual complete packet after recomputing its inventory; no native launch."""
import json
import unittest
from evidence import unpack
from recheck import check_files
from receive import HERE, digest


def put(files,name,value):
    files['attempt/'+name] = (json.dumps(value,ensure_ascii=True,separators=(',',':'))+'\n').encode('ascii')


def reindex(files):
    row = json.loads(files['attempt/INVENTORY.json'])
    row['files'] = {n.removeprefix('attempt/'):dict(bytes=len(data),sha256=digest(data)) for n,data in files.items() if n.startswith('attempt/') and n != 'attempt/INVENTORY.json'}
    put(files,'INVENTORY.json',row)


class ActualPacketControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.original = unpack(HERE/'development-1/cp1251-edited-1')

    def files(self): return self.original.copy()

    def actions(self,files): return json.loads(files['attempt/job/ui/actions.json'])

    def changed_actions(self,files,actions):
        for i,row in enumerate(actions,1): row['event'] = i
        put(files,'job/ui/actions.json',actions); reindex(files)

    def test_actual_complete_packet_retains_failed_native_preservation(self):
        result = check_files(self.original,'cp1251-edited-1')
        self.assertEqual(result['committed_edits'],2); self.assertEqual(result['editable_field_checks'],8)
        self.assertEqual(result['views'],10); self.assertEqual(result['images'],40)
        self.assertEqual(result['native_strict']['unexpected'],322); self.assertEqual(result['native_strict']['status'],'differences')
        self.assertFalse(result['whole_cad_qualified'])

    def test_changed_source_or_method_cannot_repin_itself(self):
        for name in ('source.dxf','payload.js'):
            with self.subTest(name=name):
                files = self.files(); path = 'attempt/job/'+name; files[path] += b'\nCHANGED\n'
                freeze = json.loads(files['attempt/job/JOB-FREEZE.json']); freeze['files'][name] = digest(files[path]); put(files,'job/JOB-FREEZE.json',freeze); reindex(files)
                with self.assertRaisesRegex(ValueError,'Original attempt identity'): check_files(files,'cp1251-edited-1')

    def test_missing_native_observation_refuses_after_renumbering(self):
        files = self.files(); actions = self.actions(files); del actions[next(i for i,r in enumerate(actions) if r['kind'] == 'native_observation')]
        self.changed_actions(files,actions)
        with self.assertRaisesRegex(ValueError,'observation coverage'): check_files(files,'cp1251-edited-1')

    def test_wrong_asset_edit_refuses(self):
        files = self.files(); actions = self.actions(files)
        next(r for r in actions if r['kind'] == 'native_text_edit_requested')['asset_id'] = 'validation-cp1251/asset-2'
        self.changed_actions(files,actions)
        with self.assertRaisesRegex(ValueError,'edit source/state'): check_files(files,'cp1251-edited-1')

    def test_missing_edit_commit_refuses(self):
        files = self.files(); actions = self.actions(files); del actions[next(i for i,r in enumerate(actions) if r['kind'] == 'native_text_edit_committed')]
        self.changed_actions(files,actions)
        with self.assertRaisesRegex(ValueError,'edit source/state|Incomplete native edit'): check_files(files,'cp1251-edited-1')

    def test_partial_unicode_input_cannot_be_called_complete(self):
        files = self.files(); actions = self.actions(files)
        command = next(r for r in actions if r['kind'] == 'command' and '/work/ui_text.py' in r['command']); trace = json.loads(command['stdout']); trace['completion'][-1]['text'] = 'partial'; command['stdout'] = json.dumps(trace)
        self.changed_actions(files,actions)
        with self.assertRaisesRegex(ValueError,'exact text completion'): check_files(files,'cp1251-edited-1')

    def test_foreign_field_not_editable_refuses(self):
        files = self.files(); actions = self.actions(files)
        next(r for r in actions if r['kind'] == 'native_fields')['observed']['VENDOR_PRIVATE']['editable'] = False
        self.changed_actions(files,actions)
        with self.assertRaisesRegex(ValueError,'editability differs'): check_files(files,'cp1251-edited-1')

    def test_additional_selected_asset_refuses(self):
        files = self.files(); actions = self.actions(files)
        next(r for r in actions if r['kind'] == 'exact_asset_selected')['selected'].append(82)
        self.changed_actions(files,actions)
        with self.assertRaisesRegex(ValueError,'selection binding differs'): check_files(files,'cp1251-edited-1')

    def test_lost_capture_or_pixel_file_refuses(self):
        for variant in ('capture','file'):
            with self.subTest(variant=variant):
                files = self.files(); actions = self.actions(files)
                if variant == 'capture':
                    del actions[next(i for i,r in enumerate(actions) if r['kind'] == 'capture')]; self.changed_actions(files,actions)
                else:
                    del files['attempt/job/ui/source-overview-0.png']; reindex(files)
                with self.assertRaises((ValueError,FileNotFoundError)): check_files(files,'cp1251-edited-1')

    def test_unbound_capture_camera_refuses(self):
        files = self.files(); actions = self.actions(files)
        next(r for r in actions if r['kind'] == 'capture')['observation']['view']['factor'] += 1
        self.changed_actions(files,actions)
        with self.assertRaisesRegex(ValueError,'capture observation missing'): check_files(files,'cp1251-edited-1')

    def test_original_return_cannot_replace_edited_file(self):
        files = self.files(); files['attempt/job/returned.dxf'] = files['attempt/job/source.dxf']; actions = self.actions(files)
        next(r for r in actions if r['kind'] == 'returned_file')['sha256'] = digest(files['attempt/job/returned.dxf'])
        self.changed_actions(files,actions)
        with self.assertRaisesRegex(ValueError,'Save As format|Returned DXF asset'): check_files(files,'cp1251-edited-1')

    def test_failed_receiving_history_cannot_be_promoted(self):
        files = self.files(); files['failed-receiving/EXIT.json'] = b'{"exit":0}\n'
        with self.assertRaisesRegex(ValueError,'Original attempt identity'): check_files(files,'cp1251-edited-1')


if __name__ == '__main__': unittest.main()
