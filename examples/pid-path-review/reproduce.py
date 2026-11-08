"""Run the exposed three-sheet policy/baseline/revision controls without network or model calls."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts'))
import pid_path_review as p


def verify_inputs():
    for name in ('FREEZE.json', 'PREPARATION-FREEZE.json'):
        for path, pin in json.loads((HERE / name).read_bytes())['inputs'].items():
            p.require(hashlib.sha256((HERE / path).read_bytes()).hexdigest() == pin, 'Frozen example input differs: ' + path)
    for path in (HERE / 'inputs').glob('prepared-*.json'):
        graph = json.loads(path.read_bytes())
        for row in graph['nodes'] + graph['edges']:
            source = row['source']
            p.require(hashlib.sha256((HERE / 'sources' / source['document']).read_bytes()).hexdigest() == source['sha256'], 'Example original source pin differs')


def naive(graph, start, end):
    seen, todo = {start}, [start]
    while todo:
        current = todo.pop()
        for edge in graph['edges']:
            if current in (edge['from'], edge['to']):
                other = edge['to'] if current == edge['from'] else edge['from']
                if other not in seen:
                    seen.add(other)
                    todo.append(other)
    return end in seen


def reproduce(out):
    verify_inputs()
    p.require(not out.exists(), 'Use a new example output folder')
    queries = json.loads((HERE / 'QUERIES.json').read_bytes())
    key = json.loads((HERE / 'ACCEPTANCE.json').read_bytes())
    graph = json.loads((HERE / 'inputs/prepared-initial.json').read_bytes())
    rows, results = [], {}
    for spec in queries:
        for policy in ('reviewed', 'exploratory'):
            query = dict(spec)
            identity = query.pop('id')
            query['policy'] = policy
            result = p.run(HERE / 'inputs/prepared-initial.json', query, out / (identity + '-' + policy))
            expected = key['cases'][identity][policy]
            p.require(result['answer']['status'] == expected, 'Frozen policy key differs: ' + identity + '/' + policy)
            baseline = naive(graph, query['from'], query['to'])
            p.require(baseline == key['cases'][identity]['naive_undirected'], 'Frozen baseline key differs')
            rows.append(dict(id=identity, policy=policy, expected=expected, actual=result['answer']['status'], naive_undirected=baseline))
            results[(identity, policy)] = result
    missing = results[('missing', 'reviewed')]
    p.require(any(b['node'] == key['missing_boundary'] and b['reason'] == 'continuation_not_supplied' for b in missing['boundaries']), 'Missing continuation hidden')
    remote = results[('remote', 'exploratory')]
    asset = next(r for r in remote['register'] if r['id'].endswith('/V-301'))
    p.require(asset['item_status'] == 'confirmed' and asset['association_status'] == 'qualified', 'Own fact and association conflated')
    revisions = []
    for identity in ('local', 'remote'):
        query = dict(next(q for q in queries if q['id'] == identity))
        query.pop('id')
        query['policy'] = 'reviewed'
        first = out / (identity + '-reviewed')
        corrected = out / (identity + '-corrected')
        result = p.run(HERE / 'inputs/prepared-corrected.json', query, corrected, first)
        p.require(result['comparison']['prior_answer'] == key['revision'][identity], 'Selective answer reopening differs: ' + identity)
        p.require(result['answer']['status'] == 'supported', 'Corrected path did not become supported')
        later = p.run(HERE / 'inputs/prepared-unrelated.json', query, out / (identity + '-unrelated'), corrected)
        p.require(later['comparison']['prior_answer'] == key['revision']['unrelated'], 'Unrelated record reopened answer')
        p.require(p.receive(out / (identity + '-unrelated')) == later, 'Complete historical packet does not reproduce')
        revisions.append(dict(id=identity, prior_answer=result['comparison']['prior_answer'], after_correction=result['answer']['status'],
                              changed_register_rows=len(result['comparison']['register_changes']), after_unrelated=later['comparison']['prior_answer']))
    original = json.loads((HERE / 'inputs/initial.json').read_bytes())
    spec = dict(next(q for q in queries if q['id'] == 'remote'))
    spec.pop('id')
    spec['policy'] = 'exploratory'
    unqualified = p.evaluate(original, spec)
    p.require(any(q['reason'] == 'offpage_network_kind_unknown' for q in unqualified['answer']['qualifications']), 'Original missing network meaning was silently accepted')
    summary = dict(policy_cases=rows, revisions=revisions, original_missing_network_retained=True, sources='Four authored schedule revisions, three sheets; no image reading',
                   exposure=key['exposure'], engineering_acceptance=False, cad_qualification=False)
    (out / 'replay.json').write_bytes(p.dump(summary))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(reproduce(args.out), indent=2))
