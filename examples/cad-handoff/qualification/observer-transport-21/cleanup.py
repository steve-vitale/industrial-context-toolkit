"""Separate normal UI close of the same failed read-only development process."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path('/work')
os.environ['DBUS_SESSION_BUS_ADDRESS'] = (ROOT / 'dbus-address.txt').read_text().strip()
from original_workflow import tree, matching, write, require

failure = json.loads((ROOT / 'ui/FAILURE.json').read_bytes())
pid = failure['native_pid']
events = json.loads((ROOT / 'ui/actions.json').read_bytes())
signals = [r for r in events if r['kind'] == 'fault_signal']
if signals and signals[-1]['signal'] == int(signal.SIGSTOP):
    state = Path(f'/proc/{pid}/stat').read_text().split()
    require(state[2] in ('T', 't') and state[21] == signals[-1]['start_identity'], 'Stopped process identity changed')
    os.kill(pid, signal.SIGCONT)
    time.sleep(.5)
before = subprocess.run(['ps', '-p', str(pid), '-o', 'pid,ppid,stat,etime,args'], capture_output=True, text=True)
t = tree()
write(ROOT / 'native/CLEANUP-TREE.json', t)
require(not matching(t, 'dialog'), 'Cleanup refuses an unexpected dialog')
listing = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True, check=True)
windows = [line for line in listing.stdout.splitlines() if ' - QCAD Professional Trial' in line]
require(len(windows) == 1, 'Cleanup requires same unique native window')
closed = subprocess.run(['wmctrl', '-ic', windows[0].split()[0]], capture_output=True, text=True)
write(ROOT / 'native/CLEANUP.json', dict(native_pid=pid, process_before=before.stdout,
      resume_signal=bool(signals and signals[-1]['signal'] == int(signal.SIGSTOP)),
      window=windows[0], close_exit=closed.returncode, stdout=closed.stdout, stderr=closed.stderr,
      scope='Separate cleanup; original controller still failed, no restart'))
require(closed.returncode == 0, 'Normal window close failed')
