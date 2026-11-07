"""Verify/fetch the pinned AMPS API responses and report structural relationship coverage, offline by default."""
import argparse
from collections import Counter
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import fetch_corpus as fetcher
from acquire import TABLES

REGISTRY = ROOT / 'data/public_sources_20261107_round4.json'
SOURCE = 'nyc-amps-2024w01'


def fingerprint(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def coverage(children, foreign_key, parents, primary_key):
    counts = Counter(str(row[primary_key]) for row in parents if row.get(primary_key) not in (None, ''))
    result = dict(missing_reference=0, unmatched=0, unique_match=0, ambiguous=0)
    for row in children:
        value = row.get(foreign_key)
        if value in (None, ''):
            result['missing_reference'] += 1
        else:
            n = counts[str(value)]
            result['unmatched' if not n else 'unique_match' if n == 1 else 'ambiguous'] += 1
    return result


def relationships(tables):
    errors, keys = [], {}
    for name, (_, key, fields) in TABLES.items():
        rows = tables[name]
        counts = Counter(str(row[key]) for row in rows if row.get(key) not in (None, ''))
        unknown = sorted(set().union(*(set(row) for row in rows)) - set(fields.split(','))) if rows else []
        missing = sum(row.get(key) in (None, '') for row in rows)
        duplicate_keys = sum(n > 1 for n in counts.values())
        keys[name] = dict(rows=len(rows), distinct_nonempty_keys=len(counts), missing_keys=missing,
                          duplicate_keys=duplicate_keys, excess_duplicate_rows=sum(n - 1 for n in counts.values()),
                          unexpected_columns=unknown)
        if missing or duplicate_keys or unknown:
            errors.append(f'{name}: missing/duplicate keys or unexpected projected columns; see key diagnostics')
    work = tables['work-orders']
    if not work:
        errors.append('Empty selected work-order cohort does not establish useful linked coverage')
    if any(not ('2024-01-01T00:00:00' <= row.get('evt_date', '') < '2024-01-08T00:00:00') for row in work):
        errors.append('Work order missing/outside predeclared date interval')
    links = {
        'work_orders_to_assets': coverage(work, 'evt_object', tables['assets'], 'obj_code'),
        'transactions_to_work_orders': coverage(tables['transactions'], 'tra_tocode', work, 'evt_code'),
        'details_to_transactions': coverage(tables['details'], 'trl_trans', tables['transactions'], 'tra_code'),
        'labor_to_work_orders': coverage(tables['labor'], 'boo_event', work, 'evt_code'),
    }
    # Missing parent assets remain an honest coverage gap. Foreign returned transaction/labor rows contradict
    # the actual query contract and must fail, rather than accidentally matching some other entity namespace.
    wrong_entity = sum(row.get('tra_toentity') != 'EVNT' for row in tables['transactions'])
    if wrong_entity:
        errors.append(f'{wrong_entity} transaction rows are not in the declared EVNT namespace')
    for name in ('transactions_to_work_orders', 'details_to_transactions', 'labor_to_work_orders'):
        if any(links[name][k] for k in ('missing_reference', 'unmatched', 'ambiguous')):
            errors.append(f'{name}: returned rows do not have a unique selected parent')
    requested_assets = {str(r['evt_object']) for r in work if r.get('evt_object') not in (None, '')}
    if any(str(row.get('obj_code')) not in requested_assets for row in tables['assets']):
        errors.append('Returned asset outside the selected work-order references')
    return dict(keys=keys, links=links, errors=errors,
                administrative_observations=dict(
                    work_orders_with_completion_value=sum(r.get('evt_completed') not in (None, '') for r in work),
                    work_orders_with_reopened_value=sum(r.get('evt_reopened') not in (None, '') for r in work),
                    work_orders_with_part_transactions=len({r['tra_tocode'] for r in tables['transactions'] if r.get('tra_tocode')}),
                    labor_rows_with_correction_value=sum(r.get('boo_correction') not in (None, '') for r in tables['labor'])),
                interpretation='Structural/source observations only. Completion is not repair effectiveness; '
                               'parts movements are not automatically consumption; no cost/hour totals computed.')


def run(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fetch', action='store_true')
    ap.add_argument('--max-mb', type=float, default=20, help='total missing download budget, decimal MB')
    ap.add_argument('--input-root', type=Path, default=ROOT / 'data/external', help='contains nyc-amps-2024w01/')
    ap.add_argument('--out', type=Path, required=True, help='new report directory')
    args = ap.parse_args(argv)
    if args.out.exists():
        ap.error('--out exists; choose a new report directory')
    registry = json.loads(REGISTRY.read_bytes())
    sources = registry['sources']
    pins = fetcher.load_pins()
    problems = fetcher.validate_file_pins(pins, sources)
    if problems:
        ap.error('; '.join(problems))
    dest = args.input_root / SOURCE
    needed = sum(p['bytes'] for n, p in pins[SOURCE].items()
                 if not (dest / n).is_file() or hashlib.sha256((dest / n).read_bytes()).hexdigest() != p['sha256'])
    if args.fetch and (not math.isfinite(args.max_mb) or args.max_mb < 0 or needed > args.max_mb * 1e6):
        ap.error(f'{needed} missing/replaced bytes exceed total --max-mb {args.max_mb}')
    args.out.mkdir(parents=True)
    methods = [Path(__file__), Path(__file__).with_name('acquire.py'), Path(__file__).with_name('SELECTION.md'),
               ROOT / 'scripts/fetch_corpus.py', REGISTRY]
    report = dict(schema='public-source-admission-4', created=datetime.now(timezone.utc).isoformat(),
                  role='acquired-unscored; raw integrity and structural relationship coverage only',
                  python=platform.python_version(),
                  methods={p.relative_to(ROOT).as_posix(): fingerprint(p) for p in methods},
                  fetch_receipts=[], files=[], errors=[])
    fetcher.FILE_SOURCES.update(sources)
    if args.fetch:
        try:
            report['fetch_receipts'].append(fetcher.fetch_pinned(SOURCE, args.max_mb, dest))
        except Exception as error:
            report['errors'].append(dict(stage='fetch', error=f'{type(error).__name__}: {error}'))
    tables = {name: [] for name in TABLES}
    for name, pin in pins[SOURCE].items():
        item = dict(path=name, bytes=pin['bytes'], sha256=pin['sha256'], role=pin['role'])
        try:
            raw = (dest / name).read_bytes()
            fetcher.check_bytes(name, raw, pin['bytes'], pin['sha256'])
            item['integrity'] = 'match'
            data = json.loads(raw)
            if pin['role'] == 'metadata':
                if not isinstance(data, dict) or not isinstance(data.get('columns'), list):
                    raise ValueError('Expected Socrata view metadata')
                item['inspection'] = dict(view_id=data['id'], projected_schema_source=True,
                                          license_id=data.get('licenseId'),
                                          field_names=[c['fieldName'] for c in data['columns'] if not c['fieldName'].startswith(':')])
            else:
                if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
                    raise ValueError('Expected JSON record array')
                tables[pin['role']].extend(data)
                item['inspection'] = dict(rows=len(data), schema='explicit source API field projection')
        except Exception as error:
            item['error'] = f'{type(error).__name__}: {error}'
            report['errors'].append(dict(path=name, stage='integrity/inspection', error=item['error']))
        report['files'].append(item)
    if not report['errors']:
        report['relationship_coverage'] = relationships(tables)
        report['errors'].extend(dict(stage='relationship coverage', error=e)
                                for e in report['relationship_coverage']['errors'])
    (args.out / 'admission.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(files=len(report['files']), relationship_coverage=report.get('relationship_coverage'),
                          errors=report['errors']), indent=2))
    return int(bool(report['errors']))


if __name__ == '__main__':
    raise SystemExit(run())
