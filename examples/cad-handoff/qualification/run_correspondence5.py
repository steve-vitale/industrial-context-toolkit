"""Audit the fixed retained native cohort and matched candidates, without native/model calls."""
import argparse
import json
from pathlib import Path

import recheck
import correspondence5
import check_correspondence5 as checker

HERE = Path(__file__).resolve().parent
ROUTES = ('candidate', 'native_default', 'native_r15')


def check_cohort(summary):
    wanted = {(c['id'], route) for c in recheck.cohort() for route in ROUTES}
    got = [(r['id'], r['route']) for r in summary['results']]
    recheck.require(len(got) == len(set(got)) == 63 and set(got) == wanted, 'Omitted/extra/duplicate cohort report')
    recheck.require(all((r['strict_status'] == 'pass') == (r['route'] == 'candidate') for r in summary['results']), 'Strict failure reclassified')


def run(out):
    out = Path(out)
    recheck.require(not out.exists(), 'Output exists; choose a new destination')
    checker.freeze()
    controls = checker.controls()
    out.mkdir(parents=True)
    raw, archive = recheck.unpack(HERE / 'round-2', out / 'prior')
    expected = {c['id']: c for c in recheck.cohort()}
    rows = []
    for directory, count in [('native-2-development', 9), ('native-validation-2', 12)]:
        cases = recheck.read(raw / directory / 'edited-manifest.json')['cases']
        recheck.require(len(cases) == count, 'Changed retained manifest count')
        for case in cases:
            source = recheck.saved_file(case['source'], raw)
            plan_path = recheck.saved_file(case['plan'], raw)
            plan = recheck.read(plan_path)
            known = expected[case['id']]
            recheck.require(recheck.ch.digest(source) == recheck.ch.digest(known['source'])
                            and recheck.ch.digest(plan_path) == recheck.ch.digest(known['plan']), 'Source/plan cohort binding changed')
            before = recheck.ch.snapshot(source)
            for route in ROUTES:
                returned = recheck.saved_file(case[route], raw)
                after = recheck.ch.snapshot(returned)
                strict = recheck.ch.compare(before, after, plan)
                retained = recheck.read(raw / directory / f"{case['id']}-{route}-comparison.json")
                # Existing informational on-read date diagnostic is unchanged; compare all strict fields exactly.
                recheck.require({k: v for k, v in strict.items() if k != 'save_metadata_changed'} ==
                                {k: v for k, v in retained.items() if k != 'save_metadata_changed'}, 'Retained strict comparison differs')
                report = correspondence5.audit(before, after, plan)
                checker.check_report(before, after, plan, report)
                report.update(id=case['id'], route=route, plan_sha256=recheck.ch.digest(plan_path),
                              retained_strict_comparison_sha256=recheck.ch.digest(raw / directory / f"{case['id']}-{route}-comparison.json"))
                name = f"reports/{case['id']}-{route}.json"
                path = out / name
                path.parent.mkdir(exist_ok=True)
                recheck.ch.write_json(path, report)
                rows.append(dict(id=case['id'], route=route, report=name, report_sha256=recheck.ch.digest(path),
                                 strict_status=report['strict_status'], strict_differences=report['strict_difference_count'],
                                 **report['counts']))
    summary = dict(schema='cad-correspondence-summary-5',
                   diagnostic_freeze_sha256_lf=recheck.text_hash(HERE / 'CORRESPONDENCE-5-FREEZE.json'),
                   prior_archive=archive, controls=len(controls), controls_result_sha256=correspondence5.fingerprint(controls),
                   results=rows,
                   scope='Exposed retained decoded-record diagnostic. 21 matched candidates and 42 native returns. Strict failures are not waived; no new native, visual, UI, physical-identity or engineering acceptance.')
    check_cohort(summary)
    recheck.ch.write_json(out / 'summary.json', summary)
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = run(args.out)
    print(json.dumps(dict(reports=len(result['results']), controls=result['controls'],
                          native_failures=sum(r['strict_status'] == 'differences' for r in result['results']))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
