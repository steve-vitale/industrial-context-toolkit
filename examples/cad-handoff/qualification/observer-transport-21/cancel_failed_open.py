"""Separate recovery: cancel one uncommitted Open dialog, then use the frozen normal cleanup."""
import json
from pathlib import Path
import subprocess
from original_workflow import Workflow, ROOT, matching, one, require

failure=json.loads((ROOT/'ui/FAILURE.json').read_bytes())
require('Native command failed' in failure['traceback'],'Unexpected original failure')
state=Path('/proc/'+str(failure['native_pid'])+'/stat').read_text().split()
require(state[21]==failure['native_start_identity'],'Same Qt child identity changed')
w=Workflow(out_name='cancel-open-cleanup')
t=w.snapshot('before');dialog=one(t,'dialog','Open Drawing')
field=one(dialog,'text','File name:')
require(field['text']=='/work/source.dxf','Observed later native filename differs; refuse cleanup assumption')
require([n['name']for n in matching(t,'dialog')]==['Open Drawing'],'Unexpected dialog inventory')
w.control('press',one(dialog,'push button','Cancel'))
w.wait(lambda t:not matching(t,'dialog'),'Separate cancellation completed');w.snapshot('after')
args=['python3','/work/cleanup.py'];result=subprocess.run(args,capture_output=True,text=True)
w.record('separate_cleanup',command=args,exit=result.returncode,stdout=result.stdout,stderr=result.stderr)
require(result.returncode==0,'Frozen stop/close cleanup failed; preserve same process')
