"""Conservative decoded-record correspondence diagnostic; never changes strict CAD verdicts."""
from collections import defaultdict
import copy
import hashlib
import json
import re

import recheck

POINTER_CODES = frozenset(range(330, 370)) | frozenset(range(390, 400)) | {480, 481}
HANDLE = re.compile(r'[0-9A-Fa-f]{1,16}\Z')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def expected_entities(before, plan):
    result = copy.deepcopy(before['entities'])
    edits = recheck.ch.validate_plan(before, plan) if plan is not None else {}
    for handle, change in edits.items():
        values = [tag for tag in result[handle]['tags'] if tag[0] == 1]
        recheck.require(len(values) == 1 and values[0][1] == change['before'], 'Ambiguous planned serialization')
        values[0][1] = change['after']
    return result


def signature(handle, entity):
    own = 105 if entity['type'] == 'DIMSTYLE' else 5
    values = [tag[1] for tag in entity['tags'] if tag[0] == own]
    if len(values) != 1 or values[0] != handle or not isinstance(handle, str) or not HANDLE.fullmatch(handle) or handle == '0':
        return None, 'missing, duplicate, invalid or mismatched own handle'
    body = [entity['type']]
    for tag in entity['tags']:
        if not isinstance(tag, list) or len(tag) != 2 or type(tag[0]) is not int:
            return None, 'malformed ordered tag'
        code, value = tag
        body.append(['own', code] if code == own else ['pointer', code] if code in POINTER_CODES else ['literal', code, value])
    try:
        return canonical(body), None
    except (ValueError, TypeError):
        return None, 'nonfinite or unsupported literal value'


def match(left, right):
    buckets, reasons = [], []
    for entities in (left, right):
        bins, bad = defaultdict(list), {}
        for handle, entity in entities.items():
            key, reason = signature(handle, entity)
            if reason:
                bad[handle] = dict(status='unpaired', reason=reason)
            else:
                bins[key].append(handle)
        buckets.append(bins)
        reasons.append(bad)
    seeds = {}
    for side, entities in enumerate((left, right)):
        for key, handles in buckets[side].items():
            other = buckets[1 - side].get(key, [])
            if len(handles) == len(other) == 1:
                if side == 0:
                    seeds[handles[0]] = other[0]
            else:
                for handle in handles:
                    reasons[side][handle] = dict(status='unpaired', reason='ambiguous literal body' if len(handles) > 1 or len(other) > 1 else 'literal body absent on other side',
                                                before_candidates=len(buckets[0].get(key, [])), after_candidates=len(buckets[1].get(key, [])))
    active = dict(seeds)
    rounds = []
    while active:
        removed = {}
        for a, b in active.items():
            issues = []
            for index, (lt, rt) in enumerate(zip(left[a]['tags'], right[b]['tags'])):
                code, av = lt
                if code not in POINTER_CODES:
                    continue
                bv = rt[1]
                why = None
                if av == '0' or bv == '0':
                    if av != bv:
                        why = 'null mismatch'
                elif not isinstance(av, str) or not isinstance(bv, str) or not HANDLE.fullmatch(av) or not HANDLE.fullmatch(bv):
                    why = 'malformed pointer'
                elif av not in left or bv not in right:
                    why = 'missing target record'
                elif av not in active:
                    why = 'target not in surviving correspondence'
                elif active[av] != bv:
                    why = 'target maps to another handle'
                if why:
                    issues.append(dict(tag_index=index, code=code, before_target=av, after_target=bv, reason=why))
            if issues:
                removed[a] = dict(after=b, issues=issues)
        if not removed:
            break
        rounds.append(dict(round=len(rounds) + 1, removed=removed))
        for a, detail in removed.items():
            b = active.pop(a)
            for side, handle, counterpart in ((0, a, b), (1, b, a)):
                reasons[side][handle] = dict(status='unpaired', reason='reference correspondence not established',
                                            seed_counterpart=counterpart, removed_round=len(rounds), issues=detail['issues'])
    for a, b in active.items():
        reasons[0][a] = dict(status='closed exact decoded correspondence', counterpart=b)
        reasons[1][b] = dict(status='closed exact decoded correspondence', counterpart=a)
    recheck.require(set(reasons[0]) == set(left) and set(reasons[1]) == set(right), 'Incomplete record classification')
    return dict(seed_pairs=[dict(before=a, after=b) for a, b in sorted(seeds.items())],
                pairs=[dict(before=a, after=b) for a, b in sorted(active.items())],
                pruning_rounds=rounds, before=dict(sorted(reasons[0].items())), after=dict(sorted(reasons[1].items())))


def audit(before, after, plan=None):
    strict = recheck.ch.compare(before, after, plan)
    result = match(expected_entities(before, plan), after['entities'])
    indexed = []
    for index, difference in enumerate(strict['unexpected']):
        row = dict(index=index, kind=difference['kind'], strict_difference_sha256=fingerprint(difference))
        if difference['kind'] == 'entity':
            handle = difference['handle']
            row.update(handle=handle, before=result['before'].get(handle), after=result['after'].get(handle))
        else:
            row['unchanged_strict_difference'] = difference
        indexed.append(row)
    return dict(schema='cad-decoded-correspondence-5', before_sha256=before['sha256'], after_sha256=after['sha256'],
                strict_status=strict['status'], strict_difference_count=len(strict['unexpected']),
                strict_differences=indexed, correspondence=result,
                counts=dict(before_records=len(before['entities']), after_records=len(after['entities']),
                            unique_body_seeds=len(result['seed_pairs']), closed_pairs=len(result['pairs']),
                            unpaired_before=len(before['entities']) - len(result['pairs']),
                            unpaired_after=len(after['entities']) - len(result['pairs'])),
                boundary='Diagnostic decoded tuples and declared reference edges only. Every strict verdict/index retained; no raw-byte, physical identity, visual, native UI or engineering acceptance.')
