"""Author redistributable fictional export layouts; no public records or plant truth."""
import argparse
import csv
import json
from pathlib import Path


def records():
    assets = [dict(id='P-101', scope='U1', description='Feed pump', kind='equipment'),
              dict(id='P-101', scope='U2', description='Cooling pump', kind='equipment'),
              dict(id='PARK', scope='U1', description='Fictional grounds system', kind='system')]
    def wo(n, asset, scope='U1', cls='seal', typ='CM', job='REPAIR', created='2024-01-02', completed='2024-01-03', reopened='N', parent=''):
        return dict(id=n, scope=scope, asset_id=asset, description='Inspect ' + cls, work_class=cls,
                    order_type=typ, job_type=job, created=created, completed=completed, reopened=reopened, parent_id=parent)
    orders = [wo('W1', 'P-101'), wo('W2', 'P-101', created='2024-01-05', completed='', reopened='?', parent='W1'),
              wo('W3', 'P-101', cls='inspection', typ='PPM', job='SCHD', created='2024-01-07', completed='2024-01-07'),
              wo('W4', 'P-101', scope='U2'), wo('W5', 'MISSING', created='03/04/2024', completed=''),
              wo('W6', 'PARK', cls='grounds', typ='PPM', job='SCHD'),
              wo('W7', 'PARK', cls='grounds', typ='PPM', job='SCHD', created='2024-01-06', completed='2024-01-07')]
    orders[0]['description'] = 'Inspect seal\nRetain source line; effectiveness unknown'
    def tx(n, order, scope='U1', entity='WORK', status='A'):
        return dict(id=n, scope=scope, work_order_id=order, entity=entity, status=status, type='I', date='2024-01-03')
    transactions = [tx('T1', 'W1'), tx('T2', 'W1'), tx('T3', 'W2', entity='ASSET'), tx('T4', 'W4', scope='U2', status='C')]
    def detail(n, transaction, order, qty, scope='U1'):
        return dict(id=n, scope=scope, transaction_id=transaction, work_order_id=order, part_id='SEAL-01',
                    description='Fictional seal', quantity=qty, unit='EA', price='10', date='2024-01-03')
    details = [detail('D1', 'T1', 'W1', '2'), detail('D2', 'T2', 'W1', '-1'), detail('D3', 'T3', 'W2', '100'),
               detail('D4', 'T4', 'W4', '3', scope='U2'), detail('D5', 'T1', 'W2', '5')]
    def labor(n, order, h, flag='N', scope='U1'):
        return dict(id=n, scope=scope, work_order_id=order, date='2024-01-03', hours=h, correction=flag, trade='Mechanical')
    return dict(assets=assets, work_orders=orders, transactions=transactions, details=details,
                labor=[labor('L1', 'W1', '2'), labor('L2', 'W1', '-0.5', 'Y'), labor('L3', 'W1', '0'),
                       labor('L4', 'W2', '1', '?'), labor('L5', 'W4', '3', scope='U2'), labor('L6', 'ABSENT', '4')])


def write(root, layout='comma', data=None, revision='1'):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    data = records() if data is None else data
    p = dict(schema='maintenance-history-1', namespace='FICTIONAL', question='Which selected work records need investigation or reconciliation?',
             as_of='2024-01-31', recurring_fields=['work_class', 'order_type', 'job_type'],
             labor_ledger=dict(mode='signed_all_entries', unit='h', basis='Authored fixture: hours are an additive signed ledger, including correction and zero entries.'), sources={})
    for kind, rows in data.items():
        canonical_fields = list(records()[kind][0])
        fields = list(dict.fromkeys(canonical_fields + [k for row in rows for k in row]))
        headers = {f: ('Export ' + f.replace('_', ' ').title() if layout == 'semicolon' else f) for f in fields}
        fmt = 'json' if layout == 'json' else 'csv'
        name = kind + ('.json' if fmt == 'json' else '.csv')
        if fmt == 'json':
            (root / name).write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8', newline='\n')
        else:
            with (root / name).open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(headers.values()), delimiter=';' if layout == 'semicolon' else ',', lineterminator='\n')
                writer.writeheader(); writer.writerows({headers[k]: v for k, v in row.items()} for row in rows)
        spec = dict(id='FIX-' + kind, revision=revision, owner='Maintenance records owner', coverage='Authored selected-record excerpt; no absence or installed-state guarantee',
                    format=fmt, files=[dict(path=name)], columns={name: field for field, name in headers.items()},
                    date_formats={f: 'iso_date' for f in fields if f in ('created', 'completed', 'date')})
        if spec['date_formats']:
            spec['time_basis'] = 'Authored calendar dates only; within-day event order unspecified'
        if layout == 'semicolon':
            spec['delimiter'] = ';'
        if kind == 'work_orders':
            spec['flags'] = dict(reopened=dict(true=['Y'], false=['N']))
            spec['labels'] = dict(order_type=dict(CM='Corrective work order', PPM='Planned preventative maintenance'))
        if kind == 'labor':
            spec['flags'] = dict(correction=dict(true=['Y'], false=['N']))
        if kind == 'transactions':
            spec['work_order_entities'] = ['WORK']
            spec['labels'] = dict(status=dict(A='Approved', C='Cancelled'), type=dict(I='Issue'))
        p['sources'][kind] = spec
    (root / 'profile.json').write_text(json.dumps(p, indent=2) + '\n', encoding='utf-8', newline='\n')
    return root / 'profile.json'


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        ap.error('Choose a new directory')
    for layout in ('comma', 'semicolon', 'json'):
        write(args.out / layout, layout)
