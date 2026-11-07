"""Package exact local qualification records, excluding native settings/software; never calls a model/editor."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / 'data/external/cad-qualification'
DIRECTORIES = ['development', 'regression-2', 'regression-final-2', 'validation-2-authored', 'validation-2-public',
               'native-2-development', 'native-validation-2', 'revision-controls-2', 'render-validation-2',
               'native-help', 'render-diagnostic-3', 'font-probe-4', 'render-font-4', 'render-review-3']
DRIVERS = ['native2-development.py', 'native-validation-2.py', 'revision-controls-2.py', 'render-validation-2.py',
           'display-diagnostic-3.py', 'probe-fonts-4.py', 'render-font-4.py']
LOGS = ['regression-2.log', 'regression-final-2.log', 'validation-2-authored.log', 'validation-2-public.log',
        'native-validation-2-driver.log', 'revision-controls-2-driver.log', 'render-validation-2-driver.log',
        'public-adaptation-2.log']


def collect(local=LOCAL):
    for name in ('native-validation-2/fresh-process-checks.json', 'render-review-3/receipts.json',
                 'native-2-development/summary-checked.json', 'revision-controls-2/checks.json'):
        if not (local / name).is_file():
            raise ValueError('Evidence producer incomplete: ' + name)
    files = []
    for name in DIRECTORIES:
        directory = local / name
        if not directory.is_dir():
            raise ValueError('Missing declared evidence directory: ' + name)
        for path in sorted(directory.rglob('*')):
            parts = path.relative_to(directory).parts
            if (path.is_file() and path.suffix.lower() not in {'.exe', '.com', '.dll', '.ini'}
                    and not any(p.endswith('-settings') or p in {'__pycache__', 'config'} for p in parts)):
                files.append(path)
    for name in DRIVERS + LOGS:
        path = local / name
        if not path.is_file():
            raise ValueError('Missing declared driver/log: ' + name)
        files.append(path)
    if len(set(files)) != len(files):
        raise ValueError('Duplicate evidence path')
    return sorted(files)


def run(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True, help='new committed evidence directory')
    args = ap.parse_args(argv)
    if args.out.exists():
        ap.error('Output exists; retain old evidence')
    files = collect()
    args.out.mkdir(parents=True)
    inventory = {}
    archive = args.out / 'evidence.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in files:
            raw = path.read_bytes()
            name = 'raw/' + path.relative_to(LOCAL).as_posix()
            if path.suffix.lower() in {'.exe', '.com', '.dll', '.ini'}:
                raise ValueError('Software/settings are not evidence artifacts: ' + name)
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100600 << 16
            z.writestr(info, raw)
            inventory[name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    report = dict(schema='cad-evidence-archive-2', role='Retained attempts, including failed diagnostics; not qualification',
                  raw_bytes=sum(p['bytes'] for p in inventory.values()),
                  archive=dict(path=archive.name, bytes=archive.stat().st_size,
                               sha256=hashlib.sha256(archive.read_bytes()).hexdigest()), files=inventory,
                  exclusions=['Native settings directories, executables, DLLs, INI files and Python caches'],
                  packager_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest())
    (args.out / 'INVENTORY.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}, indent=2))
    print(len(inventory), 'exact raw records packaged')


if __name__ == '__main__':
    run()
