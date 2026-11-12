"""Score per-order system classes against a publisher's separately coded system field, with wrong controls.

Task `maintenance-system-grouping` (contract `system-groups-v1`), first registered for the Nestor excavator records
(data/corpus_depth.json#nestor-excavators). Given raw work-order rows (a CSV with no work-order ID, so the CSV record
number is the identity, as `maintenance_history.py` assigns it with `identity: "record"`) and an answer that assigns
each selected record a system class or nothing, it joins every raw record to the publisher's cleaned file and scores:

- `orders`: per-order system class. A record is correct when its assigned class is one of the key's systems (the
  cleaned file's `MajorSystem`, split on `_`, with `NA` meaning no system). Precision is over assigned records whose
  key names a system; recall is over every record whose key names a system. Records the key gives no system are not
  in either denominator; how many of them got a class is reported separately (`assigned_without_key_system`).
- `groups`: the (asset, system) recurring-work groups, a class with at least two records on one asset, against the
  key's (asset, system) pairs with at least two records.
- `membership`: (record, system) pairs inside those groups, against the key's pairs inside its groups.

The join never reads the answer: raw and cleaned rows are matched on (date, asset, description with backslashes and
double quotes removed, then stripped), the k-th raw occurrence of a key to the k-th cleaned occurrence in file order.
Raw records with no cleaned row are unkeyed and left out of every count (reported). The cleaned file is read with a
backslash escape character, as the publisher's loader (`nestor/datasets/excavators.py`) reads it; the raw file is
read as plain CSV, as the tool reads it.

Every score comes with the same controls, computed here from the answer, the key and fixed constants:
`reference` (the key's own systems: must score 1.0), `raw-asset-baseline` (the predeclared AMPS raw-asset-ID
grouping of examples/maintenance-history/baseline.py: one group per asset and no system, so it assigns nothing),
`majority-system` (every record gets one fixed class), `shuffled-within-asset` (the answer's own classes permuted
among each asset's records with a fixed seed) and `misaligned-key` (the answer scored against the key of the keyed
record half the asset's records further on). Stdlib only, offline.
"""
import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

CONTRACT = 'system-groups-v1'
NO_SYSTEM = 'NA'
SEED = 420
CONTROL_ORDER = ('reference', 'raw-asset-baseline', 'majority-system', 'shuffled-within-asset', 'misaligned-key')
METRICS = ('orders', 'groups', 'membership')


def normal(text):
    return text.replace('\\', '').replace('"', '').strip()


def read_rows(path, escaped):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, escapechar='\\' if escaped else None)
        header = next(reader)
        return [(number, dict(zip(header, cells))) for number, cells in enumerate(reader, 2)]


def keyed_records(raw_path, cleaned_path, assets):
    """Raw record number -> (asset, systems) for the selected assets; plus join counts. Never reads an answer."""
    assets = set(assets)
    raw = [(n, r) for n, r in read_rows(raw_path, False) if r.get('Asset') in assets]
    cleaned = [r for _, r in read_rows(cleaned_path, True) if r.get('Asset') in assets]
    queue = defaultdict(list)
    for r in cleaned:
        queue[(r['BscStartDate'], r['Asset'], normal(r['OriginalShorttext']))].append(r)
    taken = Counter()
    key, unkeyed = {}, []
    for number, r in raw:
        k = (r['BscStartDate'], r['Asset'], normal(r['OriginalShorttext']))
        if taken[k] < len(queue[k]):
            row = queue[k][taken[k]]
            taken[k] += 1
            systems = tuple(s for s in row['MajorSystem'].split('_') if s and s != NO_SYSTEM)
            key[str(number)] = (r['Asset'], systems)
        else:
            unkeyed.append(str(number))
    join = dict(raw_records=len(raw), cleaned_records=len(cleaned), keyed=len(key), unkeyed_raw=len(unkeyed),
                unmatched_cleaned=len(cleaned) - sum(taken.values()),
                keyed_with_system=sum(bool(s) for _, s in key.values()))
    return key, join


def pairs(labels, key):
    """(asset, class) groups with >= 2 records, and their (record, class) members."""
    by = defaultdict(list)
    for rid, cls in labels.items():
        for c in ([cls] if isinstance(cls, str) else cls):
            if c:
                by[(key[rid][0], c)].append(rid)
    groups = {g for g, ids in by.items() if len(ids) >= 2}
    return groups, {(rid, g[1]) for g in groups for rid in by[g]}


def counts(assigned, key):
    """assigned: record number -> class ('' for none), over keyed records only."""
    labels = {rid: assigned.get(rid, '') for rid in key}
    with_system = [rid for rid, (_, s) in key.items() if s]
    predicted = [rid for rid in with_system if labels[rid]]
    # A single class is right when it is one of the key's systems; a tuple (the reference control) must equal them.
    correct = [rid for rid in predicted if (labels[rid] in key[rid][1] if isinstance(labels[rid], str)
                                            else set(labels[rid]) == set(key[rid][1]))]
    truth_groups, truth_members = pairs({rid: s for rid, (_, s) in key.items()}, key)
    groups, members = pairs(labels, key)
    no_system = [rid for rid, (_, s) in key.items() if not s]
    return ({'orders': dict(tp=len(correct), predicted=len(predicted), truth=len(with_system)),
             'groups': dict(tp=len(groups & truth_groups), predicted=len(groups), truth=len(truth_groups)),
             'membership': dict(tp=len(members & truth_members), predicted=len(members), truth=len(truth_members))},
            dict(assigned_without_key_system=sum(bool(labels[r]) for r in no_system), keyed_without_system=len(no_system)))


def rates(row):
    tp, pred, truth = row['tp'], row['predicted'], row['truth']
    return dict(precision=round(tp / pred, 4) if pred else None, recall=round(tp / truth, 4) if truth else None,
                f1=round(2 * tp / (pred + truth), 4) if pred + truth else None)


def control_answers(assigned, key, majority):
    ids = sorted(key, key=int)
    by_asset = defaultdict(list)
    for rid in ids:
        by_asset[key[rid][0]].append(rid)
    rng = random.Random(SEED)
    shuffled = {}
    for asset in sorted(by_asset):
        own = [assigned.get(rid, '') for rid in by_asset[asset]]
        rng.shuffle(own)
        shuffled.update(zip(by_asset[asset], own))
    return {'reference': {rid: key[rid][1] for rid in ids},
            'raw-asset-baseline': {rid: '' for rid in ids},
            'majority-system': {rid: majority for rid in ids},
            'shuffled-within-asset': shuffled}


def misaligned(key):
    """Each keyed record takes the systems of the keyed record half the asset's records further on (wrapping).

    Not the next record: the raw file is ordered so that neighbours often share a system (found on development,
    2026-11-12), which made a one-step shift a weak control."""
    by_asset = defaultdict(list)
    for rid in sorted(key, key=int):
        by_asset[key[rid][0]].append(rid)
    out = {}
    for asset, ids in by_asset.items():
        for i, rid in enumerate(ids):
            out[rid] = (asset, key[ids[(i + max(1, len(ids) // 2)) % len(ids)]][1])
    return out


def evaluate(raw_path, cleaned_path, assets, assigned, majority):
    """The answer's counts and rates beside every control's, on the same keyed records."""
    key, join = keyed_records(raw_path, cleaned_path, assets)
    unknown = sorted(set(assigned) - set(key) - set(_selected_numbers(raw_path, assets)), key=int)
    if unknown:
        raise ValueError('Answer names records outside the selected raw rows: ' + ', '.join(unknown[:5]))
    table = {}
    method, extra = counts(assigned, key)
    table['method'] = dict(counts=method, rates={m: rates(method[m]) for m in METRICS}, **extra)
    answers = control_answers(assigned, key, majority)
    for name in CONTROL_ORDER:
        c, extra = counts(assigned, misaligned(key)) if name == 'misaligned-key' else counts(answers[name], key)
        table[name] = dict(counts=c, rates={m: rates(c[m]) for m in METRICS}, **extra)
    problems = control_problems(table)
    return dict(contract=CONTRACT, assets=sorted(assets), join=join, majority_class=majority, seed=SEED,
                scores=table, control_problems=problems)


def _selected_numbers(raw_path, assets):
    return [str(n) for n, r in read_rows(raw_path, False) if r.get('Asset') in set(assets)]


def control_problems(table):
    """The reference must be perfect and the no-system baseline must score nothing; a scorer that fails is broken."""
    out = []
    for m in METRICS:
        r = table['reference']['rates'][m]
        if table['reference']['counts'][m]['truth'] and not (r['precision'] == r['recall'] == 1.0):
            out.append('reference control is not perfect on ' + m)
        if table['raw-asset-baseline']['counts'][m]['predicted']:
            out.append('raw-asset baseline assigned a system on ' + m)
    return out


def margin(table, metric='orders'):
    """Method F1 minus the best wrong control's F1 (reference excluded)."""
    f = table['method']['rates'][metric]['f1'] or 0.0
    wrong = [table[n]['rates'][metric]['f1'] or 0.0 for n in CONTROL_ORDER if n != 'reference']
    return round(f - max(wrong), 4)


if __name__ == '__main__':
    sys.exit('Import this module; examples/maintenance-history/nestor.py runs it on a packet.')
