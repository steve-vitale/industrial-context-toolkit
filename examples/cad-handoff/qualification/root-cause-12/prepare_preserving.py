"""Stage a separately frozen explicit preserve-attributes intervention."""
import argparse
import hashlib
from pathlib import Path
import prepare

HERE=Path(__file__).resolve().parent

def stage(previous,destination):
    frozen=prepare.prepare(previous,destination)
    original=(HERE/'native_probe.js').read_text(encoding='utf-8')
    if original.count('op.addObject(a);')!=1:raise ValueError('Intervention call ambiguous')
    changed=original.replace('op.addObject(a);','op.addObject(a,false);')
    changed=changed.replace('tag:String(e.getTag()),text:', 'layer_id:String(e.getLayerId()),tag:String(e.getTag()),text:')
    (destination/'native_probe.js').write_text(changed,encoding='utf-8',newline='\n')
    frozen['inputs']['native_probe.js']=prepare.sha(destination/'native_probe.js')
    frozen['intervention']='addObject(a,false); additionally observe native layer_id'
    for name in ('PRESERVE-ATTRIBUTES-PLAN.md','prepare_preserving.py'):
        frozen['methods_sha256_lf'][name]=hashlib.sha256((HERE/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    prepare.write(destination/'FREEZE.json',frozen)
    prepare.write(HERE/'PRESERVE-FREEZE.json',frozen)
    print('Frozen preserve-attributes intervention; 48 exports / 48 fresh reads')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('previous',type=Path);ap.add_argument('destination',type=Path);a=ap.parse_args()
    stage(a.previous,a.destination)
