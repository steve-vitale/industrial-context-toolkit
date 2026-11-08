"""Host-side serial container runner; no retry, restart or termination on an observation timeout."""
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess

ROOT=Path('C:/Users/Steve/.cp-scratch/cad-save-boundaries-14')
IMAGE='sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8'
for folder,label,seed in [('payload-3','payload3',None),('seed-0-a','seed0a','0'),('seed-0-b','seed0b','0')]:
    work=ROOT/folder
    command=['docker','run','--name','ict-cad-boundaries14-'+label,'--network','none','--user','1001:1001',
        '--cpus','2','--memory','3g','--shm-size','256m','--pids-limit','256','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--mount','type=bind,source='+str(work).replace('\\','/')+',target=/work']
    if seed is not None:command+=['--env','QT_HASH_SEED='+seed]
    command+=['--entrypoint','/usr/bin/python3',IMAGE,'/work/run_native.py']
    receipt=dict(command=command,started=datetime.now(timezone.utc).isoformat())
    path=work/'HOST-RUN.json';path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print('START CONTAINER',label,flush=True)
    with(work/'HOST-STDOUT').open('wb')as stdout,(work/'HOST-STDERR').open('wb')as stderr:
        child=subprocess.Popen(command,stdout=stdout,stderr=stderr);receipt['host_pid']=child.pid
        path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');receipt['exit']=child.wait()
    receipt['finished']=datetime.now(timezone.utc).isoformat();path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print('END CONTAINER',label,receipt['exit'],flush=True)
    if receipt['exit']:raise SystemExit(receipt['exit'])
