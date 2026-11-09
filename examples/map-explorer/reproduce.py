"""Real offline map builds, explorer exports and portable readback; author-known software cases."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EX = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(out, number, args, expected=0):
    command = [sys.executable, '-B', '-S', *map(str, args)]
    r = subprocess.run(command, cwd=ROOT, capture_output=True)
    name = f'{number:02d}'
    (out / (name + '.stdout.txt')).write_bytes(r.stdout)
    (out / (name + '.stderr.txt')).write_bytes(r.stderr)
    record = {'command': command, 'exit': r.returncode, 'expected_exit': expected,
              'stdout': name + '.stdout.txt', 'stderr': name + '.stderr.txt'}
    with (out / 'commands.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(record) + '\n')
    if r.returncode != expected:
        raise AssertionError(record)


def reproduce(out, phase):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    key = read(EX / 'ACCEPTANCE.json')
    commands = 0
    checks = []

    def cli(*args, expected=0):
        nonlocal commands
        commands += 1
        run(out, commands, args, expected)

    def check(label, condition):
        checks.append({'check': label, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(label)

    def build(site, name):
        target = out / name
        cli('scripts/one_map.py', 'build', site, '--out', target)
        return target / 'graph.json'

    def packet(g, sources, item, name, previous=None):
        dest = out / name
        args = ['scripts/map_explorer.py', 'export', '--map', g, '--sources', sources,
                '--item', item, '--out', dest]
        if previous:
            args += ['--previous', previous, '--previous-sources', sources]
        cli(*args)
        anchor = digest(dest / 'RECEIPT.json')
        cli('scripts/map_explorer.py', 'verify', dest, '--expected-receipt-sha256', anchor)
        received = out / (name + '-received')
        shutil.copytree(dest, received)
        cli('scripts/map_explorer.py', 'verify', received, '--expected-receipt-sha256', anchor)
        source_files = {p.relative_to(dest).as_posix(): p.read_bytes() for p in dest.rglob('*') if p.is_file()}
        received_files = {p.relative_to(received).as_posix(): p.read_bytes() for p in received.rglob('*') if p.is_file()}
        check(name + ': complete copy/reopen bytes and delivery anchor', source_files == received_files)
        check(name + ': exact original current snapshot', (received / 'current.json').read_bytes() == g.read_bytes())
        # Check the full represented node/edge set, not counts.
        graph = read(g)
        view = read(received / 'exploration.json')['views']['current']
        check(name + ': every complete node',
              {n['id']: n for n in graph['nodes']} == {k: v['node'] for k, v in view.items()})
        check(name + ': every full incident edge', all(
            v['edges'] == [e for e in graph['edges'] if k in (e['from'], e['to'])] for k, v in view.items()))
        rows = read(received / 'evidence.json')
        check(name + ': all retained sources equal declared raw hashes', all(
            digest(received / r['retained']) == r['source']['sha256'] for r in rows if r['status'] == 'retained'))
        return received

    if phase == 'development':
        k = key['development']
        g = build(k['site'], 'map')
        received = packet(g, k['sources'], k['item'], 'explorer')
        result = read(received / 'exploration.json')
        v = result['views']['current'][k['item']]
        a = k['attribute']
        check('separate expected attribute and source locator', any(
            x['name'] == a['name'] and x['value'] == a['value'] and all(
                x['source'].get(f) == a[f] for f in ('document', 'revision', 'locator'))
            for x in v['node']['attributes']))
        check('separate expected disagreement and record owner', any(
            all(c.get(f) == value for f, value in k['conflict'].items()) for c in v['conflicts']))
        check('same-tag separate scope', result['views']['current'][k['other_item']]['node']['scope'] != v['node']['scope'])
        check('all supported question kinds', sorted(v['answers']) == sorted(k['required_questions']))
        d = result['views']['current'][k['unresolved_document']]
        check('ambiguous document reference remains a conflict', any(c['type'] == 'ambiguous_reference' for c in d['conflicts']))
        cli('scripts/map_explorer.py', 'export', '--map', g, '--item', k['ambiguous'], '--out', out / 'ambiguous', expected=2)
        check('ambiguous refusal creates no output', not (out / 'ambiguous').exists())
    else:
        k = key['procedural_transfer']
        old = build(k['previous_site'], 'previous-map')
        g = build(k['site'], 'revised-map')
        received = packet(g, k['sources'], k['item'], 'revision-explorer', old)
        r = read(received / 'exploration.json')
        check('previous snapshot retained exactly', (received / 'previous.json').read_bytes() == old.read_bytes())
        check('new transmitter absent before and represented after',
              k['added_item'] not in r['views']['previous'] and k['added_item'] in r['views']['current'])
        check('independent unit full node unchanged',
              r['views']['current'][k['independent_item']]['node'] == r['views']['previous'][k['independent_item']]['node'])
        check('superseded document basis retained', any(
            c['type'] == k['basis_conflict_type'] for v in r['views']['current'].values() for c in v['conflicts']))
        check('full comparison identifies new transmitter', k['added_item'] in [c['id'] for c in r['node_changes']])
        k = key['public_transfer']
        g = build(k['site'], 'public-map')
        received = packet(g, k['sources'], k['item'], 'public-explorer')
        r = read(received / 'exploration.json')
        check('public reading remains unverified', r['views']['current'][k['item']]['node']['status'] == 'unverified')
        check('public provenance remains on selected source', bool(r['views']['current'][k['item']]['node']['appearances']))

    summary = {'schema': 'map-explorer-replay-1', 'phase': phase, 'checks': checks, 'commands': commands,
               'exposure': key['exposure'], 'claim': 'Local software and portable receiving only; no human effort or plant acceptance.'}
    (out / 'SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'phase': phase, 'checks': len(checks), 'commands': commands, 'out': str(out)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True)
    p.add_argument('--phase', required=True, choices=('development', 'transfer'))
    a = p.parse_args()
    reproduce(a.out, a.phase)
