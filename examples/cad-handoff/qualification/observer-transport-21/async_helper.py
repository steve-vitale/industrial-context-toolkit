"""Bounded scheduling probe only; never reads or changes a drawing."""
import json
import os
from pathlib import Path
import sys
import time

root = Path('/work/native')
started = time.monotonic()
identity = dict(pid=os.getpid(), qt_parent_pid=os.getppid(), uid=os.getuid())
with (root / 'ASYNC-HELPER-READY.json').open('x', encoding='utf-8') as stream:
    json.dump(identity, stream)
while not (root / 'ASYNC-RELEASE.json').is_file():
    if time.monotonic() - started >= 120:
        raise TimeoutError('Probe release not observed; no restart')
    time.sleep(.05)
print(json.dumps(dict(identity, value='\u00b5 valve'), ensure_ascii=False))
sys.stderr.write('async probe stderr\n')
