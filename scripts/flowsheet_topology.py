"""Score a described process model's units and connections against a flowsheet's own unit and Arc declarations.

Task `flowsheet-topology`, scoring contract `role-aligned-arcs-v1` (benchmarks/README.md):

- The key is read from flowsheet source code by parsing it (Python `ast`; the code is never executed). A unit is an
  attribute assignment `m.fs.<id> = <Class>(...)` whose class is imported from the IDAES unit model library; an arc is
  `m.fs.<id> = Arc(source=m.fs.<unit>.<port>, destination=m.fs.<unit>.<port>)`. Feed and Product blocks are boundary
  terminals. Every unit class maps to one coarse role (ROLE_OF_CLASS); an unknown class refuses the key.
- The answer is a native process model (the description workflow's model.json): units with a native `type`, and
  streams `from`/`to` unit ids or `BL` (battery limit). Each BL end becomes its own feed or product terminal.
  A unit's role comes from its native type (ROLE_OF_TYPE). The native vocabulary has no turbine, splitter or mixer
  type, so two name rules apply, and only inside a type group: a `compressor` whose name or id says turbine or
  expander is an expander; a vessel-type unit or `feed_header` whose name or id says split is a splitter.
- Units: multiset agreement of process-unit roles. Boundaries: feed and product terminal counts. Connections: directed
  unit-to-unit (and terminal) edges, after the role-preserving one-to-one alignment of answer nodes to key nodes that
  matches the most key arcs. Names, ports, stream identities, conditions and the order of parallel arcs are not
  graded; two units of the same role can be swapped by the alignment (a heater/cooler swap is invisible).

Controls, reported in every table: from the key alone, the reference (key converted to a native model, must score
1.0), empty, reversed (every arc reversed) and shuffled (each arc's destination moved to the next arc's, in a fixed
order); from each answer, the same reversed and shuffled corruptions of its own streams, and a naive baseline that
chains the answer's units in the order the source first mentions them (feeds into the first, products out of the
last). Wrong controls must stay at or below WRONG_CONTROL_MAX connection F1; the chain baseline is a method to beat,
not a wrong answer.

    python scripts/flowsheet_topology.py key --flowsheet <file.py> --commit <sha> --out key.json
    python scripts/flowsheet_topology.py prose --notebook <file.ipynb> [--stop "# 4."] --out source.txt
    python scripts/flowsheet_topology.py score --key key.json --model model.json
Standard library only; offline.
"""
import argparse
import ast
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys

SCHEMA = 'flowsheet-topology-key/1'
CONTRACT = 'role-aligned-arcs-v1'
METRICS = ('units', 'boundaries', 'connections')
TERMINALS = ('feed', 'product')
WRONG_KEY_CONTROLS = ('empty', 'reversed', 'shuffled')
WRONG_ANSWER_CONTROLS = ('reversed', 'shuffled')
WRONG_CONTROL_MAX = 0.35
MAX_ALIGNMENTS = 2_000_000
UNIT_LIBRARY = re.compile(r'idaes\.(models|generic_models)\.unit_models(\.|$)')
ROLE_OF_CLASS = {
    'Feed': 'feed', 'FeedFlash': 'feed', 'Product': 'product',
    'Mixer': 'mixer', 'MixerData': 'mixer',
    'Separator': 'splitter', 'SeparatorData': 'splitter',
    'Compressor': 'compressor', 'Pump': 'pump', 'Turbine': 'expander', 'PressureChanger': None,
    'Heater': 'heat_exchange', 'HeatExchanger': 'heat_exchange', 'HeatExchanger1D': 'heat_exchange',
    'HeatExchangerNTU': 'heat_exchange', 'HeatExchangerLumpedCapacitance': 'heat_exchange',
    'StoichiometricReactor': 'reactor', 'GibbsReactor': 'reactor', 'EquilibriumReactor': 'reactor',
    'CSTR': 'reactor', 'PFR': 'reactor',
    'Flash': 'separator',
}
ROLE_OF_TYPE = {'feed_header': 'mixer', 'compressor': 'compressor', 'pump': 'pump',
                'heat_exchanger': 'heat_exchange', 'condenser': 'heat_exchange', 'reactor': 'reactor',
                'separator': 'separator', 'vessel': 'separator', 'pressure_vessel': 'separator',
                'tank': 'separator', 'stripper': 'column'}
VESSEL_TYPES = ('separator', 'vessel', 'pressure_vessel', 'tank', 'feed_header')
EXPANDER_WORDS = re.compile(r'turbine|expander', re.I)
SPLIT_WORDS = re.compile(r'split', re.I)
NATIVE_FOR_ROLE = {'mixer': ('feed_header', 'Mixer'), 'compressor': ('compressor', 'Compressor'),
                   'expander': ('compressor', 'Turbine'), 'pump': ('pump', 'Pump'),
                   'heat_exchange': ('heat_exchanger', 'Heat exchanger'), 'reactor': ('reactor', 'Reactor'),
                   'separator': ('separator', 'Flash drum'), 'splitter': ('vessel', 'Splitter'),
                   'column': ('stripper', 'Column')}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def text_digest(path):
    return digest(Path(path).read_bytes().replace(b'\r\n', b'\n'))


def f1(row):
    total = row['predicted'] + row['truth']
    return 2 * row['tp'] / total if total else None


# ------------------------------------------------------------------ the key, from flowsheet source

def _fs_name(node):
    """`m.fs.<name>` -> name; anything else -> None."""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute) and node.value.attr == 'fs':
        return node.attr
    return None


def _port(node):
    """`m.fs.<unit>.<port>` -> (unit, port)."""
    if isinstance(node, ast.Attribute):
        unit = _fs_name(node.value)
        if unit:
            return unit, node.attr
    raise ValueError('Arc end is not m.fs.<unit>.<port>: ' + ast.unparse(node))


def key_from_flowsheet(path, commit=None):
    """Parse (never execute) a flowsheet module into its units and Arc connections."""
    raw = Path(path).read_bytes()
    tree = ast.parse(raw.decode('utf-8-sig'))
    library = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and UNIT_LIBRARY.match(node.module):
            library.update(alias.asname or alias.name for alias in node.names)
    units, arcs, seen = [], [], set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.value, ast.Call)):
            continue
        name = _fs_name(node.targets[0])
        func = node.value.func
        cls = func.id if isinstance(func, ast.Name) else None
        if not name or not cls:
            continue
        kwargs = {k.arg: k.value for k in node.value.keywords if k.arg}
        if cls == 'Arc':
            if 'source' not in kwargs or 'destination' not in kwargs:
                raise ValueError(f'Arc {name} needs source and destination keywords')
            (a, pa), (b, pb) = _port(kwargs['source']), _port(kwargs['destination'])
            arcs.append({'id': name, 'from': a, 'from_port': pa, 'to': b, 'to_port': pb})
        elif cls in library:
            if cls not in ROLE_OF_CLASS:
                raise ValueError(f'Unit class {cls} ({name}) has no role in ROLE_OF_CLASS; add one before scoring')
            role = ROLE_OF_CLASS[cls]
            if cls == 'PressureChanger':
                flag = kwargs.get('compressor')
                if not isinstance(flag, ast.Constant) or not isinstance(flag.value, bool):
                    raise ValueError(f'PressureChanger {name} needs a literal compressor=True/False')
                role = 'compressor' if flag.value else 'expander'
            if name in seen:
                raise ValueError('Unit declared twice: ' + name)
            seen.add(name)
            units.append({'id': name, 'class': cls, 'role': role})
    if not units or not arcs:
        raise ValueError('No units or no arcs found in ' + Path(path).name)
    if len({a['id'] for a in arcs}) != len(arcs):
        raise ValueError('Arc declared twice')
    for arc in arcs:
        for end in ('from', 'to'):
            if arc[end] not in seen:
                raise ValueError(f"Arc {arc['id']} names {arc[end]}, which is not a declared unit")
    key = {'schema': SCHEMA, 'scoring_contract': CONTRACT,
           'source': {'file': Path(path).name, 'sha256': text_digest(path), 'commit': commit},
           'derivation': 'scripts/flowsheet_topology.py key: ast parse of unit constructors imported from the IDAES '
                         'unit model library and Arc(source=..., destination=...) assignments; not executed',
           'units': units, 'arcs': arcs}
    check_key(key)
    return key


def check_key(key):
    if not (isinstance(key, dict) and key.get('schema') == SCHEMA):
        raise ValueError('Flowsheet key needs schema ' + SCHEMA)
    ids = [u.get('id') for u in key.get('units', [])]
    if not ids or len(set(ids)) != len(ids) or not all(isinstance(i, str) and i for i in ids):
        raise ValueError('Flowsheet key needs unique unit ids')
    roles = set(ROLE_OF_CLASS.values()) - {None}
    if any(u.get('role') not in roles for u in key['units']):
        raise ValueError('Flowsheet key unit with an unknown role')
    if not key.get('arcs'):
        raise ValueError('Flowsheet key has no arcs')
    for arc in key['arcs']:
        if arc.get('from') not in ids or arc.get('to') not in ids:
            raise ValueError('Flowsheet key arc names an unknown unit')


# ------------------------------------------------------------------ graphs

def key_graph(key):
    nodes = {u['id']: u['role'] for u in key['units']}
    edges = [(a['from'], a['to'], a['id']) for a in key['arcs']]
    return nodes, edges


def unit_role(row):
    kind = row.get('type')
    words = f"{row.get('id', '')} {row.get('name', '')}"
    if kind == 'compressor' and EXPANDER_WORDS.search(words):
        return 'expander'
    if kind in VESSEL_TYPES and SPLIT_WORDS.search(words):
        return 'splitter'
    return ROLE_OF_TYPE.get(kind, 'other')


def answer_graph(answer):
    """Native model -> (nodes {id: role}, edges [(from, to, stream id)], first-cited line per unit)."""
    if answer is None:
        return {}, [], {}
    if not isinstance(answer, dict):
        raise ValueError('Answer must be an object')
    model = answer.get('model', answer)
    if not isinstance(model, dict) or not isinstance(model.get('units', []), list) or \
            not isinstance(model.get('streams', []), list):
        raise ValueError('Answer needs units and streams lists')
    nodes, lines = {}, {}
    for row in model.get('units', []):
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'] or row['id'] == 'BL':
            raise ValueError('Every unit needs a nonempty id other than BL')
        if row['id'] in nodes:
            raise ValueError('Duplicate unit id: ' + row['id'])
        nodes[row['id']] = unit_role(row)
        match = re.match(r'source\.txt:L(\d+)-L\d+$', str(row.get('source', '')))
        lines[row['id']] = int(match.group(1)) if match else 10 ** 9
    edges = []
    for row in model.get('streams', []):
        if not isinstance(row, dict) or not isinstance(row.get('id'), str):
            raise ValueError('Every stream needs an id')
        ends = []
        for end, terminal in (('from', 'feed'), ('to', 'product')):
            ref = row.get(end)
            if ref == 'BL':
                tid = f'BL:{terminal}:{row["id"]}'
                nodes[tid] = terminal
                ends.append(tid)
            elif ref in nodes and not str(ref).startswith('BL:'):
                ends.append(ref)
            else:
                raise ValueError(f'Stream {row["id"]} {end} names an unknown unit: {ref!r}')
        edges.append((ends[0], ends[1], row['id']))
    return nodes, edges, lines


def best_alignment(pred_nodes, pred_edges, key_nodes, key_edges):
    """Role-preserving injective map answer node -> key node that matches the most key arcs (ties: first found)."""
    key_count = Counter((a, b) for a, b, _ in key_edges)
    roles = sorted(set(pred_nodes.values()) & set(key_nodes.values()))
    groups = []
    total = 1
    for role in roles:
        p = sorted(n for n, r in pred_nodes.items() if r == role)
        k = sorted(n for n, r in key_nodes.items() if r == role)
        if len(p) <= len(k):
            options = [dict(zip(p, perm)) for perm in itertools.permutations(k, len(p))]
        else:
            options = [dict(zip(perm, k)) for perm in itertools.permutations(p, len(k))]
        total *= len(options)
        if total > MAX_ALIGNMENTS:
            raise ValueError('Too many same-role alignments to search exactly; the answer is outside this scorer')
        groups.append(options)
    best, best_tp = {}, -1
    for combo in itertools.product(*groups):
        mapping = {}
        for part in combo:
            mapping.update(part)
        mapped = Counter((mapping.get(a), mapping.get(b)) for a, b, _ in pred_edges)
        tp = sum(min(n, key_count[pair]) for pair, n in mapped.items() if None not in pair)
        if tp > best_tp:
            best, best_tp = mapping, tp
    return best, max(best_tp, 0)


def counts_of(key, pred_nodes, pred_edges):
    key_nodes, key_edges = key_graph(key)
    def roles(nodes, terminal):
        return Counter(r for r in nodes.values() if (r in TERMINALS) == terminal)
    out = {}
    for metric, terminal in (('units', False), ('boundaries', True)):
        want, got = roles(key_nodes, terminal), roles(pred_nodes, terminal)
        out[metric] = {'tp': sum((want & got).values()), 'predicted': sum(got.values()), 'truth': sum(want.values())}
    mapping, tp = best_alignment(pred_nodes, pred_edges, key_nodes, key_edges)
    out['connections'] = {'tp': tp, 'predicted': len(pred_edges), 'truth': len(key_edges)}
    return out, mapping


def matched(key, mapping, pred_edges):
    """Which key arcs and answer streams the alignment matched (multiset, in a fixed order)."""
    _, key_edges = key_graph(key)
    remaining = list(key_edges)
    used_streams = []
    for a, b, sid in pred_edges:
        pair = (mapping.get(a), mapping.get(b))
        for i, (ka, kb, _) in enumerate(remaining):
            if (ka, kb) == pair:
                remaining.pop(i)
                used_streams.append(sid)
                break
    return sorted(arc for _, _, arc in remaining), sorted(sid for _, _, sid in pred_edges if sid not in used_streams)


def reversed_edges(edges):
    return [(b, a, sid) for a, b, sid in edges]


def shuffled_edges(edges):
    """Each edge keeps its source; destinations move one place along the edges sorted by (source, destination)."""
    ordered = sorted(edges, key=lambda e: (e[0], e[1], e[2]))
    if len(ordered) < 2:
        return reversed_edges(ordered)
    dests = [e[1] for e in ordered]
    return [(a, dests[(i + 1) % len(dests)], sid) for i, (a, _, sid) in enumerate(ordered)]


def chain_edges(nodes, edges, lines):
    """Naive baseline: the answer's own process units chained in first-mention order, its terminals at the ends."""
    units = sorted((n for n, r in nodes.items() if r not in TERMINALS), key=lambda n: (lines.get(n, 10 ** 9), n))
    if not units:
        return []
    feeds = sorted(n for n, r in nodes.items() if r == 'feed')
    products = sorted(n for n, r in nodes.items() if r == 'product')
    out = [(f, units[0], 'chain-in-' + f) for f in feeds]
    out += [(a, b, f'chain-{i}') for i, (a, b) in enumerate(zip(units, units[1:]), 1)]
    out += [(units[-1], p, 'chain-out-' + p) for p in products]
    return out


def score(key, answer):
    """Counts per metric and diagnostics (alignment, missing arcs, unexpected streams, answer-derived controls)."""
    check_key(key)
    nodes, edges, lines = answer_graph(answer)
    result, mapping = counts_of(key, nodes, edges)
    missing, unexpected = matched(key, mapping, edges)
    controls = {}
    if edges:
        controls = {'reversed': counts_of(key, nodes, reversed_edges(edges))[0],
                    'shuffled': counts_of(key, nodes, shuffled_edges(edges))[0],
                    'mention_order_chain': counts_of(key, nodes, chain_edges(nodes, edges, lines))[0]}
    return result, {'alignment': {k: v for k, v in sorted(mapping.items())}, 'missing_arcs': missing,
                    'unexpected_streams': unexpected,
                    'answer_roles': dict(sorted(Counter(nodes.values()).items())), 'controls': controls}


# ------------------------------------------------------------------ key-derived controls

def key_as_model(key):
    """The key written as a native model (positive control): roles round-trip through ROLE_OF_TYPE."""
    units, streams = [], []
    roles = {u['id']: u['role'] for u in key['units']}
    for u in key['units']:
        if u['role'] in TERMINALS:
            continue
        kind, name = NATIVE_FOR_ROLE[u['role']]
        units.append({'id': u['id'], 'name': name, 'type': kind, 'source': 'source.txt:L1-L1'})
    for a in key['arcs']:
        streams.append({'id': a['id'], 'name': a['id'],
                        'from': 'BL' if roles[a['from']] in TERMINALS else a['from'],
                        'to': 'BL' if roles[a['to']] in TERMINALS else a['to'], 'source': 'source.txt:L1-L1'})
    return {'units': units, 'streams': streams}


def key_controls(key):
    reference = key_as_model(key)
    nodes, edges, _ = answer_graph(reference)
    return {'reference': counts_of(key, nodes, edges)[0],
            'empty': counts_of(key, {}, [])[0],
            'reversed': counts_of(key, nodes, reversed_edges(edges))[0],
            'shuffled': counts_of(key, nodes, shuffled_edges(edges))[0]}


def check_key_controls(table):
    problems = []
    for metric in METRICS:
        row = table['reference'][metric]
        if not row['tp'] == row['predicted'] == row['truth'] > 0 and not (metric == 'boundaries' and row['truth'] == 0):
            problems.append(f'reference control does not reproduce the key ({metric})')
    for name in WRONG_KEY_CONTROLS:
        value = f1(table[name]['connections']) or 0.0
        if value > WRONG_CONTROL_MAX:
            problems.append(f'{name} control connection F1 {value:.3f} > {WRONG_CONTROL_MAX}')
    return problems


# ------------------------------------------------------------------ the description input

def notebook_prose(path, stop=None):
    """A notebook's markdown cells in order (code cells and their outputs dropped), trailing spaces stripped from
    each line, cells separated by a blank line, ending before the first markdown cell that starts with `stop`."""
    nb = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    parts = []
    for c in nb.get('cells', []):
        if c.get('cell_type') != 'markdown':
            continue
        text = ''.join(c.get('source', [])) if isinstance(c.get('source'), list) else str(c.get('source', ''))
        if stop and text.lstrip().startswith(stop):
            break
        parts.append('\n'.join(line.rstrip() for line in text.strip('\n').splitlines()))
    return '\n\n'.join(parts) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('key')
    p.add_argument('--flowsheet', type=Path, required=True)
    p.add_argument('--commit')
    p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('prose')
    p.add_argument('--notebook', type=Path, required=True)
    p.add_argument('--stop')
    p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('score')
    p.add_argument('--key', type=Path, required=True)
    p.add_argument('--model', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == 'key':
            key = key_from_flowsheet(args.flowsheet, args.commit)
            args.out.write_text(json.dumps(key, indent=2) + '\n', encoding='utf-8', newline='\n')
            print(f"{len(key['units'])} units, {len(key['arcs'])} arcs -> {args.out}")
        elif args.action == 'prose':
            args.out.write_text(notebook_prose(args.notebook, args.stop), encoding='utf-8', newline='\n')
            print(f'wrote {args.out}')
        else:
            key = json.loads(args.key.read_text(encoding='utf-8'))
            counts, diag = score(key, json.loads(args.model.read_text(encoding='utf-8')))
            print(json.dumps({'counts': counts, 'f1': {m: f1(r) for m, r in counts.items()},
                              'key_controls': key_controls(key), 'diagnostics': diag}, indent=2))
        return 0
    except (OSError, ValueError, SyntaxError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
