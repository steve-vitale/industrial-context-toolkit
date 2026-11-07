"""Render all six declared layout hypotheses and both translated long-label pairs; exposed diagnostics only."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--exe', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        ap.error('Choose a new destination; retain every attempt')
    args.out.mkdir(parents=True)
    inputs = HERE / 'history/layout-diagnosis-4-inputs'
    frozen = json.loads((HERE / 'LAYOUT-HYPOTHESES-4-FREEZE.json').read_bytes())
    for path, pin in frozen['inputs'].items():
        if sha(ROOT / path) != pin:
            raise ValueError('Changed diagnostic input: ' + path)
    jobs = [dict(id='layout-' + label, input=str(inputs / (label + '.dxf')), block='Qualification sheet',
                 window='7,-3,116,86') for label in ('original', 'library-save', 'add-main',
                 'add-main-restore-current', 'set-current-only', 'activate-only')]
    local = ROOT / 'data/external/cad-qualification'
    bounds = json.loads((local / 'render-diagnostic-3/bounds-receipt.json').read_bytes())['rows']
    row = next(r for r in bounds if r['id'] == 'validation-long')
    entities = [e for role in ('source', 'candidate') for e in row[role] if e.get('tag')]
    xs = [v for e in entities for v in (e['bounds'][0], e['bounds'][2])]
    ys = [v for e in entities for v in (e['bounds'][1], e['bounds'][3])]
    width, height = max(xs)-min(xs), max(ys)-min(ys)
    # Equal-scale complete unions; +/- shifts keep all target label bounds within both native frames.
    frame_height = max(height * 2.6, width / (3200/2200)) * 1.1
    frame_width = frame_height * 3200/2200
    cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
    case = next(c for c in json.loads((local / 'native-validation-2/edited-manifest.json').read_bytes())['cases']
                if c['id'] == 'validation-long')
    for shift in (-.28, .28):
        window = ','.join(f'{v:.8f}' for v in (cx-frame_width/2, cy-frame_height/2+shift*frame_height,
                                             frame_width, frame_height))
        for role in ('source', 'candidate'):
            jobs.append(dict(id=f'long-{shift:+.2f}-{role}', input=case[role], block=None, window=window))
    for job in jobs:
        job['input_sha256'] = sha(job['input'])
    font = Path('C:/Windows/Fonts/arial.ttf')
    plan = dict(role='Exposed display diagnosis only; no source edits or acceptance claim', jobs=jobs,
                executable_sha256=sha(args.exe), font_sha256=sha(font),
                driver_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
                process_environment=dict(QT_QPA_FONTDIR=str(font.parent)),
                settings=dict(width=3200, height=2200, monochrome=True, background='white',
                              font_substitution=['Standard', 'Arial'], trial_marks='retained'))
    (args.out / 'plan.json').write_text(json.dumps(plan, indent=2)+'\n', encoding='utf-8')
    def render(job):
        output = args.out / (job['id'] + '.png')
        command = [str(args.exe), '-platform', 'offscreen', '-no-gui', '-allow-multiple-instances',
                   '-config', str(args.out / (job['id'] + '-settings')), '-autostart',
                   'scripts/Pro/Tools/Dwg2Bmp/Dwg2Bmp.js', '-o', str(output), '-x', '3200', '-y', '2200',
                   '-window=' + job['window'], '-b', 'white', '-n', '-fs', 'Standard', 'Arial']
        if job['block']:
            command.append('-block=' + job['block'])
        command.append(job['input'])
        if sha(job['input']) != job['input_sha256']:
            raise ValueError('Input changed before render')
        p = subprocess.run(command, cwd=args.exe.parent, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=120, creationflags=subprocess.CREATE_NO_WINDOW,
                           env=dict(os.environ, QT_QPA_FONTDIR=str(font.parent)))
        (args.out / (job['id'] + '.log')).write_bytes(p.stdout)
        result = dict(job, command=command, exit=p.returncode, input_unchanged=sha(job['input'])==job['input_sha256'],
                      image_sha256=sha(output) if output.exists() else None)
        print(job['id'], result['exit'], bool(result['image_sha256']), flush=True)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(render, jobs))
    (args.out / 'receipt.json').write_text(json.dumps(dict(plan=plan, results=results), indent=2)+'\n', encoding='utf-8')
    if not all(r['exit']==0 and r['input_unchanged'] and r['image_sha256'] for r in results):
        raise ValueError('Incomplete render diagnostic')


if __name__ == '__main__':
    main()
