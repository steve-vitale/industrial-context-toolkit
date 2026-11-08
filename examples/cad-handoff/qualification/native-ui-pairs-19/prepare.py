"""Stage exact exposed sources, paired software controls and native jobs; no native execution."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(HERE.parent))
import cad_handoff as ch
from run_cases import run_case
from ezdxf import bbox

CASES={
 'libre-air-water':'245a50eefeabc483f16269375a3bf9bd892b9cebd125e76f5ae744f5466f4db8',
 'libre-motion':'724b0557adc753c59e23e864dc08f6de1c1ca50767b4da012be0fadf54d77b04',
 'libre-power':'8876b0c66ec7794914a2218072386f5d169a6813a675a579747fa6242cfac2bd',
 'qcad-hydraulic':'4d768e3a5ca0ba8d5e4762851a349f1679381b51d5fdf2a9b2fc89e86aa430db',
 'qcad-mechanical':'30c4a41b51dd5474889db30ca336a2cfe18df6d2dc2c6fea5affb5091327a26d',
 'qcad-template':'6e87cef8ca4178b20e9d4e2b892917636ba2fe02e030ea076379c8d57e6a1f88'}
METHODS=['PLAN.md','METHOD.md','observe_case.js','workflow.py','launch_case.py','inspect_ui.py','ui_control.py','prepare.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def frame(entities):
    b=bbox.extents(entities,fast=False);a,z=b.extmin,b.extmax
    values=[a.x,a.y,z.x,z.y];pad=max(2,.2*max(z.x-a.x,z.y-a.y))
    return [values[0]-pad,values[1]-pad,values[2]+pad,values[3]+pad]
def prepare(destination,source_root):
    destination.mkdir();results=[]
    for name,pin in CASES.items():
        case=destination/name;case.mkdir();source=source_root/name/'source.dxf'
        if sha(source)!=pin:raise ValueError('Exact exposed source differs: '+name)
        shutil.copyfile(source,case/'source.dxf');source=case/'source.dxf';assets=ch.assets(ch.load(source))
        if len(assets)!=1:raise ValueError('Expected one source asset')
        a=assets[0]
        if a['attributes']!={'MANUFACTURER':'QUAL-BEFORE','ICT_ID':'AUTHORED-QUAL/'+name+'/1','TAG':'QA-1'}:raise ValueError('Unexpected source attributes')
        plan=dict(schema='cad-edit-plan-1',source_sha256=pin,changes=[dict(id=a['id'],attribute='MANUFACTURER',before='QUAL-BEFORE',after='QUAL-AFTER',reason='Declared exposed native UI procedure development; no accepted engineering change')])
        write(case/'plan.json',plan);result=run_case(name,source,case/'plan.json',case/'software');results.append(result)
        docs=[ch.load(source),ch.load(case/'software/candidate/candidate.dxf')]
        models=[d.modelspace()for d in docs];inserts=[next(iter(m.query('INSERT'))) for m in models]
        attrs=[a for insert in inserts for a in insert.attribs]
        frames=dict(overview=frame([e for m in models for e in m]),asset=frame(inserts+attrs),labels=frame(attrs))
        write(case/'basis.json',dict(case=name,source_sha256=pin,handle=a['handle'],attributes=a['attributes'],frames=frames))
    write(destination/'SOFTWARE.json',results)
    write(destination/'PREPARATION.json',dict(methods={n:sha(HERE/n)for n in METHODS},sources=CASES,scope='Six exposed adaptations; no new qualification evidence'))
def job(destination,case,role,configuration,prior_jobs):
    destination.mkdir(parents=True);(destination/'.configuration').mkdir();shutil.copyfile(configuration,destination/'.configuration/QCAD3.conf')
    basis=json.loads((case/'basis.json').read_bytes());basis['role']=role;write(destination/'job.json',basis)
    shutil.copyfile(case/'source.dxf',destination/'source.dxf')
    if role=='receiving':
        for route in ('baseline','edited'):shutil.copyfile(prior_jobs/(case.name+'-'+route)/'returned.dxf',destination/(route+'.dxf'))
        shutil.copyfile(case/'software/candidate/candidate.dxf',destination/'candidate.dxf')
    for n in METHODS:shutil.copyfile(HERE/n,destination/n)
    files={p.relative_to(destination).as_posix():sha(p)for p in destination.rglob('*')if p.is_file()}
    write(destination/'JOB-FREEZE.json',dict(files=files,scope='Frozen before native execution; exposed development'))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('prepare');a.add_argument('out',type=Path);a.add_argument('source_root',type=Path)
    a=sub.add_parser('job');a.add_argument('out',type=Path);a.add_argument('case',type=Path);a.add_argument('role',choices=['baseline','edited','receiving']);a.add_argument('configuration',type=Path);a.add_argument('prior_jobs',type=Path)
    args=p.parse_args()
    if args.action=='prepare':prepare(args.out,args.source_root)
    else:job(args.out,args.case,args.role,args.configuration,args.prior_jobs)
