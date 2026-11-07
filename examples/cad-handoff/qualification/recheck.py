"""Rebuild frozen candidates and re-score retained native returns offline; never launches commercial CAD or models."""
import argparse
import ast
from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import cad_handoff as ch
import cad_value_patch as patcher
from run_cases import run_case
from verify_bytes import verify


def read(path):
    return json.loads(Path(path).read_bytes())


def text_hash(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def method_bindings():
    freeze = read(HERE / 'METHOD-FREEZE-2.json')
    for path, wanted in (freeze['methods'] | freeze['manifests']).items():
        require(text_hash(ROOT / path) == wanted, 'Changed frozen method/input: ' + path)
    first = HERE / 'history/method-1'
    require(text_hash(first / 'METHOD-FREEZE-1.json') == freeze['parent_method_freeze_sha256_lf'], 'Changed first freeze')
    prior = read(first / 'METHOD-FREEZE-1.json')
    require(text_hash(HERE / 'fixtures/MANIFEST.json') == prior['fixture_manifest_sha256_lf'], 'Changed original fixture manifest')
    for path, wanted in prior['methods'].items():
        require(text_hash(first / path) == wanted, 'Changed retained original method: ' + path)
    def comparator(path):
        tree = ast.parse(Path(path).read_text(encoding='utf-8'))
        return ast.dump(next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'compare'))
    require(comparator(ROOT / 'scripts/cad_handoff.py') == comparator(first / 'scripts/cad_handoff.py'), 'Strict comparator changed')
    for path in ('scripts/cad_value_patch.py', 'examples/cad-handoff/qualification/verify_bytes.py'):
        require(text_hash(ROOT / path) == prior['methods'][path], 'Patcher or independent reconstruction changed')
    admission = read(HERE / 'PUBLIC-ADAPTATION-2.json')
    require(admission['freeze_sha256_lf'] == text_hash(HERE / 'METHOD-FREEZE-2.json'), 'Changed public method admission')
    public = HERE / 'validation-2/public-adapted/MANIFEST.json'
    require(admission['manifest_sha256_lf'] == text_hash(public), 'Changed derived public cohort')
    selected = read(HERE / 'validation-2/public-originals/MANIFEST.json')
    adapted = read(public)
    require([(c['id'], c['source_sha256']) for c in selected['cases']] ==
            [(c['id'], c['original_sha256']) for c in adapted['cases']], 'Omitted/replaced public originals')
    for case in selected['cases']:
        require(ch.digest(HERE / 'validation-2/public-originals' / case['source']) == case['source_sha256'], 'Changed public original')
    return dict(method_2=text_hash(HERE / 'METHOD-FREEZE-2.json'),
                comparator_ast_unchanged=True, patcher_and_byte_checker_unchanged=True,
                public_adaptation_binding='match', evidence='frozen code/source bindings; not a model or engineering review')


def unpack(evidence, destination):
    inventory = read(evidence / 'INVENTORY.json')
    archive = evidence / inventory['archive']['path']
    require(archive.stat().st_size == inventory['archive']['bytes'] and ch.digest(archive) == inventory['archive']['sha256'], 'Archive integrity mismatch')
    with zipfile.ZipFile(archive) as z:
        require(len(z.namelist()) == len(set(z.namelist())) and set(z.namelist()) == set(inventory['files']), 'Omitted/extra/duplicate archive members')
        for info in z.infolist():
            path = PurePosixPath(info.filename)
            require(not path.is_absolute() and '..' not in path.parts and path.parts[0] == 'raw'
                    and '\\' not in info.filename and (info.external_attr >> 16) & 0o170000 != 0o120000, 'Unsafe archive member')
            pin = inventory['files'][info.filename]
            require(info.file_size == pin['bytes'], 'Changed archive member size')
            raw = z.read(info)
            require(hashlib.sha256(raw).hexdigest() == pin['sha256'], 'Changed archive member hash')
            output = destination.joinpath(*path.parts)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(raw)
    return destination / 'raw', dict(files=len(inventory['files']), raw_bytes=inventory['raw_bytes'], archive_sha256=ch.digest(archive))


def saved_file(value, raw):
    path = str(value).replace('\\', '/')
    for marker, base in [('/data/external/cad-qualification/', raw), ('/examples/cad-handoff/', ROOT / 'examples/cad-handoff')]:
        if marker in path:
            suffix = PurePosixPath(path.split(marker, 1)[1])
            require(not suffix.is_absolute() and '..' not in suffix.parts, 'Unsafe saved path')
            return base.joinpath(*suffix.parts)
    raise ValueError('Unrecognized saved file reference: ' + path)


def cohort():
    rows = []
    for path, retained in [(HERE / 'fixtures/MANIFEST.json', 'regression-final-2'),
                           (HERE / 'validation-2/authored/MANIFEST.json', 'validation-2-authored'),
                           (HERE / 'validation-2/public-adapted/MANIFEST.json', 'validation-2-public')]:
        for c in read(path)['cases']:
            source, plan = path.parent / c['source'], path.parent / c['plan']
            require(ch.digest(source) == c['source_sha256'] and ch.digest(plan) == c['plan_sha256'], 'Changed case: ' + c['id'])
            rows.append(dict(id=c['id'], source=source, plan=plan, retained=retained))
    rows.append(dict(id='original-valve', source=ROOT / 'examples/cad-handoff/source/valve.dxf',
                     plan=ROOT / 'examples/cad-handoff/source/edit-plan.json', retained='development/matched'))
    require(len(rows) == 21 and len({c['id'] for c in rows}) == 21, 'Unexpected candidate cohort')
    return rows


def stored_groups(rows):
    known, unknown = {}, Counter()
    for row in rows:
        values = row['attributes']
        identity = values.get('ICT_ID')
        if identity:
            require(identity not in known, 'Duplicate native identity')
            known[identity] = values
        else:
            unknown[json.dumps(values, sort_keys=True)] += 1
    return known, unknown


def native_receipts(raw, name, expected_count, fresh_count):
    directory = raw / name
    cases = read(directory / 'edited-manifest.json')['cases']
    require(len(cases) == expected_count, 'Omitted native cases')
    source_values, expected_values = {}, {}
    receipt = read(directory / 'edited-receipt.json')
    helper = ch.digest(HERE / 'native-batch.js')
    require(receipt['process_exit'] == 0 and receipt['expected'] == receipt['returned'] == expected_count
            and receipt['helper_sha256'] == helper, 'Failed/incomplete native receipt')
    require([r['id'] for r in receipt['readbacks']] == [c['id'] for c in cases], 'Native case ordering changed')
    comparisons = []
    for c, row in zip(cases, receipt['readbacks']):
        require(not any(v for k, v in row.items() if k.endswith('error')), 'Native case error')
        source, plan = saved_file(c['source'], raw), read(saved_file(c['plan'], raw))
        before = ch.snapshot(source)
        source_values[c['id']] = {a['id']: a['attributes'] for a in before['assets']}
        wanted = copy.deepcopy(source_values[c['id']])
        for change in plan['changes']:
            require(wanted[change['id']][change['attribute']] == change['before'], 'Native plan before mismatch')
            wanted[change['id']][change['attribute']] = change['after']
        expected_values[c['id']] = wanted
        initial, foreign = stored_groups(row['source'])
        require(initial == source_values[c['id']], 'Native source stored values changed')
        for route in ('candidate', 'native_default', 'native_r15'):
            observed, extra = stored_groups(row[route])
            require(observed == wanted and extra == foreign, 'Native stored/foreign values differ: ' + c['id'] + ':' + route)
            path = saved_file(c[route], raw)
            result = ch.compare(before, ch.snapshot(path), plan)
            retained = read(directory / f"{c['id']}-{route}-comparison.json")
            # This informational flag includes ezdxf's on-read replacement of zero creation dates with now.
            # Raw files remain pinned and all strict fields, including every unexpected difference, must match.
            strict_result = {k: v for k, v in result.items() if k != 'save_metadata_changed'}
            strict_retained = {k: v for k, v in retained.items() if k != 'save_metadata_changed'}
            require(strict_result == strict_retained, 'Stored native comparison no longer reproduces: ' + c['id'] + ':' + route)
            require((result['status'] == 'pass') == (route == 'candidate'), 'Native full-save failure unexpectedly reclassified')
            comparisons.append(dict(id=c['id'], route=route, strict_status=result['status'], unexpected=len(result['unexpected']),
                                    save_metadata_changed_retained=retained['save_metadata_changed'],
                                    save_metadata_changed_observed=result['save_metadata_changed']))
    fresh = read(directory / 'fresh-process-receipt.json')
    require(fresh['process_exit'] == 0 and fresh['expected'] == fresh['returned'] == fresh_count
            and fresh['helper_sha256'] == helper and len(fresh['readbacks']) == fresh_count, 'Incomplete fresh-process receipt')
    fresh_manifest = read(directory / 'fresh-process-manifest.json')
    require(fresh_manifest['read_only'] is True and [r['id'] for r in fresh['readbacks']] ==
            [c['id'] for c in fresh_manifest['cases']], 'Changed fresh-process cohort')
    for row in fresh['readbacks']:
        require(not row.get('error'), 'Fresh-process readback error')
        identity = row['id'].split(':', 1)[0]
        before, foreign = stored_groups(row['source'])
        after, extra = stored_groups(row['candidate'])
        require(before == source_values[identity] and after == expected_values[identity] and extra == foreign, 'Fresh-process attribute mismatch')
    return dict(native_cases=expected_count, rescored_comparisons=comparisons, fresh_process_stored_readbacks=fresh_count,
                scope='Re-scores saved native files/API receipts; does not rerun native engine or verify UI interaction')


def revision_checks(destination, raw):
    source = ROOT / 'examples/cad-handoff/source/valve.dxf'
    plan = read(source.parent / 'edit-plan.json')
    original = source.read_bytes()
    patcher.apply(source, plan, destination / 'proposal-1')
    proposal = destination / 'proposal-1/candidate.dxf'
    for label, stale in [('stale-hash', plan), ('stale-before', dict(plan, source_sha256=ch.digest(proposal)))]:
        try:
            patcher.apply(proposal, stale, destination / label)
        except ch.InputError:
            require(not (destination / label).exists(), 'Refusal created output')
        else:
            raise ValueError('Stale proposal accepted')
    concurrent = copy.deepcopy(plan)
    next(c for c in concurrent['changes'] if c['attribute'] == 'MODEL')['after'] = 'MANUAL-OTHER'
    patcher.apply(source, concurrent, destination / 'concurrent')
    returned = destination / 'concurrent/candidate.dxf'
    review = ch.review(source, returned, plan, destination / 'conflict')
    conflicts = [r for r in review['asset_attributes'] if r['status'] == 'planned edit missing or different']
    require(review['strict_difference_count'] == 1 and len(conflicts) == 1 and conflicts[0]['attribute'] == 'MODEL'
            and conflicts[0]['after'] == 'MANUAL-OTHER', 'Concurrent disagreement lost')
    resolved = read(raw / 'revision-controls-2/revision-2-plan.json')
    require(resolved['source_sha256'] == ch.digest(returned), 'Revision-2 source binding changed')
    patcher.apply(returned, resolved, destination / 'revision-2')
    candidate = destination / 'revision-2/candidate.dxf'
    verify(returned, candidate, resolved)
    spec = importlib.util.spec_from_file_location('cad_context_projection', ROOT / 'examples/cad-handoff/project_to_map.py')
    projection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(projection)
    mapping = read(source.parent / 'site-mapping.json')
    projection.project(destination / 'proposal-1', mapping, destination / 'map-before')
    projection.project(destination / 'revision-2/candidate-context', mapping, destination / 'map-selected')
    commands = []
    for label in ('map-before', 'map-selected'):
        commands.append([sys.executable, str(ROOT / 'scripts/one_map.py'), 'build', str(destination / label / 'site.json'), '--out', str(destination / label / 'map')])
    commands.append([sys.executable, str(ROOT / 'scripts/one_map.py'), 'changes', str(destination / 'map-before/map/graph.json'),
                     str(destination / 'map-selected/map/graph.json'), '--out', str(destination / 'map-change')])
    for n, command in enumerate(commands):
        proc = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        (destination / f'command-{n}.log').write_bytes(proc.stdout)
        require(proc.returncode == 0, 'Context command failed')
    observed = read(destination / 'map-selected/sheet.json')['instruments'][0]['attributes']
    require(observed == read(raw / 'revision-controls-2/checks.json')['selected_context'], 'Selected context fields changed')
    require(source.read_bytes() == original and (destination / 'map-before/cad-source.dxf').read_bytes() == original
            and (destination / 'map-selected/cad-source.dxf').read_bytes() == candidate.read_bytes(), 'Retained context sources changed')
    return dict(stale_refusals=2, explicit_conflicts=conflicts, revision_2_bytes='pass', context_commands=3,
                retained_sources='exact', scope='Fictional branches and draft drawing-reference context; no human edit, installed register or company acceptance')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evidence', type=Path, default=HERE / 'round-2')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        ap.error('Output exists; choose a new report destination')
    args.out.mkdir(parents=True)
    report = dict(scope='Offline exact-source candidate rebuild and retained-native receipt/file re-score. '
                  'No models, native commercial application, GUI or engineering acceptance.', cases=[], errors=[])
    try:
        report['method_bindings'] = method_bindings()
        raw, report['archive'] = unpack(args.evidence, args.out / 'retained')
        for c in cohort():
            result = dict(id=c['id'])
            try:
                directory = raw / c['retained'] / c['id']
                expected = read(directory / 'result.json')
                observed = run_case(c['id'], c['source'], c['plan'], args.out / 'rebuilt' / c['id'])
                for route in ('library-save', 'value-spans'):
                    wanted, got = expected['routes'][route], observed['routes'][route]
                    require(not got.get('error') and all(got[k] == wanted[k] for k in ('strict_status', 'strict_differences')), 'Matched route differs: ' + route)
                    require(got['byte_check']['status'] == wanted['byte_check']['status'], 'Raw-byte verdict changed')
                require((args.out / 'rebuilt' / c['id'] / 'candidate/candidate.dxf').read_bytes() ==
                        (directory / 'candidate/candidate.dxf').read_bytes(), 'Candidate bytes changed')
                result.update(routes=observed['routes'], exact_candidate_rebuilt=True)
            except Exception as error:
                result['error'] = f'{type(error).__name__}: {error}'
                report['errors'].append(dict(stage='candidate', id=c['id'], error=result['error']))
            report['cases'].append(result)
            print(c['id'], result.get('error', 'matched strict/byte verdicts and exact candidate'), flush=True)
        report['development_native'] = native_receipts(raw, 'native-2-development', 9, 9)
        report['replacement_native'] = native_receipts(raw, 'native-validation-2', 12, 36)
        report['revision'] = revision_checks(args.out / 'revision', raw)
    except Exception as error:
        report['errors'].append(dict(stage='bindings/archive/native/revision', error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc()))
    report['status'] = 'pass' if not report['errors'] else 'fail'
    report['qualification'] = 'not established: readable visual/UI gates and engineering acceptance are separate'
    report['rechecker_sha256_lf'] = text_hash(Path(__file__))
    ch.write_json(args.out / 'report.json', report)
    print(report['status'], len(report['cases']), 'candidate cases;', len(report['errors']), 'errors', flush=True)
    return int(bool(report['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
