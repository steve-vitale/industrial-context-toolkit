"""Challenge drawing resubmission against retained sources and the earlier authored key."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import receive_drawings as receiving

ROOT=Path(__file__).resolve().parents[1]


class Resubmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='ict-drawing-resubmission-');cls.root=Path(cls.temp.name)
        cls.prior=cls.root/'initial';receiving.run(ROOT/'examples/drawing-handoff/job.json',cls.prior)
        cls.job=json.loads((cls.prior/'job.json').read_bytes())
        cls.job['drawings'][0]['markup_manifest']=str(ROOT/'examples/pid-markup-review/corrected/manifest.json')
        cls.job['drawings'][1]['cad']={k:str(cls.prior/v) for k,v in cls.job['drawings'][1]['cad'].items()}
        cls.current=cls.root/'current';cls.jobfile=cls.root/'corrected-job.json'
        cls.jobfile.write_text(json.dumps(cls.job),encoding='utf-8')
        cls.brief=receiving.run(cls.jobfile,cls.current,cls.prior)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def read(self,p):return json.loads(p.read_bytes())

    def run_job(self,label,job,prior=None):
        path=self.root/(label+'.json');path.write_text(json.dumps(job),encoding='utf-8')
        return receiving.run(path,self.root/label,prior or self.prior)

    def test_correction_uses_existing_key_and_keeps_unresolved_evidence(self):
        expected=self.read(ROOT/'examples/pid-markup-review/ACCEPTANCE.json')['corrected_return_statuses']
        requests={r['detail']['id']:r for r in self.brief['items'] if r['kind']=='request'}
        self.assertEqual({k:v['status'] for k,v in requests.items()},expected)
        self.assertEqual(self.brief['revision']['basis_changes'],[])
        self.assertEqual(self.brief['items'][0]['priority'],'safety');self.assertTrue(requests['M02']['review_required'])
        text=(self.current/'BRIEF.md').read_text(encoding='utf-8')
        self.assertIn('335 unexpected strict drawing differences',text);self.assertIn('No observation; absence is not inferred',text)
        self.assertEqual(self.brief['authorized_decision'],'pending');self.assertFalse(self.brief['release_accepted'])
        self.assertTrue(all(r['engineering_closure']=='pending' for r in self.brief['revision']['items']))
        restored=next(r for r in self.brief['revision']['items'] if r['kind']=='other_change')
        self.assertEqual(restored['current_status'],'matches_original_reading')
        self.assertEqual(restored['current_source_check']['returned']['value'],'FC')

    def test_complete_revision_replays_from_portable_job(self):
        self.assertEqual(receiving.run(self.current/'job.json',self.root/'portable'),self.brief)

    def test_drawing_order_is_not_identity(self):
        job=copy.deepcopy(self.job);job['drawings'].reverse()
        brief=self.run_job('reordered',job)
        self.assertEqual(brief['revision']['basis_changes'],[])
        self.assertEqual([(r['drawing'],r['previous_status'],r['current_status']) for r in brief['revision']['items']],
                         [(r['drawing'],r['previous_status'],r['current_status']) for r in self.brief['revision']['items']])

    def test_omitted_cad_drawing_remains_an_unresolved_follow_up(self):
        job=copy.deepcopy(self.job);job['drawings']=job['drawings'][:1]
        brief=self.run_job('omitted',job)
        self.assertEqual(brief['revision']['basis_changes'][0]['status'],'not_reassessed')
        self.assertTrue(any(r['kind']=='revision_follow_up' and r['needs_attention'] for r in brief['items']))
        self.assertTrue(any(r['kind']=='cad_preservation' and r['current_status']=='not_reassessed' for r in brief['revision']['items']))

    def test_output_inside_previous_packet_refuses_without_changing_it(self):
        prior=self.root/'nested-output-prior';shutil.copytree(self.prior,prior)
        before=receiving.packet_files(prior)
        with self.assertRaisesRegex(ValueError,'outside the previous packet'):
            receiving.run(self.jobfile,prior/'new-return',prior)
        self.assertEqual(receiving.packet_files(prior),before)

    def changed_markup(self,label,change):
        root=self.root/(label+'-input');shutil.copytree(ROOT/'examples/pid-markup-review/corrected',root)
        manifest=self.read(root/'manifest.json');change(root,manifest)
        (root/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
        job=copy.deepcopy(self.job);job['drawings'][0]['markup_manifest']=str(root/'manifest.json')
        return self.run_job(label,job)

    def test_changed_request_scope_is_not_a_correction(self):
        def change(root,manifest):
            p=root/manifest['requests']['path'];requests=self.read(p);requests['markups'][0]['text']+='; revised scope'
            p.write_text(json.dumps(requests),encoding='utf-8');manifest['requests']['sha256']=receiving.sha(p.read_bytes())
        brief=self.changed_markup('scope',change)
        self.assertEqual(brief['revision']['basis_changes'][0]['status'],'basis_changed')
        self.assertTrue(all(r['current_status']=='basis_changed' for r in brief['revision']['items'] if r['kind']=='request'))

    def test_missing_reading_does_not_close_the_previous_change(self):
        def change(root,manifest):
            p=root/manifest['readings']['path'];readings=self.read(p)
            readings['observations']=[r for r in readings['observations'] if not (r['role']=='returned' and r['key'].get('name')=='fail_action')]
            p.write_text(json.dumps(readings),encoding='utf-8');manifest['readings']['sha256']=receiving.sha(p.read_bytes())
        brief=self.changed_markup('missing-observation',change)
        row=next(r for r in brief['revision']['items'] if r['kind']=='other_change')
        self.assertEqual(row['current']['kind'],'coverage_gap');self.assertEqual(row['current_status'],'needs_assessment')
        self.assertEqual(row['current']['detail']['returned']['state'],'unknown')

    def test_reinterpreted_original_reading_is_a_changed_basis(self):
        def change(root,manifest):
            p=root/manifest['readings']['path'];readings=self.read(p)
            original=next(r for r in readings['observations'] if r['role']=='original' and r['key'].get('name')=='size')
            original['value']='DN40'
            p.write_text(json.dumps(readings),encoding='utf-8');manifest['readings']['sha256']=receiving.sha(p.read_bytes())
        brief=self.changed_markup('reinterpreted-original',change)
        self.assertEqual(brief['revision']['basis_changes'][0]['status'],'basis_changed')

    def test_rebased_cad_plan_remains_explicit(self):
        job=copy.deepcopy(self.job);plan=self.read(Path(job['drawings'][1]['cad']['plan']))
        plan['changes'][0]['after']='DIFFERENT-SCOPE';p=self.root/'new-cad-plan.json'
        p.write_text(json.dumps(plan),encoding='utf-8');job['drawings'][1]['cad']['plan']=str(p)
        brief=self.run_job('rebased-plan',job)
        self.assertTrue(any(r['check']=='cad' and r['status']=='basis_changed' for r in brief['revision']['basis_changes']))
        self.assertTrue(all(r['current_status']=='basis_changed' for r in brief['revision']['items'] if r['kind'].startswith('cad_')))

    def test_previous_inventory_tampering_refuses_before_publication(self):
        prior=self.root/'damaged';shutil.copytree(self.prior,prior)
        p=prior/'BRIEF.md';p.write_bytes(p.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'Previous packet inventory changed'):self.run_job('refuse-damaged',self.job,prior)
        self.assertFalse((self.root/'refuse-damaged').exists())

    def test_repinned_false_previous_findings_still_refuse(self):
        prior=self.root/'repinned';shutil.copytree(self.prior,prior)
        p=prior/'brief.json';brief=self.read(p);brief['items'][0]['status']='supported'
        p.write_text(json.dumps(brief),encoding='utf-8')
        p=prior/'receipt.json';receipt=self.read(p);receipt['files']['brief.json']=receiving.sha((prior/'brief.json').read_bytes())
        p.write_text(json.dumps(receipt),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Previous findings do not reproduce'):self.run_job('refuse-repinned',self.job,prior)
        self.assertFalse((self.root/'refuse-repinned').exists())

    def test_markup_only_resubmission_runs_without_optional_packages(self):
        initial=copy.deepcopy(self.job);initial['drawings']=initial['drawings'][:1]
        initial['drawings'][0]['markup_manifest']=str(ROOT/'examples/pid-markup-review/inputs/manifest.json')
        p=self.root/'markup-initial.json';p.write_text(json.dumps(initial),encoding='utf-8')
        prior=self.root/'markup-initial';receiving.run(p,prior)
        initial['drawings'][0]['markup_manifest']=str(ROOT/'examples/pid-markup-review/corrected/manifest.json')
        p=self.root/'markup-next.json';p.write_text(json.dumps(initial),encoding='utf-8')
        result=subprocess.run([sys.executable,'-S',str(ROOT/'scripts/receive_drawings.py'),'--manifest',str(p),'--previous',str(prior),'--out',str(self.root/'markup-next')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.read(self.root/'markup-next/brief.json')['revision']['basis_changes'],[])


if __name__=='__main__':unittest.main()
