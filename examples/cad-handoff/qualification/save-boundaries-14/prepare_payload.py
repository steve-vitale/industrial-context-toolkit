"""Generate/freeze authored paired payload revisions before native execution."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parents[3]/'scripts')]
from prepare import IDS,FORMATS,sha,write
import cad_handoff as ch
import cad_value_patch
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-save-boundaries-14')
USED='ICT_BOUND14_USED';UNUSED='ICT_BOUND14_UNUSED';FOREIGN='ICT_BOUND14_FOREIGN'
def main():
    work=ROOT/'payload-2';work.mkdir(exist_ok=False);jobs=[];cases=[]
    for index,identity in enumerate(IDS):
        old=ROOT/'attempt-1/cases'/identity
        for mode in ('registered','used'):
            folder=work/'cases'/identity/mode;folder.mkdir(parents=True)
            doc=ch.load(old/'source.dxf');doc.appids.new(USED);doc.appids.new(UNUSED)
            marker='ict-boundary-foreign-v1/'+identity;user=60000+index
            record=doc.rootdict.add_xrecord(FOREIGN);record.extend([(1,marker),(90,31415926),(40,2.718281828)])
            doc.header['$USERI5']=user
            asset=ch.assets(doc)[0];xdata=[(1000,'ict-boundary-used-v1/'+identity),(1040,1.23456789),(1070,12345)]
            if mode=='used':doc.entitydb[asset['handle']].set_xdata(USED,xdata)
            source=folder/'source.dxf';doc.saveas(source)
            plan=copy.deepcopy(json.loads((old/'plan.json').read_bytes()));plan['source_sha256']=sha(source)
            write(folder/'plan.json',plan)
            cad_value_patch.apply(source,plan,folder/'patch')
            candidate=folder/'patch/candidate.dxf'
            shutil.copyfile(candidate,folder/'candidate.dxf')
            version=ch.load(source).dxfversion
            cases.append(dict(id=identity+'/'+mode,identity=identity,mode=mode,version=version,format=FORMATS[version],
                useri5=user,marker=marker,xdata=[list(x)for x in xdata]if mode=='used'else [],asset_id=asset['id']))
            jobs.append(dict(id=identity+'/'+mode,input='/work/cases/'+identity+'/'+mode+'/source.dxf',
                output='/work/cases/'+identity+'/'+mode+'/returned.dxf',format=FORMATS[version]))
    write(work/'CASES.json',cases);write(work/'export.json',dict(jobs=jobs));write(work/'fresh.json',dict(jobs=jobs,read_only=True))
    shutil.copyfile(HERE/'native_payload.js',work/'native_payload.js')
    controller=(HERE/'run_native.py').read_text(encoding='utf-8').replace('native_boundaries.js','native_payload.js')
    (work/'run_native.py').write_text(controller,encoding='utf-8',newline='\n')
    (work/'.configuration').mkdir();config=ROOT/'attempt-1/.configuration/QCAD3.conf';shutil.copyfile(config,work/'.configuration/QCAD3.conf')
    inputs={p.relative_to(work).as_posix():sha(p)for p in work.rglob('*')if p.is_file() and '.configuration'not in p.parts}
    write(work/'FREEZE.json',dict(inputs=inputs,configuration_sha256=sha(config),exposure='Twelve authored revisions of six exposed inputs'))
    shutil.copyfile(work/'FREEZE.json',HERE/'PAYLOAD-FREEZE.json')
    print('Frozen twelve paired payload sources, exact candidates and native jobs')
if __name__=='__main__':main()
