"""Freeze a fresh exposed transport job; never overwrite an earlier job."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'native-ui-pairs-19'
PROFILES = ['binding-probe', 'async-probe', 'normal', 'malformed', 'wrong-sequence', 'wrong-run', 'unsupported', 'read-open',
            'reply-collision', 'reply-write', 'error-write', 'missing-reply', 'changed-request', 'native-exit']


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path)
    parser.add_argument('configuration', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--profile', choices=PROFILES, required=True)
    parser.add_argument('--bridge', action='store_true')
    parser.add_argument('--async-bridge', action='store_true')
    args = parser.parse_args()
    if args.bridge and args.async_bridge: raise ValueError('Choose one bridge method')
    bridge = args.bridge or args.async_bridge
    if args.out.exists(): raise ValueError('New job directory required')
    args.out.mkdir(parents=True)
    job = json.loads((args.case / 'basis.json').read_bytes())
    job['role'] = 'receiving'
    (args.out / 'job.json').write_text(json.dumps(job, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(args.case / 'source.dxf', args.out / 'source.dxf')
    (args.out / '.configuration').mkdir()
    shutil.copyfile(args.configuration, args.out / '.configuration/QCAD3.conf')
    for name in ('mailbox.py', 'workflow.py', 'payload.js', 'launch_case.py', 'cleanup.py', 'PLAN.md'):
        shutil.copyfile(HERE / name, args.out / name)
    shutil.copyfile(HERE / ('binding_probe.js' if args.profile == 'binding-probe' else 'observer.js'), args.out / 'observe_case.js')
    if args.profile == 'binding-probe': shutil.copyfile(HERE / 'probe_workflow.py', args.out / 'workflow.py')
    if args.profile == 'async-probe':
        if bridge: raise ValueError('Async capability probe is a separate method')
        for source, target in [('async_probe.js','observe_case.js'),('async_workflow.py','workflow.py'),
                               ('bridge_launch.py','launch_case.py')]:
            shutil.copyfile(HERE / source, args.out / target)
        for name in ('async_helper.py','ASYNC-PLAN.md'): shutil.copyfile(HERE / name, args.out / name)
    if bridge:
        if args.profile == 'binding-probe': raise ValueError('Binding probes retain their original separate method')
        for source, target in [('bridge_observer.js','observe_case.js'),('bridge_workflow.py','workflow.py'),
                               ('bridge_launch.py','launch_case.py'),('bridge_cleanup.py','cleanup.py')]:
            shutil.copyfile(HERE / source, args.out / target)
        for name in ('native_io.py','BRIDGE-PLAN.md','BRIDGE-PROTOCOL.md'):shutil.copyfile(HERE / name,args.out / name)
        if args.async_bridge:
            shutil.copyfile(HERE / 'async_bridge_observer.js', args.out / 'observe_case.js')
            shutil.copyfile(HERE / 'ASYNC-PLAN.md', args.out / 'ASYNC-PLAN.md')
    shutil.copyfile(BASE / 'workflow.py', args.out / 'original_workflow.py')
    for name in ('ui_control.py', 'inspect_ui.py', 'native_controls.py'):
        shutil.copyfile(BASE / name, args.out / name)
    if bridge or args.profile == 'async-probe':
        shutil.copyfile(HERE / 'bridge_ui_control.py', args.out / 'ui_control.py')
        shutil.copyfile(HERE / 'ui_settle.py', args.out / 'ui_settle.py')
    config = dict(protocol='ict-native-mailbox/1', run_id=secrets.token_hex(16), profile=args.profile)
    if bridge:config['io_protocol']='ict-native-io/1'
    (args.out / 'transport.json').write_text(json.dumps(config) + '\n', encoding='utf-8')
    files = {p.relative_to(args.out).as_posix(): sha(p) for p in args.out.rglob('*') if p.is_file()}
    (args.out / 'JOB-FREEZE.json').write_text(json.dumps(dict(files=files, stage_sha256=sha(Path(__file__)),
        scope='Exposed transport development; no CAD edits/save; no full qualification'), indent=2) + '\n', encoding='utf-8')
    print(args.out)


if __name__ == '__main__': main()
