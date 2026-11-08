"""Freeze complete-coverage diagnostics with unchanged sources and preserved failures."""
from pathlib import Path
import json
import hashlib
import shutil
HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-record-paths-15')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(v):return(json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
def main():
    prior=ROOT/'attempt-3';work=ROOT/'attempt-4';work.mkdir(exist_ok=False)
    old=json.loads((prior/'FREEZE.json').read_bytes())
    for name,pin in old['inputs'].items():
        assert sha(prior/name)==pin;target=work/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(prior/name,target)
    for directory in old['directories']:(work/directory).mkdir(parents=True,exist_ok=True)
    for source,target in [('native_records_complete.js','native_records.js'),('run_native_complete.py','run_native.py')]:shutil.copyfile(HERE/source,work/target)
    freeze=dict(old,inputs=dict(old['inputs']))
    for name in('native_records.js','run_native.py'):freeze['inputs'][name]=sha(work/name)
    (work/'.configuration').mkdir();shutil.copyfile(prior/'.configuration/QCAD3.conf',work/'.configuration/QCAD3.conf')
    assert sha(work/'.configuration/QCAD3.conf')==freeze['configuration_sha256']
    for name,pin in freeze['inputs'].items():assert sha(work/name)==pin
    (work/'FREEZE.json').write_bytes(enc(freeze));(HERE/'COMPLETE-FREEZE.json').write_bytes(enc(freeze))
    print('Frozen complete-coverage successor; sources/candidates/plans/routes unchanged')
if __name__=='__main__':main()
