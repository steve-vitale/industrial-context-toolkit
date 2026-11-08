"""Keep the ambiguity failure intact; replace only the successor probe."""
from pathlib import Path
import json
import hashlib
import shutil
HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-record-paths-15')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    prior=ROOT/'attempt-1';work=ROOT/'attempt-2';work.mkdir(exist_ok=False)
    old=json.loads((prior/'FREEZE.json').read_bytes())
    for name,pin in old['inputs'].items():
        assert sha(prior/name)==pin
        target=work/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(prior/name,target)
    shutil.copyfile(HERE/'native_records_explicit.js',work/'native_records.js')
    freeze=dict(old,inputs=dict(old['inputs']));freeze['inputs']['native_records.js']=sha(work/'native_records.js')
    for name,pin in freeze['inputs'].items():assert sha(work/name)==pin
    (work/'.configuration').mkdir();shutil.copyfile(prior/'.configuration/QCAD3.conf',work/'.configuration/QCAD3.conf')
    assert sha(work/'.configuration/QCAD3.conf')==freeze['configuration_sha256']
    data=(json.dumps(freeze,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
    (work/'FREEZE.json').write_bytes(data);(HERE/'EXPLICIT-FREEZE.json').write_bytes(data)
    print('Frozen separate exact-filter successor; all other input bytes unchanged')
if __name__=='__main__':main()
