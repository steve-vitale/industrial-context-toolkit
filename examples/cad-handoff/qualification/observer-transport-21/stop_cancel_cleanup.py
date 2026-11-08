"""Second separate cleanup: acknowledge observer stop before inspecting/canceling the dialog."""
import json
from pathlib import Path
import time
from original_workflow import Workflow,ROOT,matching,one,require
from mailbox import publish,wire

failure=json.loads((ROOT/'ui/FAILURE.json').read_bytes());pid=failure['native_pid']
require(Path(f'/proc/{pid}/stat').read_text().split()[21]==failure['native_start_identity'],'Actual Qt identity changed')
w=Workflow(out_name='stop-before-cancel-cleanup')
marker=dict(protocol='ict-native-io/1',run_id=failure['run_id'],scope='cleanup-only')
publish(Path('/home/cad/ict-mailbox-21/controls/stop.json'),wire(marker));w.record('stop_marker',marker=marker)
for _ in range(150):
    console=(ROOT/'native/stdout.txt').read_text(encoding='utf-8')
    children=Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
    live=[]
    for child in children:
        try:
            if Path(f'/proc/{child}/stat').read_text().split()[2] not in ('Z','X'):live.append(int(child))
        except FileNotFoundError:pass
    if not live and ('ICT_IO_STOPPED ' in console or 'ICT_MAILBOX_FATAL ' in console):break
    time.sleep(.1)
else:raise ValueError('Transport not stopped; preserve same process')
t=w.snapshot('after-stop');dialogs=matching(t,'dialog')
w.record('observed_dialogs_after_stop',names=[r['name']for r in dialogs])
if dialogs:
    require([r['name']for r in dialogs]==['Open Drawing'],'Unexpected dialog after stop')
    dialog=one(t,'dialog','Open Drawing');require(one(dialog,'text','File name:')['text']=='/work/source.dxf','Unexpected uncommitted filename')
    w.control('press',one(dialog,'push button','Cancel'))
    w.wait(lambda t:not matching(t,'dialog'),'Cancel after transport stop')
w.snapshot('before-normal-close')
windows=[r for r in w.command(['wmctrl','-l']).splitlines() if 'Untitled 1 - QCAD Professional Trial' in r]
require(len(windows)==1,'Expected same unmodified Untitled native window')
w.command(['wmctrl','-ic',windows[0].split()[0]])
w.record('normal_cleanup_complete',native_pid=pid,native_start_identity=failure['native_start_identity'],live_helpers_before_close=live,
         scope='Original controller and first cleanup failures remain; no restart')
