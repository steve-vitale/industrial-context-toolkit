"""Native startup-only capability probe. Do not open drawings or save files here."""
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
    frozen=json.loads((ROOT/'FREEZE.json').read_bytes())
    for n,pin in frozen['inputs'].items():
        if sha(ROOT/n)!=pin:raise ValueError('Frozen preflight method differs: '+n)
    if sha(ROOT/'.configuration/QCAD3.conf')!=frozen['configuration_sha256']:raise ValueError('Selected settings differ')
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
         '-exec','/work/view_observer.js']
    row=dict(command=cmd,configuration_before=sha(CONFIG),started=datetime.now(timezone.utc).isoformat(),
             scope='No drawing opened or saved; startup/dialog preflight only')
    try:
        with(out/'stdout.txt').open('wb')as stdout,(out/'stderr.txt').open('wb')as stderr:
            p=subprocess.Popen(cmd,cwd='/opt/qcad',stdout=stdout,stderr=stderr);row['pid']=p.pid;write(out/'PROCESS.json',row)
            row['exit']=p.wait()
        row.update(configuration_after=sha(CONFIG),finished=datetime.now(timezone.utc).isoformat());write(out/'PROCESS.json',row)
    finally:
        wm.terminate();wm.wait();x.terminate();x.wait();wm_log.close();xvfb_log.close()
    for n,pin in frozen['inputs'].items():
        if sha(ROOT/n)!=pin:raise ValueError('Native changed frozen preflight method')
if __name__=='__main__':main()
