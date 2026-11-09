"""Author-run, fictional foundation transfer; actual CLIs and snapshot reads, no accounts."""
import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import foundation_handoff as handoff


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(handoff.raw(value))


def fixture(folder, commands, corrected=False, previous_history=None, layout='comma', scopes=('U1', 'U2')):
    spec = importlib.util.spec_from_file_location('history_fixtures', ROOT / 'examples/maintenance-history/fixtures.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    records = module.records()
    for rows in records.values():
        for row in rows:
            row['scope'] = dict(zip(('U1', 'U2'), scopes))[row['scope']]
    if corrected:
        records['work_orders'] = [r for r in records['work_orders'] if r['id'] != 'W3']
        records['labor'][0]['hours'] = '4'
    module.write(folder / 'history-input', layout, records, '2' if corrected else '1')
    history_args = ['scripts/maintenance_history.py', '--profile', folder / 'history-input/profile.json', '--out', folder / 'history']
    if previous_history:
        history_args += ['--previous', previous_history]
    commands(history_args)
    markup = ROOT / ('examples/pid-markup-review/corrected' if corrected else 'examples/pid-markup-review/inputs')
    shutil.copytree(markup, folder / 'markup')
    write(folder / 'job.json', dict(schema='drawing-receiving-1', id='Fictional markup-only selected job',
          drawings=[dict(id='Teaching P&ID', markup_manifest='markup/manifest.json')]))
    commands(['scripts/receive_drawings.py', '--manifest', folder / 'job.json', '--out', folder / 'drawing'])
    def attr(name, value):
        return dict(name=name, value=value, status='unverified', source=dict(kind='document', document='authored scope'))
    nodes = []
    for scope, tag in [(scopes[0], 'P-101'), (scopes[1], 'P-101'), (scopes[0], 'HV-102'), (scopes[0], 'PARK')]:
        nodes.append(dict(id=scope + '/' + tag, tag=tag, name='Fictional ' + tag,
                          kind='manual_valve' if tag.startswith('HV') else 'equipment', aliases=[],
                          attributes=[attr('scope', scope), attr('record_id', tag)] +
                          [attr('typed.' + str(i), value) for i, value in enumerate([False, 0, None, '', 'unknown', []])],
                          status='unverified', source=dict(kind='document', document='Authored scope; no installed claim')))
    graph = dict(schema='twin-graph-1', title='Fictional selected unit investigation', source_model='authored',
                 nodes=nodes, edges=[dict(id='REL1', type='acts_on', **{'from': scopes[0] + '/HV-102', 'to': scopes[0] + '/P-101'},
                 direction=None, status='unverified', source=dict(kind='document', document='Authored relation; not plant verified'))],
                 questions=[], events=[], not_exported=[])
    write(folder / 'graph.json', graph)
    qs = [('HISTORY', [scopes[0] + '/P-101']), ('DRAWING', [scopes[0] + '/HV-102']),
          ('SYNTHESIS', [scopes[0] + '/P-101', scopes[0] + '/HV-102']), ('INDEPENDENT', [scopes[0] + '/PARK']),
          ('MISSING', [scopes[0] + '/PARK'])]
    write(folder / 'questions.json', dict(schema='opportunity-questions-1', questions=[dict(
        id=q, question='What selected evidence remains to review for ' + q + '?', assets=[dict(id=a) for a in assets],
        status='asked') for q, assets in qs]))
    (folder / 'note.txt').write_text('Fictional note revision ' + ('B: reconcile replacement export.\n' if corrected else 'A: investigate, no failure established.\n'), encoding='utf-8')
    (folder / 'independent.txt').write_text('Fictional grounds note A; independent evidence.\n', encoding='utf-8')
    (folder / 'later-unavailable.txt').write_text('Fictional source supplied initially, omitted later.\n', encoding='utf-8')
    mapping = lambda scope, tag: dict(node=scope + '/' + tag, key=[scope, tag],
                                     reviewer='Fictional preparer declaration', reviewed_on='2026-11-09')
    profile = dict(schema='foundation-input-1', id='fictional-selected-unit', graph='graph.json', questions='questions.json',
        history=dict(packet='history', revision='2' if corrected else '1', mappings=[mapping(s, 'P-101') for s in scopes],
                     questions=['HISTORY', 'SYNTHESIS']),
        drawing=dict(packet='drawing', revision='2' if corrected else '1', mappings=[dict(mapping(scopes[0], 'HV-102'),
                     drawing='Teaching P&ID', request_id='M02', sheet='DEMO/U1/PID-101',
                     returned_revision='C' if corrected else 'B')], questions=['DRAWING', 'SYNTHESIS']), documents=[], unavailable=[])
    for did, path, questions in [('NOTE', 'note.txt', ['HISTORY', 'SYNTHESIS']),
                                  ('INDEPENDENT', 'independent.txt', ['INDEPENDENT']),
                                  ('OPTIONAL', 'later-unavailable.txt', ['MISSING'])]:
        if corrected and did == 'OPTIONAL':
            profile['unavailable'].append(dict(id=did, reason='Not supplied in next export; omission is not closure', questions=questions))
        else:
            profile['documents'].append(dict(id=did, path=path, revision='B' if corrected and did == 'NOTE' else 'A',
                locators=[dict(id='L1', locator='Complete authored note, line 1', questions=questions)]))
    write(folder / 'profile.json', profile)
    return folder / 'profile.json'


def run(out, reserved=False):
    if out.exists():
        raise ValueError('Choose a new output folder')
    out.mkdir(parents=True)
    logs, checks = [], []
    def command(args, expected=0):
        argv = [sys.executable, '-S', *[str(x) for x in args]]
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=240)
        logs.append(dict(argv=argv[2:], expected_exit=expected, exit=result.returncode,
                         stdout=result.stdout, stderr=result.stderr))
        write(out / 'commands.json', logs)
        if result.returncode != expected:
            raise ValueError('Unexpected CLI outcome: ' + ' '.join(argv[2:]) + '\n' + result.stderr)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
        write(out / 'checks.json', checks)
        if not condition:
            raise ValueError('Failed: ' + name)
    scopes = ('R7', 'R8') if reserved else ('U1', 'U2')
    profile = fixture(out / 'first', command, layout='semicolon' if reserved else 'comma', scopes=scopes)
    # Baseline on identical input files, before adapter execution.
    command(['examples/foundation-cycle/baseline.py', profile.parent])
    def prepare(profile, folder, register=None):
        command(['scripts/foundation_handoff.py', 'prepare', '--profile', profile, '--out', folder / 'prepared'])
        args = ['scripts/context_register.py', 'prepare', '--model', folder / 'prepared/graph.json',
                '--questions', folder / 'prepared/questions.json', '--sources', folder / 'prepared/sources.json',
                '--out', folder / 'context-prepared']
        if register:
            args += ['--register', register]
        command(args)
    prepare(profile, out / 'first')
    with (out / 'first/context-prepared/evidence_choices.csv').open(encoding='utf-8') as stream:
        choices = list(csv.DictReader(stream))
    rows = []
    for qid, source in [('HISTORY', 'NOTE'), ('DRAWING', 'DRAWING'), ('SYNTHESIS', 'NOTE'),
                        ('INDEPENDENT', 'INDEPENDENT'), ('MISSING', 'OPTIONAL')]:
        choice = next(c for c in choices if c['question_id'] == qid and c['source_id'] == source)
        row = {col: '' for col in handoff.context.COLUMNS}
        row.update(question_id=qid, answer_id='A', claim_key='next-step', value='investigate',
                   answer='Authored sourced proposal; not an operating instruction.', answer_state='answered', decision='proposed',
                   owner='Fictional responsible role', assigned_by='Fictional requester', assigned_on='2026-11-09',
                   source_match='unknown', plant_truth='unknown', source_id=source,
                   locator_id=choice['locator_id'], evidence_fingerprint=choice['evidence_fingerprint'])
        rows.append(row)
    def apply(folder, rows, register=None, suffix='applied'):
        path = folder / (suffix + '.csv')
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=handoff.context.COLUMNS)
            writer.writeheader(); writer.writerows(rows)
        args = ['scripts/context_register.py', 'apply', '--model', folder / 'prepared/graph.json',
                '--questions', folder / 'prepared/questions.json', '--sources', folder / 'prepared/sources.json',
                '--answers', path, '--out', folder / suffix]
        if register:
            args += ['--register', register]
        command(args)
        return folder / suffix
    first = out / 'first'
    applied = apply(first, rows)
    command(['scripts/foundation_handoff.py', 'deliver', '--prepared', first / 'prepared', '--context', applied, '--out', out / 'delivery-1'])
    command(['scripts/foundation_handoff.py', 'receive', '--packet', out / 'delivery-1', '--out', out / 'received-1'])
    result = handoff.load(first / 'history/result.json')
    check('scoped histories retain three/one selected orders and 2.5/3 booked hours',
          [(a['key'], len(a['work_orders']), a['booked_hours']['value']) for a in result['assets'] if a['key'][1] == 'P-101'] ==
          [([scopes[0], 'P-101'], 3, '2.5'), ([scopes[1], 'P-101'], 1, '3')])
    check('complete separate-process receive equals delivered packet', handoff.same(handoff.inventory(out / 'delivery-1'), handoff.inventory(out / 'received-1')))
    check('types remain distinct', [type(a['value']).__name__ for a in handoff.load(out / 'received-1/graph.json')['nodes'][0]['attributes'][2:8]] == ['bool', 'int', 'NoneType', 'str', 'str', 'list'])
    # Two competing proposals from the same current base, with opposite arrival order.
    proposal = dict(rows[0], answer_id='B', value='clarify', answer='Alternative proposed next step; no winner selected.')
    forward = apply(first, [rows[0], proposal], applied / 'context.json', 'conflict-forward')
    reverse = apply(first, [proposal, rows[0]], applied / 'context.json', 'conflict-reverse')
    f, r = [handoff.load(p / 'context.json') for p in (forward, reverse)]
    check('competing proposals remain disputed independent of arrival order', f['current']['HISTORY']['state'] == r['current']['HISTORY']['state'] == 'disputed')
    retry = apply(first, [rows[0], proposal], forward / 'context.json', 'retry')
    check('retry does not duplicate decision or ownership history', handoff.same(handoff.load(retry / 'context.json'), f))
    # Only a document changes: the graph and drawing results remain identical.
    note_only = out / 'note-only'
    note_only.mkdir()
    for name in ('history', 'drawing'):
        shutil.copytree(first / name, note_only / name)
    for name in ('profile.json', 'graph.json', 'questions.json', 'note.txt', 'independent.txt', 'later-unavailable.txt'):
        shutil.copyfile(first / name, note_only / name)
    (note_only / 'note.txt').write_text('Fictional same-revision bytes corrected; investigate source change.\n', encoding='utf-8')
    prepare(note_only / 'profile.json', note_only, applied / 'context.json')
    note_current = handoff.load(note_only / 'context-prepared/context.json')['current']
    check('source-only same-label byte change reopens dependent finding and synthesis',
          all(all(a['freshness'] == 'stale' for a in note_current[q]['answers']) for q in ('HISTORY', 'SYNTHESIS')))
    check('source-only change leaves independent and drawing answers current',
          all(handoff.same(note_current[q], handoff.load(applied / 'context.json')['current'][q]) for q in ('DRAWING', 'INDEPENDENT')))
    second = out / 'second'
    next_profile = fixture(second, command, corrected=True, previous_history=first / 'history',
                           layout='semicolon', scopes=scopes)
    prepare(next_profile, second, forward / 'context.json')
    revised = second / 'context-prepared'
    current = handoff.load(revised / 'context.json')['current']
    check('changed sources reopen dependent questions and synthesis',
          all(current[q]['state'] == 'unanswered' and current[q]['answers'] and
              all(a['freshness'] == 'stale' for a in current[q]['answers']) for q in ('HISTORY', 'DRAWING', 'SYNTHESIS')))
    check('independent answer stays current', handoff.same(current['INDEPENDENT'], f['current']['INDEPENDENT']))
    check('omitted source does not close earlier answer', current['MISSING']['state'] == 'unanswered' and
          all(a['freshness'] == 'stale' for a in current['MISSING']['answers']))
    command(['scripts/foundation_handoff.py', 'deliver', '--prepared', second / 'prepared', '--context', revised,
             '--previous', out / 'delivery-1', '--out', out / 'delivery-2'])
    base = hashlib.sha256((out / 'delivery-1/receipt.json').read_bytes()).hexdigest()
    command(['scripts/foundation_handoff.py', 'receive', '--packet', out / 'delivery-2', '--expected-base', base, '--out', out / 'relocated'])
    command(['scripts/foundation_handoff.py', 'receive', '--packet', out / 'relocated', '--expected-base', base, '--out', out / 'reopened'])
    check('full revised export/reopen including earlier originals and history', handoff.same(handoff.inventory(out / 'delivery-2'), handoff.inventory(out / 'reopened')))
    command(['scripts/foundation_handoff.py', 'receive', '--packet', out / 'delivery-2', '--out', out / 'wrong-base'], 2)
    command(['scripts/foundation_handoff.py', 'receive', '--packet', out / 'delivery-2', '--expected-base', base, '--out', out / 'reopened'], 2)
    command(['scripts/foundation_handoff.py', 'deliver', '--prepared', second / 'prepared', '--context', revised,
             '--previous', out / 'delivery-2', '--out', out / 'duplicate'], 2)
    check('wrong-base retry and duplicate refuse without new output', not (out / 'wrong-base').exists() and not (out / 'duplicate').exists())
    write(out / 'summary.json', dict(schema='foundation-rehearsal-1', author_run=True, reserved=reserved,
          checks=len(checks), passed=sum(c['passed'] for c in checks), cli_calls=len(logs),
          company_acceptance=False, independent_review=False,
          limits=['Authored fictional records and mappings, no blind drawing reading.',
                  'Procedural reservation is author-run, not independent site validation.',
                  'Snapshot software receiving is not company receiving or ChangePilot integration.']))
    print(json.dumps(handoff.load(out / 'summary.json')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reserved', action='store_true')
    args = parser.parse_args()
    run(args.out.resolve(), args.reserved)
