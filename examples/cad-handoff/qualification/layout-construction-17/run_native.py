"""Execute the four frozen layout constructor modes once, retaining every terminal result."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path('/work')
CONFIG=Path('/home/cad/.config/QCAD/QCAD3.conf')
LIBRARY=Path('/opt/qcad/libqcadcore.so')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

def main():
    frozen=json.loads((ROOT/'FREEZE.json').read_bytes())
    for name,pin in frozen['inputs'].items():
        if sha(ROOT/name)!=pin:raise ValueError('Changed frozen file: '+name)
    if sha(LIBRARY)!=frozen['library_sha256']:raise ValueError('Different installed CAD library')
    if sha(ROOT/'layout_ctor.so')!=frozen['helper_sha256']:raise ValueError('Different compiled helper')
    if sha(ROOT/'.configuration/QCAD3.conf')!=frozen['configuration_sha256']:raise ValueError('Different settings')
    CONFIG.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'.configuration/QCAD3.conf',CONFIG)
    out=ROOT/'native';out.mkdir(exist_ok=False)
    commands=[]
    for mode in frozen['modes']:
        command=['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances',
                 '-config',str(CONFIG),'-font-substitution','Standard','DejaVu Sans',
                 '-autostart','/work/native_layouts.js']
        env=dict(os.environ,LD_PRELOAD='/work/layout_ctor.so',ICT_LAYOUT17_MODE=mode)
        row=dict(mode=mode,command=command,environment={k:env[k]for k in ('LD_PRELOAD','ICT_LAYOUT17_MODE')},
                 configuration_before=sha(CONFIG),started=datetime.now(timezone.utc).isoformat())
        commands.append(row);write(out/'commands.json',commands);print('START',mode,flush=True)
        with (out/(mode+'.stdout')).open('wb')as stdout,(out/(mode+'.stderr')).open('wb')as stderr:
            proc=subprocess.Popen(command,cwd='/opt/qcad',env=env,stdout=stdout,stderr=stderr)
            row['pid']=proc.pid;write(out/'commands.json',commands);row['exit']=proc.wait()
        row.update(configuration_after=sha(CONFIG),finished=datetime.now(timezone.utc).isoformat());write(out/'commands.json',commands)
        print('END',mode,row['exit'],flush=True)
        if row['exit']:raise ValueError('Native process failed; retain this attempt without restart')
        stdout=(out/(mode+'.stdout')).read_text(encoding='utf-8')
        stderr=(out/(mode+'.stderr')).read_text(encoding='utf-8')
        if 'ICT_LAYOUT17_FATAL ' in stdout or 'ICT_LAYOUT17_FATAL ' in stderr:raise ValueError('Native diagnostic fatal')
        if 'ICT_LAYOUT17_CTOR ' not in stderr:raise ValueError('Constructor forwarding not observed')
        rows=[json.loads(s.split(' ',1)[1])for s in stdout.splitlines()if s.startswith('ICT_LAYOUT17_JOB ')]
        jobs=json.loads((ROOT/'jobs.json').read_bytes())['jobs']
        if [r['id']for r in rows]!=[j['id']for j in jobs]:raise ValueError('Native coverage incomplete')
        if any('error'in r for r in rows):raise ValueError('Native observation error')
        profiles=[json.loads(s.split(' ',1)[1])for s in stdout.splitlines()if s.startswith('ICT_LAYOUT17_PROFILE ')]
        if len(profiles)!=1 or profiles[0]['configuration_file']!=str(CONFIG):raise ValueError('Wrong selected native settings')
        if row['configuration_before']!=frozen['configuration_sha256']or row['configuration_after']!=frozen['configuration_sha256']:raise ValueError('Settings changed')
    for name,pin in frozen['inputs'].items():
        if sha(ROOT/name)!=pin:raise ValueError('Native changed frozen input: '+name)
    write(out/'COMPLETE.json',dict(processes=len(commands),inputs_unchanged=True,whole_cad_qualified=False,
                                 scope='Diagnostic construction/import observations; no CAD file was saved'))

if __name__=='__main__':main()
