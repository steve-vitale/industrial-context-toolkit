"""Challenge complete native concurrent packets after recomputing local inventories."""
import json
from pathlib import Path
import tempfile
import unittest
from native_revisions import HERE, receiving
from recheck_native_revisions import restore, check_packet
from evidence import unpack
from test_evidence import put, reindex
from receive import digest


class ConcurrentPacketControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packets={c:unpack(HERE/'concurrent-development-1'/(c+'-concurrent-edited-1')) for c in ('cp1251','braces')}

    def refuse(self,change,pattern):
        for case,original in self.packets.items():
            with self.subTest(case=case):
                saved=original.copy();change(saved);reindex(saved)
                with tempfile.TemporaryDirectory(prefix='ict-revision-control-') as temporary:
                    root=Path(temporary)
                    restore(saved,root)
                    with self.assertRaisesRegex(ValueError,pattern):
                        receiving(root/'attempt',root/'receiving/PREPARATION.json',root/'receiving/METHODS.json')

    def test_complete_three_edit_packets_replay(self):
        for case in self.packets:
            with self.subTest(case=case):
                result=check_packet(HERE/'concurrent-development-1'/(case+'-concurrent-edited-1'))
                self.assertEqual(result['committed_edits'],3)
                self.assertFalse(result['whole_cad_qualified'])

    def test_source_and_plan_cannot_repin_local_job(self):
        for name in ('source.dxf','plan.json'):
            def change(saved):
                path='attempt/job/'+name;saved[path]+=b'\n'
                freeze=json.loads(saved['attempt/job/JOB-FREEZE.json']);freeze['files'][name]=digest(saved[path]);put(saved,'job/JOB-FREEZE.json',freeze)
            with self.subTest(input=name):self.refuse(change,'Source/plan/configuration basis differs')

    def test_derived_preparation_cannot_change_asset_identity(self):
        def change(saved):
            name='receiving/PREPARATION.json';value=json.loads(saved[name])
            first=next(iter(value['cases'].values()));first['basis']['assets'][0]['id']='invented/identity'
            saved[name]=(json.dumps(value)+'\n').encode()
        self.refuse(change,'External pre-launch derived preparation differs')

    def test_missing_serial_commit_refuses_after_event_renumbering(self):
        def change(saved):
            actions=json.loads(saved['attempt/job/ui/actions.json'])
            index=next(i for i,r in enumerate(actions) if r['kind']=='native_text_edit_committed' and r['change']['attribute']=='SERIAL')
            del actions[index]
            for i,row in enumerate(actions,1):row['event']=i
            put(saved,'job/ui/actions.json',actions)
        self.refuse(change,'edit source/state|Incomplete native edit')

    def test_foreign_field_cannot_lose_editability(self):
        def change(saved):
            actions=json.loads(saved['attempt/job/ui/actions.json'])
            next(r for r in actions if r['kind']=='native_fields')['observed']['VENDOR_PRIVATE']['editable']=False
            put(saved,'job/ui/actions.json',actions)
        self.refuse(change,'editability differs')

    def test_failed_controller_cannot_be_hidden_by_reindexing(self):
        def change(saved):
            process=json.loads(saved['attempt/job/native/PROCESS.json']);process['controller_exit']=1
            put(saved,'job/native/PROCESS.json',process)
        self.refuse(change,'Native process/controller/configuration differs')


if __name__=='__main__':unittest.main()
