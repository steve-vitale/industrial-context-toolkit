"""Compile only the authored forwarder with the existing pinned compiler image; retain real outcome."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',required=True,type=Path);p.add_argument('--name',required=True)
    args=p.parse_args();root=args.work.resolve()
    if (root/'COMPILE.json').exists():raise ValueError('Retain previous compilation')
    image='sha256:10eed1af091798666a93fbe6e2cf438bdd3a950cb87d12487eea83ab0859e85e'
    command=['docker','run','--name',args.name,'--network','none','--read-only','--memory','2g','--cpus','2',
             '--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges','--user','1001:1001',
             '--tmpfs','/tmp:rw,nosuid,nodev,size=256m','--mount','type=bind,src='+str(root)+',dst=/work',
             '--entrypoint','/usr/bin/g++',image,'-shared','-fPIC','-O2','-std=c++17','-Wall','-Wextra','-Werror',
             '/work/layout_ctor.cpp','-o','/work/layout_ctor.so','-ldl']
    row={'command':command,'started':datetime.now(timezone.utc).isoformat(),'source_sha256':hashlib.sha256((root/'layout_ctor.cpp').read_bytes()).hexdigest()}
    (root/'COMPILE.json').write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
    result=subprocess.run(command,capture_output=True)
    (root/'compile.stdout').write_bytes(result.stdout);(root/'compile.stderr').write_bytes(result.stderr)
    row.update(exit=result.returncode,finished=datetime.now(timezone.utc).isoformat())
    if not result.returncode:row['helper_sha256']=hashlib.sha256((root/'layout_ctor.so').read_bytes()).hexdigest()
    (root/'COMPILE.json').write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(row,indent=2));raise SystemExit(result.returncode)

if __name__=='__main__':main()
