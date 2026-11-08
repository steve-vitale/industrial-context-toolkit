"""Freeze native block-name intervention with exact earlier source bytes."""
import hashlib
import json
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-record-paths-15')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(v):return(json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
def main():
    prior=ROOT/'attempt-4';work=ROOT/'symbol-5';work.mkdir(exist_ok=False);jobs=[]
    original=json.loads((prior/'FREEZE.json').read_bytes())
    for namespace in('qcad','foreign'):
        name='cases/qcad-hydraulic/'+namespace+'/source.dxf';source=prior/name
        assert sha(source)==original['inputs'][name]
        target=work/'cases'/namespace/'source.dxf';target.parent.mkdir(parents=True);shutil.copyfile(source,target)
        (target.parent/'returns').mkdir()
        for label,rename in [('unchanged',None),('target',dict(before='2/2-directional valve',after='2_2-directional valve')),
                             ('unrelated',dict(before='ICT_QUAL_TEST_ANCHOR',after='ICT_QUAL_TEST_CONTROL'))]:
            jobs.append(dict(id=namespace+'/'+label,input='/work/cases/'+namespace+'/source.dxf',
                output='/work/cases/'+namespace+'/returns/'+label+'.dxf',importer='dxflib',exporter='OpenDesign',version='R15',rename=rename))
    (work/'export.json').write_bytes(enc(dict(jobs=jobs)));(work/'fresh.json').write_bytes(enc(dict(jobs=jobs,read_only=True)))
    shutil.copyfile(HERE/'native_records_symbol.js',work/'native_records.js')
    shutil.copyfile(HERE/'run_native_complete.py',work/'run_native.py')
    (work/'.configuration').mkdir();shutil.copyfile(prior/'.configuration/QCAD3.conf',work/'.configuration/QCAD3.conf')
    freeze=dict(inputs={p.relative_to(work).as_posix():sha(p)for p in work.rglob('*')if p.is_file()and'.configuration'not in p.parts},
        configuration_sha256=sha(work/'.configuration/QCAD3.conf'),image=original['image'],exposure='Two exposed hydraulic sources; native symbol-name counterfactual')
    (work/'FREEZE.json').write_bytes(enc(freeze));(HERE/'SYMBOL-FREEZE.json').write_bytes(enc(freeze))
    print('Frozen six native name controls on two unchanged sources')
if __name__=='__main__':main()
