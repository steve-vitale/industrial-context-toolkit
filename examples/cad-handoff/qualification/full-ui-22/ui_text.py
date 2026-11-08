"""One accessible native text-control edit, exact readback and Tab; never a CAD entity API."""
import argparse
import json
import subprocess
import time
from ui_control import at, pyatspi
from ui_settle import wait_for_exact

TRACE = {}


def command(args):
    r = subprocess.run(args, capture_output=True, text=True)
    TRACE.setdefault('commands', []).append(dict(command=args, exit=r.returncode, stdout=r.stdout, stderr=r.stderr))
    if r.returncode: raise ValueError('Native input command failed')
    return r.stdout


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('path'); p.add_argument('before'); p.add_argument('after')
    a = p.parse_args()
    if any(c in a.after for c in ('\n', '\r', '\0')): raise ValueError('Single-line control value required')
    node = at(a.path); state = node.getState(); text = node.queryText()
    TRACE.update(path=a.path, name=node.name, role=node.getRoleName(), before=text.getText(0, text.characterCount),
                 expected_before=a.before, proposed=a.after, method='AT-SPI EditableText.setTextContents then exact readback and Tab')
    if TRACE['before'] != a.before: raise ValueError('Observed native before value differs')
    if not all(state.contains(s) for s in (pyatspi.STATE_ENABLED, pyatspi.STATE_SHOWING, pyatspi.STATE_EDITABLE)):
        raise ValueError('Native text control is not enabled/showing/editable')
    TRACE['focus_result'] = node.queryComponent().grabFocus()
    if TRACE['focus_result'] is not True: raise ValueError('Native focus refused')
    r = node.queryComponent().getExtents(pyatspi.DESKTOP_COORDS)
    TRACE['rectangle'] = [r.x, r.y, r.width, r.height]
    if min(r.x, r.y) < 0 or min(r.width, r.height) <= 0: raise ValueError('Native field bounds unavailable')
    command(['xdotool', 'mousemove', '--sync', str(r.x + r.width // 2), str(r.y + r.height // 2), 'click', '1'])
    time.sleep(.2)
    if not node.getState().contains(pyatspi.STATE_FOCUSED): raise ValueError('Native field did not receive focus')
    active = command(['xdotool', 'getactivewindow', 'getwindowname']).strip(); TRACE['active_window'] = active
    if active != 'Property Editor': raise ValueError('Unexpected native keyboard window')
    TRACE['editable_text_result'] = node.queryEditableText().setTextContents(a.after)
    if TRACE['editable_text_result'] is not True: raise ValueError('Accessible native text edit refused')
    TRACE['completion'] = []
    if not wait_for_exact(lambda: text.getText(0, text.characterCount), a.after, TRACE['completion'].append):
        raise ValueError('Native text did not complete exactly; no commit')
    command(['xdotool', 'key', 'Tab'])
    TRACE['tab_dispatched'] = True
    print(json.dumps(TRACE, ensure_ascii=False))


if __name__ == '__main__':
    try: main()
    except Exception as error:
        print(json.dumps(dict(error=str(error), trace=TRACE), ensure_ascii=False)); raise
