"""Stage the predeclared full-application diagnostic; never overwrite an earlier attempt."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'layout-construction-17'
HEADER=HERE.parent/'header-boundaries-16'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();prior=json.loads((OLD/'FREEZE.json').read_bytes())
    if args.out.exists():raise ValueError('Use a new attempt folder')
    args.out.mkdir(parents=True);jobs=[]
    for name,pin in prior['inputs'].items():
        if not name.startswith('cases/'):continue
        if sha(args.prior/name)!=pin:raise ValueError('Prior input differs: '+name)
        dest=args.out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.prior/name,dest)
        jobs.extend(dict(id=dest.parent.name+'/'+imp,input='/work/'+name,importer=imp)for imp in ('OpenDesign','dxflib'))
    jobs.extend(dict(id='empty/'+imp,input=None,importer=imp)for imp in ('OpenDesign','dxflib'))
    write(args.out/'jobs.json',dict(jobs=jobs))
    for name in ('FIELDS.json','layout_ctor.cpp','COMPILE.json'):
        shutil.copyfile(args.prior/name,args.out/name)
    shutil.copyfile(HEADER/'KEYS.json',args.out/'KEYS.json')
    for name in ('PLAN.md','prepare.py','native_open.js','run_native.py'):
        shutil.copyfile(HERE/name,args.out/name)
    shutil.copyfile(args.prior/'layout_ctor.so',args.out/'layout_ctor.so')
    config=args.out/'.configuration/QCAD3.conf';config.parent.mkdir()
    shutil.copyfile(args.prior/'.configuration/QCAD3.conf',config)
    prefix=(HEADER/'native_headers.js').read_text(encoding='utf-8').split('var importFilters,exportFilters;')[0]
    (args.out/'native_complete.js').write_text(prefix+(HERE/'native_open.js').read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
    if sha(config)!=prior['configuration_sha256']or sha(args.out/'layout_ctor.so')!=prior['helper_sha256']:
        raise ValueError('Prior settings/helper differs')
    write(args.out/'FREEZE.json',dict(inputs={p.relative_to(args.out).as_posix():sha(p)for p in sorted(args.out.rglob('*'))
          if p.is_file()and '.configuration'not in p.parts and p.suffix!='.so'},
          configuration_sha256=prior['configuration_sha256'],helper_sha256=prior['helper_sha256'],
          library_sha256=prior['library_sha256'],image=prior['image'],
          processes=[dict(route=r,mode=m)for r in ('bare','mdi')for m in ('observe','preset-a','preset-b')],
          jobs_per_process=14,whole_cad_qualified=False))
    print(args.out)

if __name__=='__main__':main()
