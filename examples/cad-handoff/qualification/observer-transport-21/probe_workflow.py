"""Observe the exact capability probe and dismiss/close the native UI normally."""
import json
import time
import traceback
from original_workflow import Workflow, ROOT, matching, one, require, write

w = Workflow()
try:
    w.wait(lambda t: bool(matching(t, 'dialog', 'Trial')), 'Trial', 60)
    w.snapshot('trial')
    t = w.wait(lambda t: any(n['enabled'] for n in matching(one(t, 'dialog', 'Trial'), 'push button', 'OK')), 'Trial OK enabled', 40)
    w.control('press', one(one(t, 'dialog', 'Trial'), 'push button', 'OK'))
    w.wait(lambda t: not matching(t, 'dialog'), 'Trial dismissed'); w.snapshot('ready')
    report = None
    for _ in range(200):
        try: report = json.loads((ROOT / 'native/BINDINGS.json').read_bytes())
        except (FileNotFoundError, json.JSONDecodeError): time.sleep(.1); continue
        break
    require(report is not None, 'Binding probe missing; same native process retained')
    w.record('binding_probe', report=report)
    require(report['filename'] == '' and report['modified'] is False, 'Capability probe modified/opened document')
    windows = [r for r in w.command(['wmctrl', '-l']).splitlines() if 'Untitled 1 - QCAD Professional Trial' in r]
    require(len(windows) == 1, 'Ambiguous unmodified native probe window')
    w.command(['wmctrl', '-ic', windows[0].split()[0]])
    write(w.out / 'RESULT.json', dict(status='capability-observed', report=report, whole_cad_qualified=False))
except Exception:
    write(w.out / 'FAILURE.json', dict(traceback=traceback.format_exc(), scope='Probe failed; same process retained'))
    raise
