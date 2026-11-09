"""Bounded acquisition of the already selected reserved AMPS request-date cohort.

No alternative interval or outcome filtering. Retains failed responses/attempts.
Only run after the method freeze described in PLAN.md.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('retained_amps_recipe', HERE.parent / 'public-data/round-4/acquire.py')
recipe = importlib.util.module_from_spec(spec); spec.loader.exec_module(recipe)
START, END = '2024-01-15', '2024-01-22'


def run(out):
    out = Path(out)
    if out.exists():
        raise ValueError('Choose a new destination; retain earlier attempts')
    out.mkdir(parents=True)
    now = lambda: datetime.now(timezone.utc).isoformat()
    report = dict(schema='amps-linked-acquisition-1', started=now(),
                  selection=START + ' <= evt_date < ' + END + '; all outcomes',
                  snapshot_consistency='sequential current-row reads, no transactional or historical snapshot',
                  recipe_sha256=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
                  shared_recipe_sha256=hashlib.sha256(Path(recipe.__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
                  files=[], errors=[])
    used = 0
    def get(name, url, role):
        nonlocal used
        entry = dict(path=name, url=url, role=role, attempts=[]); report['files'].append(entry)
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'industrial-context-toolkit public maintenance validation'})
                with urllib.request.urlopen(request, timeout=60) as response:
                    raw = response.read(20_000_001 - used)
                    entry['http_status'] = response.status
                used += len(raw); (out / name).write_bytes(raw)
                entry.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                entry['attempts'].append(dict(attempt=attempt + 1, state='received'))
                if used > 20_000_000:
                    raise ValueError('20 MB response budget exceeded; retained body incomplete')
                print(name, len(raw), 'bytes', flush=True)
                return json.loads(raw)
            except (urllib.error.URLError, TimeoutError) as error:
                entry['attempts'].append(dict(attempt=attempt + 1, error=str(error)))
                if attempt == 2 or isinstance(error, urllib.error.HTTPError) and error.code not in (429, 502, 503, 504):
                    raise
                time.sleep(2)
    def query(table, where, batch, ceiling):
        table_id, key, fields = recipe.TABLES[table]
        params = {'$select': fields, '$where': where, '$order': key, '$limit': str(ceiling + 1)}
        rows = get(f'{table}-{batch:03d}.json', f'https://data.cityofnewyork.us/resource/{table_id}.json?' + urllib.parse.urlencode(params), table)
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows) or len(rows) > ceiling:
            raise ValueError(table + ': non-array or bounded query overflow')
        return rows
    def related(table, ids, field, numeric=False, extra=''):
        rows = []
        for start in range(0, len(ids), 100):
            rows.extend(query(table, recipe.predicate(field, ids[start:start + 100], numeric) + extra, start // 100, 10000))
        if not ids:
            raw = b'[]\n'; name = table + '-000.json'; (out / name).write_bytes(raw)
            report['files'].append(dict(path=name, role=table, generated_empty_because='No selected parent identifiers', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        return rows
    try:
        for table, (table_id, _, _) in recipe.TABLES.items():
            get('metadata-' + table + '.json', f'https://data.cityofnewyork.us/api/views/{table_id}.json', 'metadata')
        work = query('work-orders', f"evt_date >= '{START}T00:00:00' AND evt_date < '{END}T00:00:00'", 0, 5000)
        if not work:
            raise ValueError('Empty selected work-order cohort; no useful coverage claim')
        ids = recipe.values(work, 'evt_code')
        assets = related('assets', recipe.values(work, 'evt_object'), 'obj_code')
        trans = related('transactions', ids, 'tra_tocode', extra=" AND tra_toentity = 'EVNT'")
        details = related('details', recipe.values(trans, 'tra_code'), 'trl_trans', numeric=True)
        labor = related('labor', ids, 'boo_event', numeric=True)
        report['rows'] = dict(zip(recipe.TABLES, map(len, (work, assets, trans, details, labor))))
    except Exception as error:
        report['errors'].append(type(error).__name__ + ': ' + str(error))
    report.update(finished=now(), body_bytes=used)
    (out / 'ACQUISITION.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('rows', 'errors') if k in report}, indent=2))
    return bool(report['errors'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--out', required=True, type=Path)
    raise SystemExit(run(ap.parse_args().out))
