"""Stage exact already-exposed public-11 controls; refuse replacing an attempt."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
IDS=('libre-air-water','libre-power','libre-motion','qcad-hydraulic','qcad-mechanical','qcad-template')
IMAGE='sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')

def prepare(previous,destination):
    destination.mkdir(exist_ok=False)
    old=json.loads((HERE.parent/'public-validation-11/NATIVE-INPUTS.json').read_bytes())
    jobs=[]
    for identity in IDS:
        folder=destination/'cases'/identity;folder.mkdir(parents=True);(folder/'returns').mkdir()
        for name in ('source.dxf','candidate.dxf','plan.json'):
            rel='cases/'+identity+'/'+name
            if sha(previous/rel)!=old['inputs'][rel]:raise ValueError('Prior input differs: '+rel)
            shutil.copyfile(previous/rel,destination/rel)
        for fmt,version in (('default',''),('r15','R15')):
            for route,source,operation in (
                    ('noop','source.dxf','none'),('patched','candidate.dxf','none'),('edited','source.dxf','edit'),
                    ('repeat','returns/noop-'+fmt+'.dxf','none')):
                jobs.append(dict(id=identity+'/'+route+'-'+fmt,input='/work/cases/'+identity+'/'+source,
                    output='/work/cases/'+identity+'/returns/'+route+'-'+fmt+'.dxf',operation=operation,
                    format=version,plan='/work/cases/'+identity+'/plan.json'))
    for name in ('native_probe.js','run_native.py'):shutil.copyfile(HERE/name,destination/name)
    write(destination/'export.json',dict(jobs=jobs))
    write(destination/'fresh.json',dict(jobs=jobs,read_only=True))
    config=destination/'.configuration';config.mkdir()
    shutil.copyfile(previous/'terminal-QCAD3.conf',config/'QCAD3.conf')
    frozen=dict(image=IMAGE,configuration_sha256=sha(config/'QCAD3.conf'),
        selection='All six public-validation-11 adapted inputs; all exposed development here',
        inputs={p.relative_to(destination).as_posix():sha(p) for p in sorted(destination.rglob('*'))
                if p.is_file() and '.configuration' not in p.parts},
        methods_sha256_lf={p.name:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            for p in (HERE/'PLAN.md',HERE/'prepare.py',HERE/'native_probe.js',HERE/'run_native.py')})
    write(destination/'FREEZE.json',frozen);return frozen

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('previous',type=Path);ap.add_argument('destination',type=Path);a=ap.parse_args()
    result=prepare(a.previous,a.destination);write(HERE/'FREEZE.json',result)
    print('Frozen',len(result['inputs']),'inputs; 48 exports, 48 fresh-process reads')
