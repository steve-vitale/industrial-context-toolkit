"""Run the declared exposed UI cohort in isolated containers; never restart a failed/live job."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
IMAGE='sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8'
CASES=['libre-air-water','libre-motion','libre-power','qcad-hydraulic','qcad-mechanical','qcad-template']
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def command(args,record):
    r=subprocess.run(args,capture_output=True,text=True);write(record,dict(command=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr))
    if r.returncode:raise ValueError('Command failed, retained at '+str(record))
    return r.stdout
def state(name):
    r=subprocess.run(['docker','inspect',name],capture_output=True,text=True)
    if r.returncode:raise ValueError('Native handle missing: '+name+' '+r.stderr)
    return json.loads(r.stdout)[0]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('cases',type=Path);p.add_argument('jobs',type=Path);p.add_argument('configuration',type=Path)
    a=p.parse_args();records=a.jobs/'batch';records.mkdir();pending=[];running={};completed=set()
    selected=[]
    for case in CASES:
        for role in ('baseline','edited','receiving'):
            key=case+'-'+role;existing=case=='libre-air-water'and role in ('baseline','edited')
            container='ict-cad-ui19-air-'+role+'4' if existing else 'ict-cad-ui19-'+key+'4'
            row=dict(key=key,case=case,role=role,container=container)
            selected.append(row)
            if existing:running[key]=row
            else:
                if (a.jobs/key).exists():raise ValueError('Unregistered existing job; do not reuse')
                pending.append(row)
    write(records/'COHORT.json',dict(jobs=selected,method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),image=IMAGE,max_running=3,scope='Exposed development, no restart; pre-existing air baseline/edit processes explicitly adopted'))
    while pending or running:
        for key,row in list(running.items()):
            root=a.jobs/key;s=state(row['container']);write(records/(key+'-inspect.json'),s)
            failure=root/'ui/FAILURE.json'
            if failure.exists():raise ValueError('Controller failed; preserve same live handle: '+row['container'])
            if s['State']['Status']=='exited':
                if s['State']['ExitCode']!=0 or not(root/'ui/RESULT.json').exists():raise ValueError('Native job exited without complete evidence: '+key)
                completed.add(key);del running[key];print('complete',key,flush=True)
        while len(running)<3:
            available=[r for r in pending if r['role']!='receiving' or all(r['case']+'-'+x in completed for x in ('baseline','edited'))]
            if not available:break
            row=available[0];pending.remove(row);key=row['key'];root=a.jobs/key
            command([sys.executable,str(HERE/'prepare.py'),'job',str(root),str(a.cases/row['case']),row['role'],str(a.configuration),str(a.jobs)],records/(key+'-stage.json'))
            args=['docker','run','-d','--name',row['container'],'--network','none','--user','1001:1001','--memory','3g','--cpus','2','--shm-size','256m','--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges','--mount','type=bind,source='+root.resolve().as_posix()+',target=/work','--entrypoint','dbus-run-session',IMAGE,'--','python3','/work/launch_case.py']
            command(args,records/(key+'-launch.json'));running[key]=row;print('started',key,flush=True)
        write(records/'PROGRESS.json',dict(completed=sorted(completed),running=list(running),pending=[r['key']for r in pending],whole_cad_qualified=False))
        if running:time.sleep(5)
    write(records/'COMPLETE.json',dict(completed=sorted(completed),whole_cad_qualified=False))
if __name__=='__main__':main()
