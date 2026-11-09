"""Run one separately frozen waiting-helper job; failures retain the same handle."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
IMAGE = 'sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8'


def write(path, value): path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('case', type=Path); p.add_argument('role'); p.add_argument('configuration', type=Path); p.add_argument('out', type=Path)
    p.add_argument('--name', required=True); p.add_argument('--returns', type=Path); p.add_argument('--probe', action='store_true'); a = p.parse_args()
    a.out.mkdir(parents=True); records = a.out / 'host'; records.mkdir(); counter = 0
    def command(args):
        nonlocal counter
        counter += 1; r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
        write(records / f'{counter:04d}.json', dict(command=args, exit=r.returncode, stdout=r.stdout, stderr=r.stderr))
        r.check_returncode(); return r
    args = [sys.executable, str(HERE / 'prepare_wait.py'), str(a.case), a.role, str(a.configuration), str(a.out / 'job')]
    if a.returns is not None: args += ['--returns', str(a.returns)]
    if a.probe: args += ['--probe']
    command(args); job = a.out / 'job'
    result = command(['docker', 'run', '-d', '--name', a.name, '--network', 'none', '--user', '1001:1001',
        '--memory', '3g', '--cpus', '2', '--shm-size', '256m', '--pids-limit', '256', '--cap-drop', 'ALL',
        '--security-opt', 'no-new-privileges', '--mount', 'type=bind,source=' + job.resolve().as_posix() + ',target=/work',
        '--entrypoint', 'dbus-run-session', IMAGE, '--', 'python3', '/work/launch_case.py'])
    write(records / 'HANDLE.json', dict(name=a.name, id=result.stdout.strip(), image=IMAGE))
    print('Native container live:', a.name, result.stdout.strip(), flush=True)
    while True:
        inspection = json.loads(command(['docker', 'inspect', a.name]).stdout)[0]; state = inspection['State']
        if state['Status'] == 'exited': break
        try: process = json.loads((job / 'native/PROCESS.json').read_bytes())
        except (FileNotFoundError, json.JSONDecodeError): time.sleep(.2); continue
        if process.get('controller_exit') not in (None, 0):
            raise ValueError('Controller failed; preserve same native container for inspection, no restart')
        time.sleep(1)
    command(['docker', 'cp', a.name + ':/home/cad/ict-mailbox-21', str(a.out / 'mailbox')])
    write(a.out / 'INVENTORY.json', dict(files={p.relative_to(a.out).as_posix(): dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
          for p in a.out.rglob('*') if p.is_file()}, native_container_state=state, role=a.role, whole_cad_qualified=False))
    print('Terminal:', state['ExitCode'], flush=True); return state['ExitCode']


if __name__ == '__main__': raise SystemExit(main())
