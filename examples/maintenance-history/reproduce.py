"""Offline fictional history/revision replay, matched baseline and explicit checks."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts'))
import maintenance_history as mh
from fixtures import records, write
from baseline import group


def run(out):
    out = Path(out).resolve()
    mh.require(not out.exists(), 'Choose a new replay directory')
    out.mkdir(parents=True)
    results = {}
    for name, layout in [('initial', 'comma'), ('semicolon', 'semicolon'), ('json', 'json')]:
        profile = write(out / (name + '-inputs'), layout)
        results[name] = mh.run(profile, out / name)
    def facts(r):
        return [(a['key'], len(a['work_orders']), a['booked_hours']['value'], [g['orders'] for g in a['recurring_work']]) for a in r['assets']]
    expected = [(['U1', 'P-101'], 3, '2.5', [['W1', 'W2']]), (['U1', 'PARK'], 2, None, [['W6', 'W7']]), (['U2', 'P-101'], 1, '3', [])]
    mh.require(all(facts(r) == expected for r in results.values()), 'Authored facts differ')
    baseline = group(records()['work_orders'])
    mh.require(baseline['counts']['P-101'] == 4, 'Raw-ID baseline differs')
    changed = records(); changed['work_orders'][1]['completed'] = '2024-01-08'
    profile = write(out / 'corrected-inputs', data=changed, revision='2')
    mh.run(profile, out / 'corrected', out / 'initial')
    changed['work_orders'] = [r for r in changed['work_orders'] if r['id'] != 'W2']
    profile = write(out / 'omitted-inputs', data=changed, revision='3')
    final = mh.run(profile, out / 'omitted', out / 'corrected')
    rev = json.loads((out / 'omitted/revision.json').read_bytes())
    mh.require(any(r['identity'] == ['U1', 'W2'] and r['state'] == 'omitted' for r in rev['records']), 'Omission lost')
    replay = mh.run(out / 'omitted/job.json', out / 'portable')
    mh.require(replay == final, 'Portable substantive result differs')
    mh.verify_packet(out / 'portable')
    report = dict(schema='maintenance-history-replay-1', passed=True,
                  checks=['authored scoped counts and signed hours', 'two CSV layouts plus JSON', 'raw-ID baseline merges scopes',
                          'corrected then omitted source', 'prior evidence retained', 'portable substantive replay and recursive verification'],
                  baseline=baseline, authored_asset_facts=expected, methods_sha256_lf=mh.method_pins(),
                  boundary='Author-run fictional software controls; no independent agent/human review or measured manager benefit.')
    mh.dump(out / 'REPLAY.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', required=True, type=Path)
    run(p.parse_args().out)
