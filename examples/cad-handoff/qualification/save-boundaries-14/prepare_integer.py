"""Prepare a raw-span-only correction of the out-of-range USERI5 diagnostic."""
import copy
from pathlib import Path
import shutil
import sys
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parents[3]/'scripts')]
from followup_analysis import b
import cad_value_patch
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-save-boundaries-14')

def replace_user(data,before,after):
    lines=data.splitlines(keepends=True)
    positions=[i for i,line in enumerate(lines)if line.strip()==b'$USERI5']
    b.require(len(positions)==1,'Ambiguous USERI5 raw location')
    i=positions[0]+2
    b.require(lines[i-1].strip()==b'70'and lines[i].strip()==str(before).encode(),'Wrong USERI5 raw value')
    lines[i]=lines[i].replace(str(before).encode(),str(after).encode(),1)
    return b''.join(lines)

def main():
    work=ROOT/'integer-4';work.mkdir(exist_ok=False);cases=[];jobs=[]
    oldcases=b.read(ROOT/'payload-3/CASES.json')
    selections=[(case,6000+b.IDS.index(case['identity']),case['id'])for case in oldcases]
    selections += [(oldcases[1],value,'integer-boundary/'+str(value))for value in(-32768,-1,0,1,32767)]
    for old,value,identity in selections:
        case=copy.deepcopy(old);case.update(id=identity,useri5=value)
        folder=work/'cases'/identity;folder.mkdir(parents=True)
        prior=ROOT/'payload-3/cases'/old['id'];source=folder/'source.dxf'
        source.write_bytes(replace_user((prior/'source.dxf').read_bytes(),old['useri5'],value))
        plan=b.read(prior/'plan.json');plan['source_sha256']=b.sha(source);b.write(folder/'plan.json',plan)
        cad_value_patch.apply(source,plan,folder/'patch');shutil.copyfile(folder/'patch/candidate.dxf',folder/'candidate.dxf')
        cases.append(case);jobs.append(dict(id=identity,input='/work/cases/'+identity+'/source.dxf',
            output='/work/cases/'+identity+'/returned.dxf',format=case['format']))
    b.write(work/'CASES.json',cases);b.write(work/'export.json',dict(jobs=jobs));b.write(work/'fresh.json',dict(jobs=jobs,read_only=True))
    shutil.copyfile(HERE/'native_payload_observed.js',work/'native_payload.js')
    shutil.copyfile(ROOT/'payload-3/run_native.py',work/'run_native.py')
    (work/'.configuration').mkdir();shutil.copyfile(ROOT/'payload-3/.configuration/QCAD3.conf',work/'.configuration/QCAD3.conf')
    frozen=dict(inputs={p.relative_to(work).as_posix():b.sha(p)for p in work.rglob('*')if p.is_file()and'.configuration'not in p.parts},
        configuration_sha256=b.sha(work/'.configuration/QCAD3.conf'),exposure='Seventeen exposed authored integer-control successors')
    b.write(work/'FREEZE.json',frozen);b.write(HERE/'INTEGER-FREEZE.json',frozen)
    print('Frozen seventeen valid integer sources and exact candidates')
if __name__=='__main__':main()
