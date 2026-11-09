"""Export and verify a portable read-only explorer for supplied twin-graph-2 engineering maps."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile

import map_changes as mc
import one_map as om
import ontology
import map_explorer_html

SCHEMA = 'engineering-map-explorer-1'
MAX_BYTES = 32 * 1024 * 1024


class InputError(ValueError):
    pass


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def method():
    names = ('map_explorer.py', 'map_explorer_html.py', 'map_changes.py', 'one_map.py', 'ontology.py', 'graph_export.py')
    return {name: sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n', b'\n')) for name in names}


def load(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise InputError(f'{path.name}: exceeds 32 MiB limit')
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise InputError(f'duplicate JSON key: {k}')
            out[k] = v
        return out
    def constant(value):
        raise InputError(f'non-finite JSON value: {value}')
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def graph(path):
    g = load(path)
    if not isinstance(g, dict) or g.get('schema') != om.SCHEMA:
        raise InputError('map must be a twin-graph-2 snapshot from one_map.py build')
    bad = om.problems(g)
    if bad:
        raise InputError('invalid map: ' + '; '.join(bad[:5]))
    # Validate the existing consumers before producing any output.
    mc.View(g, 'map')
    return g


def walk(value, pointer=''):
    if isinstance(value, dict):
        yield pointer, value
        for key, child in value.items():
            yield from walk(child, pointer + '/' + key.replace('~', '~0').replace('/', '~1'))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from walk(child, pointer + '/' + str(i))


def references(g):
    return [{'pointer': p, 'source': v} for p, v in walk(g) if isinstance(v.get('path'), str)]


def safe_relative(value):
    # Interpret identically on Windows and Linux; never follow an absolute/URL/ADS path.
    if not isinstance(value, str) or not value or '\\' in value or ':' in value or '\x00' in value:
        raise InputError('unsafe relative evidence path')
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ('', '.', '..') for x in value.split('/')):
        raise InputError('unsafe relative evidence path')
    return p


def local_file(root, relative):
    rel = safe_relative(relative)
    root = Path(root).resolve()
    path = root.joinpath(*rel.parts)
    # Refuse links/junctions even if their resolved target would be within root.
    for part in [path, *path.parents]:
        if part == root:
            break
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise InputError('linked evidence path')
    if not path.resolve().is_relative_to(root):
        raise InputError('evidence path escapes root')
    return path


def evidence(g, label, root, retained):
    rows = []
    for ref in references(g):
        src = ref['source']
        row = {'snapshot': label, **ref, 'status': 'unbound', 'retained': None}
        digest = src.get('sha256')
        try:
            safe_relative(src['path'])
        except InputError:
            row['status'] = 'unsafe_path'
        else:
            if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
                row['status'] = 'unbound'
            elif root is None:
                row['status'] = 'not_supplied'
            else:
                try:
                    p = local_file(root, src['path'])
                    if not p.is_file():
                        row['status'] = 'missing'
                    elif p.stat().st_size > MAX_BYTES:
                        row['status'] = 'too_large'
                    else:
                        content = p.read_bytes()
                        actual = sha(content)
                        row['observed_sha256'] = actual
                        if actual != digest:
                            row['status'] = 'hash_mismatch'
                        else:
                            # Content addressing prevents old/new same-path collisions.
                            target = 'evidence/' + digest + '.bin'
                            retained[target] = content
                            row.update(status='retained', retained=target)
                except InputError:
                    row['status'] = 'unsafe_path'
        rows.append(row)
    return rows


def inspect(g, nid):
    node = next(n for n in g['nodes'] if n['id'] == nid)
    item = nid in mc.View(g, 'map').items
    answers = {k: ontology.ask(g, k, nid) for k in ontology.QUESTION_KINDS} if item else {}
    docs = {f['other'] for a in answers.values() for f in a['facts']
            if f.get('other') and any(n['id'] == f['other'] and n['kind'] == 'document' for n in g['nodes'])}
    return {'node': node,
            'edges': [e for e in g['edges'] if nid in (e['from'], e['to'])],
            'documents': [n for n in g['nodes'] if n['id'] in docs],
            'conflicts': [n['conflict'] for n in g['nodes'] if n['kind'] == 'conflict'
                          and n['conflict']['subject'] == nid],
            'records': {kind: [r for r in rows if r.get('item') == nid]
                        for kind, rows in (g.get('records') or {}).items()
                        if any(r.get('item') == nid for r in rows)},
            'answers': answers}


def derived(current, previous, item):
    if previous and current.get('site') != previous.get('site'):
        raise InputError('previous and current map must have the same site identity')
    selected = None
    if item:
        selected, reason = ontology.resolve_item(current, item)
        if selected is None:
            raise InputError(reason)
    snapshots = {'current': current, **({'previous': previous} if previous else {})}
    # The same complete source records are available to CLI users and the HTML viewer.
    views = {label: {n['id']: inspect(g, n['id']) for n in g['nodes']} for label, g in snapshots.items()}
    change = mc.changes(previous, current) if previous else None
    node_changes = []
    if previous:
        old = {n['id']: n for n in previous['nodes']}
        new = {n['id']: n for n in current['nodes']}
        for nid in sorted(old.keys() | new.keys()):
            if encoded(old.get(nid)) != encoded(new.get(nid)):
                node_changes.append({'id': nid, 'before': old.get(nid), 'after': new.get(nid)})
    return {'schema': SCHEMA, 'selected': selected, 'views': views,
            'changes': change, 'node_changes': node_changes,
            'limits': [
                'Supplied snapshots and prepared interpretations; no new model/image extraction or plant verification.',
                'Recorded relationships are not isolation instructions, operating consequences or proof of physical adjacency.',
                'Source authority and document release are declared metadata; no authentication or engineering sign-off.',
                'Missing/unbound originals remain unavailable. Hash matches bind bytes, not the truth of a claim.',
                'Snapshot comparison does not refresh a context register or manage ongoing work.',
                'Export contains the entire selected map and retained sources; item selection does not restrict access.'
            ]}


def files_at(root):
    out = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()):
            raise InputError('linked packet member')
        if p.is_file() and p != root / 'RECEIPT.json':
            out[p.relative_to(root).as_posix()] = sha(p.read_bytes())
    return out


def export(map_path, out, previous_path=None, sources=None, previous_sources=None, item=None):
    out = Path(out)
    if out.exists():
        raise InputError('output already exists; choose a new directory')
    current = graph(map_path)
    previous = graph(previous_path) if previous_path else None
    if previous_sources and not previous:
        raise InputError('--previous-sources needs --previous')
    result = derived(current, previous, item)
    retained = {}
    refs = evidence(current, 'current', sources, retained)
    if previous:
        refs += evidence(previous, 'previous', previous_sources, retained)
    payload = {'exploration': result, 'evidence': refs}
    blobs = {'current.json': Path(map_path).read_bytes(),
             'exploration.json': encoded(result), 'evidence.json': encoded(refs),
             'index.html': map_explorer_html.render(payload).encode('utf-8'), **retained}
    if previous:
        blobs['previous.json'] = Path(previous_path).read_bytes()
    if result['changes']:
        blobs['changes.md'] = mc.changes_md(result['changes']).encode('utf-8')
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.map-explorer-', dir=out.parent) as temp:
        stage = Path(temp) / 'packet'
        stage.mkdir()
        for name, data in blobs.items():
            p = stage / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        receipt = {'schema': SCHEMA, 'method': method(), 'files': files_at(stage)}
        (stage / 'RECEIPT.json').write_bytes(encoded(receipt))
        verify(stage)
        stage.rename(out)
    return result


def verify(root, expected_receipt_sha256=None):
    root = Path(root)
    if expected_receipt_sha256 and sha((root / 'RECEIPT.json').read_bytes()) != expected_receipt_sha256:
        raise InputError('receipt differs from the independently retained delivery hash')
    receipt = load(root / 'RECEIPT.json')
    if receipt.get('method') != method():
        raise InputError('packet method differs; use the recorded tool revision to verify this delivery')
    if receipt.get('schema') != SCHEMA or receipt.get('files') != files_at(root):
        raise InputError('packet inventory/hash mismatch')
    current = graph(root / 'current.json')
    previous = graph(root / 'previous.json') if (root / 'previous.json').exists() else None
    result = load(root / 'exploration.json')
    expected = derived(current, previous, result.get('selected'))
    if encoded(result) != encoded(expected):
        raise InputError('derived map views differ from complete retained snapshots')
    refs = load(root / 'evidence.json')
    source_refs = [{'snapshot': label, **ref}
                   for label, g in [('current', current), *([('previous', previous)] if previous else [])]
                   for ref in references(g)]
    if encoded([{k: row[k] for k in ('snapshot', 'pointer', 'source')} for row in refs]) != encoded(source_refs):
        raise InputError('evidence references differ from snapshots')
    expected_names = {'current.json', 'exploration.json', 'evidence.json', 'index.html'}
    if previous:
        expected_names |= {'previous.json', 'changes.md'}
        if (root / 'changes.md').read_bytes() != mc.changes_md(expected['changes']).encode('utf-8'):
            raise InputError('change report differs from retained snapshots')
    for row in refs:
        if row['status'] == 'retained':
            name = row['retained']
            digest = row['source'].get('sha256')
            if name != 'evidence/' + str(digest) + '.bin' or row.get('observed_sha256') != digest:
                raise InputError('invalid retained evidence binding')
            if sha(local_file(root, name).read_bytes()) != digest:
                raise InputError('retained source hash differs from declared source')
            expected_names.add(name)
        elif row['retained'] is not None or row['status'] not in (
                'unbound', 'unsafe_path', 'not_supplied', 'missing', 'too_large', 'hash_mismatch'):
            raise InputError('invalid unavailable evidence status')
    if set(receipt['files']) != expected_names:
        raise InputError('unexpected or omitted packet member')
    html = map_explorer_html.render({'exploration': expected, 'evidence': refs}).encode('utf-8')
    if (root / 'index.html').read_bytes() != html:
        raise InputError('explorer HTML differs from retained records')
    return {'schema': SCHEMA, 'verified': True, 'files': len(receipt['files']),
            'meaning': 'Complete local snapshot/view/source-byte consistency, not source authentication or engineering acceptance.'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('export', help='make an offline explorer; exports the entire map')
    q.add_argument('--map', required=True)
    q.add_argument('--previous')
    q.add_argument('--sources', help='explicit local root for current hash-bound source paths')
    q.add_argument('--previous-sources', help='separate local root for previous snapshot sources')
    q.add_argument('--item', help='initial item; ambiguous tags are refused before writing')
    q.add_argument('--out', required=True)
    q = sub.add_parser('verify', help='recompute complete derived views and check retained bytes offline')
    q.add_argument('packet')
    q.add_argument('--expected-receipt-sha256', help='independently retained receipt hash for this exact delivery')
    a = p.parse_args(argv)
    try:
        if a.command == 'verify':
            print(json.dumps(verify(a.packet, a.expected_receipt_sha256), ensure_ascii=False))
        else:
            r = export(a.map, a.out, a.previous, a.sources, a.previous_sources, a.item)
            print(json.dumps({'schema': SCHEMA, 'out': str(Path(a.out)), 'selected': r['selected']}, ensure_ascii=False))
    except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f'map explorer: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
