"""Compare source-bound P&ID markup requests with supplied original/returned drawing readings.

Reads local files only; does not interpret images, infer missing connections, release a drawing or edit CAD.
See docs/PID_MARKUP_REVIEW.md. Exit 0 means a comparison packet was written, including open findings;
exit 2 means invalid/stale inputs or an output collision. Python standard library only.
"""
import argparse
import copy
import csv
import hashlib
import html
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict


class InputError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InputError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def typed(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def parse(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 'Duplicate JSON key: ' + key)
            out[key] = value
        return out
    def constant(value):
        raise InputError('Non-finite JSON value: ' + value)
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=constant)


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + ' needs nonempty text')
    return value


def fact_key(key):
    require(isinstance(key, dict), 'Fact key must be an object')
    kind = key.get('kind')
    fields = {'symbol': {'sheet', 'kind', 'subject'},
              'attribute': {'sheet', 'kind', 'subject', 'name'},
              'note': {'sheet', 'kind', 'subject'},
              'connection': {'sheet', 'kind', 'subject', 'relation', 'to'}}
    require(kind in fields and set(key) == fields[kind], 'Unsupported/ambiguous fact key')
    for field, value in key.items():
        text(value, 'Fact ' + field)
    return typed(key)


def value_check(key, value):
    typed(value)  # retain exact JSON types, including numeric/string/Boolean distinctions
    if key['kind'] in ('symbol', 'connection'):
        require(type(value) is bool, 'Symbol/connection presence needs an explicit Boolean')


def prepare(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    root = manifest_path.parent
    captured = {manifest_path: manifest_path.read_bytes()}
    manifest = parse(captured[manifest_path])
    require(isinstance(manifest, dict), 'Manifest must be an object')
    require(manifest.get('schema') == 'pid-markup-review-1', 'Expected pid-markup-review-1 manifest')

    def read_pin(ref):
        require(isinstance(ref, dict), 'File reference must be an object')
        name = text(ref.get('path'), 'File path')
        require(not Path(name).is_absolute() and ':' not in name and '\\' not in name,
                'Use a relative local path with forward slashes')
        path = (root / name).resolve()
        require(path.is_relative_to(root) and path.is_file(), 'Input must be a file inside the manifest folder')
        require(isinstance(ref.get('sha256'), str) and re.fullmatch('[0-9a-f]{64}', ref['sha256']), 'Invalid SHA-256')
        raw = path.read_bytes()
        require(digest(raw) == ref['sha256'], 'Stale file binding: ' + name)
        require(path not in captured or captured[path] == raw, 'Input changed during reading')
        captured[path] = raw
        return raw

    documents, pages, copies = {}, {}, {}
    docs = manifest.get('documents')
    require(isinstance(docs, list) and bool(docs), 'Documents are required')
    for index, doc in enumerate(docs):
        require(isinstance(doc, dict), 'Document must be an object')
        identity = text(doc.get('id'), 'Document id')
        require(identity not in documents and doc.get('role') in ('original', 'markup', 'returned'), 'Duplicate document id/invalid role')
        raw = read_pin(doc)
        require(isinstance(doc.get('pages'), list) and bool(doc['pages']), 'Declare source pages/sheets/revisions')
        documents[identity] = doc
        numbers = set()
        for page in doc['pages']:
            require(isinstance(page, dict), 'Page identity must be an object')
            number = page.get('page')
            require(type(number) is int and number > 0 and number not in numbers, 'Invalid/duplicate page number')
            numbers.add(number)
            sheet = text(page.get('sheet'), 'Qualified sheet identity')
            text(page.get('revision'), 'Source revision')
            require(page.get('identity') in ('confirmed', 'uncertain'), 'Declare sheet/revision identity confidence')
            require((doc['role'], sheet) not in pages, 'Ambiguous repeated sheet identity in one role')
            pages[doc['role'], sheet] = (doc, page)
        # Source paths never become output names or HTML attributes.
        suffix = Path(doc['path']).suffix.lower()
        require(re.fullmatch(r'\.[a-z0-9]{1,10}', suffix or ''), 'Source needs a simple file extension')
        copies[identity] = (f'sources/{index + 1:03d}{suffix}', raw)
    require({d['role'] for d in docs} == {'original', 'markup', 'returned'}, 'Retain original, markup and returned sources')
    requests_raw, readings_raw = read_pin(manifest.get('requests')), read_pin(manifest.get('readings'))
    requests, readings = parse(requests_raw), parse(readings_raw)
    require(isinstance(requests, dict) and isinstance(readings, dict), 'Requests/readings must be objects')
    require(requests.get('schema') == 'pid-markup-requests-1', 'Expected pid-markup-requests-1')
    require(readings.get('schema') == 'pid-drawing-readings-1', 'Expected pid-drawing-readings-1')
    text(requests.get('inventory_basis'), 'Markup inventory coverage/basis')
    text(readings.get('method'), 'Reading method and limitations')

    def evidence(locators, role, sheet):
        require(isinstance(locators, list) and bool(locators), 'Every intent/observation needs source evidence')
        confirmed = True
        for loc in locators:
            require(isinstance(loc, dict), 'Evidence locator must be an object')
            doc = documents.get(loc.get('document'))
            require(doc is not None and doc['role'] == role, 'Evidence uses the wrong source role')
            require(loc.get('sha256') == doc['sha256'], 'Stale observation/markup document hash')
            pair = pages.get((role, sheet))
            require(pair is not None and pair[0]['id'] == doc['id'] and type(loc.get('page')) is int
                    and pair[1]['page'] == loc['page'], 'Evidence sheet/page/document mismatch')
            box = loc.get('box_0_1000')
            require(isinstance(box, list) and len(box) == 4
                    and all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1000 for v in box)
                    and box[0] < box[2] and box[1] < box[3], 'Invalid source region')
            text(loc.get('description'), 'Evidence description/reading')
            confirmed = confirmed and pair[1]['identity'] == 'confirmed'
        return confirmed

    inventory = requests.get('markups')
    require(isinstance(inventory, list) and bool(inventory), 'Retain a nonempty markup inventory')
    markup_ids, desired = set(), {}
    for markup in inventory:
        require(isinstance(markup, dict), 'Markup must be an object')
        mid = text(markup.get('id'), 'Markup id')
        require(mid not in markup_ids, 'Duplicate markup id')
        markup_ids.add(mid)
        text(markup.get('text'), 'Requested change')
        sheet = text(markup.get('sheet'), 'Markup sheet')
        require(markup.get('priority') in ('normal', 'safety'), 'Priority must be normal or safety')
        require(markup.get('interpretation') in ('prepared', 'unreadable', 'unsupported'), 'Unknown markup interpretation')
        markup['_identity_confirmed'] = evidence(markup.get('evidence'), 'markup', sheet)
        checks = markup.get('checks')
        require(isinstance(checks, list), 'Markup checks must be a list')
        if markup['interpretation'] != 'prepared':
            require(not checks, 'Uninterpreted markups cannot have manufactured checks')
            text(markup.get('reason'), 'Uninterpreted markup reason')
        else:
            require(bool(checks), 'A prepared markup needs explicit checks')
        seen = set()
        for check in checks:
            require(isinstance(check, dict), 'Markup check must be an object')
            key = fact_key(check.get('key'))
            require(key not in seen and 'before' in check and 'after' in check, 'Duplicate/incomplete markup check')
            seen.add(key)
            value_check(check['key'], check['before']); value_check(check['key'], check['after'])
            require(typed(check['before']) != typed(check['after']), 'Markup check must describe a change')
            binding = typed([check['before'], check['after']])
            require(key not in desired or desired[key] == binding, 'Conflicting markup requests for one fact')
            desired[key] = binding
    observations = readings.get('observations')
    require(isinstance(observations, list), 'Drawing observations must be a list')
    index = defaultdict(list)
    for observation in observations:
        require(isinstance(observation, dict), 'Observation must be an object')
        role = observation.get('role')
        require(role in ('original', 'returned'), 'Observation role must be original or returned')
        key = fact_key(observation.get('key'))
        require(observation.get('state') in ('known', 'unknown'), 'Observation state must be known or unknown')
        confirmed = evidence(observation.get('evidence'), role, observation['key']['sheet'])
        if observation['state'] == 'known':
            require('value' in observation, 'Known observation needs a value')
            value_check(observation['key'], observation['value'])
            if observation['key']['kind'] in ('symbol', 'connection') and observation['value'] is False:
                text(observation.get('reason'), 'Explicit absence needs a reviewed-region/coverage reason')
        else:
            require('value' not in observation, 'Unknown observation cannot carry a guessed value')
            text(observation.get('reason'), 'Unknown reading reason')
        index[role, key].append(dict(observation, identity_confirmed=confirmed))
    return manifest, requests, readings, index, desired, copies, captured, requests_raw, readings_raw


def resolve(rows):
    if not rows:
        return dict(state='unknown', reason='No observation; absence is not inferred', observations=[])
    if not all(r['identity_confirmed'] for r in rows):
        return dict(state='unknown', reason='Sheet/revision identity unconfirmed', observations=rows)
    known = {typed(r['value']): r['value'] for r in rows if r['state'] == 'known'}
    if len(known) > 1 or (known and any(r['state'] == 'unknown' for r in rows)):
        return dict(state='ambiguous', reason='Conflicting or mixed known/unknown readings', observations=rows)
    if not known:
        return dict(state='unknown', reason='; '.join(r['reason'] for r in rows), observations=rows)
    return dict(state='known', value=next(iter(known.values())), observations=rows)


def compare(requests, index, desired):
    results = []
    for markup in requests['markups']:
        checks = []
        for check in markup['checks']:
            key = fact_key(check['key'])
            before, returned = (resolve(index.get((role, key), [])) for role in ('original', 'returned'))
            if not markup['_identity_confirmed']:
                status = 'not_verifiable'
            elif 'ambiguous' in (before['state'], returned['state']):
                status = 'ambiguous'
            elif before['state'] != 'known':
                status = 'not_verifiable'
            elif typed(before['value']) != typed(check['before']):
                status = 'baseline_mismatch'
            elif returned['state'] != 'known':
                status = 'not_verifiable'
            elif typed(returned['value']) == typed(check['after']):
                status = 'matches_request'
            elif typed(returned['value']) == typed(before['value']):
                status = 'unchanged'
            else:
                status = 'different_from_request'
            checks.append(dict(check, status=status, original=before, returned=returned))
        statuses = [c['status'] for c in checks]
        if checks and all(s == 'matches_request' for s in statuses):
            status = 'supported'
        elif 'baseline_mismatch' in statuses:
            status = 'baseline_mismatch'
        elif 'matches_request' in statuses:
            status = 'partly_supported'
        elif any(s in ('unchanged', 'different_from_request') for s in statuses):
            status = 'not_supported'
        else:
            status = 'not_verifiable'
        results.append({k: v for k, v in markup.items() if k not in ('checks', '_identity_confirmed')} |
                       dict(status=status, checks=checks, review_required=True))
    other, gaps = [], []
    for key in sorted({key for role, key in index} - set(desired)):
        before, returned = (resolve(index.get((role, key), [])) for role in ('original', 'returned'))
        row = dict(key=json.loads(key), original=before, returned=returned)
        if before['state'] != 'known' or returned['state'] != 'known':
            gaps.append(row)
        elif typed(before['value']) != typed(returned['value']):
            other.append(row)
    return dict(schema='pid-markup-result-1', release_accepted=False, automatic_drawing_reading=False,
                basis='Comparison of supplied source-bound readings, not independent verification of their meaning',
                inventory_basis=requests['inventory_basis'], counts=dict(Counter(r['status'] for r in results)),
                markups=results, other_observed_changes=other, other_fact_coverage_gaps=gaps,
                observed_fact_keys=len({key for role, key in index}),
                boundary='Only supplied facts are compared. Unlisted markups, geometry, drafting quality, off-page continuity, '
                         'functional adequacy and installed state are not established. No drawing release or company acceptance.')


def describe_key(key):
    subject = key['subject']
    if key['kind'] == 'connection':
        label = f'{subject} → {key["to"]}: {key["relation"]} connection'
    else:
        label = subject + ': ' + {'symbol': 'symbol presence', 'attribute': key.get('name', ''), 'note': 'note text'}[key['kind']]
    return label + ' · ' + key['sheet']


LABELS = {'supported': 'Supported by readings', 'partly_supported': 'Partly supported',
          'not_supported': 'Not supported', 'not_verifiable': 'Cannot verify',
          'baseline_mismatch': 'Original differs from request', 'matches_request': 'Matches request',
          'unchanged': 'Unchanged', 'different_from_request': 'Different from request', 'ambiguous': 'Ambiguous readings'}


def render(report, copies):
    esc = lambda value: html.escape(str(value), quote=True)
    def display(value, key):
        return ('Present' if value else 'Absent') if key['kind'] in ('symbol', 'connection') else typed(value)
    def locators(evidence):
        return '<br>'.join(f'<a href="{esc(copies[e["document"]][0])}">{esc(e["document"])}, page {e["page"]}</a> '
                          f'box {esc(e["box_0_1000"])}: {esc(e["description"])}' for e in evidence)
    def reading(value, key):
        label = display(value['value'], key) if value['state'] == 'known' else value.get('reason', value['state'])
        evidence = [e for o in value['observations'] for e in o['evidence']]
        return f'{esc(label)}<br>{locators(evidence)}'
    rows = []
    for markup in sorted(report['markups'], key=lambda m: (m['priority'] != 'safety', m['id'])):
        detail = []
        for check in markup['checks']:
            detail.append(f'<tr><td data-label="Requested check">{esc(describe_key(check["key"]))}<br>Wanted: {esc(display(check["before"],check["key"]))} → '
                          f'{esc(display(check["after"],check["key"]))}<br><strong>{esc(LABELS[check["status"]])}</strong></td>'
                          f'<td data-label="Original reading">{reading(check["original"],check["key"])}</td><td data-label="Returned reading">{reading(check["returned"],check["key"])}</td></tr>')
        rows.append(f'<section><h2>{esc(markup["id"])} — {esc(LABELS[markup["status"]])}</h2>'
                    f'<p><strong>{esc(markup["priority"])} priority · review required</strong></p>'
                    f'<p>{esc(markup["text"])}</p><p>{locators(markup["evidence"])}</p>'
                    f'<p>{esc(markup.get("reason", ""))}</p>'
                    '<table><tr><th>Requested check</th><th>Original reading</th><th>Returned reading</th></tr>'
                    + ''.join(detail) + '</table></section>')
    other = ''.join(f'<tr><td data-label="Fact">{esc(describe_key(r["key"]))}</td><td data-label="Original reading">{reading(r["original"],r["key"])}</td>'
                    f'<td data-label="Returned reading">{reading(r["returned"],r["key"])}</td></tr>' for r in report['other_observed_changes'])
    sources = ' · '.join(f'<a href="{esc(path)}">{esc(identity)}</a>' for identity, (path, raw) in copies.items())
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>P&amp;ID markup return review</title><style>*{box-sizing:border-box}body{font:16px system-ui;max-width:1200px;margin:2em auto;'
            'padding:0 1em;color:#172c3b;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;table-layout:fixed}'
            'td,th{border:1px solid #bdcbd3;padding:.7em;text-align:left;vertical-align:top;overflow-wrap:anywhere}'
            'section{margin:2em 0}a{color:#075c92}h1,h2{line-height:1.25}@media(max-width:650px){'
            'h1{font-size:26px}table,tr,td{display:block;width:100%}tr:has(th){display:none}'
            'td{padding:.6em;font-size:15px}td:before{content:attr(data-label);display:block;font-weight:bold;margin-bottom:.4em}'
            'tr{margin-bottom:1em}}'
            '</style><h1>P&amp;ID markup return review</h1><p><strong>Draft review packet — no drawing release.</strong></p>'
            f'<p>{esc(report["basis"])}</p><p>{esc(report["inventory_basis"])}</p><p>Sources: {sources}</p>'
            f'<p>Markup outcomes: {esc(" · ".join(str(count)+" "+LABELS[status].lower() for status,count in report["counts"].items()))}. '
            'All rows require review, including supported safety items.</p>'
            + ''.join(rows) + '<h2>Other observed changes</h2><table><tr><th>Fact</th><th>Original</th><th>Returned</th></tr>'
            + other + '</table><p>Other supplied facts with incomplete/conflicting coverage: '
            + str(len(report['other_fact_coverage_gaps'])) + ' (full evidence in result.json).</p><p>'
            + esc(report['boundary']) + '</p></html>')


def run(manifest_path, out):
    out = Path(out)
    require(not out.exists(), 'Output exists; retain the earlier packet')
    manifest, requests, readings, index, desired, copies, captured, request_raw, reading_raw = prepare(manifest_path)
    report = compare(requests, index, desired)
    report['documents'] = [dict(doc, path=copies[doc['id']][0]) for doc in manifest['documents']]
    report['reading_method'] = readings['method']
    report['input_sha256'] = {k: v['sha256'] for k, v in manifest.items() if k in ('requests', 'readings')}
    report['tool_sha256_lf'] = digest(Path(__file__).read_bytes().replace(b'\r\n', b'\n'))
    with tempfile.TemporaryDirectory(prefix='pid-markup-review-') as temporary:
        root = Path(temporary); (root / 'sources').mkdir()
        for path, raw in copies.values():
            (root / path).write_bytes(raw)
        (root / 'input-manifest.json').write_bytes(captured[Path(manifest_path).resolve()])
        portable = copy.deepcopy(manifest)
        for doc in portable['documents']:
            doc['path'] = copies[doc['id']][0]
        for name in ('requests', 'readings'):
            portable[name]['path'] = name + '.json'
        (root / 'manifest.json').write_text(json.dumps(portable, indent=2, ensure_ascii=False)+'\n', encoding='utf-8', newline='\n')
        (root / 'requests.json').write_bytes(request_raw); (root / 'readings.json').write_bytes(reading_raw)
        (root / 'result.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
        (root / 'REPORT.html').write_text(render(report, copies), encoding='utf-8', newline='\n')
        md = ['# P&ID markup return review', '', report['basis'], '', report['inventory_basis'], '',
              '| Markup | Priority | Outcome | Request |', '|---|---|---|---|']
        for row in report['markups']:
            # JSON quoting retains complete multiline/pipe text without creating extra Markdown rows.
            label = json.dumps(row['text'], ensure_ascii=False).replace('|', '&#124;').replace('<', '&lt;')
            md.append(f'| {row["id"].replace("|", "&#124;")} | {row["priority"]} | {row["status"]} | {label} |')
        md += ['', f'Other observed changes: {len(report["other_observed_changes"])}. '
               f'Other coverage gaps: {len(report["other_fact_coverage_gaps"])}.', '',
               'Open REPORT.html for both source readings/locators on every check. result.json retains every observation.', '', report['boundary']]
        (root / 'REPORT.md').write_text('\n'.join(md) + '\n', encoding='utf-8', newline='\n')
        with (root / 'review_queue.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream); writer.writerow(('review_item_id', 'priority', 'status', 'check_statuses', 'review_required', 'request'))
            for row in sorted(report['markups'], key=lambda r: (r['priority'] != 'safety', r['id'])):
                safe = lambda s: "'" + s if s.startswith(('=', '+', '-', '@')) else s
                writer.writerow((safe(row['id']), row['priority'], row['status'],
                                 ';'.join(c['status'] for c in row['checks']), 'yes', safe(row['text'])))
            for prefix, priority, status, items in (
                    ('OTHER', 'needs_assessment', 'other_observed_change', report['other_observed_changes']),
                    ('COVERAGE', 'normal', 'not_verifiable', report['other_fact_coverage_gaps'])):
                for number, row in enumerate(items, 1):
                    writer.writerow((f'{prefix}-{number:03d}', priority, status, '', 'yes', safe(describe_key(row['key']))))
        receipt = dict(schema='pid-markup-receipt-1', tool_sha256_lf=report['tool_sha256_lf'],
                       input_manifest_sha256=digest(captured[Path(manifest_path).resolve()]),
                       files={p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()})
        (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
        require(all(path.read_bytes() == raw for path, raw in captured.items()), 'Input changed before publication')
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(root, out)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run(args.manifest, args.out)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('REFUSED: ' + str(error), file=sys.stderr); return 2
    print('Draft comparison written: ' + typed(report['counts']) + '; other observed changes: '
          + str(len(report['other_observed_changes'])) + '. No drawing release/acceptance. Open REPORT.html.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
