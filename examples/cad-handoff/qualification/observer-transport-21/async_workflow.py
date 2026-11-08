"""Exercise native UI while the same asynchronous helper is deliberately live."""
import json
from pathlib import Path
import time
import traceback
from original_workflow import Workflow, ROOT, matching, one, require, write


def read_when_ready(path, seconds=15):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if (ROOT / 'native/ASYNC-FAILURE.json').exists():
            raise ValueError('Native async probe failed; preserve same process')
        try: return json.loads(path.read_bytes())
        except (FileNotFoundError, json.JSONDecodeError): time.sleep(.1)
    raise TimeoutError('Observation deadline; preserve same process')


def require_live(helper):
    stat = Path(f'/proc/{helper["pid"]}/stat')
    require(stat.read_text().split()[2] not in ('Z', 'X'), 'Helper already terminal before release')
    require(not (ROOT / 'native/ASYNC.json').exists(), 'Native finished before UI observations/release')


w = Workflow()
try:
    w.wait(lambda t: bool(matching(t, 'dialog', 'Trial')), 'Trial', 60)
    w.snapshot('trial')
    t = w.wait(lambda t: any(n['enabled'] for n in matching(one(t, 'dialog', 'Trial'), 'push button', 'OK')), 'Trial OK enabled', 40)
    w.control('press', one(one(t, 'dialog', 'Trial'), 'push button', 'OK'))
    w.wait(lambda t: not matching(t, 'dialog'), 'Trial dismissed'); w.snapshot('ready')
    with (ROOT / 'native/ASYNC-START.json').open('x', encoding='utf-8') as stream: json.dump(dict(scope='probe-only'), stream)
    helper = read_when_ready(ROOT / 'native/ASYNC-HELPER-READY.json')
    process = json.loads((ROOT / 'native/PROCESS.json').read_bytes())
    require(helper['uid'] == 1001 and helper['qt_parent_pid'] == process['engine_pid'], 'Helper/native ownership differs')
    require_live(helper); w.record('async_helper_live_before_ui', helper=helper)
    w.command(['xdotool', 'key', '--clearmodifiers', 'ctrl+o'])
    t = w.wait(lambda t: bool(matching(t, 'dialog', 'Open Drawing')), 'Open Drawing')
    dialog = one(t, 'dialog', 'Open Drawing'); w.snapshot('open-dialog')
    w.control('type', one(dialog, 'text', 'File name:'), '/work/source.dxf')
    t = w.snapshot('filename-completed')
    require(one(one(t, 'dialog', 'Open Drawing'), 'text', 'File name:')['text'] == '/work/source.dxf', 'Exact filename completion missing')
    require_live(helper); w.record('async_helper_live_after_text', helper=helper)
    w.control('press', one(one(t, 'dialog', 'Open Drawing'), 'push button', 'Cancel'))
    w.wait(lambda t: not matching(t, 'dialog'), 'Open Drawing canceled'); w.snapshot('canceled')
    require_live(helper); w.record('async_helper_live_after_cancel', helper=helper)
    with (ROOT / 'native/ASYNC-RELEASE.json').open('x', encoding='utf-8') as stream: json.dump(dict(helper=helper), stream)
    w.record('async_release', helper=helper)
    report = read_when_ready(ROOT / 'native/ASYNC.json')
    require(report['started'] and report['exit'] == report['exit_status'] == 0, 'Actual async process completion differs')
    require(json.loads(report['stdout']) == dict(helper, value='\u00b5 valve') and report['stderr'] == 'async probe stderr\n', 'Exact UTF-8 process output differs')
    require(report['ticks_at_finish'] - report['ticks_at_start'] >= 20, 'Native event loop did not keep ticking')
    require(report['filename'] == '' and report['modified'] is False, 'Probe opened/modified a drawing')
    w.record('async_probe', report=report)
    windows = [r for r in w.command(['wmctrl', '-l']).splitlines() if 'Untitled 1 - QCAD Professional Trial' in r]
    require(len(windows) == 1, 'Ambiguous unmodified native window')
    w.command(['wmctrl', '-ic', windows[0].split()[0]])
    write(w.out / 'RESULT.json', dict(status='async-capability-observed', report=report, whole_cad_qualified=False))
except Exception:
    write(w.out / 'FAILURE.json', dict(traceback=traceback.format_exc(), scope='Probe failed; same native/helper process retained'))
    raise
