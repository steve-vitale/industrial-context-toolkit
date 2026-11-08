"""Prepare the six exposed public sources and separate default/original-version branches."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[3]/'scripts'))
import cad_handoff as ch
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-save-boundaries-14')/'attempt-1'
OLD=Path('C:/Users/Steve/.cp-scratch/cad-root-cause-12/attempt-2')
IDS=('libre-air-water','libre-power','libre-motion','qcad-hydraulic','qcad-mechanical','qcad-template')
FORMATS={'AC1015':'R15','AC1021':'R21','AC1024':'R24'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
    ROOT.mkdir(exist_ok=False);(ROOT/'.configuration').mkdir();jobs=[];inputs={};cases=[]
    config=Path('C:/Users/Steve/.cp-scratch/cad-public-validation-11/native-1/terminal-QCAD3.conf')
    assert sha(config)=='2c23f1511046e1ce876753efa354185a733d88e1264713ee13cc72d735f73a6c'
    shutil.copyfile(config,ROOT/'.configuration/QCAD3.conf')
    oldpin=json.loads((OLD/'FREEZE.json').read_bytes())['inputs']
    for identity in IDS:
        folder=ROOT/'cases'/identity;(folder/'returns').mkdir(parents=True)
        for name in ('source.dxf','candidate.dxf','plan.json'):
            source=OLD/'cases'/identity/name
            assert sha(source)==oldpin[f'cases/{identity}/{name}']
            shutil.copyfile(source,folder/name)
        (folder/'history').mkdir()
        for name in ('noop-default.dxf','repeat-default.dxf','noop-r15.dxf','repeat-r15.dxf'):
            shutil.copyfile(OLD/'cases'/identity/'returns'/name,folder/'history'/name)
        version=ch.load(folder/'source.dxf').dxfversion;fmt=FORMATS[version]
        cases.append(dict(id=identity,version=version,format=fmt))
        for route,format_name,input_name in [('default','',f'/work/cases/{identity}/source.dxf'),
                ('original',fmt,f'/work/cases/{identity}/source.dxf'),
                ('repeat',fmt,f'/work/cases/{identity}/returns/original.dxf')]:
            jobs.append(dict(id=identity+'/'+route,input=input_name,output=f'/work/cases/{identity}/returns/{route}.dxf',format=format_name))
    (ROOT/'empty').mkdir()
    for fmt in ('','R15','R21','R24'):
        label=fmt or 'default';jobs.append(dict(id='empty/'+label,input=None,output='/work/empty/'+label+'.dxf',format=fmt))
    write(ROOT/'CASES.json',cases);write(ROOT/'export.json',dict(jobs=jobs))
    write(ROOT/'fresh.json',dict(jobs=jobs,read_only=True))
    for name in ('native_boundaries.js','run_native.py'):shutil.copyfile(HERE/name,ROOT/name)
    inputs={p.relative_to(ROOT).as_posix():sha(p)for p in ROOT.rglob('*')if p.is_file() and '.configuration'not in p.parts}
    write(ROOT/'FREEZE.json',dict(inputs=inputs,configuration_sha256=sha(config),
        native_image='sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8',
        exposure='All six already exposed sources; original-version diagnostics and empty controls, no reserved-source claim'))
    shutil.copyfile(ROOT/'FREEZE.json',HERE/'FREEZE.json')
    print('Frozen',len(jobs),'native exports and separate fresh reads on six exposed inputs')
if __name__=='__main__':main()
