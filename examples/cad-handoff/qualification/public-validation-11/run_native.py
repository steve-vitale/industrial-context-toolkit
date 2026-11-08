"""Explicit-profile serial native execution; retained process handles, no timeout/restart."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

ROOT=Path('/work')
CONFIG=Path('/home/cad/.config/QCAD/QCAD3.conf')


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data): path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


def main():
    manifest=json.loads((ROOT/'NATIVE.json').read_bytes())
    out=ROOT/'native';out.mkdir(exist_ok=False)
    supplied=ROOT/'.local-configuration/QCAD3.conf'
    if sha(supplied)!=manifest['configuration_sha256']: raise ValueError('Configuration identity mismatch')
    CONFIG.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(supplied,CONFIG)
    if sha(CONFIG)!=sha(supplied): raise ValueError('Installed configuration differs')
    for name,pin in manifest['inputs'].items():
        if sha(ROOT/name)!=pin: raise ValueError('Frozen native input differs: '+name)
    records=[]
    base=['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances','-config',str(CONFIG),
          '-font-substitution','Standard','DejaVu Sans','-autostart','/work/native_profile.js']
    for identity,mode,path in [('edit-save','batch','BATCH.json'),('fresh-readback','batch','FRESH.json'),('bounds','bounds','BATCH.json')]:
        row=dict(id=identity,command=base+['-mode',mode,'-m',str(ROOT/path)],
                 started=datetime.now(timezone.utc).isoformat(),configuration_sha256_before=sha(CONFIG))
        records.append(row);write(out/'commands.json',records);print('START',identity,flush=True)
        with (out/(identity+'.stdout')).open('wb') as stdout,(out/(identity+'.stderr')).open('wb') as stderr:
            child=subprocess.Popen(row['command'],cwd='/opt/qcad',stdout=stdout,stderr=stderr)
            row['pid']=child.pid;write(out/'commands.json',records)
            row['exit']=child.wait()
        row.update(finished=datetime.now(timezone.utc).isoformat(),configuration_sha256_after=sha(CONFIG))
        write(out/'commands.json',records)
        if row['exit']: raise ValueError('Native process failed: '+identity)
        if ('absConfigFile: "'+str(CONFIG)+'"').encode() not in (out/(identity+'.stderr')).read_bytes():
            raise ValueError('Missing selected configuration stderr: '+identity)
        lines=(out/(identity+'.stdout')).read_text(encoding='utf-8').splitlines()
        prefix='ICT_VIEW_BOUNDS ' if mode=='bounds' else 'ICT_QUAL_NATIVE '
        values=[json.loads(line[len(prefix):]) for line in lines if line.startswith(prefix)]
        expected=json.loads((ROOT/path).read_bytes())['cases']
        if [v['id'] for v in values]!=[c['id'] for c in expected]: raise ValueError('Native case coverage differs')
        if any(any(k.endswith('error') for k in v) for v in values): raise ValueError('Native case reported error; retain and stop')
        if not any(line.startswith('ICT_TRANSFER11_PROFILE ') and json.loads(line.split(' ',1)[1])['configuration_file']==str(CONFIG) for line in lines):
            raise ValueError('Native settings self-report missing')
        print('END',identity,flush=True)
    if any(sha(ROOT/name)!=pin for name,pin in manifest['inputs'].items()): raise ValueError('Native changed supplied input')
    write(out/'COMPLETE.json',dict(commands=len(records),input_unchanged=True,whole_cad_qualified=False,
          scope='Native API edit/save/document reopen plus fresh-process reads and bounds; no UI/render acceptance'))


if __name__=='__main__':main()
