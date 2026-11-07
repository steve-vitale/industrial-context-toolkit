"""Fetch optionally, verify pins, and inventory this public-source acquisition offline.

No downloaded code is executed. Archives are inventoried without reading members.
CAD contents and Parquet rows/labels stay unopened for later declared evaluation.
"""
import argparse
import importlib.util
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PARENT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / 'data/public_sources_20261107_round5.json'
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(PARENT))
import fetch_corpus  # noqa: E402

spec = importlib.util.spec_from_file_location('public_admission_v2', PARENT / 'round-2/reproduce.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)


def inspect(path, sid):
    if path.suffix.lower() == '.aasx':
        # AASX is a ZIP container; inventory only, never unpack or execute.
        import zipfile
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            return {'parser': 'stdlib AASX ZIP directory only', 'extracted': False,
                    'members': [{'name': x.filename, 'bytes': x.file_size} for x in members],
                    'semantic_or_schema_conformance': 'not assessed'}
    if path.suffix.lower() in {'.fcstd', '.dxf', '.step', '.stp'}:
        return {'parser': 'intentionally not run', 'status': 'content uninspected',
                'reason': 'CAD originals reserved as acquired bytes; no archive/XML/geometry inspection.'}
    if path.suffix.lower() == '.inp':
        sections, active = {}, None
        for raw in path.read_text(encoding='utf-8-sig').splitlines():
            line = raw.split(';', 1)[0].strip()
            if line.startswith('[') and line.endswith(']'):
                active = line[1:-1]
                sections.setdefault(active, 0)
            elif line and active is not None:
                sections[active] += 1
        return {'parser': 'passive INP section inventory', 'section_noncomment_rows': sections,
                'solver_executed': False, 'semantic_validity': 'not assessed'}
    return previous.inspect(path, sid)


def run(argv=None):
    registry = json.loads(REGISTRY.read_bytes())
    sources = registry['sources']
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', action='append', choices=sorted(sources))
    ap.add_argument('--fetch', action='store_true', help='opt in to pinned public downloads')
    ap.add_argument('--max-mb', type=float, default=210, help='total missing download budget, decimal MB')
    ap.add_argument('--out', type=Path, required=True, help='new report directory; no evidence replaced')
    args = ap.parse_args(argv)
    selected = list(dict.fromkeys(args.source or sources))
    if args.out.exists():
        ap.error('--out exists; choose a new directory')
    pins = fetch_corpus.load_pins()
    problems = fetch_corpus.validate_file_pins(pins, sources)
    if problems:
        ap.error('; '.join(problems))
    needed = sum(pin['bytes'] for sid in selected for name, pin in pins[sid].items()
                 if not (fetch_corpus.EXTERNAL / sid / name).is_file()
                 or previous.base.digest(fetch_corpus.EXTERNAL / sid / name) != pin['sha256'])
    if args.fetch and (not 0 <= args.max_mb < float('inf') or needed > args.max_mb * 1e6):
        ap.error(f'{needed} missing/replaced bytes exceed total --max-mb {args.max_mb}')
    args.out.mkdir(parents=True)
    methods = [Path(__file__), PARENT / 'round-2/reproduce.py', PARENT / 'reproduce.py',
               ROOT / 'scripts/extract_text.py', ROOT / 'scripts/fetch_corpus.py', REGISTRY]
    report = dict(schema='public-source-admission-5', created=datetime.now(timezone.utc).isoformat(),
                  role='acquired-unscored; integrity and structural admission only',
                  python=platform.python_version(),
                  fingerprint_convention='methods/registry CRLF normalized to LF; originals raw bytes',
                  methods={p.relative_to(ROOT).as_posix(): previous.fingerprint(p) for p in methods},
                  fetch_receipts=[], sources={}, errors=[])
    fetch_corpus.FILE_SOURCES.update(sources)
    fetch_corpus.USER_AGENT = 'industrial-context-toolkit public source acquisition https://github.com/steve-vitale/industrial-context-toolkit'
    if args.fetch:
        for sid in selected:
            try:
                report['fetch_receipts'].append(fetch_corpus.fetch_pinned(sid, args.max_mb, fetch_corpus.EXTERNAL / sid))
            except Exception as error:
                report['errors'].append(dict(source=sid, stage='fetch', error=f'{type(error).__name__}: {error}'))
    for sid in selected:
        files = []
        for name, pin in pins[sid].items():
            path = fetch_corpus.EXTERNAL / sid / name
            item = dict(path=name, bytes=pin['bytes'], sha256=pin['sha256'])
            try:
                fetch_corpus.check_bytes(name, path.read_bytes(), pin['bytes'], pin['sha256'])
                item['integrity'] = 'match'
                item['inspection'] = inspect(path, sid)
                if item['inspection'].get('status') == 'error':
                    raise ValueError('Document parser error: ' + str(item['inspection'].get('warnings')))
            except Exception as error:
                item['error'] = f'{type(error).__name__}: {error}'
                report['errors'].append(dict(source=sid, path=name, stage='inspection', error=item['error']))
            files.append(item)
        report['sources'][sid] = dict(categories=sources[sid]['categories'], files=files)
        print(sid, len(files), 'files checked', flush=True)
    (args.out / 'admission.json').write_text(json.dumps(report, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    return int(bool(report['errors']))


if __name__ == '__main__':
    raise SystemExit(run())
