"""Build a source-linked maintenance-history review from explicitly mapped exports.

Standard library only. Company decisions, failure diagnosis and installed state
are not inferred. See docs/MAINTENANCE_HISTORY.md for the input contract.
"""
import argparse
from collections import Counter, defaultdict
import csv
import datetime as dt
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import maintenance_intake as intake

SCHEMA = 'maintenance-history-1'
FIELDS = {
    'assets': {'id', 'scope', 'description', 'kind', 'type', 'manufacturer', 'model', 'serial'},
    'work_orders': {'id', 'scope', 'asset_id', 'description', 'work_class', 'order_type', 'job_type',
                    'created', 'completed', 'reopened', 'parent_id', 'status'},
    'transactions': {'id', 'scope', 'work_order_id', 'entity', 'status', 'type', 'date', 'from_id'},
    'details': {'id', 'scope', 'transaction_id', 'work_order_id', 'part_id', 'catalog_part_id',
               'description', 'unit', 'quantity', 'price', 'date', 'type'},
    'labor': {'id', 'scope', 'work_order_id', 'date', 'hours', 'rate', 'cost', 'correction', 'trade'},
}
REQUIRED = {
    'assets': {'id', 'scope'}, 'work_orders': {'id', 'scope', 'asset_id', 'created'},
    'transactions': {'id', 'scope', 'work_order_id', 'entity'},
    'details': {'id', 'scope', 'transaction_id'}, 'labor': {'id', 'scope', 'work_order_id'},
}
DATE_FIELDS = {'created', 'completed', 'date'}
NUMBER_FIELDS = {'hours', 'rate', 'cost', 'quantity', 'price'}
DATE_FORMATS = {'iso_date', 'iso_datetime', 'iso_utc', 'dmy_date', 'mdy_date', 'english_datetime'}
MAX_BYTES, MAX_ROWS = 64_000_000, 200_000
dump, sha, inventory = intake.dump, intake.sha, intake.inventory


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def key(row, field='id'):
    return row['scope'], row.get(field, '')


def strict_json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, 'Duplicate JSON object key: ' + k)
            result[k] = v
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_int=str, parse_float=str,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON value: ' + value)))


def text(value):
    require(value is None or isinstance(value, str), 'Mapped cells must be scalar text/numbers or null; boolean/nested meanings need explicit preparation')
    return value if value is not None else ''


def profile_check(p):
    require(isinstance(p, dict) and p.get('schema') == SCHEMA, 'Expected schema ' + SCHEMA)
    for field in ('namespace', 'question', 'as_of'):
        require(isinstance(p.get(field), str) and p[field].strip(), 'Supply profile ' + field)
    require(re.fullmatch(r'\d{4}-\d{2}-\d{2}', p['as_of']) is not None, 'as_of must be ISO date')
    dt.date.fromisoformat(p['as_of'])
    sources = p.get('sources')
    require(isinstance(sources, dict) and {'assets', 'work_orders'} <= set(sources) <= set(FIELDS), 'Supply assets/work_orders and only supported source tables')
    require('details' not in sources or 'transactions' in sources, 'Details require a supplied transactions table')
    grouping = p.get('recurring_fields', ['work_class', 'order_type', 'job_type'])
    require(isinstance(grouping, list) and grouping and len(set(grouping)) == len(grouping) and
            set(grouping) <= {'work_class', 'order_type', 'job_type'}, 'Declare unique recurring_fields from class/order_type/job_type')
    ids = []
    for kind, spec in sources.items():
        require(isinstance(spec, dict), kind + ': expected source specification')
        for field in ('id', 'revision', 'owner', 'coverage'):
            require(isinstance(spec.get(field), str) and spec[field].strip(), kind + ': supply ' + field)
        ids.append(spec['id'])
        mapping, constants = spec.get('columns'), spec.get('constants', {})
        require(isinstance(mapping, dict) and mapping and all(isinstance(k, str) and k and isinstance(v, str) for k, v in mapping.items()), kind + ': explicit source-to-canonical columns required')
        require(len(set(mapping.values())) == len(mapping) and set(mapping.values()) <= FIELDS[kind], kind + ': duplicate/unsupported mapped fields')
        require(isinstance(constants, dict) and set(constants) <= {'scope', 'entity'} and not (set(constants) & set(mapping.values())) and all(isinstance(v, str) and v for v in constants.values()), kind + ': constants may explicitly declare scope/entity only')
        identity = spec.get('identity')
        require(identity in (None, 'record'), kind + ': identity may only be "record" (the source record number)')
        if identity == 'record':
            require('id' not in mapping.values() and isinstance(spec.get('files'), list) and len(spec['files']) == 1,
                    kind + ': record identity needs exactly one file and no mapped id column')
        require(REQUIRED[kind] <= set(mapping.values()) | set(constants) | ({'id'} if identity == 'record' else set()),
                kind + ': missing required mappings ' + str(sorted(REQUIRED[kind])))
        select = spec.get('select')
        if select is not None:
            require(kind == 'work_orders' and isinstance(select, dict) and len(select) == 1, kind + ': select one work-order field')
            (field, values), = select.items()
            require(field in set(mapping.values()) - {'id'} and isinstance(values, list) and values and
                    all(isinstance(v, str) and v for v in values) and len(set(values)) == len(values),
                    kind + ': select names one mapped field and a list of distinct exact nonempty values')
        derive = spec.get('derive')
        if derive is not None:
            require(kind == 'work_orders' and isinstance(derive, dict) and derive and set(derive) <= {'work_class', 'order_type', 'job_type'},
                    kind + ': derive work_class, order_type or job_type on work orders only')
            for target, rule_set in derive.items():
                require(target not in mapping.values() and isinstance(rule_set, dict) and set(rule_set) == {'source', 'rules', 'basis'} and
                        rule_set['source'] in set(mapping.values()) - {'id'} and isinstance(rule_set['basis'], str) and rule_set['basis'].strip(),
                        kind + ': derive ' + target + ' needs an unmapped target, a mapped source field, rules and a basis')
                rules = rule_set['rules']
                require(isinstance(rules, list) and rules and all(
                    isinstance(r, dict) and set(r) == {'value', 'terms'} and isinstance(r['value'], str) and r['value'].strip() and
                    isinstance(r['terms'], list) and r['terms'] and all(isinstance(t, str) and words(t) for t in r['terms']) for r in rules),
                    kind + ': derive rules need a value and nonempty word terms')
        ignored = spec.get('ignored_columns', [])
        require(isinstance(ignored, list) and all(isinstance(x, str) for x in ignored) and len(set(ignored)) == len(ignored) and not set(ignored) & set(mapping), kind + ': invalid ignored_columns')
        require(spec.get('format', 'csv') in ('csv', 'json'), kind + ': supported formats are csv/json records')
        require(spec.get('encoding', 'utf-8-sig') in ('utf-8', 'utf-8-sig', 'cp1252'), kind + ': unsupported encoding')
        require(spec.get('delimiter', ',') in (',', ';', '\t', '|'), kind + ': unsupported delimiter')
        require(isinstance(spec.get('files'), list) and spec['files'], kind + ': supply files')
        for f in spec['files']:
            require(isinstance(f, dict) and isinstance(f.get('path'), str) and f['path'], kind + ': each file needs a path')
            require('sha256' not in f or re.fullmatch('[0-9a-f]{64}', f['sha256']) is not None, kind + ': invalid expected SHA256')
        dates = set(mapping.values()) & DATE_FIELDS
        require(set(spec.get('date_formats', {})) == dates and all(x in DATE_FORMATS for x in spec.get('date_formats', {}).values()), kind + ': explicitly declare a supported format for every mapped date')
        require(not dates or isinstance(spec.get('time_basis'), str) and spec['time_basis'].strip(), kind + ': supply time_basis, including any unknown timezone')
        for field, flags in spec.get('flags', {}).items():
            require(field in set(mapping.values()) & {'reopened', 'correction'} and isinstance(flags, dict) and set(flags) == {'true', 'false'}, kind + ': invalid flag field/mapping')
            a, b = flags['true'], flags['false']
            require(isinstance(a, list) and isinstance(b, list) and all(isinstance(x, str) and x for x in a + b) and len(set(a + b)) == len(a + b), kind + ': flags must use disjoint exact nonempty codes')
        for field, labels in spec.get('labels', {}).items():
            require(field in mapping.values() and isinstance(labels, dict) and all(isinstance(k, str) and k and isinstance(v, str) and v for k, v in labels.items()), kind + ': invalid declared labels')
    require(len(ids) == len(set(ids)), 'Source document IDs must be distinct')
    if 'transactions' in sources:
        entities = sources['transactions'].get('work_order_entities')
        require(isinstance(entities, list) and entities and all(isinstance(e, str) and e for e in entities), 'Transactions need explicit work_order_entities')
    policy = p.get('labor_ledger')
    if policy is not None:
        require('labor' in sources and policy.get('mode') == 'signed_all_entries' and policy.get('unit') == 'h' and
                isinstance(policy.get('basis'), str) and policy['basis'].strip() and 'hours' in sources['labor']['columns'].values(), 'Hours aggregation needs signed_all_entries, unit h, mapped hours and a source basis')


def words(value):
    """Upper-case words of letters and digits; every other character separates words."""
    return ' '.join(re.findall('[A-Z0-9]+', value.upper()))


def derived(text_value, rules):
    """First declared rule with a whole-word term in the text: (rule number, term), or None."""
    padded = ' ' + words(text_value) + ' '
    for number, rule in enumerate(rules, 1):
        for term in rule['terms']:
            if ' ' + words(term) + ' ' in padded:
                return number, term
    return None


def parse_date(value, fmt):
    if fmt == 'iso_date':
        require(re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'not ISO date')
        return dt.date.fromisoformat(value).isoformat()
    if fmt in ('iso_datetime', 'iso_utc'):
        require(re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?', value), 'not ISO timestamp')
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        require((parsed.tzinfo is not None) == (fmt == 'iso_utc'), 'timestamp timezone differs from declared format')
        return (parsed.astimezone(dt.timezone.utc) if fmt == 'iso_utc' else parsed).isoformat()
    if fmt in ('dmy_date', 'mdy_date'):
        require(re.fullmatch(r'\d{2}/\d{2}/\d{4}', value), 'not declared numeric date')
        a, b, year = map(int, value.split('/'))
        return dt.date(year, b if fmt == 'dmy_date' else a, a if fmt == 'dmy_date' else b).isoformat()
    match = re.fullmatch(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s+(\d{4})\s+(\d{1,2}):(\d{2})(AM|PM)', value)
    require(match is not None, 'not declared English AM/PM timestamp')
    month, day, year, hour, minute, ampm = match.groups()
    require(1 <= int(hour) <= 12, 'invalid AM/PM hour')
    return dt.datetime(int(year), 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split().index(month) + 1,
                       int(day), int(hour) % 12 + (12 if ampm == 'PM' else 0), int(minute)).isoformat()


def number(value):
    require(re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)', value) is not None, 'not an ungrouped decimal')
    try:
        result = Decimal(value)
    except InvalidOperation:
        raise ValueError('not a decimal') from None
    require(result.is_finite(), 'nonfinite decimal')
    return result


def decimal_text(value):
    s = format(value, 'f')
    return s.rstrip('0').rstrip('.') if '.' in s else s


def prepare(profile_path):
    profile_path = Path(profile_path).resolve()
    captured = {profile_path: profile_path.read_bytes()}
    p = json.loads(captured[profile_path].decode('utf-8-sig'))
    profile_check(p)
    tables, originals, total, selection = {}, {}, 0, {}
    for kind, spec in p['sources'].items():
        rows, seen, excluded = [], set(), 0
        for nth, f in enumerate(spec['files'], 1):
            path = (profile_path.parent / f['path']).resolve()
            require(path not in captured, 'Each supplied file must have one explicit source role: ' + str(path))
            raw = path.read_bytes(); captured[path] = raw; total += len(raw)
            require(total <= MAX_BYTES, 'Input exceeds 64 MB source budget')
            h = hashlib.sha256(raw).hexdigest()
            require('sha256' not in f or f['sha256'] == h, 'Pinned source bytes differ: ' + kind)
            fmt = spec.get('format', 'csv')
            member = f'originals/{kind}/{nth:03d}.' + ('json' if fmt == 'json' else 'csv')
            originals[member] = raw
            source_text = raw.decode(spec.get('encoding', 'utf-8-sig'))
            if fmt == 'csv':
                reader = csv.reader(io.StringIO(source_text, newline=''), delimiter=spec.get('delimiter', ','), strict=True)
                headers = next(reader, [])
                require(headers and all(headers) and len(set(headers)) == len(headers), kind + ': blank/duplicate CSV header')
                require(set(headers) == set(spec['columns']) | set(spec.get('ignored_columns', [])), kind + ': headers differ from explicit columns/ignored_columns')
                incoming = []
                for ordinal, cells in enumerate(reader, 2):
                    require(len(cells) == len(headers), kind + ': ragged CSV record ' + str(ordinal))
                    incoming.append((dict(zip(headers, cells)), ordinal, reader.line_num))
            else:
                records = strict_json(source_text)
                require(isinstance(records, list) and all(isinstance(r, dict) for r in records), kind + ': expected JSON array of objects')
                require(all(set(r) <= set(spec['columns']) | set(spec.get('ignored_columns', [])) for r in records), kind + ': unmapped/unignored JSON columns')
                incoming = [(r, n, None) for n, r in enumerate(records, 1)]
            for rawrow, ordinal, end_line in incoming:
                r = {target: text(rawrow.get(source)) for source, target in spec['columns'].items()}
                r.update(spec.get('constants', {}))
                if spec.get('identity') == 'record':
                    r['id'] = str(ordinal)
                if spec.get('select'):
                    (field, values), = spec['select'].items()
                    if r.get(field) not in values:
                        excluded += 1
                        continue
                for field in ('id', 'scope'):
                    require(r.get(field) and r[field] == r[field].strip(), kind + ': blank/noncanonical primary identity at record ' + str(ordinal))
                require(key(r) not in seen, kind + ': duplicate scoped primary identity ' + canonical(key(r)))
                seen.add(key(r))
                r['origin'] = dict(table=kind, document=spec['id'], revision=spec['revision'], member=member,
                                   record=ordinal, end_line=end_line, sha256=h,
                                   locator=('CSV record ' + str(ordinal) + ', ends at physical line ' + str(end_line)) if end_line else 'JSON array record ' + str(ordinal))
                rows.append(r)
                require(len(rows) <= MAX_ROWS, kind + ': row ceiling exceeded')
        tables[kind] = rows
        if spec.get('select'):
            (field, values), = spec['select'].items()
            selection[kind] = dict(field=field, values=values, kept=len(rows), excluded=excluded)
    require(sum(map(len, tables.values())) <= MAX_ROWS, 'Combined row ceiling exceeded')
    return p, tables, originals, captured, selection


def analyze(p, tables, selection=None):
    issues = {}

    def issue(code, table, row, field, action, raw=None):
        # Unknown code meanings group once per source/value; other findings bind a record.
        identity = [code, table, field, raw if code in ('unknown_flag', 'unknown_code') else list(key(row))]
        identity = digest(identity)[:24]
        if identity not in issues:
            issues[identity] = dict(id=identity, code=code, table=table, field=field, raw_value=raw,
                                    action=action, suggested_role=p['sources'][table]['owner'],
                                    assigned_person='needs owner', disposition='pending', evidence=[])
        issues[identity]['evidence'].append(row['origin'])

    for table, rows in tables.items():
        spec = p['sources'][table]
        for row in rows:
            row['_dates'], row['_numbers'], row['_flags'], row['_labels'] = {}, {}, {}, {}
            if spec.get('derive'):
                row['_derived'] = {}
                for target, rule_set in spec['derive'].items():
                    found = derived(row.get(rule_set['source'], ''), rule_set['rules'])
                    if found:
                        row[target] = rule_set['rules'][found[0] - 1]['value']
                        row['_derived'][target] = dict(value=row[target], rule=found[0], term=found[1], source=rule_set['source'])
            for field, fmt in spec.get('date_formats', {}).items():
                raw = row.get(field, '')
                result = dict(state='missing', raw=raw, value=None, format=fmt, time_basis=spec['time_basis'])
                if raw:
                    try:
                        result.update(state='known', value=parse_date(raw, fmt))
                        if result['value'][:10] > p['as_of']:
                            result['state'] = 'after_cutoff'
                            issue('date_after_cutoff', table, row, field, 'Confirm the cutoff and this later recorded date; do not infer historical completion.', raw)
                    except (ValueError, OverflowError):
                        result['state'] = 'unparsed'
                        issue('unparsed_date', table, row, field, 'Confirm the source date and declared format; no locale or chronology is guessed.', raw)
                row['_dates'][field] = result
                if table == 'work_orders' and field == 'created' and not raw:
                    issue('missing_creation_date', table, row, field, 'Obtain the creation date; this record has no established place in the chronology.')
            for field in NUMBER_FIELDS & set(row):
                raw = row[field]
                row['_numbers'][field] = None
                if raw:
                    try:
                        row['_numbers'][field] = decimal_text(number(raw))
                    except ValueError:
                        issue('invalid_number', table, row, field, 'Obtain a numeric value and confirm its unit/ledger meaning; this subtotal remains unavailable.', raw)
                elif table == 'labor' and field == 'hours' and p.get('labor_ledger'):
                    issue('missing_hours', table, row, field, 'Obtain the missing booked hours; the associated subtotal remains unavailable, not zero.')
            for field in ('reopened', 'correction'):
                if field not in row:
                    continue
                values, raw = spec.get('flags', {}).get(field, {}), row[field]
                state = 'true' if raw in values.get('true', []) else 'false' if raw in values.get('false', []) else 'unknown'
                row['_flags'][field] = state
                if raw and state == 'unknown':
                    issue('unknown_flag', table, row, field, 'Obtain the exact source code definition; retain this flag as unknown.', raw)
            for field, labels in spec.get('labels', {}).items():
                raw = row.get(field, '')
                row['_labels'][field] = labels.get(raw, 'meaning not supplied')
                if raw and raw not in labels:
                    issue('unknown_code', table, row, field, 'Confirm this source code meaning before using it to classify work or transactions.', raw)
            if table == 'details' and row['_numbers'].get('quantity') is not None and number(row['_numbers']['quantity']) < 0:
                issue('negative_material_quantity', table, row, 'quantity', 'Review the signed movement and any return/correction; do not infer installed quantity or consumption.', row['quantity'])
            if table == 'work_orders' and 'completed' in spec['columns'].values() and not row.get('completed'):
                issue('missing_completion_value', table, row, 'completed', 'Check the current work-order record and disposition; missing completion does not prove open or overdue work.')

    indices = {kind: {key(r): r for r in rows} for kind, rows in tables.items()}
    assets, work = indices['assets'], indices['work_orders']
    wo_asset, trans_wo, detail_wo, labor_wo = {}, {}, {}, {}
    unlinked = {kind: [] for kind in ('work_orders', 'transactions', 'details', 'labor')}

    def unlink(table, row, reason):
        unlinked[table].append(dict(record=list(key(row)), reason=reason, evidence=row['origin']))
        issue('unlinked_' + table, table, row, 'relationship', reason + ' Confirm the exact scoped parent/source relationship.', None)

    for row in tables['work_orders']:
        if key(row, 'asset_id') in assets:
            wo_asset[key(row)] = key(row, 'asset_id')
        else:
            unlink('work_orders', row, 'Asset reference is missing or not uniquely present in supplied assets.')
        if row.get('parent_id') and key(row, 'parent_id') not in work:
            issue('unavailable_parent_order', 'work_orders', row, 'parent_id', 'Obtain the parent work order if needed; the selected cohort may omit it.', row['parent_id'])
    for row in tables.get('transactions', []):
        if row['entity'] not in p['sources']['transactions']['work_order_entities']:
            unlink('transactions', row, 'Transaction target entity is outside the declared work-order namespace.')
        elif key(row, 'work_order_id') not in work:
            unlink('transactions', row, 'Transaction work-order reference is unavailable.')
        else:
            trans_wo[key(row)] = key(row, 'work_order_id')
    for row in tables.get('details', []):
        target = trans_wo.get(key(row, 'transaction_id'))
        if target is None:
            unlink('details', row, 'Transaction is missing or has no qualified work-order association.')
        elif row.get('work_order_id') and key(row, 'work_order_id') != target:
            unlink('details', row, 'Detail work-order reference disagrees with its transaction target; row quarantined.')
        else:
            detail_wo[key(row)] = target
        if row.get('part_id') and row.get('catalog_part_id') and row['part_id'] != row['catalog_part_id']:
            issue('part_identity_conflict', 'details', row, 'part_id', 'Reconcile transaction part and supplied catalog identity before identifying this material.', row['part_id'])
    for row in tables.get('labor', []):
        if key(row, 'work_order_id') in work:
            labor_wo[key(row)] = key(row, 'work_order_id')
        else:
            unlink('labor', row, 'Labor work-order reference is unavailable.')

    children = {kind: defaultdict(list) for kind in ('transactions', 'details', 'labor')}
    for kind, links in (('transactions', trans_wo), ('details', detail_wo), ('labor', labor_wo)):
        for child, parent in links.items():
            children[kind][parent].append(indices[kind][child])

    def hours(rows):
        if not p.get('labor_ledger'):
            return dict(state='not_authorized', value=None, unit=None, rows=len(rows), basis='No explicit signed ledger policy supplied')
        if not rows:
            return dict(state='no_rows_supplied', value=None, unit='h', rows=0, basis=p['labor_ledger']['basis'])
        values = [r['_numbers'].get('hours') for r in rows]
        return dict(state='known' if all(v is not None for v in values) else 'unavailable',
                    value=decimal_text(sum((number(v) for v in values), Decimal(0))) if all(v is not None for v in values) else None,
                    unit='h', rows=len(rows), basis=p['labor_ledger']['basis'])

    dossiers, grouped_work = [], defaultdict(list)
    for row in tables['work_orders']:
        if key(row) in wo_asset:
            grouped_work[wo_asset[key(row)]].append(row)
    grouping = p.get('recurring_fields', ['work_class', 'order_type', 'job_type'])
    for asset_key, asset in sorted(assets.items()):
        orders, groups, asset_labor = [], defaultdict(list), []
        for row in sorted(grouped_work[asset_key], key=lambda r: (r['_dates']['created']['state'] != 'known', r['_dates']['created']['value'] or '', r['id'])):
            k = key(row)
            labor = children['labor'][k]; asset_labor.extend(labor)
            orders.append(dict(record=row, transactions=children['transactions'][k], details=children['details'][k],
                               labor=labor, booked_hours=hours(labor)))
            values = tuple(row.get(f, '') for f in grouping)
            if all(values):
                groups[values].append(row)
        derived_fields = [f for f in grouping if f in p['sources']['work_orders'].get('derive', {})]
        recurring = [dict(fields=dict(zip(grouping, values)), selected_order_count=len(rows),
                          orders=[r['id'] for r in rows], evidence=[r['origin'] for r in rows],
                          action='Review these distinct selected work orders and their descriptions/parent links; recurrence is not proof of repeat failure or independent repair.',
                          **(dict(derived_fields=derived_fields) if derived_fields else {}))
                     for values, rows in sorted(groups.items()) if len(rows) >= 2]
        dossiers.append(dict(key=list(asset_key), page='assets/' + digest([p['namespace'], list(asset_key)])[:24] + '.html',
                             asset=asset, work_orders=orders, recurring_work=recurring, booked_hours=hours(asset_labor),
                             unclassified_orders=[r['id'] for r in grouped_work[asset_key] if not all(r.get(f) for f in grouping)]))
    return dict(schema='maintenance-history-result-1', namespace=p['namespace'], question=p['question'], as_of=p['as_of'],
                **(dict(selection=selection) if selection else {}),
                sources={kind: {k: spec[k] for k in ('id', 'revision', 'owner', 'coverage')} for kind, spec in p['sources'].items()},
                counts={kind: len(rows) for kind, rows in tables.items()}, assets=dossiers,
                relationship_coverage={kind: dict(supplied=len(tables.get(kind, [])), linked=len(tables.get(kind, [])) - len(unlinked[kind]),
                                                 unlinked=len(unlinked[kind])) for kind in unlinked},
                unlinked=unlinked, issues=sorted(issues.values(), key=lambda r: (r['code'], r['id'])),
                all_records=tables, authorized_decision='pending', company_acceptance=False,
                boundary='Selected administrative records and supplied meanings. Recurring work is not proven failure. No associated rows proves only none were found in supplied exports. No installed parts, net consumption, root cause, MTBF or savings established.')


def method_pins():
    paths = [Path(__file__), Path(intake.__file__)]
    renderer = Path(__file__).with_name('maintenance_history_report.py')
    if renderer.exists():
        paths.append(renderer)
    return {p.name: hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in paths}


def verify_packet(root, depth=0):
    require(depth <= 20, 'Retained history exceeds 20 revisions; verify/archive earlier history separately')
    require(not Path(root).is_symlink() and not getattr(Path(root), 'is_junction', lambda: False)(), 'Previous packet root may not be a link/junction')
    root = Path(root).resolve()
    require(root.is_dir(), 'Previous packet must be a directory')
    require(not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in root.rglob('*')), 'Previous packet may not contain links/junctions')
    receipt = json.loads((root / 'receipt.json').read_bytes())
    require(receipt.get('schema') == 'maintenance-history-receipt-1' and receipt.get('files') == inventory(root), 'Previous packet inventory differs')
    job = json.loads((root / 'job.json').read_bytes())
    refs = [f['path'] for spec in job['sources'].values() for f in spec['files']]
    require(all((root / ref).resolve().is_relative_to(root) for ref in refs), 'Previous portable sources escape retained packet')
    p, rows, _, _, selection = prepare(root / 'job.json')
    old = json.loads((root / 'result.json').read_bytes())
    # Current code can only reproduce a prior result under the same method identity.
    reproduced = analyze(p, rows, selection) if receipt['methods_sha256_lf'] == method_pins() else None
    require(reproduced is None or reproduced == old, 'Previous substantive findings do not reproduce')
    if job.get('previous_packet'):
        previous = (root / job['previous_packet']).resolve()
        require(previous != root and previous.is_relative_to(root), 'Previous history escapes retained packet')
        prior_receipt, prior_result, prior_job = verify_packet(previous, depth + 1)
        require(receipt.get('previous_receipt_sha256') == sha(previous / 'receipt.json'), 'Previous history receipt binding differs')
        recorded = json.loads((root / 'revision.json').read_bytes())
        if reproduced is not None:
            require(recorded == revision(prior_result, old, p, prior_job, prior_receipt), 'Previous revision findings do not reproduce')
    else:
        require(receipt.get('previous_receipt_sha256') is None and not (root / 'revision.json').exists(), 'Unexpected previous history binding')
    return receipt, old, job


def revision(previous, result, p, job, receipt):
    old_records = {(kind, *key(r)): r for kind, rows in previous['all_records'].items() for r in rows}
    new_records = {(kind, *key(r)): r for kind, rows in result['all_records'].items() for r in rows}
    def values(row):
        return {k: v for k, v in row.items() if k != 'origin' and not k.startswith('_')}
    changes = []
    for k in sorted(set(old_records) | set(new_records)):
        a, b = old_records.get(k), new_records.get(k)
        state = 'added' if a is None else 'omitted' if b is None else 'changed' if values(a) != values(b) else None
        if state:
            changes.append(dict(table=k[0], identity=list(k[1:]), state=state, before=a, after=b,
                                meaning='Omission is not physical removal, closure or an accepted correction.' if state == 'omitted' else 'Source observation only; disposition remains pending.'))
    basis = ['namespace', 'recurring_fields', 'labor_ledger']
    basis_changes = [k for k in basis if job.get(k) != p.get(k)]
    for kind in sorted(set(job['sources']) | set(p['sources'])):
        a, b = job['sources'].get(kind), p['sources'].get(kind)
        if a is None or b is None:
            basis_changes.append(kind + ': source omitted/added')
        else:
            for field in ('id', 'owner', 'coverage', 'columns', 'constants', 'date_formats', 'time_basis', 'flags', 'labels', 'work_order_entities', 'encoding', 'delimiter', 'format', 'identity', 'select', 'derive'):
                if a.get(field) != b.get(field):
                    basis_changes.append(kind + ': ' + field)
    if receipt['methods_sha256_lf'] != method_pins():
        basis_changes.append('method changed; prior findings not recomputed under their original method')
    old_issues, new_issues = {r['id']: r for r in previous['issues']}, {r['id']: r for r in result['issues']}
    return dict(schema='maintenance-history-revision-1', basis_changes=basis_changes, as_of=dict(before=previous['as_of'], after=p['as_of']),
                records=changes, prior_issues=[dict(previous=row, current=new_issues.get(identity),
                state='still_detected' if identity in new_issues else 'no_longer_detected_needs_reconciliation') for identity, row in old_issues.items()],
                meaning='Changed or disappeared findings need source and receiving review. No prior disposition is inherited; changed basis and omissions remain explicit.')


def run(profile_path, out, previous=None):
    profile_path, out = Path(profile_path).resolve(), Path(out).resolve()
    require(not out.exists(), 'Output exists; choose a new directory')
    p, tables, originals, captured, selection = prepare(profile_path)
    if previous is None and p.get('previous_packet'):
        previous = profile_path.parent / p['previous_packet']
    previous = Path(previous).resolve() if previous else None
    require(all(out != path and out not in path.parents for path in captured), 'Output aliases or contains an input source')
    require(previous is None or previous != out and previous not in out.parents and out not in previous.parents, 'Previous/new packets must be separate')
    prior = verify_packet(previous, 1) if previous else None
    result = analyze(p, tables, selection)
    history = None
    if prior:
        receipt, old, job = prior
        for kind in set(job['sources']) & set(p['sources']):
            a, b = job['sources'][kind], p['sources'][kind]
            if (a['id'], a['revision']) == (b['id'], b['revision']):
                hashes = [hashlib.sha256(originals[f'originals/{kind}/{n:03d}.' + ('json' if b.get('format') == 'json' else 'csv')]).hexdigest() for n in range(1, len(b['files']) + 1)]
                require([f['sha256'] for f in a['files']] == hashes, kind + ': source bytes changed under unchanged document revision')
        history = revision(old, result, p, job, receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.maintenance-history-', dir=out.parent) as temporary:
        stage = Path(temporary) / 'packet'; stage.mkdir()
        for member, raw in originals.items():
            target = stage / member; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        (stage / 'input-profile.json').write_bytes(captured[profile_path])
        portable = json.loads(json.dumps(p))
        for kind, spec in portable['sources'].items():
            spec['files'] = [dict(path=member, sha256=hashlib.sha256(raw).hexdigest()) for member, raw in originals.items() if member.startswith('originals/' + kind + '/')]
        portable.pop('previous_packet', None)
        if previous:
            shutil.copytree(previous, stage / 'previous')
            portable['previous_packet'] = 'previous'
            dump(stage / 'revision.json', history)
        dump(stage / 'job.json', portable)
        dump(stage / 'result.json', result)
        from maintenance_history_report import render
        render(stage, p, result, history)
        require(all(path.read_bytes() == raw for path, raw in captured.items()), 'Source changed during processing; output refused')
        if previous:
            require(inventory(previous) == prior[0]['files'], 'Previous evidence changed during processing')
        dump(stage / 'receipt.json', dict(schema='maintenance-history-receipt-1', methods_sha256_lf=method_pins(),
                                         files=inventory(stage), previous_receipt_sha256=sha(previous / 'receipt.json') if previous else None,
                                         python=sys.version, company_acceptance=False))
        require(not out.exists(), 'Output appeared during processing; refusing replacement')
        stage.rename(out)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--check-packet', type=Path, help='verify retained inventory, source derivation and revision chain without writing')
    parser.add_argument('--previous', type=Path)
    a = parser.parse_args()
    try:
        if a.check_packet:
            require(not (a.profile or a.out or a.previous), 'Use --check-packet alone')
            receipt, _, _ = verify_packet(a.check_packet)
            print('Packet inventory and retained history verified; current-method findings ' + ('reproduced.' if receipt['methods_sha256_lf'] == method_pins() else 'NOT reproduced: method differs.'))
            return
        require(a.profile and a.out, 'Supply --profile and --out')
        result = run(a.profile, a.out, a.previous)
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as error:
        parser.exit(2, 'REFUSED: ' + str(error) + '\n')
    print(f"Draft history packet: {a.out / 'REPORT.html'}; {len(result['assets'])} scoped assets; {len(result['issues'])} review issues; authorized decision pending.")


if __name__ == '__main__':
    main()
