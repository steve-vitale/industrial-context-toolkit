"""Source-specific AMPS profile and independent original-row check; not a generic CMMS adapter."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import maintenance_history as mh
from baseline import group

MAPS = {
 'assets': dict(obj_code='id', obj_desc='description', obj_obtype='type', obj_manufact='manufacturer', obj_serialno='serial', obj_manufactmodel='model'),
 'work_orders': dict(evt_code='id', evt_desc='description', evt_type='order_type', evt_date='created', evt_object='asset_id', evt_class='work_class', evt_jobtype='job_type', evt_completed='completed', evt_reopened='reopened', evt_parent='parent_id'),
 'transactions': dict(tra_code='id', tra_type='type', tra_date='date', tra_status='status', tra_fromcode='from_id', tra_toentity='entity', tra_tocode='work_order_id'),
 'details': dict(trl_sqlidentity='id', trl_trans='transaction_id', trl_type='type', trl_date='date', trl_event='work_order_id', trl_part='part_id', trl_price='price', trl_qty='quantity', par_code='catalog_part_id', par_desc='description', par_uom='unit'),
 'labor': dict(boo_code='id', boo_event='work_order_id', boo_date='date', boo_trade='trade', boo_hours='hours', boo_rate='rate', boo_cost='cost', boo_correction='correction'),
}
ROLES = {k: 'work-orders' if k == 'work_orders' else k for k in MAPS}


def profile(source, target):
    source, target = Path(source).resolve(), Path(target).resolve()
    if target.exists():
        raise ValueError('Profile destination exists')
    acq = source / 'ACQUISITION.json'
    if acq.exists():
        receipt = json.loads(acq.read_bytes())
        mh.require(not receipt['errors'], 'Retain acquisition failure; no useful-cohort claim')
        pins = {f['path']: f for f in receipt['files']}
        coverage = receipt['selection'] + '; sequential current-row reads; acquired ' + receipt['finished']
    else:
        pins = json.loads((ROOT / 'data/corpus_pins.json').read_bytes())['nyc-amps-2024w01']
        coverage = '2024-01-01 <= evt_date < 2024-01-08; linked rows acquired 2026-11-07; sequential current rows, not a historical snapshot'
    p = dict(schema=mh.SCHEMA, namespace='NYC-PARKS-AMPS', as_of='2026-11-08',
             question='Which selected administrative work histories and source meanings need investigation?',
             recurring_fields=['work_class', 'order_type', 'job_type'],
             labor_ledger=dict(mode='signed_all_entries', unit='h', basis='Publisher dictionary Labor!M10: additive ledger including correction entries; not productive/wrench hours or actual payroll.'), sources={})
    for kind, mapping in MAPS.items():
        files, headers = [], set()
        for name in sorted(pins):
            if not name.startswith(ROLES[kind] + '-') or not name.endswith('.json'):
                continue
            path = source / name
            raw = path.read_bytes()
            mh.require(hashlib.sha256(raw).hexdigest() == pins[name]['sha256'], 'Original bytes differ: ' + name)
            headers.update(k for row in json.loads(raw) for k in row)
            files.append(dict(path=str(path), sha256=pins[name]['sha256']))
        # A valid acquisition may return zero related rows and hence no query files.
        # The bounded recipe writes explicit empty tables for those roles (see acquire_reserved.py).
        mh.require(files, 'No retained source files for ' + kind)
        revision = mh.digest([f['sha256'] for f in files])
        spec = dict(id='NYC-AMPS-' + kind, revision=revision, owner='AMPS source records owner', coverage=coverage + '; related selection only, not complete asset history',
                    format='json', encoding='utf-8', constants=dict(scope='AMPS'), columns=mapping,
                    ignored_columns=sorted(headers - set(mapping)), files=files,
                    date_formats={f: 'iso_datetime' if f == 'created' else 'english_datetime' for f in mapping.values() if f in mh.DATE_FIELDS},
                    time_basis='Source floating timestamp; timezone not declared here')
        if kind == 'assets':
            spec['labels'] = dict(type=dict(A='Asset', S='System'))
        if kind == 'work_orders':
            spec['labels'] = dict(order_type=dict(JOB='Work order', PPM='Planned preventative maintenance', IN='Inspection'), job_type={})
        if kind == 'labor':
            spec['flags'] = dict(correction=dict(true=['+'], false=['-']))
        if kind == 'transactions':
            spec['work_order_entities'] = ['EVNT']
            spec['labels'] = dict(type=dict(CORR='Correction', I='Issue', MISC='Miscellaneous', MPTC='Manual price type change', RECV='Receipt', STTK='Stock take'), status=dict(A='Approved', C='Cancelled', U='Unfinished'))
        p['sources'][kind] = spec
    target.parent.mkdir(parents=True, exist_ok=True); mh.dump(target, p)
    return p


def audit(source, packet):
    """Independent joins and signed totals from publisher columns; no analyze() calls."""
    source, packet = Path(source), Path(packet)
    rows = {kind: [r for f in sorted(source.glob(role + '-*.json')) for r in json.loads(f.read_bytes())] for kind, role in ROLES.items()}
    result = json.loads((packet / 'result.json').read_bytes())
    a = {str(r['obj_code']) for r in rows['assets']}
    w = {str(r['evt_code']): r for r in rows['work_orders']}
    t = {str(r['tra_code']): r for r in rows['transactions'] if r.get('tra_toentity') == 'EVNT' and str(r.get('tra_tocode', '')) in w}
    d = [r for r in rows['details'] if str(r.get('trl_trans')) in t and
         (not r.get('trl_event') or str(r['trl_event']) == str(t[str(r['trl_trans'])]['tra_tocode']))]
    l = [r for r in rows['labor'] if str(r.get('boo_event')) in w]
    linked = dict(work_orders=sum(str(r.get('evt_object')) in a for r in w.values()), transactions=len(t), details=len(d), labor=len(l))
    expected_counts = {kind: len(value) for kind, value in rows.items()}
    checks = dict(original_counts=result['counts'] == expected_counts,
                  qualified_joins=all(result['relationship_coverage'][kind]['linked'] == n for kind, n in linked.items()))
    baseline = group([dict(asset_id=str(r.get('evt_object', ''))) for r in w.values()])
    selected = Counter(str(r.get('evt_object')) for r in w.values())
    hours = defaultdict(list)
    for row in l:
        hours[str(w[str(row['boo_event'])].get('evt_object'))].append(row.get('boo_hours', ''))
    bad_hours = 0
    for dossier in result['assets']:
        identity = dossier['key'][1]
        checks['asset_order_counts'] = checks.get('asset_order_counts', True) and len(dossier['work_orders']) == selected[identity]
        values = hours[identity]
        try:
            value = sum((Decimal(str(x)) for x in values), Decimal(0)) if values else None
            good = value is None and dossier['booked_hours']['value'] is None or value is not None and value.is_finite() and Decimal(dossier['booked_hours']['value']) == value
        except Exception:
            bad_hours += 1; good = dossier['booked_hours']['value'] is None
        checks['per_asset_signed_hours'] = checks.get('per_asset_signed_hours', True) and good
    groups = Counter((str(r.get('evt_object', '')), str(r.get('evt_class', '')), str(r.get('evt_type', '')), str(r.get('evt_jobtype', '')))
                     for r in w.values() if str(r.get('evt_object', '')) in a and all(r.get(f) for f in ('evt_class', 'evt_type', 'evt_jobtype')))
    expected_groups = {(k[0], *k[1:]): n for k, n in groups.items() if n >= 2}
    actual_groups = {(x['key'][1], g['fields']['work_class'], g['fields']['order_type'], g['fields']['job_type']): g['selected_order_count']
                     for x in result['assets'] for g in x['recurring_work']}
    checks['recurring_groups'] = expected_groups == actual_groups
    # Every emitted locator must identify the earliest retained publisher bytes,
    # not just another representation generated by the analysis.
    locators = True
    originals = json.loads((packet / 'input-profile.json').read_bytes())
    cached = {}
    for kind, emitted in result['all_records'].items():
        for row in emitted:
            origin = row['origin']; pfile = Path(origin['member']).name
            f = originals['sources'][kind]['files'][int(pfile.split('.')[0]) - 1]
            original = Path(f['path'])
            if original not in cached:
                raw = original.read_bytes(); cached[original] = (json.loads(raw), hashlib.sha256(raw).hexdigest())
            records, h = cached[original]
            actual = records[origin['record'] - 1]
            pk = next(k for k, v in MAPS[kind].items() if v == 'id')
            locators = locators and str(actual[pk]) == row['id'] and h == origin['sha256'] and mh.sha(packet / origin['member']) == h
    checks['every_record_locator'] = locators
    return dict(schema='maintenance-history-public-audit-1', checks=checks, passed=all(checks.values()),
                rows=expected_counts, linked=linked, invalid_hours_asset_count=bad_hours,
                baseline=dict(method=baseline['method'], raw_id_groups=len(baseline['counts']), count_distribution=dict(sorted(Counter(baseline['counts'].values()).items())), boundary=baseline['boundary']),
                tool=dict(scoped_assets=len(result['assets']), recurring_groups=sum(len(x['recurring_work']) for x in result['assets']),
                          issues=dict(Counter(x['code'] for x in result['issues']))),
                boundary='Original-column procedural checks, same source. No human review, planted public key, failure diagnosis, savings or plant acceptance.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', required=True, type=Path)
    ap.add_argument('--profile', type=Path)
    ap.add_argument('--packet', type=Path)
    ap.add_argument('--audit-out', type=Path)
    args = ap.parse_args()
    if args.profile:
        profile(args.source, args.profile)
    elif args.packet and args.audit_out:
        mh.require(not args.audit_out.exists(), 'Audit destination exists')
        report = audit(args.source, args.packet); mh.dump(args.audit_out, report)
        print(json.dumps(report, indent=2)); sys.exit(0 if report['passed'] else 1)
    else:
        ap.error('Use --profile NEW.json or --packet PACKET --audit-out NEW.json')
