"""Visible-only startup acknowledgement and observed post-DONE native window close."""
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import time

ROOT=Path('C:/Users/Steve/.cp-scratch/cad-open-initialization-18/attempt-1')
CONTAINER='ict-cad-open18-1'
def run(args,allowed=(0,)):
    r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8')
    if r.returncode not in allowed:raise ValueError(str(args)+': '+r.stderr)
    return r
def visible(name):
    r=run(['docker','exec',CONTAINER,'xdotool','search','--onlyvisible','--name','^'+name+'$'],allowed=(0,1))
    return r.stdout.splitlines()
def main():
    receipts=[];closed=set();out=ROOT/'CONTROL-ACTIONS.json'
    if out.exists():raise ValueError('Retain previous controller evidence')
    while True:
        state=json.loads(run(['docker','inspect',CONTAINER]).stdout)[0]['State']
        if not state['Running']:
            print(json.dumps(dict(terminal=state,actions=len(receipts))));return
        commands=json.loads((ROOT/'native/commands.json').read_bytes());current=commands[-1]
        if 'exit'in current:time.sleep(.2);continue
        label=current['route']+'-'+current['mode'];pid=current['pid'];action=None;window=None
        trial=visible('Trial')
        if trial:
            if len(trial)!=1:raise ValueError('Ambiguous visible Trial window')
            action='acknowledge-visible-trial';window=trial[0]
        elif pid not in closed:
            stdout=(ROOT/('native/'+label+'.stdout')).read_text(encoding='utf-8')
            stderr=(ROOT/('native/'+label+'.stderr')).read_text(encoding='utf-8')
            if 'ICT_OPEN18_DONE 'in stdout and "'QCoreApplication.quit' [undefined] is not a function"in stderr:
                mains=visible('QCAD Professional Trial')
                if len(mains)!=1:raise ValueError('Expected one visible post-DONE main window')
                action='close-after-recorded-quit-exception';window=mains[0];closed.add(pid)
        if action:
            index=len(receipts);shot=f'native/control-{index}.png'
            run(['docker','exec',CONTAINER,'scrot','/work/'+shot])
            cmd=(['docker','exec',CONTAINER,'xdotool','windowactivate','--sync',window,'key','Return']
                 if action=='acknowledge-visible-trial'else['docker','exec',CONTAINER,'wmctrl','-ic',hex(int(window))])
            result=run(cmd)
            receipts.append(dict(action=action,process=label,pid=pid,at=datetime.now(timezone.utc).isoformat(),
                                 command=cmd,exit=result.returncode,stdout=result.stdout,stderr=result.stderr,screenshot=shot))
            out.write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf-8',newline='\n')
            print(action,label,flush=True)
        time.sleep(.5)
if __name__=='__main__':main()
