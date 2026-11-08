"""Prepare separate ordinary and traced GUI workdirs; keep publisher binaries/settings local."""
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-gui-scene-13')
OLD=Path('C:/Users/Steve/.cp-scratch/cad-font-views-9/default-replay-2')
CONFIG=Path('C:/Users/Steve/.cp-scratch/cad-public-validation-11/native-1/terminal-QCAD3.conf')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(CONFIG)=='2c23f1511046e1ce876753efa354185a733d88e1264713ee13cc72d735f73a6c'
expected={'source':'320f335dfce8b55b4176e7bf130a4d2a35767c60bd25b39834cf6f42473991a0',
          'candidate':'49b483ae1782527d2aa68db8fa350a0b076e858519ead2bd145b14d213e20c5e'}
guard='''
var selected=String(RSettings.getFileName());
print('ICT_SCENE13_PROFILE '+JSON.stringify({configuration_file:selected}));
if(selected!=='/home/cad/.config/QCAD/QCAD3.conf')throw new Error('Wrong selected GUI settings');
'''
for mode in ('ordinary','observed'):
    work=ROOT/mode;work.mkdir(exist_ok=False)
    (work/'receipts').mkdir();(work/'.configuration').mkdir()
    shutil.copyfile(CONFIG,work/'.configuration/QCAD3.conf')
    for role,h in expected.items():
        original=OLD/f'validation-long-{role}.dxf';assert sha(original)==h
        shutil.copyfile(original,work/original.name)
    shutil.copyfile(HERE/'desktop.sh',work/'desktop.sh')
    shutil.copyfile(ROOT/'build/paint_trace.so',work/'paint_trace.so')
    listener=(OLD/'native_views.js').read_text(encoding='utf-8')
    listener=listener.replace('include("scripts/File/NewFile/NewFile.js");','include("scripts/File/NewFile/NewFile.js");'+guard)
    (work/'native_views.js').write_text(listener,encoding='utf-8',newline='\n')
    capture=(OLD/'capture.py').read_text(encoding='utf-8')
    capture=capture.replace('temporary=Path("/work/request.next.json")','Path("/work/epoch.json").write_text(json.dumps(request),encoding="utf-8")\n            temporary=Path("/work/request.next.json")')
    (work/'capture.py').write_text(capture,encoding='utf-8',newline='\n')
    requests=[dict(seq=106+i,case_id='validation-long',asset_id='__ALL__',role=role,
        source='/work/validation-long-source.dxf',candidate='/work/validation-long-candidate.dxf')for i,role in enumerate(expected)]
    (work/'requests.json').write_text(json.dumps(requests,indent=2)+'\n',encoding='utf-8')
    frozen={p.name:dict(sha256=sha(p),bytes=p.stat().st_size)for p in work.iterdir()if p.is_file()}
    frozen['.configuration/QCAD3.conf']=dict(sha256=sha(CONFIG),bytes=CONFIG.stat().st_size)
    (work/'FREEZE.json').write_text(json.dumps(dict(mode=mode,files=frozen),indent=2)+'\n',encoding='utf-8')
print('Prepared separate ordinary and observed workdirs with identical inputs/configuration')
