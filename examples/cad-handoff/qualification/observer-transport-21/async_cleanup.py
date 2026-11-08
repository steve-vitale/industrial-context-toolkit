"""Separate cleanup of a failed signal probe that never started its helper."""
import json
from pathlib import Path
from original_workflow import Workflow, ROOT, matching, require, write

failure = json.loads((ROOT / 'native/ASYNC-FAILURE.json').read_bytes())
process = json.loads((ROOT / 'native/PROCESS.json').read_bytes())
pid = process['engine_pid']
require(Path(f'/proc/{pid}/stat').read_text().split()[21] == process['engine_start_identity'], 'Native identity changed')
require(failure['started'] is False and not (ROOT / 'native/ASYNC-HELPER-READY.json').exists(), 'Helper started; this cleanup does not apply')
children = Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
require(not children, 'Native still owns a helper; preserve it')
w = Workflow(out_name='async-separate-cleanup')
tree = w.snapshot('before-close')
require(not matching(tree, 'dialog'), 'Active dialog; preserve same native process')
windows = [r for r in w.command(['wmctrl', '-l']).splitlines() if 'Untitled 1 - QCAD Professional Trial' in r]
require(len(windows) == 1, 'Expected original unmodified unnamed window')
w.command(['wmctrl', '-ic', windows[0].split()[0]])
write(w.out / 'RESULT.json', dict(status='separate-normal-close-dispatched', native_pid=pid,
      native_start_identity=process['engine_start_identity'], original_controller_exit=process['controller_exit']))
