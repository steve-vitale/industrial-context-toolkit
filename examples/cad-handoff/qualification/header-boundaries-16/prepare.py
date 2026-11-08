"""Freeze exact earlier sources and full native known-variable/style observations."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parents[3]/'scripts')]
import cad_handoff as ch
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-header-boundaries-16/attempt-1')
OLD=Path('C:/Users/Steve/.cp-scratch/cad-save-boundaries-14/attempt-1')
PUBLIC=Path('C:/Users/Steve/.cp-scratch/cad-header-research-16')
IDS=('libre-air-water','libre-power','libre-motion','qcad-hydraulic','qcad-mechanical','qcad-template')
FORMATS={'AC1015':'R15','AC1021':'R21','AC1024':'R24'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')

def main():
    ROOT.mkdir(parents=True,exist_ok=False)
    sources=json.loads((PUBLIC/'SOURCES.json').read_bytes())
    for row in sources:assert sha(PUBLIC/Path(row['path']).name)==row['sha256']
    source=(PUBLIC/'RS.h').read_text(encoding='utf-8').split('enum KnownVariable {',1)[1].split('};',1)[0]
    source=re.sub(r'/\*.*?\*/|//[^\n]*','',source,flags=re.S)
    names=[]
    for item in source.split(','):
        key=item.strip()
        if key and '='not in key:
            assert re.fullmatch('[A-Z][A-Z0-9]*',key);names.append(key)
    assert names[0]=='ANGBASE'and names[-1]=='WORLDVIEW'and len(names)==len(set(names))
    dims=re.findall(r'initDimX\(\w+, RS::(\w+), RS::(\w+)\)',(PUBLIC/'RDimStyle.cpp').read_text(encoding='utf-8'))
    assert len(dims)==len({k for k,t in dims})and all(k in names for k,t in dims)
    layout=(PUBLIC/'RLayout.h').read_text(encoding='utf-8')
    getters=re.findall(r'\b(?:QString|int|double|bool|RVector|RLayout::\w+) (get\w+)\(\) const\s*\{',layout)
    assert len(getters)==len(set(getters))and 'getMinLimits'in getters and 'getPlotOrigin'in getters
    keys=dict(known_variables=names,dimension_variables=[dict(name=k,type=t)for k,t in dims],layout_getters=getters,
        sources=[r for r in sources if Path(r['path']).name in('RS.h','RDimStyle.cpp','RLayout.h')])
    write(ROOT/'KEYS.json',keys);write(HERE/'KEYS.json',keys);write(ROOT/'SOURCES.json',sources)
    jobs=[];cases=[];pins=json.loads((OLD/'FREEZE.json').read_bytes())['inputs']
    for identity in IDS:
        source=OLD/'cases'/identity/'source.dxf';assert sha(source)==pins['cases/'+identity+'/source.dxf']
        base=ROOT/'cases'/identity;base.mkdir(parents=True);shutil.copyfile(source,base/'source.dxf');(base/'returns').mkdir()
        version=ch.load(source).dxfversion;cases.append(dict(id=identity,source_sha256=sha(source),version=version))
        for importer in('OpenDesign','dxflib'):
            for exporter in('OpenDesign','dxflib'):
                route=importer+'-'+exporter
                jobs.append(dict(id=identity+'/'+route,input='/work/cases/'+identity+'/source.dxf',output='/work/cases/'+identity+'/returns/'+route+'.dxf',
                    importer=importer,exporter=exporter,version=FORMATS[version]if exporter=='OpenDesign'else'R15'))
    empty=ROOT/'cases/empty/returns';empty.mkdir(parents=True)
    for writer in('OpenDesign','dxflib'):
        jobs.append(dict(id='empty/'+writer,input=None,output='/work/cases/empty/returns/'+writer+'.dxf',importer=writer,exporter=writer,version='R24'if writer=='OpenDesign'else'R15'))
    write(ROOT/'CASES.json',cases);write(ROOT/'export.json',dict(jobs=jobs));write(ROOT/'fresh.json',dict(jobs=jobs,read_only=True))
    shutil.copyfile(HERE/'native_headers.js',ROOT/'native_headers.js');shutil.copyfile(HERE/'run_native.py',ROOT/'run_native.py')
    (ROOT/'.configuration').mkdir();shutil.copyfile(OLD/'.configuration/QCAD3.conf',ROOT/'.configuration/QCAD3.conf')
    freeze=dict(inputs={p.relative_to(ROOT).as_posix():sha(p)for p in ROOT.rglob('*')if p.is_file()and'.configuration'not in p.parts},
        configuration_sha256=sha(ROOT/'.configuration/QCAD3.conf'),image='sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8',
        exposure='Six exact exposed adapted sources, two empty native controls; no new holdout')
    write(ROOT/'FREEZE.json',freeze);write(HERE/'FREEZE.json',freeze)
    print('Frozen',len(jobs),'jobs;',len(names),'known variables;',len(dims),'dimension variants;',len(getters),'layout getters')
if __name__=='__main__':main()
