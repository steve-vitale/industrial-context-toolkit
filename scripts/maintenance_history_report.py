"""Readable offline views of a maintenance-history packet; no source decisions."""
from collections import Counter, defaultdict
import csv
import html
from pathlib import Path


def esc(value):
    return html.escape(str(value), quote=True)


def md(value):
    return esc(value).replace('|', '&#124;').replace('[', '&#91;').replace(']', '&#93;').replace('\n', '<br>')


def view_member(origin):
    return 'evidence/' + origin['member'].removeprefix('originals/').replace('/', '-').rsplit('.', 1)[0] + '.html'


def evidence(origin, prefix=''):
    return f"<a href='{prefix}{view_member(origin)}#r{origin['record']}'>{esc(origin['document'])} rev {esc(origin['revision'])}, {esc(origin['locator'])}</a>"


def hours(value):
    return (esc(value['value']) + ' booked h from ' + str(value['rows']) + ' signed ledger entries') if value['state'] == 'known' else esc(value['state'].replace('_', ' '))


def date_text(value):
    if not value:
        return 'not mapped'
    return esc((value['value'] or value['raw'] or 'not supplied') + ' [' + value['state'] + '; ' + value['time_basis'] + ']')


def page(title, body):
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>""" + esc(title) + """</title><style>
body{font:16px/1.5 system-ui,sans-serif;color:#18202a;background:#fafafa;max-width:76rem;margin:2rem auto;padding:0 1rem;overflow-wrap:anywhere}
h1{font-size:1.9rem;line-height:1.2}h2{font-size:1.35rem}a{color:#095b91}main>section,article{background:white;border:1px solid #c5ced8;border-radius:.35rem;padding:1rem;margin:1rem 0}
table{border-collapse:collapse;width:100%;text-align:left;margin:.7rem 0}th,td{vertical-align:top;border-bottom:1px solid #dbe0e5;padding:.5rem}th{background:#edf1f5}details{margin:.6rem 0}summary{cursor:pointer;font-weight:600}dt{font-weight:600}dd{margin:0 0 .6rem 0}input{font:inherit;padding:.45rem;max-width:95%}.note{color:#425466}.scroll{overflow-x:auto}code{white-space:pre-wrap}
@media(max-width:700px){body{margin:1rem auto}h1{font-size:1.5rem}th,td{padding:.35rem}.scroll table{min-width:38rem}}@media print{details>*{display:block}input{display:none}article{break-inside:avoid}}
</style></head><body><main>""" + body + '</main></body></html>\n'


def record_fields(row):
    return '<dl>' + ''.join(f'<dt>{esc(k)}</dt><dd>{esc(v) if v != "" else "Not supplied"}</dd>'
                            for k, v in row.items() if not k.startswith('_') and k != 'origin') + '</dl>'


def rows_table(rows, prefix, kind):
    if not rows:
        return '<p>No associated ' + esc(kind) + ' rows in the supplied export. This does not establish no activity.</p>'
    fields = {'transactions': ('id', 'date', 'type', 'status', 'entity', 'work_order_id'),
              'details': ('id', 'part_id', 'description', 'quantity', 'unit', 'transaction_id'),
              'labor': ('id', 'date', 'trade', 'hours', 'correction', 'cost')}[kind]
    return '<div class="scroll"><table><thead><tr>' + ''.join('<th>' + esc(f) + '</th>' for f in fields) + '<th>Evidence / meanings</th></tr></thead><tbody>' + ''.join(
        '<tr>' + ''.join('<td>' + esc(row.get(f, '')) + '</td>' for f in fields) + '<td>' + evidence(row['origin'], prefix) +
        '<br>' + esc('; '.join(f'{f}: {meaning}' for f, meaning in row['_labels'].items())) +
        '<br>' + esc('; '.join(f'{f}: {meaning}' for f, meaning in row['_flags'].items())) + '</td></tr>' for row in rows) + '</tbody></table></div>'


def render(root, profile, result, history):
    (root / 'assets').mkdir(); (root / 'evidence').mkdir()
    by_member = defaultdict(list)
    for rows in result['all_records'].values():
        for row in rows:
            by_member[row['origin']['member']].append(row)
    for member, rows in by_member.items():
        body = '<h1>Source record evidence</h1><p><a href="../REPORT.html">Manager brief</a> · <a href="../' + member + '">Exact original file</a></p><p>Mapped fields and explicitly declared scope/entity constants are shown below. Original headers, ignored fields and exact bytes remain in the original file and portable profile.</p>'
        for row in rows:
            origin = row['origin']
            body += f'<article id="r{origin["record"]}"><h2>{esc(origin["locator"])}</h2><p>{esc(origin["document"])} rev {esc(origin["revision"])}; SHA256 <code>{origin["sha256"]}</code></p>' + record_fields(row) + '</article>'
        (root / view_member(rows[0]['origin'])).write_text(page('Source record evidence', body), encoding='utf-8', newline='\n')

    index = []
    for dossier in result['assets']:
        asset = dossier['asset']; identity = ' / '.join(dossier['key'])
        body = '<p><a href="../REPORT.html">Manager brief and review actions</a> · <a href="../result.json">Complete evidence</a></p><h1>' + esc(identity) + '</h1><p>' + esc(asset.get('description', '')) + '</p><p>' + evidence(asset['origin'], '../') + '</p>'
        body += '<p>' + str(len(dossier['work_orders'])) + ' selected work orders; ' + hours(dossier['booked_hours']) + '.</p><p class="note">' + esc(result['boundary']) + '</p>'
        body += '<details><summary>Asset fields supplied</summary>' + record_fields(asset) + '</details>'
        if dossier['recurring_work']:
            body += '<section><h2>Recurring-work review candidates</h2>'
            for group in dossier['recurring_work']:
                body += '<p><strong>' + str(group['selected_order_count']) + ' orders:</strong> ' + esc(', '.join(group['orders'])) + '. ' + esc('; '.join(k + '=' + v for k, v in group['fields'].items())) + (' (derived from description by the declared vocabulary: ' + esc(', '.join(group['derived_fields'])) + ')' if group.get('derived_fields') else '') + '</p><p>' + esc(group['action']) + '</p>'
            body += '</section>'
        if dossier['unclassified_orders']:
            body += '<p>Grouping fields unavailable for: ' + esc(', '.join(dossier['unclassified_orders'])) + '. These orders remain in the chronology.</p>'
        body += '<h2>Selected-record chronology</h2><p>Sorted by the declared creation-date format, with unresolved dates last. Within-day order is unknown where the source supplies dates only. Other event dates and their raw values remain attached to each record.</p>'
        for order in dossier['work_orders']:
            row = order['record']; date = row['_dates']['created']
            body += '<article><h2>' + esc(row['id']) + ': ' + esc(date['value'] or date['raw'] or 'Creation date unavailable') + '</h2><p>' + esc(row.get('description', '')) + '</p><p>' + evidence(row['origin'], '../') + '</p><p>Created: ' + date_text(date) + '<br>Completed: ' + date_text(row['_dates'].get('completed')) + '<br>Parent: ' + esc(row.get('parent_id') or 'not supplied') + '.</p>'
            for field, d in row.get('_derived', {}).items():
                body += '<p>' + esc(field + '=' + d['value']) + ' is derived from ' + esc(d['source']) + ' term ' + esc(repr(d['term'])) + ' by declared rule ' + str(d['rule']) + ' of the profile vocabulary, not a source code.</p>'
            body += '<p>Code meanings: ' + esc('; '.join(k + '=' + v for k, v in row['_labels'].items()) or 'No code labels supplied') + '. Flags: ' + esc('; '.join(k + '=' + v for k, v in row['_flags'].items()) or 'not supplied') + '.</p>'
            body += '<p>Labor: ' + hours(order['booked_hours']) + '.</p>'
            for kind in ('transactions', 'details', 'labor'):
                supplied = kind in result['sources']
                body += '<details><summary>' + esc(kind.title()) + ': ' + str(len(order[kind])) + ' associated rows' + ('' if supplied else ' (export not supplied)') + '</summary>'
                body += rows_table(order[kind], '../', kind) + '</details>'
            body += '</article>'
        (root / dossier['page']).write_text(page(identity, body), encoding='utf-8', newline='\n')
        index.append((len(dossier['work_orders']), identity, dossier))

    total_groups = sum(len(d['recurring_work']) for d in result['assets'])
    body = '<h1>Maintenance history review</h1><p><strong>' + esc(profile['question']) + '</strong></p><p>Namespace: ' + esc(profile['namespace']) + '; cutoff: ' + esc(profile['as_of']) + '.</p><p>' + str(len(result['assets'])) + ' supplied assets; ' + str(result['counts']['work_orders']) + ' selected work orders; ' + str(total_groups) + ' recurring-work review groups; ' + str(len(result['issues'])) + ' review issues. Authorized decision: <strong>pending</strong>.</p><p class="note">' + esc(result['boundary']) + '</p>'
    body += '<p><a href="REPORT.md">Text brief</a> · <a href="actions.csv">Proposed actions</a> · <a href="result.json">Complete evidence</a> · <a href="job.json">Portable profile</a></p>'
    lines = ['# Maintenance history review', '', profile['question'], '', f"Namespace: {md(profile['namespace'])}; cutoff: {profile['as_of']}.", '', f"{len(result['assets'])} supplied assets; {result['counts']['work_orders']} selected work orders; {total_groups} recurring-work review groups; {len(result['issues'])} review issues.", '', result['boundary'], '', 'Authorized decision: pending. Suggested roles need named owners and source readback.', '']
    body += '<section><h2>What needs review</h2><p>Actions below are proposals, with owners and dispositions pending. Grouped code issues retain every affected source locator.</p>'
    lines += ['## Review actions', '']
    for code, count in sorted(Counter(x['code'] for x in result['issues']).items()):
        body += '<p>' + esc(code.replace('_', ' ')) + ': ' + str(count) + ' issue(s).</p>'
    for issue in result['issues']:
        refs = issue['evidence']
        body += '<details><summary>' + esc(issue['code'].replace('_', ' ')) + ': ' + esc(issue['table'] + ' / ' + issue['field']) + ' (' + str(len(refs)) + ' source rows)</summary><p>' + esc(issue['action']) + '</p><p>Suggested role: ' + esc(issue['suggested_role']) + '; assigned person: needs owner; disposition: pending.</p><ul>' + ''.join('<li>' + evidence(o) + '</li>' for o in refs) + '</ul></details>'
        lines += [f"- {md(issue['code'])}: {md(issue['action'])} Suggested role: {md(issue['suggested_role'])}. " + '; '.join(f"[{md(o['document'])}, {md(o['locator'])}]({view_member(o)}#r{o['record']})" for o in refs)]
    body += '</section>'
    if history:
        body += '<section><h2>Changes since the previous packet</h2><p>' + esc(history['meaning']) + '</p><p>' + str(len(history['records'])) + ' added, changed or omitted records; ' + str(len(history['basis_changes'])) + ' comparison-basis changes.</p><ul>' + ''.join('<li>' + esc(x) + '</li>' for x in history['basis_changes']) + '</ul><p><a href="revision.json">Exact before/after records and earlier issues</a> · <a href="previous/REPORT.html">Previous packet</a></p></section>'
        lines += ['', '## Changes since the previous packet', '', history['meaning'], '', f"{len(history['records'])} added, changed or omitted records; {len(history['basis_changes'])} basis changes. Inspect [revision evidence](revision.json) and [previous packet](previous/REPORT.html)."]
    body += '<section><h2>Asset dossiers</h2><p>Sorted by selected work-order count. This is not an asset-criticality ranking.</p><label>Find an asset <input id="filter" type="search" placeholder="ID, scope or description"></label><div class="scroll"><table><thead><tr><th>Scoped asset</th><th>Description / source type</th><th>Selected orders</th><th>Recorded labor</th><th>Recurring groups</th></tr></thead><tbody id="assets">'
    lines += ['', '## Asset dossiers', '', '| Scoped asset | Selected orders | Booked hours | Recurring groups |', '|---|---:|---|---:|']
    for count, identity, d in sorted(index, key=lambda x: (-x[0], x[1])):
        body += '<tr><td><a href="' + d['page'] + '">' + esc(identity) + '</a></td><td>' + esc(d['asset'].get('description', '')) + '<br>' + esc(d['asset'].get('kind', '')) + ' ' + esc(d['asset'].get('type', '')) + '</td><td>' + str(count) + '</td><td>' + hours(d['booked_hours']) + '</td><td>' + str(len(d['recurring_work'])) + '</td></tr>'
        lines.append('| [' + md(identity) + '](' + d['page'] + ') | ' + str(count) + ' | ' + (d['booked_hours']['value'] if d['booked_hours']['state'] == 'known' else d['booked_hours']['state']) + ' | ' + str(len(d['recurring_work'])) + ' |')
    body += '</tbody></table></div></section><section><h2>Unlinked records and source coverage</h2>'
    lines += ['', '## Source coverage and unlinked records', '']
    for kind, coverage in result['relationship_coverage'].items():
        supplied = kind in result['sources']
        body += '<p>' + esc(kind) + ': ' + (str(coverage['supplied']) + ' supplied, ' + str(coverage['linked']) + ' associated, ' + str(coverage['unlinked']) + ' unlinked.' if supplied else 'Export not supplied.') + '</p>'
        for row in result['unlinked'][kind]:
            body += '<p>' + esc(' / '.join(row['record'])) + ': ' + esc(row['reason']) + ' ' + evidence(row['evidence']) + '</p>'
    for kind, spec in result['sources'].items():
        line = kind + ': ' + spec['id'] + ' rev ' + spec['revision'] + '; owner role ' + spec['owner'] + '; coverage: ' + spec['coverage']
        body += '<p>' + esc(line) + '</p>'; lines.append('- ' + md(line))
    body += '</section><script>document.getElementById("filter").addEventListener("input",function(){const q=this.value.toLowerCase();document.querySelectorAll("#assets tr").forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q));});</script>'
    (root / 'REPORT.html').write_text(page('Maintenance history review', body), encoding='utf-8', newline='\n')
    (root / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    with (root / 'actions.csv').open('w', encoding='utf-8', newline='') as stream:
        fields = ['issue', 'table', 'field', 'action', 'suggested_role', 'assigned_person', 'disposition', 'evidence']
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n'); writer.writeheader()
        for issue in result['issues']:
            row = {k: issue[k] for k in fields if k in issue}
            row.update(issue=issue['id'], evidence='; '.join(view_member(o) + '#r' + str(o['record']) for o in issue['evidence']))
            writer.writerow({k: "'" + str(v) if str(v).startswith(('=', '+', '-', '@')) else v for k, v in row.items()})
