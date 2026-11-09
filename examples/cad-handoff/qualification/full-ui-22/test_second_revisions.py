"""Replay completed second native saves and reject reindexed source/field/history losses."""
import json
from pathlib import Path
import tempfile
import unittest
from second_revisions import HERE, read, sha, lf, receiving, check
from evidence import unpack
from recheck_native_revisions import restore
from test_evidence import put, reindex
from receive import digest


class SecondRevisionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identities=read(HERE/'SECOND-RETAINED-1.json')['attempts']
        cls.edited={c:unpack(HERE/'second-development-1'/(c+'-second-edited-1')) for c in ('cp1251','braces')}

    def refuse(self,change,pattern):
        for case,original in self.edited.items():
            with self.subTest(case=case):
                saved=original.copy();change(saved);reindex(saved)
                with tempfile.TemporaryDirectory(prefix='ict-second-revision-control-') as temporary:
                    root=Path(temporary);restore(saved,root)
                    with self.assertRaisesRegex(ValueError,pattern):receiving(root/'attempt')

    def test_all_four_completed_saves_replay_without_accepting_preservation(self):
        expected={c+'-second-'+r+'-1' for c in ('cp1251','braces') for r in ('baseline','edited')}
        self.assertEqual(set(self.identities),expected)
        for label,pins in self.identities.items():
            with self.subTest(label=label):
                packet=HERE/'second-development-1'/label
                self.assertEqual(lf(packet/'INVENTORY.json'),pins['inventory_sha256_lf'])
                self.assertEqual(lf(packet/'RESULT.json'),pins['result_sha256_lf'])
                self.assertEqual(sha(packet/'evidence.tar.xz'),pins['archive_sha256'])
                result=check(packet)
                self.assertEqual(result['edits'],1 if '-edited-' in label else 0)
                self.assertGreater(result['strict'],0);self.assertFalse(result['whole_cad_qualified'])

    def test_reindexed_source_and_plan_changes_refuse(self):
        for name in ('source.dxf','plan.json'):
            def change(saved):
                saved['attempt/job/'+name]+=b'\n'
                freeze=json.loads(saved['attempt/job/JOB-FREEZE.json']);freeze['files'][name]=digest(saved['attempt/job/'+name])
                put(saved,'job/JOB-FREEZE.json',freeze)
            with self.subTest(input=name):self.refuse(change,'Source/plan/configuration basis differs')

    def test_missing_model_commit_refuses_after_renumbering(self):
        def change(saved):
            actions=json.loads(saved['attempt/job/ui/actions.json'])
            del actions[next(i for i,r in enumerate(actions) if r['kind']=='native_text_edit_committed')]
            for i,row in enumerate(actions,1):row['event']=i
            put(saved,'job/ui/actions.json',actions)
        self.refuse(change,'edit source/state|Incomplete native edit')

    def test_foreign_field_editability_loss_refuses(self):
        def change(saved):
            actions=json.loads(saved['attempt/job/ui/actions.json'])
            next(r for r in actions if r['kind']=='native_fields')['observed']['VENDOR_PRIVATE']['editable']=False
            put(saved,'job/ui/actions.json',actions)
        self.refuse(change,'editability differs')

    def test_failed_controller_cannot_be_hidden(self):
        def change(saved):
            process=json.loads(saved['attempt/job/native/PROCESS.json']);process['controller_exit']=1
            put(saved,'job/native/PROCESS.json',process)
        self.refuse(change,'Native process/controller/configuration differs')


if __name__=='__main__':unittest.main()
