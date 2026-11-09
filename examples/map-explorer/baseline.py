"""Inventory the same supplied folder and fixed questions; no simulated human answers or timing."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def baseline():
    key = json.loads((Path(__file__).with_name('ACCEPTANCE.json')).read_text(encoding='utf-8'))
    folders = sorted({key[k]['sources'] for k in ('development', 'procedural_transfer', 'public_transfer')})
    files = {}
    for folder in folders:
        for path in sorted((ROOT / folder).rglob('*')):
            if path.is_file():
                files[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {'schema': 'map-explorer-folder-baseline-1', 'files': files,
            'questions': key, 'answers': None,
            'limit': 'Ordinary supplied-folder inventory only. No person searched it; no effort or benefit measured.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    target = Path(a.out)
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(baseline(), stream, ensure_ascii=False, indent=2)
        stream.write('\n')
