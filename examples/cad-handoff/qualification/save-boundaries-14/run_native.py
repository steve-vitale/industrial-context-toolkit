"""Run frozen version/object boundary controls serially; exact settings selection and terminal process evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path('/work')
CONFIG=Path('/home/cad/.config/QCAD/QCAD3.conf')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')

def main():
    frozen=json.loads((ROOT/'FREEZE.json').read_bytes())
    for name,pin in frozen['inputs'].items():
        if sha(ROOT/name)!=pin:raise ValueError('Changed frozen input: '+name)
    supplied=ROOT/'.configuration/QCAD3.conf'
    if sha(supplied)!=frozen['configuration_sha256']:raise ValueError('Supplied settings differ')
    CONFIG.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(supplied,CONFIG)
    if sha(CONFIG)!=sha(supplied):raise ValueError('Installed settings differ')
    out=ROOT/'native';out.mkdir(exist_ok=False)
    commands=[]
    for name in ('export','fresh'):
        command=['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances',
            '-config',str(CONFIG),'-font-substitution','Standard','DejaVu Sans',
            '-autostart','/work/native_boundaries.js','-m',str(ROOT/(name+'.json'))]
        row=dict(id=name,command=command,configuration_sha256_before=sha(CONFIG),started=datetime.now(timezone.utc).isoformat())
        commands.append(row);write(out/'commands.json',commands);print('START',name,flush=True)
        with (out/(name+'.stdout')).open('wb') as stdout,(out/(name+'.stderr')).open('wb') as stderr:
            child=subprocess.Popen(command,cwd='/opt/qcad',stdout=stdout,stderr=stderr)
            row['pid']=child.pid;write(out/'commands.json',commands);row['exit']=child.wait()
        row.update(configuration_sha256_after=sha(CONFIG),finished=datetime.now(timezone.utc).isoformat());write(out/'commands.json',commands)
        if row['exit']:raise ValueError('Native process failed')
        lines=(out/(name+'.stdout')).read_text(encoding='utf-8').splitlines()
        rows=[json.loads(s.split(' ',1)[1]) for s in lines if s.startswith('ICT_BOUND14 ')]
        jobs=json.loads((ROOT/(name+'.json')).read_bytes())['jobs']
        if [r['id'] for r in rows]!=[j['id'] for j in jobs] or any('error' in r for r in rows):raise ValueError('Native incomplete/error')
        if any('ICT_BOUND14_FATAL ' in s for s in lines):raise ValueError('Native fatal')
        profile=[json.loads(s.split(' ',1)[1]) for s in lines if s.startswith('ICT_BOUND14_PROFILE ')]
        if len(profile)!=1 or profile[0]['configuration_file']!=str(CONFIG):raise ValueError('Native settings self-report differs')
        if ('absConfigFile: "'+str(CONFIG)+'"').encode() not in (out/(name+'.stderr')).read_bytes():raise ValueError('Native selected config missing')
        print('END',name,flush=True)
    for name,pin in frozen['inputs'].items():
        if sha(ROOT/name)!=pin:raise ValueError('Native changed supplied input: '+name)
    write(out/'COMPLETE.json',dict(commands=len(commands),jobs=len(jobs),inputs_unchanged=True,whole_cad_qualified=False))

if __name__=='__main__':main()
