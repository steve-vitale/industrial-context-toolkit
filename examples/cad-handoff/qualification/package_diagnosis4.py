"""Package exact exposed display diagnostic records; no native software/settings or drawing edits."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / 'data/external/cad-qualification'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        ap.error('Choose a new destination')
    files = []
    for directory in ('layout-probe-4', 'layout-hypotheses-4', 'render-diagnosis-4'):
        base = LOCAL / directory
        if not (base / 'receipt.json').exists():
            raise ValueError('Producer incomplete: ' + directory)
        files += [p for p in sorted(base.rglob('*')) if p.is_file()
                  and p.suffix.lower() not in {'.exe', '.dll', '.com', '.ini'}
                  and not any(x.endswith('-settings') or x=='__pycache__' for x in p.relative_to(base).parts)]
    args.out.mkdir(parents=True)
    archive = args.out / 'evidence.zip'
    inventory = {}
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            name = 'raw/' + p.relative_to(LOCAL).as_posix()
            raw = p.read_bytes()
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100600 << 16
            z.writestr(info, raw)
            inventory[name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    report = dict(role='Exposed compatibility/display diagnostics, not qualification', files=inventory,
                  raw_bytes=sum(p['bytes'] for p in inventory.values()),
                  archive=dict(path=archive.name, bytes=archive.stat().st_size,
                               sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),
                  exclusions=['Native settings, executables, libraries, INI and Python caches'],
                  packager_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest())
    (args.out / 'INVENTORY.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(len(files), 'exact records;', report['raw_bytes'], 'raw bytes;', archive.stat().st_size, 'archive bytes')


if __name__ == '__main__':
    main()
