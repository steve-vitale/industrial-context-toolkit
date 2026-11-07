"""One-time, bounded acquisition of the predeclared NYC AMPS linked cohort; no downloaded code runs."""
import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TABLES = {
    'work-orders': ('8sdw-8vja', 'evt_code', 'evt_code,evt_desc,evt_type,evt_date,evt_object,evt_obtype,evt_class,evt_jobtype,evt_priority,evt_reported,evt_start,evt_due,evt_completed,evt_reopened,evt_parent,evt_updated,evt_updatecount'),
    'assets': ('e25p-jzfy', 'obj_code', 'obj_code,obj_desc,obj_obtype,obj_class,obj_category,obj_position,obj_parent,obj_manufact,obj_serialno,obj_status,obj_commiss,obj_withdraw,obj_notused,obj_manufactmodel,obj_updated,obj_updatecount'),
    'transactions': ('gcys-vvnq', 'tra_code', 'tra_code,tra_desc,tra_type,tra_date,tra_status,tra_fromentity,tra_fromcode,tra_toentity,tra_tocode,tra_updated,tra_updatecount'),
    'details': ('ub9z-gccp', 'trl_sqlidentity', 'trl_trans,trl_type,trl_line,trl_date,trl_event,trl_part,trl_store,trl_price,trl_qty,trl_avgprice,trl_sqlidentity,par_code,par_desc,par_class,par_uom,par_notused'),
    'labor': ('xzj8-i3jk', 'boo_code', 'boo_code,boo_event,boo_date,boo_trade,boo_hours,boo_rate,boo_cost,boo_correction'),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def values(rows, field):
    return sorted({str(row[field]) for row in rows if row.get(field) not in (None, '')})


def predicate(field, identifiers, numeric=False):
    if numeric:
        if not all(v.isascii() and v.isdecimal() for v in identifiers):
            raise ValueError('Non-integer source identifier in numeric relationship')
        terms = identifiers
    else:
        terms = ["'" + v.replace("'", "''") + "'" for v in identifiers]
    return field + ' in (' + ','.join(terms) + ')'


def run(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True, help='new local directory for original API responses')
    ap.add_argument('--reuse', type=Path, action='append', default=[], help='reuse exact successful query bytes from retained incomplete attempts, oldest first')
    args = ap.parse_args(argv)
    if args.out.exists():
        ap.error('Output exists; retain it and choose another directory')
    args.out.mkdir(parents=True)
    report = dict(schema='amps-linked-acquisition-1', started=datetime.now(timezone.utc).isoformat(),
                  recipe_sha256=digest(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
                  selection_sha256=digest(Path(__file__).with_name('SELECTION.md').read_bytes().replace(b'\r\n', b'\n')),
                  selection='2024-01-01 <= evt_date < 2024-01-08; all outcomes',
                  snapshot_consistency='sequential live reads; no transactional snapshot', files=[], errors=[])
    used, downloaded = 0, 0
    cached = {}
    for directory in args.reuse:
        previous = json.loads((directory / 'ACQUISITION.json').read_bytes())
        for item in previous['files']:
            if item.get('error') or not item.get('sha256') or item['url'] in cached:
                continue
            if Path(item['path']).name != item['path']:
                ap.error('Unsafe cached filename')
            raw = (directory / item['path']).read_bytes()
            if len(raw) != item['bytes'] or digest(raw) != item['sha256']:
                ap.error('Cached bytes no longer match their retained attempt')
            cached[item['url']] = (raw, directory.name, item['role'])

    def get(name, url, role):
        nonlocal used, downloaded
        entry = dict(path=name, url=url, role=role)
        report['files'].append(entry)
        try:
            if url in cached:
                data, previous, previous_role = cached[url]
                if previous_role != role:
                    raise ValueError('Cached query role mismatch')
                entry['reused_from'] = previous
            else:
                entry['transport_attempts'] = []
                for attempt in range(3):
                    try:
                        request = urllib.request.Request(url, headers={'User-Agent': 'industrial-context-toolkit public data acquisition'})
                        with urllib.request.urlopen(request, timeout=60) as response:
                            data = response.read(20_000_001 - used)
                            entry['http_status'] = response.status
                        downloaded += len(data)
                        entry['transport_attempts'].append(dict(attempt=attempt + 1, status='received'))
                        break
                    except (urllib.error.URLError, TimeoutError) as error:
                        entry['transport_attempts'].append(dict(attempt=attempt + 1, error=f'{type(error).__name__}: {error}'))
                        if attempt == 2 or isinstance(error, urllib.error.HTTPError) and error.code not in (429, 502, 503, 504):
                            raise
                        time.sleep(2)
            used += len(data)
            (args.out / name).write_bytes(data)
            entry.update(bytes=len(data), sha256=digest(data))
            print(name, len(data), 'bytes', 'cached' if 'reused_from' in entry else 'received', flush=True)
            if used > 20_000_000:
                raise ValueError('20 MB total response budget exceeded; retained bounded body is incomplete')
            return json.loads(data)
        except Exception as error:
            entry['error'] = f'{type(error).__name__}: {error}'
            raise

    def query(table, where, batch, ceiling):
        table_id, key, fields = TABLES[table]
        params = {'$select': fields, '$where': where, '$order': key, '$limit': str(ceiling + 1)}
        url = f'https://data.cityofnewyork.us/resource/{table_id}.json?' + urllib.parse.urlencode(params)
        rows = get(f'{table}-{batch:03d}.json', url, table)
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError(f'{table}: response is not a record array')
        if len(rows) > ceiling:
            raise ValueError(f'{table}: bounded query overflow; retained rows do not establish completeness')
        return rows

    def related(table, ids, field, numeric=False, extra=''):
        rows = []
        for start in range(0, len(ids), 100):
            where = predicate(field, ids[start:start + 100], numeric)
            rows.extend(query(table, where + extra, start // 100, 10000))
        return rows

    try:
        for table, (table_id, _, _) in TABLES.items():
            get(f'metadata-{table}.json', f'https://data.cityofnewyork.us/api/views/{table_id}.json', 'metadata')
        work = query('work-orders', "evt_date >= '2024-01-01T00:00:00' AND evt_date < '2024-01-08T00:00:00'", 0, 5000)
        ids = values(work, 'evt_code')
        assets = related('assets', values(work, 'evt_object'), 'obj_code')
        trans = related('transactions', ids, 'tra_tocode', extra=" AND tra_toentity = 'EVNT'")
        details = related('details', values(trans, 'tra_code'), 'trl_trans', numeric=True)
        labor = related('labor', ids, 'boo_event', numeric=True)
        report['rows'] = {k: len(v) for k, v in zip(TABLES, [work, assets, trans, details, labor])}
    except Exception as error:
        report['errors'].append(f'{type(error).__name__}: {error}')
    report['body_bytes'] = used
    report['downloaded_bytes'] = downloaded
    report['finished'] = datetime.now(timezone.utc).isoformat()
    (args.out / 'ACQUISITION.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('rows', 'downloaded_bytes', 'errors') if k in report}, indent=2))
    return int(bool(report['errors']))


if __name__ == '__main__':
    sys.exit(run())
