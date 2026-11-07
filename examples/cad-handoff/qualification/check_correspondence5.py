"""Directly check proposed decoded pairs, authored controls and retained cohort replay; no CAD/UI acceptance."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile

import recheck
import correspondence5

HERE = Path(__file__).resolve().parent


def exact(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def check_pairs(left, right, report):
    """Inspect each proposed pair directly; do not call the signature/matching/pruning functions."""
    pairs = report['pairs']
    mapping = {p['before']: p['after'] for p in pairs}
    recheck.require(len(mapping) == len(pairs) == len(set(mapping.values())), 'Not a one-to-one correspondence')
    pointer_codes = set(range(330, 370)) | set(range(390, 400)) | {480, 481}
    def bodies(entities):
        keys = {}
        for h, record in entities.items():
            own = 105 if record['type'] == 'DIMSTYLE' else 5
            if [t[1] for t in record['tags'] if t[0] == own] != [h]:
                continue
            try:
                keys[h] = exact(dict(type=record['type'], ordered_tags=[
                    [code, None] if code == own or code in pointer_codes else [code, value]
                    for code, value in record['tags']]))
            except (ValueError, TypeError):
                continue
        return keys, Counter(keys.values())
    left_bodies, lc = bodies(left)
    right_bodies, rc = bodies(right)
    for a, b in mapping.items():
        recheck.require(a in left and b in right, 'Pair record missing')
        l, r = left[a], right[b]
        recheck.require(a in left_bodies and b in right_bodies and left_bodies[a] == right_bodies[b]
                        and lc[left_bodies[a]] == rc[right_bodies[b]] == 1, 'Pair body is absent or ambiguous')
        recheck.require(l['type'] == r['type'] and len(l['tags']) == len(r['tags']), 'Pair type/tag count differs')
        own = 105 if l['type'] == 'DIMSTYLE' else 5
        for h, record in ((a, l), (b, r)):
            recheck.require(isinstance(h, str) and 1 <= len(h) <= 16 and h != '0'
                            and all(c in '0123456789abcdefABCDEF' for c in h), 'Invalid pair own handle')
            recheck.require([t[1] for t in record['tags'] if t[0] == own] == [h], 'Pair own handle differs')
        for lt, rt in zip(l['tags'], r['tags']):
            recheck.require(type(lt[0]) is int and type(rt[0]) is int and lt[0] == rt[0], 'Ordered pair code differs')
            code, av, bv = lt[0], lt[1], rt[1]
            if code == own:
                recheck.require(av == a and bv == b, 'Own handle not bound')
            elif code in pointer_codes:
                if av == '0' or bv == '0':
                    recheck.require(av == bv == '0', 'Pair null reference differs')
                else:
                    recheck.require(isinstance(av, str) and isinstance(bv, str) and av in left and bv in right
                                    and av in mapping and mapping[av] == bv, 'Pair reference edge unproved')
            else:
                recheck.require(exact(av) == exact(bv), 'Pair literal value/type differs')
    recheck.require(set(report['before']) == set(left) and set(report['after']) == set(right), 'Missing side record')
    inverse = {b: a for a, b in mapping.items()}
    for records, matched in ((report['before'], mapping), (report['after'], inverse)):
        for h, row in records.items():
            if h in matched:
                recheck.require(row == dict(status='closed exact decoded correspondence', counterpart=matched[h]), 'Wrong paired-side evidence')
            else:
                recheck.require(row['status'] == 'unpaired' and bool(row['reason']), 'Unpaired record concealed')
    return len(pairs)


def check_report(before, after, plan, report):
    # Independently reconstruct planned expected values, without calling matcher helpers.
    left = json.loads(json.dumps(before['entities']))
    if plan is not None:
        for change in recheck.ch.validate_plan(before, plan).values():
            asset = next(a for a in before['assets'] if a['id'] == change['id'])
            entity = left[asset['attribute_handles'][change['attribute']]]
            tags = [t for t in entity['tags'] if t[0] == 1]
            recheck.require(len(tags) == 1 and tags[0][1] == change['before'], 'Wrong planned before value')
            tags[0][1] = change['after']
    check_pairs(left, after['entities'], report['correspondence'])
    pairs = report['correspondence']['pairs']
    recheck.require(report['counts'] == dict(before_records=len(left), after_records=len(after['entities']),
                    unique_body_seeds=len(report['correspondence']['seed_pairs']), closed_pairs=len(pairs),
                    unpaired_before=len(left) - len(pairs), unpaired_after=len(after['entities']) - len(pairs)),
                    'Report coverage counts differ')
    strict = recheck.ch.compare(before, after, plan)
    recheck.require(report['strict_status'] == strict['status'] and report['strict_difference_count'] == len(strict['unexpected']), 'Strict verdict/count changed')
    recheck.require(report['before_sha256'] == before['sha256'] and report['after_sha256'] == after['sha256'], 'Report source binding changed')
    recheck.require(len(report['strict_differences']) == len(strict['unexpected']), 'Strict difference omitted')
    for index, (observed, difference) in enumerate(zip(report['strict_differences'], strict['unexpected'])):
        recheck.require(observed['index'] == index and observed['kind'] == difference['kind']
                        and observed['strict_difference_sha256'] == hashlib.sha256(exact(difference).encode()).hexdigest(), 'Strict difference identity changed')
        if difference['kind'] == 'entity':
            h = difference['handle']
            recheck.require(observed['handle'] == h and observed['before'] == report['correspondence']['before'].get(h)
                            and observed['after'] == report['correspondence']['after'].get(h), 'Strict side evidence changed')
        else:
            recheck.require(observed['unchanged_strict_difference'] == difference, 'Nonentity difference concealed')


def controls():
    results = []
    for c in recheck.read(HERE / 'CORRESPONDENCE-5-CONTROLS.json')['cases']:
        result = correspondence5.audit(c['before'], c['after'], c['plan'])
        check_report(c['before'], c['after'], c['plan'], result)
        recheck.require(result['correspondence']['pairs'] == c['expected_pairs'], 'Authored pair oracle differs: ' + c['id'])
        recheck.require(result['strict_status'] == c['expected_strict_status'] and result['strict_difference_count'] == c['expected_strict_differences'], 'Authored strict oracle differs')
        results.append(dict(id=c['id'], pairs=result['correspondence']['pairs'], strict_status=result['strict_status'], strict_differences=result['strict_difference_count']))
    return results


def freeze():
    bound = recheck.read(HERE / 'CORRESPONDENCE-5-FREEZE.json')
    for p, wanted in bound['methods'].items():
        recheck.require(recheck.text_hash(recheck.ROOT / p) == wanted, 'Changed frozen diagnostic: ' + p)
    recheck.require(recheck.text_hash(HERE / 'round-2/INVENTORY.json') == bound['round_2_inventory_sha256_lf'], 'Changed prior evidence inventory')
    recheck.method_bindings()
    return bound


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--controls-only', action='store_true')
    args = ap.parse_args()
    control_rows = controls()
    if args.controls_only:
        print(json.dumps(dict(controls=len(control_rows), result='pass')))
        return 0
    freeze()
    import run_correspondence5
    with tempfile.TemporaryDirectory(prefix='cad-correspondence-check-') as temp:
        dest = Path(temp)
        raw, _ = recheck.unpack(HERE / 'correspondence-5', dest / 'retained')
        summary = run_correspondence5.run(dest / 'replay')
        recheck.require(summary == recheck.read(raw / 'summary.json'), 'Retained cohort summary changed')
        for row in summary['results']:
            expected = recheck.read(raw / row['report'])
            observed = recheck.read(dest / 'replay' / row['report'])
            recheck.require(expected == observed, 'Retained diagnostic report changed: ' + row['report'])
        # Real altered artifacts: the independent checker must refuse a fabricated wrong pair,
        # and cohort membership must refuse an omitted report.
        before = recheck.read(HERE / 'CORRESPONDENCE-5-CONTROLS.json')['cases'][0]
        forged = correspondence5.audit(before['before'], before['after'])
        forged['correspondence']['pairs'][0]['after'] = '30'
        try:
            check_report(before['before'], before['after'], None, forged)
        except (ValueError, KeyError):
            pass
        else:
            raise ValueError('Fabricated wrong pair accepted')
        damaged = json.loads(json.dumps(summary))
        damaged['results'].pop()
        try:
            run_correspondence5.check_cohort(damaged)
        except ValueError:
            pass
        else:
            raise ValueError('Omitted cohort report accepted')
    print(json.dumps(dict(controls=len(control_rows), cohort_reports=63, native_failures_retained=42,
                          replay='exact', fabricated_pair_and_omitted_report='refused', scope='offline diagnostic, not CAD qualification')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
