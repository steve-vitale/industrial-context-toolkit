"""Portable selected-record foundation using existing graph/context receiving contracts.

No drawing reading, identity discovery, company approval or governed-service importer.
Prepare supplied projections, apply context_register separately, then deliver/receive.
"""
import argparse
import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import context_register as context
import maintenance_history as history
import receive_drawings as drawing
from serve_snapshot import Snapshot, read_snapshot


def require(test, message):
    if not test:
        raise ValueError(message)


def raw(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def same(a, b):
    # JSON's bool and number must not collapse through Python's True == 1.
    return raw(a) == raw(b)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def load(path):
    return read_snapshot(path, 'Foundation')[0]


def local(root, name):
    require(isinstance(name, str) and name and '\\' not in name,
            'Reference needs a relative POSIX path')
    part = Path(name)
    require(not part.is_absolute() and '..' not in part.parts, 'Reference escapes retained root')
    path = root / part
    require(path.resolve().is_relative_to(root.resolve()) and path.resolve() != root.resolve(),
            'Reference escapes retained root')
    require(not any(p.is_symlink() for p in [path, *path.parents] if p != root.parent),
            'Symlink references are not retained originals')
    return path


def inventory(root):
    paths = list(root.rglob('*'))
    require(not any(p.is_symlink() for p in paths), 'Packet contains a symlink')
    return {p.relative_to(root).as_posix(): sha(p.read_bytes())
            for p in sorted(paths) if p.is_file()}


def write_files(out, files, kind, extra=None):
    require(not out.exists(), 'Output already exists; choose a new receiving directory')
    out.parent.mkdir(parents=True, exist_ok=True)
    # Validate all relative names before publishing any output.
    for name in files:
        local(out, name)
    with tempfile.TemporaryDirectory(prefix='foundation-', dir=out.parent) as tmp:
        stage = Path(tmp) / 'stage'
        stage.mkdir()
        for name, content in files.items():
            path = local(stage, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        receipt = dict(schema=kind, files=inventory(stage), **(extra or {}))
        (stage / 'receipt.json').write_bytes(raw(receipt))
        stage.rename(out)
    return receipt


def check_inventory(root, schema):
    receipt = load(root / 'receipt.json')
    require(receipt.get('schema') == schema, 'Wrong foundation packet kind')
    actual = inventory(root)
    actual.pop('receipt.json', None)
    require(same(receipt.get('files'), actual), 'Retained packet inventory changed')
    require(receipt.get('company_acceptance') is False, 'Company acceptance is not established')
    return receipt


def copied(root, prefix):
    inventory(root)
    return {prefix + '/' + p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob('*')) if p.is_file()}


def leaves(value, pointer=''):
    if isinstance(value, dict) and value:
        for key, child in value.items():
            yield from leaves(child, pointer + '/' + key.replace('~', '~0').replace('/', '~1'))
    elif isinstance(value, list) and value:
        for index, child in enumerate(value):
            yield from leaves(child, pointer + '/' + str(index))
    else:
        yield pointer, value


def project(graph, node_id, prefix, value, document, revision, digest, locator, mappings, omissions):
    nodes = {n['id']: n for n in graph['nodes']}
    require(node_id in nodes, 'Unknown scoped graph node')
    attrs = nodes[node_id]['attributes']
    for pointer, item in leaves(value):
        name = prefix + pointer
        require(not any(a['name'] == name for a in attrs), 'Projection attribute collision')
        if isinstance(item, dict):
            omissions.append(dict(node=node_id, locator=locator + pointer,
                                  reason='Empty object retained in original; no plain graph attribute'))
            continue
        attrs.append(dict(name=name, value=item, status='unverified', source=dict(
            kind='document', document=document, revision=revision, sha256=digest,
            locator=locator + pointer, interpretation='Supplied identity/review declaration; not plant verification')))
    mappings.append(dict(node=node_id, prefix=prefix, source=document,
                         revision=revision, sha256=digest, locator=locator))


def identity(graph, mapping):
    require(set(mapping) >= {'node', 'key', 'reviewer', 'reviewed_on'},
            'Mapping needs explicit scoped key and review declaration')
    require(isinstance(mapping['key'], list) and len(mapping['key']) == 2
            and all(isinstance(x, str) and x for x in mapping['key']), 'Expected [scope, record_id]')
    require(mapping['reviewer'] and mapping['reviewed_on'], 'Mapping review declaration is missing')
    nodes = [n for n in graph['nodes'] if n['id'] == mapping['node']]
    require(len(nodes) == 1, 'Mapping must identify exactly one node')
    attrs = nodes[0]['attributes']
    for field, expected in zip(('scope', 'record_id'), mapping['key']):
        actual = [a['value'] for a in attrs if a['name'] == field]
        require(same(actual, [expected]), 'Scoped identity disagrees with graph; bare tags cannot join')


def prepare(profile_path, out):
    root = profile_path.parent.resolve()
    profile = load(profile_path)
    require(set(profile) <= {'schema', 'id', 'graph', 'questions', 'history', 'drawing', 'documents', 'unavailable'},
            'Unknown profile fields')
    require(profile.get('schema') == 'foundation-input-1' and profile.get('id'), 'Wrong foundation profile')
    graph = load(local(root, profile['graph']))
    Snapshot(local(root, profile['graph']))
    require(not graph.get('context_register') and not graph.get('questions'),
            'Supply a source graph before context binding, with questions separately')
    questions = load(local(root, profile['questions']))
    files = {'originals/graph.json': local(root, profile['graph']).read_bytes(),
             'questions.json': local(root, profile['questions']).read_bytes()}
    portable = copy.deepcopy(profile)
    portable.update(graph='originals/graph.json', questions='questions.json')
    sources, mappings, omissions = [], [], []
    for kind in ('history', 'drawing'):
        spec = profile.get(kind)
        if spec is None:
            continue
        require(set(spec) == {'packet', 'revision', 'mappings', 'questions'}, 'Unknown source packet fields')
        require(isinstance(spec['revision'], str) and spec['revision'], 'Source version label required')
        packet = local(root, spec['packet']).resolve()
        require(not out.resolve().is_relative_to(packet), 'Output aliases a retained source packet')
        if kind == 'history':
            history.verify_packet(packet)
            docname, result = 'result.json', load(packet / 'result.json')
        else:
            _, result, _ = drawing.previous_packet(packet)
            docname = 'brief.json'
        prefix = 'originals/' + kind
        files.update(copied(packet, prefix))
        portable[kind]['packet'] = prefix
        digest = sha((packet / docname).read_bytes())
        document = kind.upper()
        require(len({tuple(m['key']) for m in spec['mappings']}) == len(spec['mappings']),
                'Duplicate selected identities')
        for mapping in spec['mappings']:
            identity(graph, mapping)
            if kind == 'history':
                selected = [(i, a) for i, a in enumerate(result['assets']) if same(a['key'], mapping['key'])]
                require(len(selected) == 1, 'History scoped key is missing or ambiguous')
                index, record = selected[0]
                locator = '/assets/' + str(index)
            else:
                require(set(mapping) >= {'drawing', 'request_id', 'sheet', 'returned_revision'},
                        'Drawing request, sheet and expected returned revision required')
                selected = [(i, r) for i, r in enumerate(result['items'])
                            if r['kind'] == 'request' and r['drawing'] == mapping['drawing']
                            and r['detail']['id'] == mapping['request_id']]
                require(len(selected) == 1, 'Drawing request is missing or ambiguous')
                index, record = selected[0]
                require(record['detail']['sheet'] == mapping['sheet'], 'Wrong selected drawing sheet')
                job = load(packet / 'job.json')
                selected_job = [d for d in job['drawings'] if d['id'] == mapping['drawing']]
                require(len(selected_job) == 1 and 'markup_manifest' in selected_job[0], 'Selected markup job missing')
                manifest = load(local(packet, selected_job[0]['markup_manifest']))
                versions = [p['revision'] for d in manifest['documents'] if d['role'] == 'returned'
                            for p in d['pages'] if p['sheet'] == mapping['sheet']]
                require(versions and all(v == mapping['returned_revision'] for v in versions),
                        'Wrong drawing/source returned revision association')
                subjects = {c['key']['subject'] for c in record['detail']['checks']}
                require(subjects == {mapping['key'][1]},
                        'Selected drawing subjects differ from mapped asset; use a separately reviewed multi-asset route')
                locator = '/items/' + str(index)
            prefix_name = 'foundation.' + kind + '.'
            project(graph, mapping['node'], prefix_name, record, document, spec['revision'], digest,
                    locator, mappings, omissions)
        sources.append(dict(id=document, revision=spec['revision'], path=prefix + '/' + docname,
                            sha256=digest, locators=[dict(id='selected-records', locator='Complete ' + docname +
                            '; selected projections use JSON pointers', questions=spec['questions'])]))
    for index, doc in enumerate(profile.get('documents', [])):
        require(set(doc) == {'id', 'revision', 'path', 'locators'}, 'Unknown source document fields')
        path = local(root, doc['path'])
        name = 'originals/documents/' + str(index) + path.suffix
        files[name] = path.read_bytes()
        portable['documents'][index]['path'] = name
        sources.append(dict(doc, path=name, sha256=sha(files[name])))
    unavailable = profile.get('unavailable', [])
    require(all(set(d) == {'id', 'reason', 'questions'} and d['reason'] for d in unavailable),
            'Unavailable source needs explicit reason/questions')
    require(not ({d['id'] for d in unavailable} & {d['id'] for d in sources}), 'Source is both supplied and unavailable')
    report = dict(schema='foundation-projection-1', mappings=mappings, identity_declarations=[
        dict(source=kind, **m) for kind in ('history', 'drawing')
        for m in profile.get(kind, {}).get('mappings', [])], unavailable=unavailable,
        not_native=omissions, boundary=[
            'Only selected history dossiers and exact single-subject requests are projected as unverified graph attributes.',
            'Graph scalar values retain original JSON types; decimal text remains text, not a measured number.',
            'Full structured records, unselected findings, originals and receipts remain source archives.',
            'Review names and source authority are declarations, not authenticated company decisions.',
            'No extraction, operating acceptance, automatic synchronization or governed-service import.'])
    files.update({'profile.json': raw(portable), 'graph.json': raw(graph),
                  'sources.json': raw(dict(schema='context-sources-1', documents=sources)),
                  'projection.json': raw(report)})
    # Validate bindings/locators against the retained paths before publishing.
    with tempfile.TemporaryDirectory(prefix='foundation-admit-') as tmp:
        stage = Path(tmp)
        for name, content in files.items():
            target = local(stage, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        _, _, qmap = context.load_inputs(stage / 'graph.json', stage / 'questions.json')
        context.load_sources(stage / 'sources.json', qmap, stage)
        Snapshot(stage / 'graph.json')
        require(all(q in qmap for d in unavailable for q in d['questions']), 'Unavailable source has unknown question')
    return write_files(out, files, 'foundation-preparation-receipt-1',
                       dict(company_acceptance=False, input_id=profile['id']))


def verify_preparation(root):
    receipt = check_inventory(root, 'foundation-preparation-receipt-1')
    with tempfile.TemporaryDirectory(prefix='foundation-reproduce-') as tmp:
        rebuilt = Path(tmp) / 'prepared'
        prepare(root / 'profile.json', rebuilt)
        require(same(inventory(root), inventory(rebuilt)), 'Prepared projections do not reproduce from originals')
    return receipt


def pages(function, key, *args):
    found, offset = [], 0
    while True:
        result = function(*args, limit=2, offset=offset)['result']
        found.extend(result[key])
        if result['next_offset'] is None:
            require(len(found) == result['total'], 'Incomplete receiver pagination')
            return found
        offset = result['next_offset']


def readback(graph_path, context_path):
    snapshot = Snapshot(graph_path, context_path)
    graph, register = snapshot.graph, snapshot.context
    nodes = [snapshot.asset(n['id'])['result'] for n in graph['nodes']]
    edges = {}
    for n in graph['nodes']:
        for e in pages(snapshot.relations, 'relations', n['id']):
            require(e['id'] not in edges or same(edges[e['id']], e), 'Contradictory receiver relationship')
            edges[e['id']] = e
    questions = [snapshot.question(q['id'])['result'] for q in graph.get('questions', [])]
    question_ids = pages(snapshot.context_questions, 'questions')
    current, owners, sources = {}, [], {}
    for q in question_ids:
        response = snapshot.context_question(q['id'])['result']
        current[q['id']] = response['current']
        owners.extend(response['ownership_history'])
        for source in response['sources']:
            entry = sources.setdefault(source['id'], dict(source, locators={}))
            for loc in source['locators']:
                prior = entry['locators'].setdefault(loc['id'], dict(loc, questions=[]))
                prior['questions'] = sorted(set(prior['questions'] + loc['questions']))
    decisions = pages(snapshot.decisions, 'decisions')
    require(same(nodes, graph['nodes']), 'Node fields lost in receiving readback')
    require(same([edges[e['id']] for e in graph['edges'] if e['id'] in edges], graph['edges']),
            'Relationship fields lost in receiving readback')
    require(same(questions, graph.get('questions', [])) and same(current, register['current']),
            'Question/current fields lost in receiving readback')
    require(same(decisions, register['decisions']), 'Decision history lost in receiving readback')
    require(same(sorted(owners, key=raw), sorted(register['ownership_history'], key=raw)),
            'Ownership history lost in receiving readback')
    reconstructed_sources = []
    for source in sources.values():
        reconstructed_sources.append(dict(source, locators=sorted(source['locators'].values(), key=lambda x: x['id'])))
    normalize = lambda rows: sorted([dict(s, locators=sorted([dict(l, questions=sorted(l['questions']))
                             for l in s['locators']], key=lambda x: x['id'])) for s in rows], key=lambda x: x['id'])
    require(same(normalize(reconstructed_sources), normalize(register['sources'])), 'Source fields lost in readback')
    return dict(receiver='serve_snapshot.Snapshot (actual bounded read-only reader)',
                nodes=nodes, edges=[edges[e['id']] for e in graph['edges']], questions=questions,
                current=current, decisions=decisions, ownership_history=register['ownership_history'],
                sources=register['sources'], company_acceptance=False,
                unserved_graph_fields=['events, graph metadata and not_exported are retained in the source graph; not graph tool records'])


def deliver(prepared, context_folder, out, previous=None, _verified_previous=False):
    require(not out.resolve().is_relative_to(prepared.resolve())
            and not out.resolve().is_relative_to(context_folder.resolve()), 'Output aliases a retained input packet')
    if previous is not None:
        require(not out.resolve().is_relative_to(previous.resolve()), 'Output aliases previous delivery')
    verify_preparation(prepared)
    graph_path, context_path = context_folder / 'enriched_graph.json', context_folder / 'context.json'
    observed = readback(graph_path, context_path)
    enriched, register = load(graph_path), load(context_path)
    expected = load(prepared / 'graph.json')
    expected['questions'] = load(prepared / 'questions.json')['questions']
    actual = copy.deepcopy(enriched)
    actual.pop('context_register', None)
    for question in actual['questions']:
        question.pop('context', None)
    if isinstance(expected.get('counts'), dict):
        expected['counts']['questions'] = len(expected['questions'])
    require(same(actual, expected), 'Selected context graph differs from the prepared projection')
    _, _, qmap = context.load_inputs(prepared / 'graph.json', prepared / 'questions.json')
    sources, _, _ = context.load_sources(prepared / 'sources.json', qmap, prepared)
    require(same(sorted(sources.values(), key=lambda x: x['id']),
                 sorted(register['sources'], key=lambda x: x['id'])), 'Selected source bindings differ from retained inputs')
    files = copied(prepared, 'prepared')
    files.update({'graph.json': graph_path.read_bytes(), 'context.json': context_path.read_bytes(),
                  'readback.json': raw(observed)})
    base = None
    changes = dict(base=None, mapping_changes=[], unavailable=load(prepared / 'projection.json')['unavailable'])
    if previous is not None:
        if not _verified_previous:
            verify_delivery(previous)
        old = load(previous / 'context.json')
        for field in ('decisions', 'ownership_history'):
            require(same(register[field][:len(old[field])], old[field]), 'Prior history is not an unchanged prefix')
        base = sha((previous / 'receipt.json').read_bytes())
        changes['base'] = base
        prior_projection = load(previous / 'prepared/projection.json')
        current_projection = load(prepared / 'projection.json')
        if not same(prior_projection['identity_declarations'], current_projection['identity_declarations']):
            changes['mapping_changes'] = [dict(before=prior_projection['identity_declarations'],
                                               after=current_projection['identity_declarations'],
                                               disposition='Review declarations changed; company acceptance remains unestablished')]
        require(not same(inventory(prepared), inventory(previous / 'prepared')) or not same(register, old),
                'Duplicate delivery has no new evidence/history')
        files.update(copied(previous, 'previous'))
    files['changes.json'] = raw(changes)
    states = {qid: q['state'] for qid, q in register['current'].items()}
    files['HANDOFF.md'] = ('# Selected-record foundation handoff\n\n'
        'Receiving target: toolkit graph/context snapshot reader. Company acceptance: not established.\n\n'
        '## Current questions\n\n' + ''.join('- ' + qid + ': ' + state + '\n' for qid, state in states.items()) +
        '\nSee `prepared/projection.json` for identity declarations, native omissions and unavailable sources. '
        'Exact originals/receipts are in `prepared/originals`; prior deliveries are retained in `previous`. '
        'Owners/reviewers in context are supplied declarations. Ask the responsible company record owner '
        'to resolve stale/disputed items and record any receiving decision in their authorized system.\n\n'
        'No live synchronization, authenticated approval, plant truth or governed-service importer is established.\n').encode('utf-8')
    return write_files(out, files, 'foundation-delivery-receipt-1',
                       dict(company_acceptance=False, base_receipt_sha256=base))


def verify_delivery(root, depth=0):
    require(depth <= 8, 'Foundation revision chain exceeds eight retained deliveries')
    receipt = check_inventory(root, 'foundation-delivery-receipt-1')
    verify_preparation(root / 'prepared')
    expected = readback(root / 'graph.json', root / 'context.json')
    require(same(expected, load(root / 'readback.json')), 'Saved readback differs from actual receiver')
    prior = root / 'previous'
    if receipt.get('base_receipt_sha256') is not None:
        verify_delivery(prior, depth + 1)
        require(sha((prior / 'receipt.json').read_bytes()) == receipt['base_receipt_sha256'], 'Stale/changed delivery base')
        old, new = load(prior / 'context.json'), load(root / 'context.json')
        for field in ('decisions', 'ownership_history'):
            require(same(new[field][:len(old[field])], old[field]), 'Retained decision/ownership history was dropped')
    else:
        require(not prior.exists(), 'Unbound prior delivery')
    # Re-run admission against the exact retained graph, sources and previous history.
    with tempfile.TemporaryDirectory(prefix='foundation-delivery-check-') as tmp:
        folder = Path(tmp) / 'selected-context'
        folder.mkdir()
        shutil.copyfile(root / 'graph.json', folder / 'enriched_graph.json')
        shutil.copyfile(root / 'context.json', folder / 'context.json')
        reproduced = Path(tmp) / 'reproduced'
        deliver(root / 'prepared', folder, reproduced, prior if prior.exists() else None, _verified_previous=True)
        require(same(inventory(root), inventory(reproduced)), 'Delivery does not reproduce from retained inputs')
    return receipt


def receive(packet, out, expected_base):
    require(not out.resolve().is_relative_to(packet.resolve()), 'Receiving output aliases supplied packet')
    receipt = verify_delivery(packet)
    require(receipt.get('base_receipt_sha256') == expected_base,
            'Receiver expected base disagrees; reconcile current receiving history explicitly')
    require(not out.exists(), 'Receiving output already exists; retries must not append/replace history')
    # Export/reopen retains exact source graph, sidecar, full history and original archives.
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='foundation-receive-', dir=out.parent) as tmp:
        stage = Path(tmp) / 'packet'
        shutil.copytree(packet, stage)
        verify_delivery(stage)
        require(same(inventory(stage), inventory(packet)), 'Export/reopen changed retained content')
        stage.rename(out)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('prepare')
    p.add_argument('--profile', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p = commands.add_parser('deliver')
    p.add_argument('--prepared', type=Path, required=True)
    p.add_argument('--context', type=Path, required=True)
    p.add_argument('--previous', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p = commands.add_parser('receive')
    p.add_argument('--packet', type=Path, required=True)
    p.add_argument('--expected-base', default='initial', help='initial or exact prior receipt SHA256')
    p.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'prepare':
            result = prepare(args.profile.resolve(), args.out.resolve())
        elif args.command == 'deliver':
            result = deliver(args.prepared.resolve(), args.context.resolve(), args.out.resolve(),
                             args.previous.resolve() if args.previous else None)
        else:
            result = receive(args.packet.resolve(), args.out.resolve(),
                             None if args.expected_base == 'initial' else args.expected_base)
        print(json.dumps(dict(schema=result['schema'], files=len(result['files']), company_acceptance=False)))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print('REFUSED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
