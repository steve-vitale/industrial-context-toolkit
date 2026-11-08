"""Run the six frozen full-GUI processes once. Observation timeouts never restart CAD."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT=Path('/work');CONFIG=Path('/home/cad/.config/QCAD/QCAD3.conf')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def stamp():return datetime.now(timezone.utc).isoformat()

def main():
    freeze=json.loads((ROOT/'FREEZE.json').read_bytes())
    for name,pin in freeze['inputs'].items():
        if sha(ROOT/name)!=pin:raise ValueError('Frozen input differs: '+name)
    if sha(ROOT/'layout_ctor.so')!=freeze['helper_sha256']or sha(Path('/opt/qcad/libqcadcore.so'))!=freeze['library_sha256']:
        raise ValueError('Native helper/library differs')
    out=ROOT/'native';out.mkdir(exist_ok=False);CONFIG.parent.mkdir(parents=True,exist_ok=True)
    xvfb_log=(out/'xvfb.log').open('wb');wm_log=(out/'openbox.log').open('wb')
    xvfb=subprocess.Popen(['Xvfb',':99','-screen','0','2400x1400x24','-nolisten','tcp'],stdout=xvfb_log,stderr=xvfb_log)
    wm=None;commands=[]
    try:
        for n in range(100):
            if subprocess.run(['xdpyinfo','-display',':99'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
            if xvfb.poll()is not None:raise ValueError('Xvfb terminated')
            time.sleep(.2)
        else:raise ValueError('Display readiness not observed; retain without restart')
        wm=subprocess.Popen(['openbox'],stdout=wm_log,stderr=wm_log)
        for process in freeze['processes']:
            shutil.copyfile(ROOT/'.configuration/QCAD3.conf',CONFIG)
            write(ROOT/'current.json',process);name=process['route']+'-'+process['mode']
            cmd=['/opt/qcad/qcad','-allow-multiple-instances','-config',str(CONFIG),
                 '-font-substitution','Standard','DejaVu Sans','-exec','/work/native_complete.js']
            env=dict(os.environ,LD_PRELOAD='/work/layout_ctor.so',LD_LIBRARY_PATH='/opt/qcad',ICT_LAYOUT17_MODE=process['mode'])
            row=dict(process,command=cmd,environment={k:env[k]for k in ('LD_PRELOAD','LD_LIBRARY_PATH','ICT_LAYOUT17_MODE')},
                     started=stamp(),configuration_before=sha(CONFIG));commands.append(row);write(out/'commands.json',commands)
            print('START',name,flush=True)
            with(out/(name+'.stdout')).open('wb')as stdout,(out/(name+'.stderr')).open('wb')as stderr:
                proc=subprocess.Popen(cmd,cwd='/opt/qcad',env=env,stdout=stdout,stderr=stderr)
                row['pid']=proc.pid;write(out/'commands.json',commands);row['exit']=proc.wait()
            row.update(finished=stamp(),configuration_after=sha(CONFIG));write(out/'commands.json',commands)
            print('END',name,row['exit'],flush=True)
            text=(out/(name+'.stdout')).read_text(encoding='utf-8')
            if row['exit']or 'ICT_OPEN18_FATAL 'in text:raise ValueError('Native process failed; retain without restart')
            records=[json.loads(s.split(' ',1)[1])for s in text.splitlines()if s.startswith('ICT_OPEN18_JOB ')]
            if len(records)!=14 or any('error'in r for r in records):raise ValueError('Native job failed; retain without restart')
        for name,pin in freeze['inputs'].items():
            if sha(ROOT/name)!=pin:raise ValueError('Native changed frozen input: '+name)
        write(out/'COMPLETE.json',dict(processes=6,jobs=84,inputs_unchanged=True,cad_files_saved=0,whole_cad_qualified=False))
    finally:
        if wm is not None:wm.terminate();wm.wait()
        xvfb.terminate();xvfb.wait();xvfb_log.close();wm_log.close()

if __name__=='__main__':main()
