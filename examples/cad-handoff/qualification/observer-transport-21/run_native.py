"""Stage and run one frozen development attempt; preserve native handles on unexpected failure."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
IMAGE = 'sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8'


def write(path, value): path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('case', type=Path); p.add_argument('configuration', type=Path); p.add_argument('out', type=Path)
    p.add_argument('--profile', required=True); p.add_argument('--name', required=True)
    p.add_argument('--bridge', action='store_true')
    a = p.parse_args()
    a.out.mkdir(parents=True)
    records = a.out / 'host'; records.mkdir()
    counter = 0
    def command(args, *, check=True):
        nonlocal counter
        counter += 1
        r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
        write(records / f'{counter:04d}.json', dict(command=args, exit=r.returncode, stdout=r.stdout, stderr=r.stderr))
        if check and r.returncode: raise ValueError('Host command failed; see retained command ' + str(counter))
        return r
    # Refuse a used output before launching anything; stage.py separately refuses the job.
    command([sys.executable, str(HERE / 'stage.py'), str(a.case), str(a.configuration), str(a.out / 'job'), '--profile', a.profile] + (['--bridge'] if a.bridge else []))
    job = a.out / 'job'
    args = ['docker', 'run', '-d', '--name', a.name, '--network', 'none', '--user', '1001:1001',
            '--memory', '3g', '--cpus', '2', '--shm-size', '256m', '--pids-limit', '256', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--mount', 'type=bind,source=' + job.resolve().as_posix() + ',target=/work',
            '--entrypoint', 'dbus-run-session', IMAGE, '--', 'python3', '/work/launch_case.py']
    result = command(args); write(records / 'HANDLE.json', dict(name=a.name, id=result.stdout.strip(), image=IMAGE))
    print('Native container live:', a.name, result.stdout.strip(), flush=True)
    cleaned = False
    while True:
        inspection = json.loads(command(['docker', 'inspect', a.name]).stdout)[0]
        state = inspection['State']
        if state['Status'] == 'exited': break
        try: process = json.loads((job / 'native/PROCESS.json').read_bytes())
        except (FileNotFoundError, json.JSONDecodeError):
            # A partial mutable progress observation is not native termination.
            time.sleep(.2);continue
        if process.get('controller_exit') not in (None, 0) and not cleaned:
            actions = json.loads((job / 'ui/actions.json').read_bytes()) if (job / 'ui/actions.json').exists() else []
            injected = any(r['kind'] == 'fault_injection' for r in actions)
            if a.profile == 'normal' or not injected:
                raise ValueError('Unexpected controller failure; same native container preserved for inspection')
            command(['docker', 'exec', a.name, 'ps', '-eo', 'pid,ppid,stat,etime,args'])
            command(['docker', 'exec', a.name, 'python3', '/work/cleanup.py'])
            cleaned = True
            print('Original fault retained; separate same-process UI cleanup:', a.name, flush=True)
        time.sleep(1)
    command(['docker', 'cp', a.name + ':/home/cad/ict-mailbox-21', str(a.out / 'mailbox')])
    files = {p.relative_to(a.out).as_posix(): dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
             for p in a.out.rglob('*') if p.is_file()}
    write(a.out / 'INVENTORY.json', dict(files=files, native_container_state=state, profile=a.profile,
           scope='Actual development attempt; expected faults are not a clean CAD pass', whole_cad_qualified=False))
    print('Terminal:', a.name, state['ExitCode'], flush=True)
    return state['ExitCode']


if __name__ == '__main__': raise SystemExit(main())
