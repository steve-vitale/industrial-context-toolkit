"""Nestor excavator records through the maintenance-history tool, scored on the publisher's system codes.

Source-specific profile and scorer driver for `nestor-excavators` (data/corpus_depth.json); not a generic adapter.
The tool (scripts/maintenance_history.py) reads only the raw export `excavators.csv` (BscStartDate, Asset,
OriginalShorttext, PMType; Cost is ignored) and derives a system class from each short text with the declared
vocabulary in nestor/system_vocabulary.json. The key, the cleaned file's MajorSystem column, is read only by
scripts/score_maintenance_systems.py, after the packet is written. Originals stay local (terms unresolved): this
script reads them from the pinned cache and checks their sha256 against data/corpus_pins.json.

  python examples/maintenance-history/nestor.py --split development --out NEW_DIR
  python examples/maintenance-history/nestor.py --split held-out --out NEW_DIR   # refused unless the method is frozen

The split was decided on 2026-11-12, before any result: development assets A, B and C; held out D and E.
"""
import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(HERE))
import maintenance_history as mh  # noqa: E402
import score_maintenance_systems as scorer  # noqa: E402
from baseline import group  # noqa: E402

GROUP = 'nestor-excavators'
RAW = 'nestor/datasets/excavators.csv'
CLEANED = 'nestor/datasets/excavators-cleaned.csv'
SPLITS = {'development': ['A', 'B', 'C'], 'held-out': ['D', 'E']}
VOCABULARY = HERE / 'nestor' / 'system_vocabulary.json'
FREEZE = HERE / 'nestor' / 'FREEZE.json'
# Fixed from the development key before any held-out read: the most frequent development system.
MAJORITY = 'Hydraulic System'
# Matrix and benchmark pass margin, fixed 2026-11-12 before the first held-out run: the tool's per-order F1 must beat
# the best deliberately wrong control by at least this much on each split.
PASS_MARGIN = 0.20
FROZEN_FILES = ('scripts/maintenance_history.py', 'scripts/maintenance_history_report.py', 'scripts/maintenance_intake.py',
                'scripts/score_maintenance_systems.py', 'examples/maintenance-history/nestor.py',
                'examples/maintenance-history/baseline.py', 'examples/maintenance-history/nestor/system_vocabulary.json')


def lf_sha(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def pinned(source, rel):
    pins = json.loads((ROOT / 'data/corpus_pins.json').read_bytes())[GROUP]
    path = Path(source) / rel
    mh.require(path.is_file(), 'Local original absent (fetch-by-hash, not committed): ' + str(path))
    mh.require(hashlib.sha256(path.read_bytes()).hexdigest() == pins[rel]['sha256'], 'Original bytes differ from the pin: ' + rel)
    return path, pins[rel]['sha256']


def frozen_problems():
    if not FREEZE.is_file():
        return ['no method freeze recorded (examples/maintenance-history/nestor/FREEZE.json)']
    freeze = json.loads(FREEZE.read_bytes())
    return [rel + ' changed since the freeze' for rel, h in freeze['files_sha256_lf'].items() if lf_sha(ROOT / rel) != h]


def profile(source, split, target):
    """Write assets.csv and profile.json for one split into a new folder; return the profile path."""
    target = Path(target)
    mh.require(not target.exists(), 'Profile folder exists; choose a new one')
    raw, digest = pinned(source, RAW)
    vocabulary = json.loads(VOCABULARY.read_bytes())
    target.mkdir(parents=True)
    with (target / 'assets.csv').open('w', encoding='utf-8', newline='') as stream:
        w = csv.writer(stream, lineterminator='\n')
        w.writerow(['id', 'description'])
        # Asset letters from the publisher's loader categories (nestor/datasets/excavators.py), not from the rows.
        w.writerows([a, 'Excavator ' + a] for a in SPLITS[split])
    scope = 'NESTOR-EXCAVATORS'
    p = dict(schema=mh.SCHEMA, namespace=scope, as_of='2012-12-31',
             question='Which systems keep coming back on each excavator, and which records support that?',
             recurring_fields=['work_class'], sources=dict(
                 assets=dict(id='NESTOR-assets-' + split, revision='authored-2026-11-12', owner='Fleet maintenance records owner',
                             coverage='Asset letters from the publisher loader categories; ' + split + ' split ' + ', '.join(SPLITS[split]),
                             files=[dict(path='assets.csv')], constants=dict(scope=scope),
                             columns=dict(id='id', description='description')),
                 work_orders=dict(id='NESTOR-excavators-raw', revision=digest[:16], owner='Fleet maintenance records owner',
                                  coverage='Published raw excavator work orders (usnistgov/nestor 1d9cd96); selected assets '
                                           + ', '.join(SPLITS[split]) + '; no work-order id, so the CSV record number is the identity',
                                  files=[dict(path=str(raw), sha256=digest)], constants=dict(scope=scope), identity='record',
                                  columns=dict(BscStartDate='created', Asset='asset_id', OriginalShorttext='description', PMType='order_type'),
                                  ignored_columns=['Cost'], select=dict(asset_id=SPLITS[split]),
                                  date_formats=dict(created='iso_date'),
                                  time_basis='Work-order start date only (BscStartDate); timezone and within-day order unknown',
                                  labels=dict(order_type=dict(PM01='Repair (publisher loader docstring)', PM02='Replacement (publisher loader docstring)')),
                                  derive=dict(work_class=dict(source=vocabulary['source'], rules=vocabulary['rules'], basis=vocabulary['basis'])))))
    mh.dump(target / 'profile.json', p)
    return target / 'profile.json'


def answer(result):
    """Record number -> derived class ('' when none), read from the packet's result; checks the tool's groups agree."""
    orders = result['all_records']['work_orders']
    assigned = {w['id']: w.get('work_class', '') for w in orders}
    mine = Counter((w['asset_id'], w['work_class']) for w in orders if w.get('work_class'))
    tool = {(d['key'][1], g['fields']['work_class']): g['selected_order_count'] for d in result['assets'] for g in d['recurring_work']}
    mh.require(tool == {k: n for k, n in mine.items() if n >= 2}, 'Packet recurring groups disagree with its own derived classes')
    return assigned


def procedural(source, result, split):
    """Independent original-row checks: selected counts, record locators, chronology and exclusions."""
    raw, _ = pinned(source, RAW)
    with raw.open(encoding='utf-8-sig', newline='') as stream:
        rows = {str(n): r for n, r in enumerate(csv.DictReader(stream), 2)}
    selected = {n: r for n, r in rows.items() if r['Asset'] in SPLITS[split]}
    per_asset = Counter(r['Asset'] for r in selected.values())
    orders = result['all_records']['work_orders']
    checks = dict(
        selected_count=len(orders) == len(selected) and result['selection']['work_orders']['excluded'] == len(rows) - len(selected),
        per_asset_counts={d['key'][1]: len(d['work_orders']) for d in result['assets']} == dict(per_asset),
        record_locators=all(w['origin']['record'] == int(w['id']) and selected.get(w['id'], {}).get('BscStartDate') == w['created'] and
                            selected[w['id']]['Asset'] == w['asset_id'] and selected[w['id']]['OriginalShorttext'] == w['description']
                            for w in orders),
        chronology=all([o['record']['created'] for o in d['work_orders']] == sorted(o['record']['created'] for o in d['work_orders'])
                       for d in result['assets']),
        all_linked=result['relationship_coverage']['work_orders']['unlinked'] == 0)
    return dict(checks=checks, passed=all(checks.values()), selected_rows=len(selected), per_asset=dict(sorted(per_asset.items())))


def run(split, out, source=None):
    source = Path(source or ROOT / 'data' / 'external' / GROUP)
    out = Path(out)
    mh.require(split in SPLITS, 'Unknown split')
    if split == 'held-out':
        problems = frozen_problems()
        mh.require(not problems, 'Held-out run refused: ' + '; '.join(problems))
    mh.require(not out.exists(), 'Choose a new output folder')
    prof = profile(source, split, out / 'profile')
    result = mh.run(prof, out / 'packet')
    assigned = answer(result)
    cleaned, _ = pinned(source, CLEANED)
    scored = scorer.evaluate(pinned(source, RAW)[0], cleaned, SPLITS[split], assigned, MAJORITY)
    base = group([dict(asset_id=w['asset_id']) for w in result['all_records']['work_orders']])
    report = dict(schema='nestor-system-grouping-1', split=split, assets=SPLITS[split],
                  procedural=procedural(source, result, split), score=scored,
                  raw_asset_baseline=dict(method=base['method'], groups=len(base['counts']), boundary=base['boundary']),
                  orders_margin_over_best_wrong_control=scorer.margin(scored['scores']),
                  pass_margin=PASS_MARGIN,
                  tool=dict(issues=dict(sorted(Counter(i['code'] for i in result['issues']).items())),
                            recurring_groups=sum(len(d['recurring_work']) for d in result['assets']),
                            unclassified=sum(len(d['unclassified_orders']) for d in result['assets'])),
                  frozen=not frozen_problems())
    report['passed'] = (report['procedural']['passed'] and not scored['control_problems']
                        and report['orders_margin_over_best_wrong_control'] >= PASS_MARGIN)
    mh.dump(out / 'score.json', report)
    return report, assigned


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--split', required=True, choices=sorted(SPLITS))
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--source', type=Path, help='folder holding the pinned nestor-excavators originals (default data/external/nestor-excavators)')
    a = ap.parse_args()
    report, _ = run(a.split, a.out, a.source)
    print(json.dumps({k: report[k] for k in ('split', 'procedural', 'orders_margin_over_best_wrong_control', 'passed')}, indent=1))
    print(json.dumps({n: v['rates'] for n, v in report['score']['scores'].items()}, indent=1))
