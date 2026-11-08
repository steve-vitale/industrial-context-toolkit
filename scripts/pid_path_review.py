"""Trace source-qualified process or signal paths in supplied twin graphs and retain revision comparisons.

    python scripts/pid_path_review.py graph.json --from SITE/P1/U1/P-101 --to SITE/P1/U1/V-301 --basis logical --out review

Standard library only. Supplied review labels are assumptions, not authenticated approvals. No model,
source fetching, CAD editing, consequence simulation or isolation instructions. See docs/PID_GRAPH_QUESTIONS.md.
"""
import argparse
import copy
import csv
import hashlib
import heapq
import html
import io
import json
from pathlib import Path, PurePosixPath
import sys

import one_map
from output_paths import protect_outputs

SCHEMA = 'pid-path-review-1'
REVIEWED = {'confirmed', 'corrected'}
EXCLUDED = {'rejected', 'unresolvable'}
TRANSPORT = {'connects', 'piped_to', 'signal_line', 'instrument_connection'}
BASE_FILES = {'input.json', 'query.json', 'result.json', 'REGISTER.csv', 'REPORT.md', 'REPORT.html'}
MAX_BYTES, MAX_NODES, MAX_EDGES, MAX_PACKET = 8 * 1024**2, 2000, 5000, 64 * 1024**2


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def parse(data):
    require(len(data) <= MAX_BYTES, 'Input exceeds 8 MiB limit')
    def pairs(rows):
        out = {}
        for key, value in rows:
            require(key not in out, 'Duplicate JSON key: ' + key)
            out[key] = value
        return out
    def invalid(value):
        raise ValueError('Nonfinite JSON number: ' + value)
    return json.loads(data.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=invalid)


def bindings():
    here = Path(__file__).resolve().parent
    return {name: sha((here / name).read_bytes().replace(b'\r\n', b'\n'))
            for name in ('pid_path_review.py', 'one_map.py', 'graph_export.py')}


def evidence(record):
    return {key: copy.deepcopy(record[key]) for key in ('source', 'citations', 'appearances') if key in record}


def source_issues(record):
    source = record.get('source') or {}
    reasons = []
    if not any(source.get(k) for k in ('document', 'file', 'drawing')):
        reasons.append('source_document_missing')
    if not any(source.get(k) for k in ('revision', 'rev', 'sha256')):
        reasons.append('source_revision_or_hash_missing')
    if not any(source.get(k) for k in ('locator', 'sheet', 'zone', 'pointer')):
        reasons.append('source_locator_missing')
    return reasons


def validate(graph):
    require(isinstance(graph, dict) and graph.get('schema') in ('twin-graph-1', 'twin-graph-2'), 'Expected twin-graph-1 or twin-graph-2')
    require(isinstance(graph.get('nodes'), list) and isinstance(graph.get('edges'), list), 'Graph needs node/edge arrays')
    require(0 < len(graph['nodes']) <= MAX_NODES and len(graph['edges']) <= MAX_EDGES, 'Graph exceeds 2000-node/5000-edge bounded scope')
    for section in ('nodes', 'edges'):
        require(all(isinstance(r, dict) and isinstance(r.get('id'), str) and r['id'] for r in graph[section]), 'Missing record identity')
        require(len({r['id'] for r in graph[section]}) == len(graph[section]), 'Duplicate ' + section + ' identity')
        for r in graph[section]:
            require(isinstance(r.get('attributes', []), list), 'Attributes must be an array')
            require(all(isinstance(a, dict) and isinstance(a.get('name'), str) for a in r.get('attributes', [])), 'Malformed attribute')
            require(len({a['name'] for a in r.get('attributes', [])}) == len(r.get('attributes', [])), 'Ambiguous duplicate attribute')
    problems = one_map.problems(graph)
    require(not problems, 'Invalid twin graph: ' + '; '.join(problems[:8]))
    nodes = {r['id']: r for r in graph['nodes']}
    for edge in graph['edges']:
        require(edge.get('from') in nodes and edge.get('to') in nodes, 'Path consumer requires explicit node endpoints (stream references unsupported)')
        if edge['type'] in TRANSPORT:
            require(edge.get('direction') in ('known', 'unknown', 'both', None), 'Unsupported direction vocabulary')
        for a in edge.get('attributes', []):
            if a['name'] == 'network_kind':
                require(a['value'] in ('process', 'signal'), 'network_kind must explicitly name process or signal')
    for node in graph['nodes']:
        if node['kind'] == 'conflict':
            conflict = node['conflict']
            require(type(conflict.get('detected', True)) is bool, 'Conflict detected must be Boolean')
            require(not conflict.get('detected', True) or conflict['status'] == 'resolved' or
                    conflict.get('subject') in nodes or conflict.get('subject') in {e['id'] for e in graph['edges']},
                    'Conflict subject is outside supplied graph; reconcile before tracing')


def family(edge, query):
    if edge['type'] == 'connects' and edge.get('layer') == 'offpage_pair':
        declarations = [a for a in edge.get('attributes', []) if a['name'] == 'network_kind']
        return not declarations or declarations[0]['value'] == query['network']
    if query['network'] == 'signal':
        return edge['type'] in ('signal_line', 'instrument_connection')
    if edge['type'] == 'piped_to':
        return query['basis'] == 'physical'
    return edge['type'] == 'connects' and (edge.get('layer') == 'offpage_pair' or
            query['basis'] == 'logical' and edge.get('layer') == 'stream')


def query_check(query, nodes):
    require(set(query) == {'from', 'to', 'network', 'basis', 'policy'}, 'Query fields differ from documented contract')
    require(query['from'] in nodes and query['to'] in nodes, 'Use exact supplied node IDs; endpoint not found')
    require(query['network'] in ('process', 'signal') and query['basis'] in ('physical', 'logical') and
            query['policy'] in ('reviewed', 'exploratory'), 'Unknown network, basis or policy')


def evaluate(graph, query):
    validate(graph)
    nodes, edges = {r['id']: r for r in graph['nodes']}, {r['id']: r for r in graph['edges']}
    query_check(query, nodes)
    conflicts = {}
    for n in graph['nodes']:
        if n['kind'] == 'conflict' and n['conflict'].get('detected', True) and n['conflict']['status'] != 'resolved':
            conflicts.setdefault(n['conflict']['subject'], []).append(n)
    incident = {nid: [] for nid in nodes}
    for e in graph['edges']:
        if e['type'] in TRANSPORT:
            incident[e['from']].append(e['id'])
            if e['to'] != e['from']:
                incident[e['to']].append(e['id'])
    for ids in incident.values():
        ids.sort()

    def issues(record):
        out = [{'record': record['id'], 'reason': x} for x in source_issues(record)]
        if record['status'] not in REVIEWED:
            out.append(dict(record=record['id'], reason='review_status_' + record['status']))
        for c in sorted(conflicts.get(record['id'], []), key=lambda r: r['id']):
            out.append(dict(record=record['id'], reason='open_conflict', conflict=c['id'],
                            owner=c['conflict']['record_owner'], evidence=evidence(c), detail=copy.deepcopy(c['conflict'])))
        return out

    def edge_issues(edge, destination):
        out = issues(edge) + issues(nodes[destination])
        for a in edge.get('attributes', []):
            if a['status'] not in REVIEWED or source_issues(a):
                out.append(dict(record=edge['id'], reason='edge_attribute_unreviewed_or_unsourced', attribute=a['name'], claim=copy.deepcopy(a)))
        if edge.get('direction') not in ('known', 'both'):
            out.append(dict(record=edge['id'], reason='direction_unknown'))
        if edge['type'] == 'connects' and edge.get('layer') == 'offpage_pair':
            declarations = [a for a in edge.get('attributes', []) if a['name'] == 'network_kind']
            if not declarations or declarations[0]['value'] not in ('process', 'signal'):
                out.append(dict(record=edge['id'], reason='offpage_network_kind_unknown'))
        return out

    start = query['from']
    first = issues(nodes[start])
    forbidden_start = nodes[start]['status'] in EXCLUDED or query['policy'] == 'reviewed' and first
    best = {} if forbidden_start else {start: (len(first), 0)}
    parents, qualifications, settled, boundaries = {}, {start: first}, [], []
    queue = [] if forbidden_start else [(len(first), 0, start)]
    if forbidden_start:
        boundaries.append(dict(node=start, edge=None, reason='start_not_eligible', qualifications=first))
    while queue:
        cost, hops, current = heapq.heappop(queue)
        if best.get(current) != (cost, hops):
            continue
        settled.append(current)
        for eid in incident[current]:
            edge = edges[eid]
            if not family(edge, query):
                boundaries.append(dict(node=current, edge=eid, reason='relation_outside_selected_network_or_basis', evidence=evidence(edge)))
                continue
            destination = edge['to'] if current == edge['from'] else edge['from']
            if current != edge['from'] and edge.get('direction') == 'known':
                if parents.get(current, (None, None))[1] == eid:
                    continue
                boundaries.append(dict(node=current, edge=eid, reason='known_reverse_direction', evidence=evidence(edge)))
                continue
            extra = edge_issues(edge, destination)
            if edge['status'] in EXCLUDED or nodes[destination]['status'] in EXCLUDED or any(a['status'] in EXCLUDED for a in edge.get('attributes', [])):
                boundaries.append(dict(node=current, edge=eid, reason='rejected_or_unresolvable', qualifications=extra))
                continue
            if query['policy'] == 'reviewed' and extra:
                boundaries.append(dict(node=current, edge=eid, reason='review_or_evidence_required', qualifications=extra, evidence=evidence(edge)))
                continue
            candidate = (cost + len(extra), hops + 1)
            if destination not in best or candidate < best[destination]:
                best[destination] = candidate
                parents[destination] = (current, eid)
                qualifications[destination] = qualifications[current] + extra
                heapq.heappush(queue, (*candidate, destination))
    # Missing continuations remain evidence requests, including when the query itself ends at that connector.
    for nid in settled:
        if nodes[nid]['kind'] == 'offpage_connector' and not any(family(edges[eid], query) and (edges[eid]['type'] == 'connects' and edges[eid].get('layer') == 'offpage_pair'
                or edges[eid]['type'] == 'signal_line' and nodes[edges[eid]['from']]['kind'] == nodes[edges[eid]['to']]['kind'] == 'offpage_connector'
                ) for eid in incident[nid]):
            boundaries.append(dict(node=nid, edge=None, reason='continuation_not_supplied', evidence=evidence(nodes[nid])))

    def path_to(nid):
        ns, es = [nid], []
        while nid in parents:
            nid, eid = parents[nid]
            ns.append(nid)
            es.append(eid)
        return list(reversed(ns)), list(reversed(es))

    target = query['to']
    found = target in best
    route_nodes, route_edges = path_to(target) if found else ([], [])
    # Answer dependencies cover the search prefix needed to establish this selected route (or the complete
    # reachable search for a negative answer). The wider register has a separate explicit change comparison.
    prefix = settled[:settled.index(target) + 1] if found else settled
    deps = {}
    touched = set(prefix) | {start, target}
    for nid in prefix:
        ids = incident[nid] if nid != target or not found else []
        deps['adjacency:' + nid] = digest(ids)
        for eid in ids:
            deps['edge:' + eid] = digest(edges[eid])
            touched.update((edges[eid]['from'], edges[eid]['to']))
    for nid in touched:
        deps['node:' + nid] = digest(nodes[nid])
    for key in touched | {eid.removeprefix('edge:') for eid in deps if eid.startswith('edge:')}:
        deps['conflicts:' + key] = digest(sorted(conflicts.get(key, []), key=lambda c: c['id']))
    selected = []
    for previous, destination, eid in zip(route_nodes, route_nodes[1:], route_edges):
        edge = edges[eid]
        selected.append(dict(edge=copy.deepcopy(edge), traversed_from=previous, traversed_to=destination,
                             qualifications=edge_issues(edge, destination)))
    register = []
    for nid in sorted(best):
        n = nodes[nid]
        ns, es = path_to(nid)
        register.append(dict(id=nid, tag=n.get('tag'), kind=n['kind'], item_status=n['status'],
                             association_status='qualified' if qualifications[nid] else 'supported',
                             facts=copy.deepcopy(n.get('attributes', [])), evidence=evidence(n),
                             path_nodes=ns, path_edges=es, qualifications=qualifications[nid]))
    status = 'not_established' if not found else 'qualified' if qualifications[target] else 'supported'
    return dict(schema=SCHEMA, tool_bindings=bindings(), query=copy.deepcopy(query), answer=dict(status=status,
                path_nodes=route_nodes, steps=selected, qualifications=qualifications.get(target, []), dependencies=dict(sorted(deps.items()))),
                register=register, boundaries=boundaries,
                coverage=dict(supplied_nodes=len(nodes), supplied_edges=len(edges), reached_nodes=len(best), search_complete=True),
                limits=['Supplied review labels and source references are not authenticated engineering acceptance.',
                        'No established path means insufficient supported coverage, not physical disconnection.',
                        'Topology does not establish operating consequences, current lineup or maintenance isolation.',
                        'The register is a query-relative association projection, not complete line/valve lists or a plant inventory.'])


def compare(current, previous=None):
    if previous is None:
        return dict(prior_answer='first_run', changed_dependencies=[], register_changes=[])
    require(previous['query'] == current['query'], 'Previous query/policy/basis differs; start a separate comparison')
    require(previous['tool_bindings'] == current['tool_bindings'], 'Previous method basis differs; retain it and start a new packet')
    a, b = previous['answer']['dependencies'], current['answer']['dependencies']
    changed = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
    old, new = ({r['id']: r for r in x['register']} for x in (previous, current))
    delta = [dict(id=k, before=old.get(k), after=new.get(k)) for k in sorted(old.keys() | new.keys()) if canonical(old.get(k)) != canonical(new.get(k))]
    return dict(prior_answer='reopened' if changed else 'unchanged', changed_dependencies=changed, register_changes=delta)


def render(result):
    q, ans = result['query'], result['answer']
    findings = dict(supported='The supplied records support this selected route within the stated scope.',
                    qualified='A candidate route exists, with unresolved evidence or review requirements.',
                    not_established='This route is not established under the selected policy and supplied coverage.')
    def source_text(record):
        s = record.get('source') or {}
        return ' / '.join(str(s[k]) for k in ('document', 'file', 'drawing', 'revision', 'rev', 'locator', 'sheet', 'zone') if s.get(k)) or 'Source reference incomplete'
    reasons = dict(known_reverse_direction='The recorded direction cannot be followed toward this destination.',
                   continuation_not_supplied='The continuation beyond this connector was not supplied. Obtain its next sheet or field evidence.',
                   relation_outside_selected_network_or_basis='This relationship is outside the selected process/signal or physical/logical scope.',
                   review_or_evidence_required='Review the evidence below before using this continuation.',
                   rejected_or_unresolvable='The supplied record is rejected or unresolvable.',
                   start_not_eligible='The starting item needs evidence or review.')
    def qualifier_text(qualifier):
        if qualifier['reason'] == 'open_conflict':
            c = qualifier['detail']
            return f"{c['what']}. Owner: {c['record_owner']}. Sources: {source_text(c['source_a'])} says {canonical(c['source_a'].get('says'))}; {source_text(c['source_b'])} says {canonical(c['source_b'].get('says'))}."
        return qualifier['reason'].replace('_', ' ') + ': ' + str(qualifier.get('attribute') or qualifier['record'])
    lines = ['# Drawing path review', '', f"Question: {q['from']} → {q['to']}", '', findings[ans['status']], '',
             f"Result: {ans['status']}; {q['network']} / {q['basis']} / {q['policy']}.",
             f"Prior answer: {result['comparison']['prior_answer']}. Register changes: {len(result['comparison']['register_changes'])}.", '',
             'A changed register does not automatically invalidate an unaffected local answer. Inspect each comparison.', '', '## Selected steps', '']
    for qualifier in ans['qualifications']:
        if qualifier['record'] == q['from']:
            lines.append('  - Starting record review: ' + qualifier_text(qualifier))
    for step in ans['steps']:
        lines.append(f"- {step['traversed_from']} → {step['traversed_to']}; source: {source_text(step['edge'])}")
        for qualifier in step['qualifications']:
            lines.append('  - Review: ' + qualifier_text(qualifier))
    if not ans['steps']:
        lines.append('No connection steps established within this policy and supplied coverage.')
    lines += ['', '## Review boundaries', '']
    for b in result['boundaries']:
        lines.append(f"- {b['node']}: {reasons[b['reason']]}" + (' Record: ' + b['edge'] if b.get('edge') else ''))
        lines += ['  - ' + qualifier_text(x) for x in b.get('qualifications', [])]
    lines += ['', '## Limits', ''] + ['- ' + x for x in result['limits']]
    md = '\n'.join(lines) + '\n'
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Drawing path review</title><style>body{font:16px/1.55 system-ui;max-width:960px;margin:auto;padding:24px;color:#192b35}h1,h2{line-height:1.2}p,td{overflow-wrap:anywhere}.bullet{padding-left:16px;border-left:3px solid #b5c8d4}.detail{margin-left:24px;background:#fff3d9;padding:10px}table{border-collapse:collapse;width:100%}td,th{padding:8px;border:1px solid #ccc;text-align:left}a{color:#075e87}</style><body><h1>Drawing path review</h1>'
    for line in lines[1:]:
        escaped = html.escape(line.lstrip('- ').strip())
        if line.startswith('## '):
            page += '<h2>' + html.escape(line[3:]) + '</h2>'
        elif line.startswith('  - '):
            page += '<p class="detail">' + escaped + '</p>'
        elif line.startswith('- '):
            page += '<p class="bullet">' + escaped + '</p>'
        elif line:
            page += '<p>' + html.escape(line) + '</p>'
    page += '<h2>Reachable record associations</h2><table><tr><th>Item</th><th>Own status</th><th>Association</th></tr>'
    for row in result['register']:
        page += '<tr>' + ''.join('<td>' + html.escape(str(row[k])) + '</td>' for k in ('id', 'item_status', 'association_status')) + '</tr>'
    page += '</table><p><a href="REGISTER.csv">Download register with sources and qualifications</a> · <a href="REPORT.md">Plain report</a> · <a href="result.json">Complete evidence and revision comparison</a></p></body></html>\n'
    stream = io.StringIO(newline='')
    fields = ['id', 'tag', 'kind', 'item_status', 'association_status', 'facts', 'evidence', 'path_nodes', 'path_edges', 'qualifications']
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    for row in result['register']:
        # JSON cells preserve literal values while keeping user strings from becoming spreadsheet formulas.
        writer.writerow({k: canonical(row[k]) for k in fields})
    return dict(**{'REPORT.md': md.encode('utf-8'), 'REPORT.html': page.encode('utf-8'), 'REGISTER.csv': stream.getvalue().encode('utf-8')})


def receive(folder, depth=0):
    require(depth <= 8, 'Previous history exceeds eight revisions; retain older history separately')
    folder = Path(folder)
    require(folder.is_dir() and not folder.is_symlink(), 'Previous packet must be a regular directory')
    files = {}
    total = 0
    for p in folder.rglob('*'):
        require(not p.is_symlink(), 'Packet links are unsupported')
        if p.is_file():
            name = p.relative_to(folder).as_posix()
            require(p.stat().st_size <= MAX_PACKET, 'Oversized packet member')
            total += p.stat().st_size
            require(total <= MAX_PACKET and len(files) < 72, 'Packet history exceeds size/file limits')
            files[name] = p.read_bytes()
    require(sum(map(len, files.values())) <= MAX_PACKET and len(files) <= 72, 'Packet history exceeds size/file limits')
    require('receipt.json' in files, 'Previous packet receipt missing')
    receipt = parse(files['receipt.json'])
    require(receipt.get('schema') == SCHEMA and set(receipt['files']) == set(files) - {'receipt.json'}, 'Packet receipt coverage differs')
    for name, pin in receipt['files'].items():
        path = PurePosixPath(name)
        require(not path.is_absolute() and '..' not in path.parts and ':' not in name and '\\' not in name, 'Unsafe packet member')
        require(pin == dict(bytes=len(files[name]), sha256=sha(files[name])), 'Packet member altered: ' + name)
    require(BASE_FILES <= set(files) and all(n in BASE_FILES or n.startswith('previous/') for n in files if n != 'receipt.json'), 'Unexpected packet member')
    prior = receive(folder / 'previous', depth + 1) if (folder / 'previous').exists() else None
    query, saved = parse(files['query.json']), parse(files['result.json'])
    require(saved.get('tool_bindings') == bindings(), 'Previous method basis differs; retain it and start a new packet')
    expected = evaluate(parse(files['input.json']), query)
    expected['comparison'] = compare(expected, prior)
    require(canonical(saved) == canonical(expected), 'Previous answer does not reproduce')
    for name, data in render(expected).items():
        require(files[name] == data, 'Previous projection does not reproduce: ' + name)
    return saved


def run(graph_path, query, out, previous=None):
    graph_path, out = Path(graph_path), Path(out)
    require(not out.exists() and not out.is_symlink(), 'Use a new output folder; existing destinations are retained')
    if previous:
        require(not out.resolve().is_relative_to(Path(previous).resolve()), 'Output must stay outside the retained previous packet')
    require(graph_path.stat().st_size <= MAX_BYTES, 'Input exceeds 8 MiB limit')
    raw = graph_path.read_bytes()
    result = evaluate(parse(raw), query)
    prior = receive(previous) if previous else None
    result['comparison'] = compare(result, prior)
    files = dict(render(result), **{'input.json': raw, 'query.json': dump(query), 'result.json': dump(result)})
    require(all(len(files[k]) <= MAX_BYTES for k in ('input.json', 'query.json', 'result.json')), 'JSON result exceeds 8 MiB; narrow the scope')
    inputs = [graph_path]
    if previous:
        for p in Path(previous).rglob('*'):
            if p.is_file():
                files['previous/' + p.relative_to(previous).as_posix()] = p.read_bytes()
                inputs.append(p)
    require(sum(map(len, files.values())) <= MAX_PACKET and len(files) < 72, 'Result exceeds bounded packet size/history; narrow the scope')
    files['receipt.json'] = dump(dict(schema=SCHEMA, files={k: dict(bytes=len(v), sha256=sha(v)) for k, v in sorted(files.items())}))
    protect_outputs([out / name for name in files], inputs)
    for name, data in files.items():
        p = out / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('graph', type=Path)
    parser.add_argument('--from', dest='start', required=True)
    parser.add_argument('--to', dest='end', required=True)
    parser.add_argument('--policy', choices=('reviewed', 'exploratory'), default='reviewed')
    parser.add_argument('--network', choices=('process', 'signal'), default='process')
    parser.add_argument('--basis', choices=('physical', 'logical'), default='physical')
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        query = dict(**{'from': args.start, 'to': args.end}, policy=args.policy, network=args.network, basis=args.basis)
        result = run(args.graph, query, args.out, args.previous)
    except (ValueError, KeyError, TypeError, OSError, UnicodeError, RecursionError) as exc:
        print('Cannot prepare path review: ' + str(exc), file=sys.stderr)
        return 2
    print(f"{result['answer']['status']}: {len(result['answer']['steps'])} selected steps; prior answer {result['comparison']['prior_answer']}; {args.out / 'REPORT.html'}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
