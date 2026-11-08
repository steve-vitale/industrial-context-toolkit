"""Isolated fresh QCAD process; do not kill/restart it when the UI controller fails."""
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
def main():
    frozen=json.loads((ROOT/'JOB-FREEZE.json').read_bytes())
    for n,pin in frozen['files'].items():
        if sha(ROOT/n)!=pin:raise ValueError('Frozen input differs: '+n)
    mailbox=Path('/home/cad/ict-mailbox-21');mailbox.mkdir(mode=0o700)
    for name in ('requests','replies','errors','events','controls','staging'):(mailbox/name).mkdir(mode=0o700)
    for name in ('requests','replies','errors','events','controls'):(mailbox/'staging'/name).mkdir(mode=0o700)
    CONFIG.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'.configuration/QCAD3.conf',CONFIG)
    (ROOT/'dbus-address.txt').write_text(os.environ['DBUS_SESSION_BUS_ADDRESS'])
    out=ROOT/'native';out.mkdir();(ROOT/'replies').mkdir()
    xvfb_log=(out/'xvfb.log').open('wb');wm_log=(out/'openbox.log').open('wb')
    x=subprocess.Popen(['Xvfb',':99','-screen','0','2400x1400x24','-nolisten','tcp'],stdout=xvfb_log,stderr=xvfb_log)
    for _ in range(100):
        if subprocess.run(['xdpyinfo','-display',':99'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
        if x.poll()is not None:raise ValueError('Display terminated')
        time.sleep(.2)
    else:raise ValueError('Display not observed; retain without restart')
    wm=subprocess.Popen(['openbox'],stdout=wm_log,stderr=wm_log)
    cmd=['/opt/qcad/qcad','-allow-multiple-instances','-config',str(CONFIG),'-font-substitution','Standard','DejaVu Sans',
         '-exec','/work/observe_case.js']
    row=dict(command=cmd,configuration_before=sha(CONFIG),started=datetime.now(timezone.utc).isoformat(),job=json.loads((ROOT/'job.json').read_bytes()))
    with(out/'stdout.txt').open('wb')as stdout,(out/'stderr.txt').open('wb')as stderr:
        p=subprocess.Popen(cmd,cwd='/opt/qcad',stdout=stdout,stderr=stderr);row['pid']=p.pid;write(out/'PROCESS.json',row)
        # /opt/qcad/qcad is a shell wrapper. Faults must target its actual Qt child.
        for _ in range(100):
            children=Path('/proc/'+str(p.pid)+'/task/'+str(p.pid)+'/children').read_text().split()
            engines=[]
            for child in children:
                arguments=Path('/proc/'+child+'/cmdline').read_bytes().split(b'\0')
                if arguments and arguments[0]==b'/opt/qcad/qcad-bin':engines.append(int(child))
            if len(engines)==1:break
            time.sleep(.1)
        else:
            row['engine_observation_error']='Actual Qt child not uniquely observed; same process retained';write(out/'PROCESS.json',row)
            p.wait();raise ValueError(row['engine_observation_error'])
        row['engine_pid']=engines[0]
        row['engine_start_identity']=Path('/proc/'+str(engines[0])+'/stat').read_text().split()[21]
        write(out/'PROCESS.json',row)
        with(out/'controller.stdout').open('wb')as co,(out/'controller.stderr').open('wb')as ce:
            controller=subprocess.Popen(['python3','/work/workflow.py'],stdout=co,stderr=ce)
            row['controller_pid']=controller.pid;write(out/'PROCESS.json',row)
            row['controller_exit']=controller.wait();write(out/'PROCESS.json',row)
        # A failed controller is not proof of native termination. Leave the same app/display live.
        row['exit']=p.wait()
    row.update(configuration_after=sha(CONFIG),finished=datetime.now(timezone.utc).isoformat());write(out/'PROCESS.json',row)
    wm.terminate();wm.wait();x.terminate();x.wait();wm_log.close();xvfb_log.close()
    for n,pin in frozen['files'].items():
        if sha(ROOT/n)!=pin:raise ValueError('Native changed frozen input: '+n)
    return int(row['controller_exit']!=0 or row['exit']!=0)
if __name__=='__main__':raise SystemExit(main())
