"""Exercise own-input receiving, portable replay and source/output preservation."""
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


class ReceivingJob(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='ict-own-drawing-job-');cls.root=Path(cls.temporary.name)
        cls.source=ROOT/'examples/drawing-handoff/job.json';cls.packet=cls.root/'first'
        cls.brief=receiving.run(cls.source,cls.packet)

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def job(self,name,value):
        path=self.root/(name+'.json');path.write_text(json.dumps(value),encoding='utf-8');return path

    def read(self,path):return json.loads(path.read_bytes())

    def test_existing_checker_results_and_every_finding_are_retained(self):
        markup=self.read(self.packet/'drawings/001/markup/result.json');cad=self.read(self.packet/'drawings/002/cad/review.json')
        self.assertEqual(markup,self.read(ROOT/'examples/drawing-handoff/worked/markup/result.json'))
        self.assertEqual(cad,self.read(ROOT/'examples/drawing-handoff/worked/cad/review.json'))
        requests=[r for r in self.brief['items'] if r['kind']=='request']
        self.assertEqual({r['detail']['id']:r['detail'] for r in requests},{r['id']:r for r in markup['markups']})
        self.assertEqual(len([r for r in self.brief['items'] if r['kind']=='other_change']),len(markup['other_observed_changes']))
        self.assertEqual(len([r for r in self.brief['items'] if r['kind']=='coverage_gap']),len(markup['other_fact_coverage_gaps']))
        self.assertEqual(self.brief['items'][0]['priority'],'safety')
        self.assertFalse(self.brief['release_accepted']);self.assertEqual(self.brief['authorized_decision'],'pending')
        text=(self.packet/'BRIEF.md').read_text(encoding='utf-8')
        self.assertIn('335 unexpected strict drawing differences',text);self.assertIn('No observation; absence is not inferred',text)
        self.assertTrue(all(r['owner'] is None for r in self.brief['items']))

    def test_portable_job_reproduces_complete_brief(self):
        actual=receiving.run(self.packet/'job.json',self.root/'portable')
        self.assertEqual(actual,self.brief)

    def test_occupied_output_refuses_without_changing_packet(self):
        before={p.relative_to(self.packet):p.read_bytes() for p in self.packet.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError,'Output exists'):receiving.run(self.source,self.packet)
        self.assertEqual(before,{p.relative_to(self.packet):p.read_bytes() for p in self.packet.rglob('*') if p.is_file()})

    def test_stale_later_drawing_refuses_before_publication(self):
        source=self.root/'stale-input';shutil.copytree(self.packet/'drawings/001/markup',source)
        manifest=self.read(source/'manifest.json');returned=next(d for d in manifest['documents'] if d['role']=='returned')
        changed=source/returned['path'];changed.write_bytes(changed.read_bytes()+b'\nCHANGED\n')
        job=self.read(self.packet/'job.json');job['drawings'].reverse()
        job['drawings'][0]['cad']={k:str((self.packet/v).resolve()) for k,v in job['drawings'][0]['cad'].items()}
        job['drawings'][1]['markup_manifest']=str(source/'manifest.json')
        out=self.root/'stale-output'
        with self.assertRaisesRegex(ValueError,'Stale file binding'):receiving.run(self.job('stale-job',job),out)
        self.assertFalse(out.exists())

    def test_duplicate_drawing_ids_refuse(self):
        job=dict(schema='drawing-receiving-1',id='duplicates',drawings=[dict(id='same',markup_manifest=str(self.packet/'drawings/001/markup/manifest.json'))]*2)
        out=self.root/'duplicates'
        with self.assertRaisesRegex(ValueError,'Duplicate drawing id'):receiving.run(self.job('duplicate-job',job),out)
        self.assertFalse(out.exists())

    def test_markup_only_runs_without_optional_packages(self):
        job=dict(schema='drawing-receiving-1',id='stdlib',drawings=[dict(id='markup',markup_manifest=str(self.packet/'drawings/001/markup/manifest.json'))])
        result=subprocess.run([sys.executable,'-S',str(ROOT/'scripts/receive_drawings.py'),'--manifest',str(self.job('stdlib-job',job)),'--out',str(self.root/'stdlib')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(self.read(self.root/'stdlib/brief.json')['checks']),1)

    def test_supplied_two_format_association_is_not_certified(self):
        job=self.read(self.packet/'job.json');one=dict(id='supplied association',markup_manifest=str(self.packet/job['drawings'][0]['markup_manifest']),
            cad={k:str(self.packet/v) for k,v in job['drawings'][1]['cad'].items()})
        actual=receiving.run(self.job('paired-job',dict(schema='drawing-receiving-1',id='paired',drawings=[one])),self.root/'paired')
        correspondence=[r for r in actual['items'] if r['kind']=='representation_correspondence']
        self.assertEqual(len(correspondence),1);self.assertEqual(correspondence[0]['status'],'not_verified')
        self.assertFalse(actual['release_accepted'])


if __name__=='__main__':unittest.main()
