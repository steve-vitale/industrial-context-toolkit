"""Freeze all six exact sources and matched native dimensional-store interventions."""
import hashlib
import json
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-header-boundaries-16')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
def main():
    prior=ROOT/'attempt-1';work=ROOT/'dimension-2';work.mkdir(exist_ok=False)
    frozen=json.loads((prior/'FREEZE.json').read_bytes());cases=json.loads((prior/'CASES.json').read_bytes());jobs=[]
    for case in cases:
        identity=case['id'];base=work/'cases'/identity;base.mkdir(parents=True);(base/'returns').mkdir()
        source=prior/'cases'/identity/'source.dxf';assert sha(source)==frozen['inputs']['cases/'+identity+'/source.dxf']
        shutil.copyfile(source,base/'source.dxf')
        for operation in('unchanged','known','style','unrelated'):
            for writer in('OpenDesign','dxflib'):
                label=operation+'-'+writer
                jobs.append(dict(id=identity+'/'+label,input='/work/cases/'+identity+'/source.dxf',output='/work/cases/'+identity+'/returns/'+label+'.dxf',
                    importer='OpenDesign',exporter=writer,version={'AC1015':'R15','AC1021':'R21','AC1024':'R24'}[case['version']]if writer=='OpenDesign'else'R15',operation=operation))
    for name in('KEYS.json','CASES.json','SOURCES.json'):shutil.copyfile(prior/name,work/name)
    write(work/'export.json',dict(jobs=jobs));write(work/'fresh.json',dict(jobs=jobs,read_only=True))
    shutil.copyfile(HERE/'native_dimensions.js',work/'native_headers.js');shutil.copyfile(HERE/'run_native.py',work/'run_native.py')
    (work/'.configuration').mkdir();shutil.copyfile(prior/'.configuration/QCAD3.conf',work/'.configuration/QCAD3.conf')
    freeze=dict(inputs={p.relative_to(work).as_posix():sha(p)for p in work.rglob('*')if p.is_file()and'.configuration'not in p.parts},
        configuration_sha256=sha(work/'.configuration/QCAD3.conf'),image=frozen['image'],exposure='Six exact exposed adapted sources; dimensional-store intervention, no new holdout')
    write(work/'FREEZE.json',freeze);write(HERE/'DIMENSION-FREEZE.json',freeze)
    print('Frozen',len(jobs),'matched dimensional-store controls')
if __name__=='__main__':main()
