"""Opt-in native display review on all replacement cases/assets; no drawing writes or UI acceptance."""
import argparse
import concurrent.futures
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import cad_handoff as ch


def window(rows, pad_fraction):
    if not rows or any('bounds_error' in row for row in rows):
        raise ValueError('Missing/failed native bounds; no invented view')
    xs = [v for row in rows for v in (row['bounds'][0], row['bounds'][2])]
    ys = [v for row in rows for v in (row['bounds'][1], row['bounds'][3])]
    if not all(math.isfinite(v) for v in xs + ys):
        raise ValueError('Nonfinite native bounds')
    width, height = max(xs) - min(xs), max(ys) - min(ys)
    pad = max(width, height, 1) * pad_fraction
    return ','.join(f'{v:.8f}' for v in (min(xs)-pad, min(ys)-pad, width+2*pad, height+2*pad))


def groups(records):
    parents = {row['parent']: row['text'] for row in records if row.get('tag') == 'ICT_ID'}
    if len(set(parents.values())) != len(parents):
        raise ValueError('Duplicate native stable identity')
    return {identity: [r for r in records if r.get('parent') == parent] for parent, identity in parents.items()}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--exe', type=Path, required=True, help='pre-existing qualified QCAD qcadcmd.com; never downloaded')
    ap.add_argument('--font-dir', type=Path, required=True, help='existing system fonts; no install/redistribution')
    ap.add_argument('--bounds', type=Path, required=True, help='retained read-only native bounds receipt')
    ap.add_argument('--native-manifest', type=Path, required=True)
    ap.add_argument('--earlier-plan', type=Path, required=True, help='retained first views, including paper-layout windows')
    ap.add_argument('--out', type=Path, required=True, help='new evidence directory')
    args = ap.parse_args(argv)
    if args.out.exists():
        ap.error('Output exists; retain every attempt')
    frozen = json.loads((HERE / 'VISUAL-FREEZE-3.json').read_bytes())
    for name, wanted in frozen['methods'].items():
        if hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != wanted:
            ap.error('Display method changed after freeze: ' + name)
    if sha(args.exe) != frozen['executable_sha256'] or sha(args.font_dir / 'arial.ttf') != frozen['font_sha256']:
        ap.error('Native executable or display font differs from declared run')
    manifest = json.loads(args.native_manifest.read_bytes())['cases']
    bound_receipt = json.loads(args.bounds.read_bytes())
    if bound_receipt['helper_sha256'] != sha(HERE / 'native-view-bounds.js'):
        ap.error('Bounds helper does not match retained receipt')
    bounds = {r['id']: r for r in bound_receipt['rows']}
    if len(manifest) != 12 or set(bounds) != {c['id'] for c in manifest}:
        ap.error('Omitted/extra display cases')
    old = json.loads(args.earlier_plan.read_bytes())['jobs']
    jobs = []
    for case in manifest:
        data = bounds[case['id']]
        source = ch.snapshot(case['source'])
        candidate = ch.snapshot(case['candidate'])
        plan = json.loads(Path(case['plan']).read_bytes())
        if ch.compare(source, candidate, plan)['status'] != 'pass':
            ap.error('Candidate does not pass frozen strict comparison: ' + case['id'])
        actual = {route: groups(data[route]) for route in ('source', 'candidate')}
        for route, snap in [('source', source), ('candidate', candidate)]:
            expected = {a['id']: a['attributes'] for a in snap['assets']}
            observed = {identity: {r['tag']: r['text'] for r in rows} for identity, rows in actual[route].items()}
            if observed != expected:
                ap.error('Native bounds labels disagree with retained input: ' + case['id'])
        views = [('model-full', None, window([r for route in ('source', 'candidate') for r in data[route]], .1), None)]
        for number, identity in enumerate(sorted(actual['source']), 1):
            rows = actual['source'][identity] + actual['candidate'][identity]
            views.append((f'asset-{number:02d}', None, window(rows, .5), identity))
        for row in old:
            if row['case'] == case['id'] and row['route'] == 'source' and row.get('block'):
                views.append((row['view'], row['block'], row['window'], None))
        for name, block, view_window, identity in views:
            for route in ('source', 'candidate'):
                jobs.append(dict(case=case['id'], view=name, route=route, identity=identity, block=block,
                    window=view_window, input=case[route], input_sha256=sha(case[route]),
                    bounds_method='prior passive layout bounds' if block else 'native source/candidate union',
                    width=3200, height=2200))
    args.out.mkdir(parents=True)
    evidence = dict(scope='Post-exposure display review only. Arial substitution changes display typography, '
                   'not drawing bytes. No original-font fidelity, GUI or engineering acceptance inferred.',
                   jobs=jobs, native_manifest_sha256=sha(args.native_manifest), bounds_receipt_sha256=sha(args.bounds),
                   earlier_plan_sha256=sha(args.earlier_plan), display_freeze_sha256=sha(HERE / 'VISUAL-FREEZE-3.json'),
                   process_environment=dict(QT_QPA_FONTDIR=str(args.font_dir)),
                   settings=dict(monochrome=True, background='white', font_substitution=['Standard', 'Arial']),
                   expected_cases=12, expected_asset_pairs=sum(len(groups(bounds[c['id']]['source'])) for c in manifest))
    ch.write_json(args.out / 'plan.json', evidence)
    env = dict(os.environ, QT_QPA_FONTDIR=str(args.font_dir))

    def render(job):
        stem = '-'.join([job['case'], job['view'], job['route']])
        output = args.out / (stem + '.png')
        command = [str(args.exe), '-platform', 'offscreen', '-no-gui', '-allow-multiple-instances',
            '-config', str(args.out / (stem + '-settings')), '-autostart', 'scripts/Pro/Tools/Dwg2Bmp/Dwg2Bmp.js',
            '-o', str(output), '-x', '3200', '-y', '2200', '-window=' + job['window'],
            '-b', 'white', '-n', '-fs', 'Standard', 'Arial']
        if job['block']:
            command += ['-block=' + job['block']]
        command.append(job['input'])
        result = dict(job, command=command)
        try:
            if sha(job['input']) != job['input_sha256']:
                raise ValueError('Input changed before render')
            proc = subprocess.run(command, cwd=args.exe.parent, env=env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
            (args.out / (stem + '.log')).write_bytes(proc.stdout)
            result.update(exit=proc.returncode, input_unchanged=sha(job['input']) == job['input_sha256'],
                          image_sha256=sha(output) if output.exists() else None)
        except Exception as error:
            result['error'] = f'{type(error).__name__}: {error}'
        print(stem, result.get('exit'), result.get('error', result.get('input_unchanged')), flush=True)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(render, jobs))
    ch.write_json(args.out / 'receipts.json', dict(results=results, executable_sha256=sha(args.exe),
                   font_sha256=sha(args.font_dir / 'arial.ttf'), driver_sha256=sha(Path(__file__))))
    return int(any(r.get('error') or r.get('exit') != 0 or not r.get('input_unchanged') or not r.get('image_sha256') for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
