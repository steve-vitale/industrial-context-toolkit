"""Prepare declared exposed cases/software controls and freeze fresh native jobs."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TRANSPORT = HERE.parent / 'observer-transport-21'
UI = HERE.parent / 'native-ui-pairs-19'
sys.path.insert(0, str(ROOT / 'scripts')); sys.path.insert(0, str(HERE.parent))
import cad_handoff as ch
from run_cases import run_case
from ezdxf import bbox


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path, value): Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n', encoding='utf-8', newline='\n')
def require(ok, message):
    if not ok: raise ValueError(message)


def frame(entities):
    b = bbox.extents(entities, fast=False); a, z = b.extmin, b.extmax
    pad = max(2, .2 * max(z.x - a.x, z.y - a.y))
    return [a.x - pad, a.y - pad, z.x + pad, z.y + pad]


def cases(out):
    if out.exists(): raise ValueError('New case destination required')
    catalog = json.loads((HERE / 'DEVELOPMENT-INPUTS.json').read_bytes())
    for row in catalog['cases']:
        require(sha(ROOT / row['source']) == row['source_sha256'] and sha(ROOT / row['plan']) == row['plan_sha256'], 'Declared exposed input differs')
    out.mkdir(parents=True); results = []
    for row in catalog['cases']:
        case = out / row['case']; case.mkdir()
        shutil.copyfile(ROOT / row['source'], case / 'source.dxf'); shutil.copyfile(ROOT / row['plan'], case / 'plan.json')
        source = case / 'source.dxf'; before = ch.snapshot(source); plan = json.loads((case / 'plan.json').read_bytes())
        ch.validate_plan(before, plan)
        require(len(before['assets']) == row['assets'], 'Declared asset count differs')
        result = run_case(row['case'], source, case / 'plan.json', case / 'software'); results.append(result)
        write(out / 'SOFTWARE.json', results)
        candidate = case / 'software/candidate/candidate.dxf'
        require(result['routes']['value-spans'].get('strict_status') == 'pass' and result['routes']['value-spans'].get('byte_check', {}).get('status') == 'pass', 'Candidate software route failed; preserve this preparation')
        docs = [ch.load(source), ch.load(candidate)]; models = [d.modelspace() for d in docs]
        frames = dict(overview=frame([e for m in models for e in m]))
        for number, asset in enumerate(before['assets'], 1):
            inserts = [d.entitydb[asset['handle']] for d in docs]
            attrs = [a for insert in inserts for a in insert.attribs]
            frames['asset-' + str(number)] = frame(inserts + attrs)
            frames['labels-' + str(number)] = frame(attrs)
        write(case / 'basis.json', dict(case=row['case'], source_sha256=sha(source), plan_sha256=sha(case / 'plan.json'),
              assets=before['assets'], changes=plan['changes'], frames=frames,
              scope='Already exposed authored multi-asset development; not reserved, plant or engineering acceptance'))
    write(out / 'PREPARATION.json', dict(producer_sha256=sha(__file__), declared_inputs=catalog,
          comparison_source_sha256_lf={n: hashlib.sha256((ROOT / n).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
              for n in ('scripts/cad_handoff.py', 'scripts/cad_value_patch.py', 'examples/cad-handoff/qualification/verify_bytes.py', 'examples/cad-handoff/qualification/run_cases.py')}))
    return results


def job(case, role, configuration, out, returns=None):
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
        'workflow.py': HERE / 'workflow.py', 'contract.py': HERE / 'contract.py', 'ui_text.py': HERE / 'ui_text.py',
        'payload.js': HERE / 'payload.js', 'PLAN.md': HERE / 'PLAN.md', 'METHOD.md': HERE / 'METHOD.md',
        'original_workflow.py': UI / 'workflow.py', 'inspect_ui.py': UI / 'inspect_ui.py', 'native_controls.py': UI / 'native_controls.py',
        'ui_control.py': TRANSPORT / 'bridge_ui_control.py', 'ui_settle.py': TRANSPORT / 'ui_settle.py',
        'bridge_workflow.py': TRANSPORT / 'bridge_workflow.py', 'mailbox.py': TRANSPORT / 'mailbox.py',
        'native_io.py': TRANSPORT / 'native_io.py', 'observe_case.js': TRANSPORT / 'async_bridge_observer.js',
        'launch_case.py': TRANSPORT / 'bridge_launch.py', 'BRIDGE-PROTOCOL.md': TRANSPORT / 'BRIDGE-PROTOCOL.md',
    }
    for target, source in sources.items(): shutil.copyfile(source, out / target)
    write(out / 'transport.json', dict(protocol='ict-native-mailbox/1', io_protocol='ict-native-io/1', run_id=secrets.token_hex(16), profile='normal'))
    write(out / 'JOB-FREEZE.json', dict(files={p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()},
          producer_sha256=sha(__file__), scope='Frozen before native full UI development; not fresh validation or qualification'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='action', required=True)
    a = sub.add_parser('cases'); a.add_argument('out', type=Path)
    a = sub.add_parser('job'); a.add_argument('case', type=Path); a.add_argument('role'); a.add_argument('configuration', type=Path)
    a.add_argument('out', type=Path); a.add_argument('--returns', type=Path)
    a = p.parse_args()
    if a.action == 'cases': print(json.dumps(cases(a.out), indent=2))
    else: job(a.case, a.role, a.configuration, a.out, a.returns)
