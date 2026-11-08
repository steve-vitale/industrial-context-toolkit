"""Receive each original camera job only after its actual container is terminal; never launch CAD."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent;PARENT=HERE.parent
CASES=['libre-air-water','libre-motion','libre-power','qcad-hydraulic','qcad-mechanical','qcad-template']

def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args,p):
    r=subprocess.run(args,capture_output=True,text=True)
    write(p,dict(command=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr))
    if r.returncode:raise ValueError('Receiving command failed; retained at '+str(p))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('work',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    a.out.mkdir();methods={str(p.resolve()):sha(p)for p in (Path(__file__),PARENT/'check_camera20.py',PARENT/'package_camera20.py',PARENT/'package_ui19.py',PARENT/'ui19_archive.py',HERE/'METHODS.json')}
    write(a.out/'FREEZE.json',dict(methods=methods,scope='Offline receiving only, original native jobs are never started or restarted'))
    completed={};pending=list(CASES)
    while pending:
        observed={}
        for case in list(pending):
            name='ict-cad-ui19-camera-air1'if case=='libre-air-water'else'ict-cad-ui20-camera-'+case
            r=subprocess.run(['docker','inspect',name],capture_output=True,text=True)
            if r.returncode:
                if 'no such object:'in r.stderr.lower() and case!='libre-air-water':
                    observed[case]=dict(status='not-yet-created',stderr=r.stderr);continue
                raise ValueError('Cannot inspect original handle '+name+': '+r.stderr)
            native=json.loads(r.stdout)[0];state=native['State'];observed[case]=dict(id=native['Id'],state=state)
            job=a.work/'camera-1'/case
            if (job/'ui/FAILURE.json').exists():raise ValueError('Original controller failed; preserve same native handle '+name)
            if state['Status']!='exited':continue
            if state['ExitCode']!=0 or state['OOMKilled']:raise ValueError('Original native container failed: '+name)
            for path,pin in methods.items():
                if sha(Path(path))!=pin:raise ValueError('Frozen receiving method changed: '+path)
            packet=a.work/'camera-packets-1'/case
            if case!='libre-air-water':command([sys.executable,str(PARENT/'package_camera20.py'),str(a.work),case,str(packet)],a.out/(case+'-package.json'))
            destination=a.out/case
            command([sys.executable,str(PARENT/'check_camera20.py'),str(packet),str(destination),'--packet'],a.out/(case+'-receive.json'))
            completed[case]=json.loads((destination/'RESULT.json').read_bytes());pending.remove(case);print('received',case,flush=True)
        write(a.out/'PROGRESS.json',dict(completed=list(completed),pending=pending,observed=observed,whole_cad_qualified=False))
        if pending:time.sleep(5)
    write(a.out/'SUMMARY.json',dict(scope='All original exposed camera repeats; no CAD saves or reserved qualification',whole_cad_qualified=False,results=[completed[case]for case in CASES]))
    print('All six original camera packets received',flush=True)
if __name__=='__main__':main()
