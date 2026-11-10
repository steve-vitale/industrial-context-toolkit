"""Frozen source-known crosswalk/scoped replay integration controls; no product admission claim."""
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import context_basis as cb
import context_packet as cp

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/map-component-cycle/inputs/identity-change"
PUMP, OTHER = "IX/P1/U1/FP-1001", "IX/P1/U2/FP-2001"


class ScopedIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="scope-identity-")
        self.root = Path(self.temp.name)
        self.calls = []

    def tearDown(self):
        evidence = os.environ.get("SCOPE_IDENTITY_TEST_EVIDENCE")
        if evidence:
            target = Path(evidence) / self.id().split(".")[-1]
            shutil.copytree(self.root, target)
            (target / "calls.json").write_bytes(cp.encode(self.calls))
        self.temp.cleanup()

    def cli(self, *args, code=0, message=None):
        run = subprocess.run([sys.executable, "-B", "-S", str(ROOT / "scripts/context_workflow.py"), *map(str,args)],
                             capture_output=True, timeout=90)
        self.calls.append({"args":list(map(str,args)),"code":run.returncode,"stdout":run.stdout.decode(),"stderr":run.stderr.decode()})
        self.assertEqual(run.returncode,code,run.stderr.decode())
        if message:self.assertIn(message,run.stderr.decode())
        return json.loads(run.stdout if code==0 else run.stderr)

    def full(self,rev=1,name="full",previous=None,records=None,contribution=None):
        out=self.root/name
        args=["prepare","--records",records or FIXTURE/('rev'+str(rev)),"--site","IX","--plant","P1","--out",out]
        if previous:args += ["--previous",previous]
        else:args += ["--identity-crosswalk","identity-crosswalk.csv"]
        if contribution:args += ["--contributions",contribution]
        self.cli(*args)
        return out

    def scope(self,full,item=PUMP,name="scoped"):
        preview=self.root/(name+'.preview.json')
        result=self.cli("scope-preview",full,"--item",item,"--out",preview)
        out=self.root/name
        self.cli("package-scope",full,"--item",item,"--permit-whole-files-preview",result['preview_sha256'],"--out",out)
        return out,json.loads(preview.read_bytes())

    def repair(self,p):
        receipt=cb.read_json(p/'RECEIPT.json');receipt['files']={k:v for k,v in cp.inventory(p).items() if k!='RECEIPT.json'}
        (p/'RECEIPT.json').write_bytes(cp.encode(receipt))

    def test_alias_three_revisions_keep_projection_local_lookup_and_inactive_history(self):
        r1=self.full()
        self.cli("scope-preview",r1,"--item","P-101","--out",self.root/'ambiguous.json',code=2,message="ambiguous item")
        s1,preview=self.scope(r1)
        answer=self.cli("query",s1,"--item","LEGACY-7","--field","class")
        self.assertEqual(answer['subject'],PUMP)
        self.assertIn('projection-local',answer['scope_coverage']['identity_lookup'])
        evidence=answer['identity_resolution']['alias_evidence'][0]
        self.assertEqual(evidence['locator'],'CSV record 4; physical lines 4-4; column Alias')
        self.assertEqual(self.cli('query',s1,'--item','P-101','--field','class')['subject'],PUMP)
        self.cli('query',s1,'--item','IX/P1/U2/P-101',code=2,message='item not found')
        opened=cp.open_packet(s1)
        self.assertNotIn(OTHER,[e['id'] for e in opened['basis']['entities']])
        self.assertTrue(all(c['subject']==PUMP for c in opened['basis']['claims'] if c['predicate']=='identity_alias'))
        for config in [opened['config'],opened['scope']['source_input']]:self.assertEqual(config['identity_crosswalk'],'identity-crosswalk.csv')
        raw=(s1/'originals/identity-crosswalk.csv').read_bytes()
        self.assertEqual(raw,(FIXTURE/'rev1/identity-crosswalk.csv').read_bytes())
        self.assertIn(b'FP-2001,U2,P-101',raw)
        self.assertTrue(any(r['path']=='identity-crosswalk.csv' and r['contains_unfiltered_whole_file_content'] for r in preview['whole_files']))
        r2=self.full(2,'r2',r1);r3=self.full(3,'r3',r2);s3,_=self.scope(r3,name='scoped3')
        self.cli('query',s3,'--item','P-201',code=2,message='item not found')
        current=self.cli('query',s3,'--item',PUMP,'--field','identity_alias')
        self.assertEqual(current['state'],'inactive_evidence')
        self.assertTrue(all(not c['lookup_active'] for c in current['alternatives']))
        self.assertEqual(self.cli('query',s3/'previous','--item','P-201','--field','class')['subject'],PUMP)
        self.assertEqual(self.cli('verify',s3)['history_depth'],2)

    def test_whole_crosswalk_does_not_require_unrelated_target_source_or_declarations(self):
        records=self.root/'records';shutil.copytree(FIXTURE/'rev1',records)
        raw=(records/'equipment.csv').read_bytes().splitlines(keepends=True)
        (records/'equipment.csv').write_bytes(raw[0]+raw[1])
        (records/'other-equipment.csv').write_bytes(raw[0]+raw[2])
        with (records/'source-register.csv').open('a',encoding='utf-8',newline='') as f:
            csv.writer(f,lineterminator='\n').writerow(['other-equipment.csv','OTHER-EQ','1','supplied','Other unit','unrelated source'])
        full=self.full(records=records);scoped,_=self.scope(full)
        opened=cp.open_packet(scoped)
        self.assertFalse((scoped/'originals/other-equipment.csv').exists())
        self.assertNotIn('OTHER-EQ',[s['id'] for s in opened['basis']['sources']])
        self.assertNotIn(OTHER,[e['id'] for e in opened['basis']['entities']])
        self.assertEqual({d['DocumentID'] for d in opened['scope']['source_input']['declarations']},{s['id'] for s in opened['basis']['sources']})
        self.assertEqual((scoped/'originals/identity-crosswalk.csv').read_bytes(),(records/'identity-crosswalk.csv').read_bytes())
        self.assertEqual(self.cli('query',scoped,'--item','LEGACY-7','--field','class')['subject'],PUMP)

    def test_strict_optional_crosswalk_path_types_binding_and_config_refuse(self):
        scoped,_=self.scope(self.full())
        for i,value in enumerate([None,False,'../escape.csv','unknown.csv','equipment.csv']):
            with self.subTest(value=value):
                packet=self.root/('mutant'+str(i));shutil.copytree(scoped,packet)
                manifest=cb.read_json(packet/'scope.json');manifest['source_input']['identity_crosswalk']=value
                (packet/'scope.json').write_bytes(cp.encode(manifest));self.repair(packet)
                self.cli('verify',packet,code=2,message='scoped identity')
        packet=self.root/'wrong-config';shutil.copytree(scoped,packet)
        config=cb.read_json(packet/'intake.json');config['identity_crosswalk']='equipment.csv'
        (packet/'intake.json').write_bytes(cp.encode(config));self.repair(packet)
        self.cli('verify',packet,code=2,message='scoped intake selection differs')

    def test_supporting_only_scope_omits_unneeded_crosswalk_optin_and_bytes(self):
        full=self.full();item='IX/P1/U1/item:ITEM-A';scoped,_=self.scope(full,item)
        opened=cp.open_packet(scoped)
        self.assertNotIn('identity_crosswalk',opened['config'])
        self.assertNotIn('identity_crosswalk',opened['scope']['source_input'])
        self.assertFalse((scoped/'originals/identity-crosswalk.csv').exists())
        self.cli('query',scoped,'--item','LEGACY-7',code=2,message='item not found')
        self.assertEqual(opened['draft']['selection']['entities'],[item])

    def test_alias_correction_dependency_artifact_and_export_reopen_keep_exact_evidence(self):
        r1=self.full();r2=self.full(2,'r2',r1);edited=self.root/'edited'
        self.cli('edit',r2,'--item','P-201','--field','description','--value','Check seal source','--rationale','Confirm retained record','--out',edited)
        scoped,_=self.scope(edited);opened=cp.open_packet(scoped)
        original=cp.open_packet(edited)['basis']['corrections'][0]
        self.assertEqual(opened['basis']['corrections'][0],original)
        self.assertEqual(opened['draft']['annotations'][0]['annotation'],original)
        physical='IX/P1/U1/item:ITEM-B';artifact=self.root/'dependency.json'
        self.cli('materialize',scoped,'--item',physical,'--out',artifact)
        exported=cb.read_json(artifact)
        self.assertEqual(exported['schema'],'engineering-scoped-component-materialization-1')
        self.assertEqual(exported['supporting_context'],[cb.View(opened['basis']).inspect(physical)])
        self.assertEqual(exported['selection']['entities'],[physical])
        self.assertEqual(exported['component_draft']['components']['equipment_instrument_list']['items'][physical]['identity']['identity_role'],'physical_item')
        self.assertEqual(opened['draft']['selection']['entities'],[PUMP])
        wire=self.root/'delivery.json';result=self.cli('bundle',scoped,'--out',wire)
        shutil.rmtree(r1);shutil.rmtree(r2);shutil.rmtree(edited);shutil.rmtree(scoped)
        reopened=self.root/'reopened';self.cli('unbundle',wire,'--expected-sha256',result['sha256'],'--out',reopened)
        self.assertEqual(self.cli('query',reopened,'--item','P-201','--field','class')['subject'],PUMP)
        self.assertEqual(cp.open_packet(reopened)['basis']['corrections'][0],original)

    def test_external_subject_aliases_are_not_imported_and_cycle_expansion_still_refuses(self):
        contributions=self.root/'contributions.csv'
        contributions.write_bytes(('Subject,Predicate,Source,Locator,Quote,Target\n'+
            f'{PUMP},associated_with,XW,line 3,FP-2001,U2,P-101,{OTHER}\n').encode())
        # Quote contains CSV commas: preserve the actual literal through the normal CSV writer.
        with contributions.open('w',encoding='utf-8',newline='') as f:
            writer=csv.writer(f,lineterminator='\n');writer.writerow(['Subject','Predicate','Source','Locator','Quote','Target'])
            for a,b in [(PUMP,OTHER),(OTHER,PUMP)]:writer.writerow([a,'associated_with','XW','line 3','FP-2001,U2,P-101',b])
        full=self.full(contribution=contributions);scoped,_=self.scope(full)
        opened=cp.open_packet(scoped)
        self.assertIn(OTHER,opened['scope']['external_subject_references'])
        self.assertFalse(any(c['subject']==OTHER for c in opened['basis']['claims']))
        self.cli('query',scoped,'--item',OTHER,code=2,message='external_subject_reference')
        self.cli('query',scoped,'--item','IX/P1/U2/P-101',code=2,message='item not found')
        self.cli('query',scoped,'--item',PUMP,'--relation','associated_with','--depth',1)
        self.cli('query',scoped,'--item',PUMP,'--relation','associated_with','--depth',2,code=2,message='external_subject_reference')

    def test_sparse_identity_constructor_source_row_is_retained_without_engineering_facts(self):
        records=self.root/'sparse-records';records.mkdir()
        (records/'equipment.csv').write_bytes(b'Equipment,Area\nFP-1001,U1\nFP-2001,U2\n')
        (records/'identity-crosswalk.csv').write_bytes(b'Position,Area,Alias\nFP-1001,U1,P-101\nFP-2001,U2,P-201\n')
        (records/'source-register.csv').write_bytes(b'File,DocumentID,Revision,Status,Owner,Applicability\nequipment.csv,EQ,1,withdrawn,Maintenance,literal fictional position keys\nidentity-crosswalk.csv,XW,1,supplied,Engineering,literal fictional aliases\n')
        full=self.full(records=records);scoped,_=self.scope(full)
        opened=cp.open_packet(scoped)
        self.assertEqual({r['id'] for r in opened['basis']['sources']},{'EQ','XW'})
        origins=[r for r in opened['basis']['preparation'] if r.get('kind')=='scoped_identity_origin']
        self.assertEqual(len(origins),1)
        self.assertEqual({k:origins[0][k] for k in ['source','subject','locator','identity_role']},
                         {'source':'EQ','subject':PUMP,'locator':'CSV record 2; physical lines 2-2','identity_role':'functional_position'})
        self.assertIn('not an engineering fact',origins[0]['qualification'])
        self.assertEqual(next(r for r in opened['basis']['sources'] if r['id']=='EQ')['status'],'withdrawn')
        self.assertTrue(all(r['predicate']=='identity_alias' and r['source']=='XW' for r in opened['basis']['claims']))
        alias=self.cli('query',scoped,'--item','P-101','--field','identity_alias')
        self.assertEqual(alias['distinct_declared_roots'],['XW'])
        self.assertEqual(alias['scope_coverage']['identity_origins'],origins)
        self.assertEqual(self.cli('query',scoped,'--item',PUMP,'--field','class')['state'],'unknown')
        self.assertEqual((scoped/'originals/equipment.csv').read_bytes(),(records/'equipment.csv').read_bytes())
        forged=self.root/'wrong-origin';shutil.copytree(scoped,forged)
        basis=cb.read_json(forged/'basis.json');witness=next(r for r in basis['preparation'] if r.get('kind')=='scoped_identity_origin')
        witness['locator']='CSV record 3; physical lines 3-3'
        (forged/'basis.json').write_bytes(cp.encode(basis));receipt=cb.read_json(forged/'RECEIPT.json');receipt['basis_sha256']=cb.digest(basis)
        (forged/'RECEIPT.json').write_bytes(cp.encode(receipt));self.repair(forged)
        self.cli('verify',forged,code=2,message='scoped basis replay differs')
        plain=self.root/'plain-full'
        self.cli('prepare','--records',records,'--site','IX','--plant','P1','--out',plain)
        bare,_=self.scope(plain,name='bare-unopted')
        self.assertNotIn('identity_crosswalk',cp.open_packet(bare)['config'])
        self.assertEqual(self.cli('query',bare,'--item',PUMP,'--field','class')['state'],'unknown')


if __name__=='__main__':unittest.main()
