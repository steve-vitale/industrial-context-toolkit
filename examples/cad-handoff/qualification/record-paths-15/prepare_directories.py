"""Prepare missing planned directories in a separate frozen successor."""
from pathlib import Path
import json
import hashlib
import shutil
HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-record-paths-15')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def encode(v):return(json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
def main():
    prior=ROOT/'attempt-2';work=ROOT/'attempt-3';work.mkdir(exist_ok=False)
    old=json.loads((prior/'FREEZE.json').read_bytes())
    for name,pin in old['inputs'].items():
        assert sha(prior/name)==pin;target=work/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(prior/name,target)
    shutil.copyfile(HERE/'native_records_observed.js',work/'native_records.js')
    shutil.copyfile(HERE/'run_native_preflight.py',work/'run_native.py')
    jobs=json.loads((work/'export.json').read_bytes())['jobs'];directories=[]
    for job in jobs:
        name=job['output'].removeprefix('/work/');assert name!=job['output']and'..'not in Path(name).parts
        (work/name).parent.mkdir(parents=True,exist_ok=True);directories.append(str(Path(name).parent).replace('\\','/'))
    directories=sorted(set(directories));(work/'REQUIRED-DIRECTORIES.json').write_bytes(encode(directories))
    freeze=dict(old,inputs=dict(old['inputs']),directories=directories)
    for name in('native_records.js','run_native.py','REQUIRED-DIRECTORIES.json'):freeze['inputs'][name]=sha(work/name)
    for name,pin in freeze['inputs'].items():assert sha(work/name)==pin
    (work/'.configuration').mkdir();shutil.copyfile(prior/'.configuration/QCAD3.conf',work/'.configuration/QCAD3.conf')
    assert sha(work/'.configuration/QCAD3.conf')==freeze['configuration_sha256']
    (work/'FREEZE.json').write_bytes(encode(freeze));(HERE/'DIRECTORY-FREEZE.json').write_bytes(encode(freeze))
    print('Frozen',len(directories),'planned output parents and successor methods; all data bytes unchanged')
if __name__=='__main__':main()
