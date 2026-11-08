"""Close completed MDI processes only after their observed null-document cleanup exception."""
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import time

ROOT=Path('C:/Users/Steve/.cp-scratch/cad-open-initialization-18/attempt-1');NAME='ict-cad-open18-1'
def run(cmd,allowed=(0,)):
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8')
    if r.returncode not in allowed:raise ValueError(str(cmd)+': '+r.stderr)
    return r
def main():
    out=ROOT/'MDI-CLOSE-ACTIONS.json';rows=[];closed=set()
    if out.exists():raise ValueError('Retain earlier controller evidence')
    while True:
        state=json.loads(run(['docker','inspect',NAME]).stdout)[0]['State']
        if not state['Running']:
            print(json.dumps(dict(terminal=state,actions=len(rows))));return
        current=json.loads((ROOT/'native/commands.json').read_bytes())[-1]
        if current['route']=='mdi'and 'exit'not in current and current['pid']not in closed:
            label=current['route']+'-'+current['mode']
            stdout=(ROOT/('native/'+label+'.stdout')).read_text(encoding='utf-8')
            stderr=(ROOT/('native/'+label+'.stderr')).read_text(encoding='utf-8')
            if 'ICT_OPEN18_DONE 'in stdout and "'ws[j].getDocument()' [null] is not an object"in stderr:
                main=run(['docker','exec',NAME,'xdotool','search','--onlyvisible','--name','^QCAD Professional Trial$']).stdout.splitlines()
                if len(main)!=1:raise ValueError('Expected one visible post-DONE MDI main window')
                screenshot='native/mdi-close-'+str(len(rows))+'.png'
                run(['docker','exec',NAME,'scrot','/work/'+screenshot])
                cmd=['docker','exec',NAME,'wmctrl','-ic',hex(int(main[0]))];result=run(cmd)
                rows.append(dict(action='close-after-recorded-null-document-exception',process=label,pid=current['pid'],
                    at=datetime.now(timezone.utc).isoformat(),command=cmd,exit=result.returncode,stdout=result.stdout,stderr=result.stderr,screenshot=screenshot))
                out.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8',newline='\n');closed.add(current['pid'])
                print('Closed completed MDI process',label,flush=True)
        time.sleep(.5)
if __name__=='__main__':main()
