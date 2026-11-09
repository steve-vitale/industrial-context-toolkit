"""Stage a separately frozen waiting-helper development job; retain original method."""
import argparse
from pathlib import Path
import json
import shutil
import secrets
from prepare import HERE, TRANSPORT, UI, sha, write, require

def job(case, role, configuration, out, returns=None, probe=False):
    if out.exists(): raise ValueError('New job destination required')
    basis = json.loads((case / 'basis.json').read_bytes())
    require(sha(case / 'source.dxf') == basis['source_sha256'] and sha(case / 'plan.json') == basis['plan_sha256'], 'Prepared source/plan differs')
    require(role in ('baseline', 'edited', 'receiving'), 'Unknown role')
    if role == 'receiving': require(returns is not None, 'Matched native returns required')
    out.mkdir(parents=True); (out / '.configuration').mkdir()
    shutil.copyfile(configuration, out / '.configuration/QCAD3.conf')
    write(out / 'job.json', dict(basis, role=role))
    for name in ('source.dxf', 'plan.json'): shutil.copyfile(case / name, out / name)
    if role == 'receiving':
        for name in ('baseline', 'edited'): shutil.copyfile(returns / (case.name + '-' + name) / 'job/returned.dxf', out / (name + '.dxf'))
        shutil.copyfile(case / 'software/candidate/candidate.dxf', out / 'candidate.dxf')
    sources = {
        'workflow.py': HERE / ('waiting_probe.py' if probe else 'workflow.py'), 'contract.py': HERE / 'contract.py', 'ui_text.py': HERE / 'ui_text.py',
        'payload.js': HERE / 'payload.js', 'PLAN.md': HERE / 'PLAN.md', 'METHOD.md': HERE / 'METHOD.md',
        'original_workflow.py': UI / 'workflow.py', 'inspect_ui.py': UI / 'inspect_ui.py', 'native_controls.py': UI / 'native_controls.py',
        'ui_control.py': TRANSPORT / 'bridge_ui_control.py', 'ui_settle.py': TRANSPORT / 'ui_settle.py',
        'bridge_workflow.py': TRANSPORT / 'bridge_workflow.py', 'mailbox.py': TRANSPORT / 'mailbox.py',
        'native_io.py': HERE / 'native_io_wait.py', 'base_native_io.py': TRANSPORT / 'native_io.py',
        'observe_case.js': HERE / 'waiting_observer.js', 'WAITING-HELPER-PLAN.md': HERE / 'WAITING-HELPER-PLAN.md',
        'launch_case.py': TRANSPORT / 'bridge_launch.py', 'BRIDGE-PROTOCOL.md': TRANSPORT / 'BRIDGE-PROTOCOL.md',
    }
    for target, source in sources.items(): shutil.copyfile(source, out / target)
    write(out / 'transport.json', dict(protocol='ict-native-mailbox/1', io_protocol='ict-native-io/1', run_id=secrets.token_hex(16), profile='normal'))
    write(out / 'JOB-FREEZE.json', dict(files={p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()},
          producer_sha256=sha(__file__), scope='Frozen waiting-helper development job; not fresh validation or qualification'))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('case',type=Path);p.add_argument('role');p.add_argument('configuration',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--returns',type=Path);p.add_argument('--probe',action='store_true');a=p.parse_args()
    job(**vars(a))
