"""Frozen public-cohort intake and matched existing CAD routes; no silent case substitution."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
QUAL = HERE.parent
sys.path.insert(0, str(QUAL))
import adapt_public
import run_cases
import cad_handoff as ch


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def verify_methods():
    root = QUAL.parents[2]
    freeze = json.loads((HERE / 'METHODS.json').read_bytes())
    for name, expected in freeze['methods_lf'].items():
        actual = hashlib.sha256((root / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        if actual != expected:
            raise ValueError('Frozen method changed: ' + name)
    if sha(HERE/'SELECTION.json') != freeze['selection_sha256']:
        raise ValueError('Selection changed')


def intake(out):
    out.mkdir(parents=True, exist_ok=False)
    selected = json.loads((HERE/'SELECTION.json').read_bytes())
    rows = []
    for item in selected['cases']:
        folder = out/item['id']; folder.mkdir()
        row = dict(item)
        rows.append(row)
        try:
            url = 'https://raw.githubusercontent.com/' + item['repository'] + '/' + item['commit'] + '/' + quote(item['path'])
            original = folder/'original.dxf'
            command = ['curl.exe', '--fail', '--location', '--silent', '--show-error', url, '--output', str(original)]
            result = subprocess.run(command, capture_output=True, timeout=120)
            row['transport'] = dict(command=command, exit=result.returncode, stderr=result.stderr.decode('utf-8', errors='replace'))
            if result.returncode:
                raise ValueError('Download failed; retained, no replacement')
            raw = original.read_bytes()
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            if blob != item['git_blob_sha1'] or len(raw) != item['bytes']:
                raise ValueError('Pinned upstream Git blob/size mismatch')
            row['original_sha256'] = sha(original)
            try:
                original_snapshot = ch.snapshot(original)
                row['original_admission'] = dict(status='pass', assets=len(original_snapshot['assets']))
            except Exception as error:
                row['original_admission'] = dict(status='refused', error=str(error))
            source = folder/'source.dxf'
            plan, recipe = adapt_public.adapt(original, item['id'], source)
            write(folder/'plan.json', plan); write(folder/'adaptation.json', recipe)
            row.update(source_sha256=sha(source), plan_sha256=sha(folder/'plan.json'), status='adapted_not_tested')
        except Exception as error:
            row.update(status='failed', error=str(error), traceback=traceback.format_exc())
        write(out/'ADMISSION.json', dict(cases=rows, candidate_executed=False, whole_cad_qualified=False))
        print(item['id'], row['status'], flush=True)
    return int(any(row['status']=='failed' for row in rows))


def candidates(inputs, admission, out):
    expected = json.loads(admission.read_bytes())
    actual = json.loads((inputs/'ADMISSION.json').read_bytes())
    if actual != expected:
        raise ValueError('Admission does not match the committed derived-input receipt')
    out.mkdir(parents=True, exist_ok=False)
    rows=[]
    for item in expected['cases']:
        row=dict(id=item['id']); rows.append(row)
        if item['status']!='adapted_not_tested':
            row['status']='not_admitted'; continue
        folder=inputs/item['id']
        if sha(folder/'source.dxf')!=item['source_sha256'] or sha(folder/'plan.json')!=item['plan_sha256']:
            raise ValueError('Derived source/plan changed')
        row.update(run_cases.run_case(item['id'],folder/'source.dxf',folder/'plan.json',out/item['id']))
        write(out/'RESULTS.json',dict(cases=rows,whole_cad_qualified=False))
        print(item['id'],row['routes'],flush=True)
    return 0


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode',choices=['intake','candidates'])
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--inputs',type=Path)
    ap.add_argument('--admission',type=Path)
    args=ap.parse_args(); verify_methods()
    return intake(args.out) if args.mode=='intake' else candidates(args.inputs,args.admission,args.out)


if __name__=='__main__':
    raise SystemExit(main())
