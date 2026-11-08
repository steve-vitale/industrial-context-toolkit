"""Finish the frozen exposed camera controls; preserve original handles on failure."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
IMAGE='sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8'
CASES=['libre-motion','libre-power','qcad-hydraulic','qcad-mechanical','qcad-template']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def command(args,p):
    r=subprocess.run(args,text=True,capture_output=True)
    write(p,dict(command=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr))
    if r.returncode:raise ValueError('Command failed: '+str(p))
    return r.stdout

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('work',type=Path);p.add_argument('configuration',type=Path);a=p.parse_args()
    root=a.work/'camera-1';records=root/'remaining-batch';records.mkdir()
    preparer=HERE.parent/'prepare_camera19.py'
    paths=[Path(__file__),HERE/'PLAN.md',preparer,HERE.parent/'native-ui-pairs-19/camera_repeat.py']
    methods={str(p.resolve()):sha(p)for p in paths}
    write(records/'FREEZE.json',dict(methods=methods,cases=CASES,image=IMAGE,max_running=3,scope='Remaining five original exposed camera cases; no restart'))
    pending=list(CASES);running={};completed=[]
    while pending or running:
        for case,name in list(running.items()):
            job=root/case
            s=json.loads(command(['docker','inspect',name],records/(case+'-inspection.json')))[0]
            if (job/'ui/FAILURE.json').exists():raise ValueError('Controller failed; preserve same native handle: '+name)
            if s['State']['Status']=='exited':
                if s['State']['ExitCode']!=0 or not(job/'ui/RESULT.json').exists():raise ValueError('Native job failed: '+name)
                completed.append(case);del running[case];print('complete',case,flush=True)
        while pending and len(running)<3:
            for path,pin in methods.items():
                if sha(Path(path))!=pin:raise ValueError('Frozen batch method changed')
            case=pending.pop(0);job=root/case;name='ict-cad-ui20-camera-'+case
            command([sys.executable,str(preparer),str(a.work),case,str(job),str(a.configuration)],records/(case+'-stage.json'))
            args=['docker','run','-d','--name',name,'--network','none','--user','1001:1001','--memory','3g','--cpus','2','--shm-size','256m','--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges','--mount','type=bind,source='+job.resolve().as_posix()+',target=/work','--entrypoint','dbus-run-session',IMAGE,'--','python3','/work/launch_case.py']
            command(args,records/(case+'-launch.json'));running[case]=name;print('started',case,flush=True)
        write(records/'PROGRESS.json',dict(completed=completed,running=running,pending=pending,whole_cad_qualified=False))
        if running:time.sleep(5)
    write(records/'COMPLETE.json',dict(completed=completed,whole_cad_qualified=False))
if __name__=='__main__':main()
