"""Acknowledge only the observed Linux Trial information dialog; retain every action."""
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import subprocess
import time

ROOT=Path('C:/Users/Steve/.cp-scratch/cad-open-initialization-18/attempt-1')
CONTAINER='ict-cad-open18-1'

def run(*args):
    r=subprocess.run(list(args),capture_output=True,text=True,encoding='utf-8')
    if r.returncode:raise ValueError(str(args)+': '+r.stderr)
    return r.stdout

def main():
    receipts=[];out=ROOT/'STARTUP-ACTIONS.json'
    if out.exists():raise ValueError('Retain earlier controller evidence')
    while True:
        state=json.loads(run('docker','inspect',CONTAINER))[0]['State']
        if not state['Running']:
            print(json.dumps(dict(terminal=state,acknowledgements=len(receipts))));return
        tree=run('docker','exec',CONTAINER,'xwininfo','-root','-tree')
        matches=re.findall(r'^\s*(0x[0-9a-f]+) "Trial":',tree,re.M)
        if matches:
            if len(matches)!=1:raise ValueError('Ambiguous Trial dialog')
            index=len(receipts);prefix=f'/work/native/startup-{index}'
            run('docker','exec',CONTAINER,'scrot',prefix+'.png')
            command=['docker','exec',CONTAINER,'xdotool','windowactivate','--sync',matches[0],'key','Return']
            result=run(*command)
            receipts.append(dict(at=datetime.now(timezone.utc).isoformat(),window=matches[0],tree=tree,
                                 command=command,exit=0,stdout=result,screenshot='native/startup-'+str(index)+'.png'))
            out.write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf-8',newline='\n')
            print('Acknowledged observed Trial information',index,flush=True)
        time.sleep(1)

if __name__=='__main__':main()
