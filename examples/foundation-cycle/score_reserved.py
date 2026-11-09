"""Compare the retained procedural run to the separately frozen authored key."""
import argparse
import json
from pathlib import Path


def score(root, key):
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    checks = []
    for phase in ('first', 'second'):
        history = read(root / phase / 'history/result.json')
        drawing = read(root / phase / 'drawing/brief.json')
        for expected in key[phase]['history']:
            actual = next(a for a in history['assets'] if a['key'] == expected['key'])
            checks.append(dict(name=phase + ' scoped history ' + '/'.join(expected['key']),
                passed=len(actual['work_orders']) == expected['orders'] and actual['booked_hours']['value'] == expected['hours']))
        request = key[phase]['request']
        actual = [r for r in drawing['items'] if r['kind'] == 'request' and r['detail']['id'] == request['id']]
        checks.append(dict(name=phase + ' selected request state', passed=len(actual) == 1 and actual[0]['status'] == request['status']))
    current = read(root / 'second/context-prepared/context.json')['current']
    checks.append(dict(name='all selected changed/omitted-source answers stale', passed=all(
        current[q]['answers'] and all(a['freshness'] == 'stale' for a in current[q]['answers'])
        for q in key['second']['stale_questions'])))
    checks.append(dict(name='independent answer current', passed=all(a['freshness'] == 'current'
        for a in current[key['second']['current_question']]['answers'])))
    check_ids = [d['id'] for d in read(root / 'delivery-2/prepared/projection.json')['unavailable']]
    checks.append(dict(name='unavailable source explicit', passed=key['second']['unavailable_source'] in check_ids))
    return dict(schema='foundation-procedural-score-1', checks=checks,
                passed=sum(c['passed'] for c in checks), total=len(checks), independent_review=False,
                boundary='Author-known generator and key; supports bounded software transfer only')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--key', type=Path, default=Path(__file__).with_name('RESERVED-KEY.json'))
    args = parser.parse_args()
    result = score(args.run, json.loads(args.key.read_text(encoding='utf-8')))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] == result['total'] else 1)
