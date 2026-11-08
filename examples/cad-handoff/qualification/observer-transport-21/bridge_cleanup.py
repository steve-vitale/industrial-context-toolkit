"""Separate acknowledged same-process transport stop and normal UI cleanup after failure."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from mailbox import publish, wire

ROOT = Path('/work'); MAILBOX = Path('/home/cad/ict-mailbox-21')
os.environ['DBUS_SESSION_BUS_ADDRESS'] = (ROOT / 'dbus-address.txt').read_text().strip()
from original_workflow import tree, matching, write, require

failure = json.loads((ROOT / 'ui/FAILURE.json').read_bytes())
pid = failure['native_pid']; identity = failure['native_start_identity']
state = Path(f'/proc/{pid}/stat').read_text().split()
require(state[21] == identity and state[2] not in ('Z', 'X'), 'Original actual Qt child is no longer live')
marker = dict(protocol='ict-native-io/1', run_id=failure['run_id'], scope='cleanup-only')
publish(MAILBOX / 'controls/stop.json', wire(marker))
resumed = state[2] in ('T', 't')
if resumed: os.kill(pid, signal.SIGCONT)
for _ in range(150):
    console = '\n'.join((ROOT / 'native' / n).read_text(encoding='utf-8', errors='replace') for n in ('stdout.txt', 'stderr.txt'))
    children = Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
    live = []
    for child in children:
        try:
            if Path(f'/proc/{child}/stat').read_text().split()[2] not in ('Z', 'X'): live.append(int(child))
        except FileNotFoundError: pass
    if not live and ('ICT_IO_STOPPED ' in console or 'ICT_MAILBOX_FATAL ' in console): break
    time.sleep(.1)
else: raise ValueError('Transport/helper has not acknowledged stop; preserve same native process')
before = subprocess.run(['ps', '-p', str(pid), '-o', 'pid,ppid,stat,etime,args'], capture_output=True, text=True)
t = tree(); write(ROOT / 'native/CLEANUP-TREE.json', t)
require(not matching(t, 'dialog'), 'Unexpected dialog; cleanup refuses')
listing = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True, check=True)
windows = [line for line in listing.stdout.splitlines() if ' - QCAD Professional Trial' in line]
require(len(windows) == 1, 'Cleanup requires same unique native window')
closed = subprocess.run(['wmctrl', '-ic', windows[0].split()[0]], capture_output=True, text=True)
write(ROOT / 'native/CLEANUP.json', dict(native_pid=pid, native_start_identity=identity, process_before=before.stdout,
      stop_marker=marker, resume_signal=resumed, live_helpers_before_close=live,
      window=windows[0], close_exit=closed.returncode, stdout=closed.stdout, stderr=closed.stderr,
      scope='Separate acknowledged cleanup; original controller attempt remains failed, no restart'))
require(closed.returncode == 0, 'Normal window close failed')
