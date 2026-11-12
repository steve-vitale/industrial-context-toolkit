"""Re-score versioned corpus cases and compare saved model/method runs by task, family and identical coverage.

Offline; no model calls, downloads or executable commands from manifests. See CONTRIBUTING.md.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parent.parent
TASKS = {'drawing-extraction': 'pid2graph-v1', 'description-facts': 'native-facts-v1',
         'source-support': 'claim-judgments-v1', 'tag-reading': 'tag-text-v1',
         'maintenance-system-grouping': 'system-groups-v1'}
# Cases whose input/key files sit in a local cache of originals that may not be redistributed (data/external/<group>,
# fetch-by-hash). A clean clone lacks the whole cache: --registry then reports the suite UNVERIFIED instead of failing.
# A present cache with a missing or changed file still fails.
EXTERNAL = 'data/external/'
TEXT = {'.json', '.graphml', '.xml', '.md', '.txt', '.csv', '.py'}
FIELDS = {'units': ('id', ('type',)), 'streams': ('id', ('from', 'to')),
          'instruments': ('tag', ('unit', 'stream', 'variable', 'uom')),
          'final_elements': ('tag', ('unit', 'stream', 'uom')),
          'manual_valves': ('tag', ('unit', 'stream')),
          'relief_devices': ('tag', ('unit', 'stream')),
          'controllers': ('tag', ('unit', 'measurement'))}


class ProvenanceError(ValueError):
    pass


def bound(condition, message):
    if not condition:
        raise ProvenanceError(message)


def check_saved_metadata(record, run, case):
    """A schema label is not permission to discard conflicting recorded provenance."""
    if record.get('schema') == 'pid-prediction/1':
        bound('prediction' in record or bool(record.get('error') or record.get('parse_error')),
              'Saved pid-prediction envelope needs prediction or an explicit failure')
    known = (record.get('schema') == 'pid-prediction/1' and record.get('prediction') is not None
             and not record.get('error') and not record.get('parse_error'))
    for field, expected in [('model', run['model']['id']),
                            ('image_sha256', case['files']['input']['sha256'])]:
        if known or field in record:
            bound(record.get(field) == expected, 'Saved ' + field + ' disagrees with run/case')
    if known or 'prompt_sha256' in record:
        prompts = [r['sha256'] for r in run['recipe'] if r.get('role') == 'main_prompt']
        bound(len(prompts) == 1 and record.get('prompt_sha256') == prompts[0], 'Saved main prompt disagrees with its recipe role')
    if 'tool' in record:
        bound(record['tool'] == run.get('recorded_tool'), 'Saved tool disagrees with recorded_tool')
    tiling, tracer = record.get('tiling'), record.get('tracer')
    if isinstance(tiling, dict):
        if 'preface_sha256' in tiling:
            prefaces = [r['sha256'] for r in run['recipe'] if r.get('role') == 'tile_preface']
            bound(len(prefaces) == 1 and tiling['preface_sha256'] == prefaces[0], 'Saved tile preface disagrees with its recipe role')
        for field, setting in [('grid', 'tiles'), ('overlap', 'overlap')]:
            if field in tiling:
                bound(tiling[field] == run['configuration'].get(setting), 'Saved tiling disagrees with configuration.' + setting)
    if isinstance(tracer, dict) and 'mode' in tracer:
        bound(tracer['mode'] == run['configuration'].get('trace'), 'Saved tracer disagrees with configuration.trace')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def read_json(path):
    with path.open('rb') as stream:
        raw = stream.read(16 * 1024 * 1024 + 1)
    require(len(raw) <= 16 * 1024 * 1024, 'JSON input exceeds 16 MiB')
    def invalid(value):
        raise ValueError('Non-finite JSON number: ' + value)
    value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=strict_pairs, parse_constant=invalid)
    encoded(value)  # Also refuse overflow and invalid Unicode before reporting.
    return value


def file_hash(path):
    raw = path.read_bytes()
    return digest(raw.replace(b'\r\n', b'\n') if path.suffix.lower() in TEXT else raw)


def local(root, value):
    require(isinstance(value, str) and value and not Path(value).is_absolute(), 'Use a root-relative file path')
    path = (root / value).resolve()
    require(path.is_relative_to(root.resolve()), 'File reference escapes the selected root')
    return path


def reference(root, ref, missing=False):
    require(isinstance(ref, dict) and {'path', 'sha256'} <= set(ref) <= {'path', 'sha256', 'role'},
            'File reference needs path and sha256, with optional recipe role')
    if 'role' in ref:
        require(isinstance(ref['role'], str) and ref['role'], 'Recipe role must be nonempty text')
    require(isinstance(ref['sha256'], str) and len(ref['sha256']) == 64 and
            all(c in '0123456789abcdef' for c in ref['sha256']), 'Invalid file fingerprint')
    path = local(root, ref['path'])
    if missing and not path.exists():
        return None
    require(path.is_file(), 'Referenced file is unavailable: ' + ref['path'])
    require(file_hash(path) == ref['sha256'], 'Stale file fingerprint: ' + ref['path'])
    return path


def text_fields(row, fields, label):
    require(isinstance(row, dict), label + ' must be an object')
    for field in fields:
        require(isinstance(row.get(field), str) and row[field].strip(), label + '.' + field + ' must be nonempty text')


def native_facts(value):
    """Literal identity/type/placement/connection/control fields only; no name or source interpretation score."""
    require(isinstance(value, dict), 'Native answer must be an object')
    model = value.get('model', value)
    require(isinstance(model, dict), 'Native model must be an object')
    require(any(k in model for k in FIELDS), 'Answer has no supported native-model sections')
    facts = []
    for section, (identity, fields) in FIELDS.items():
        rows = model.get(section, [])
        require(isinstance(rows, list), section + ' must be a list')
        seen = set()
        for row in rows:
            text_fields(row, (identity,), section)
            ident = row[identity]
            require(ident not in seen, 'Duplicate native record identity: ' + ident)
            seen.add(ident)
            facts.append([section, ident, 'exists', True])
            for field in fields:
                if field in row:
                    require(isinstance(row[field], str) or row[field] is None, 'Native fact fields must be text or null')
                    facts.append([section, ident, field, row[field]])
            if section == 'controllers':
                output = row.get('output', {})
                require(isinstance(output, dict), 'Controller output must be an object')
                for field, target in output.items():
                    if field == 'split_range':
                        require(isinstance(target, list), 'split_range must be a list')
                        for item in target:
                            facts.append([section, ident, 'output.final_element', item])
                    else:
                        facts.append([section, ident, 'output.' + field, target])
    return {json.dumps(f, sort_keys=True, ensure_ascii=False, allow_nan=False) for f in facts}


def counts(tp, predicted, truth):
    return {'tp': tp, 'predicted': predicted, 'truth': truth}


def metrics(total):
    result = {}
    for name, row in total.items():
        tp, pred, truth = row['tp'], row['predicted'], row['truth']
        result[name] = {'precision': tp / pred if pred else 0.0,
                        'recall': tp / truth if truth else None,
                        'f1': 2 * tp / (pred + truth) if pred + truth else None}
    return result


def absent_caches(suite, root):
    """data/external/<group> folders a suite's case files need that are entirely absent from this checkout."""
    out = set()
    for case in suite.get('cases', []) if isinstance(suite, dict) else []:
        for ref in (case.get('files') or {}).values() if isinstance(case, dict) else []:
            path = ref.get('path', '') if isinstance(ref, dict) else ''
            if path.startswith(EXTERNAL):
                cache = '/'.join(path.split('/')[:3])
                if not (root / cache).exists():
                    out.add(cache)
    return sorted(out)


def system_answer(prediction):
    if prediction is None:
        return {}
    assigned = prediction.get('assigned') if isinstance(prediction, dict) else None
    require(isinstance(assigned, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in assigned.items()),
            'Expected {"assigned": {record number: class or ""}}')
    return assigned


def score_case(task, files, prediction):
    if task == 'maintenance-system-grouping':
        import score_maintenance_systems as systems
        case = files['_case']
        out = systems.evaluate(files['input'], files['key'], case['assets'], system_answer(prediction), case['majority'])
        method = out['scores']['method']
        return ({m: counts(**method['counts'][m]) for m in systems.METRICS},
                {'assigned_without_key_system': method['assigned_without_key_system'],
                 'keyed_without_system': method['keyed_without_system'], 'join': out['join']})
    if task == 'source-support':
        import source_support
        if '_artifact_value_review' in files:
            return files['_artifact_value_review'].score(prediction)
        return source_support.score(read_json(files['input']), read_json(files['key']), prediction)
    if task == 'drawing-extraction':
        import score_pid2graph as scorer
        value = prediction if prediction is not None else {'symbols': [], 'connections': []}
        require(isinstance(value, dict) and isinstance(value.get('symbols'), list) and
                isinstance(value.get('connections'), list), 'Expected symbols/connections lists')
        scored = scorer.score(files['key'], value, files['input'])
        result = {}
        for name, row in (('symbols_rough', scored['rough']['classified']),
                          ('symbols_strict', scored['strict']['classified']), ('networks', scored['connections'])):
            result[name] = counts(row['tp'], row['predicted'], row['in_key'])
        return result, {'ignored_or_malformed_symbols': scored['malformed_symbols']}
    expected = read_json(files['key'])
    require(isinstance(expected, dict) and set(expected) == {'facts'}, 'Fact key needs exactly facts')
    require(isinstance(expected['facts'], list) and expected['facts'], 'Fact key must not be empty')
    require(all(isinstance(f, list) and len(f) == 4 and f[0] in FIELDS and
                isinstance(f[1], str) and f[1] and isinstance(f[2], str) for f in expected['facts']),
            'Fact key needs [section, identity, field, value] atoms')
    truth = {json.dumps(f, sort_keys=True, ensure_ascii=False, allow_nan=False) for f in expected['facts']}
    require(len(truth) == len(expected['facts']), 'Fact key contains duplicates')
    actual = native_facts(prediction) if prediction is not None else set()
    result = {'facts': counts(len(actual & truth), len(actual), len(truth))}
    for section in FIELDS:
        want = {f for f in truth if json.loads(f)[0] == section}
        got = {f for f in actual if json.loads(f)[0] == section}
        result[section] = counts(len(want & got), len(got), len(want))
    return result, {'missing_facts': [json.loads(f) for f in sorted(truth - actual)],
                    'unexpected_facts': [json.loads(f) for f in sorted(actual - truth)]}


def evaluate(suite_path, root=ROOT):
    suite = read_json(suite_path)
    text_fields(suite, ('id', 'version', 'task', 'protocol', 'registration'), 'suite')
    task = suite['task']
    require(task in TASKS, 'Unsupported task; add a tested scorer adapter before registering this task')
    if task == 'tag-reading':
        import benchmark_tags
        return benchmark_tags.evaluate(suite_path, root, sys.modules[__name__], suite)
    sources = ['benchmark.py'] + (['score_pid2graph.py', 'evaluate_vendor.py', 'replicate_stats.py',
                                 'score_tags.py', 'test_scorer_controls.py'] if task == 'drawing-extraction' else [])
    if task == 'maintenance-system-grouping':
        sources.append('score_maintenance_systems.py')
    if task == 'source-support':
        sources.append('source_support.py')
        if any(isinstance(c, dict) and 'artifact_values_protocol' in c for c in suite.get('cases', [])):
            sources.extend(['artifact_value_review.py', 'description_workflow.py'])
    code_hashes = {p: file_hash(Path(__file__).parent / p) for p in sources}
    require(isinstance(suite.get('cases'), list) and suite['cases'], 'Suite needs cases')
    require(isinstance(suite.get('runs'), list) and suite['runs'], 'Suite needs run manifest paths')
    cases, loaded, controls = {}, {}, {}
    for case in suite['cases']:
        text_fields(case, ('id', 'family', 'split', 'evidence', 'source_url', 'license', 'key_author'), 'case')
        require(case['split'] in ('development', 'validation', 'held-out', 'synthetic-control'), 'Unknown case split')
        require(case['id'] not in cases, 'Duplicate case ID')
        required = {'input', 'key'} | ({'expected'} if task == 'description-facts' else set())
        require(set(case.get('files', {})) == required, 'Case needs ' + ', '.join(sorted(required)) + ' references')
        if 'artifact_values_protocol' in case:
            require(task == 'source-support', 'Artifact value review is an opt-in source-support case')
            import artifact_value_review
            require(case['artifact_values_protocol'] == artifact_value_review.PROTOCOL, 'Unsupported artifact value review protocol')
            files = {'_artifact_value_review': artifact_value_review.admit(root, case['files']['input'], case['files']['key'])}
        else:
            files = {k: reference(root, v) for k, v in case['files'].items()}
        if task == 'maintenance-system-grouping':
            require(isinstance(case.get('assets'), list) and case['assets'] and all(isinstance(a, str) and a for a in case['assets'])
                    and isinstance(case.get('majority'), str) and case['majority'], 'System case needs assets and a majority class')
            files['_case'] = {'assets': case['assets'], 'majority': case['majority']}
        # Validate keys independently: a bad key must stop evaluation, never become a model failure.
        score_case(task, files, None)
        if task == 'drawing-extraction':
            import evaluate_vendor as vendor
            import score_pid2graph as scorer
            table = {}
            for name, pred in vendor.controls_for(files['key'], files['input']).items():
                detail = scorer.score(files['key'], pred, files['input'])
                row = vendor.sheet_metrics(detail)
                if name == 'shifted':
                    row['_strict_located_tp'] = detail['strict']['located']['tp']
                    row['_strict_located_key'] = detail['strict']['located']['in_key']
                table[name] = row
            table['_key_links'] = detail['connections']['in_key']
            failures = vendor.check_controls({case['id']: table}, {k: table[k] for k in vendor.CONTROL_ORDER})
            require(not failures, 'Known-answer control failed: ' + '; '.join(failures))
            require(table['perfect']['key_items'] > 0, 'Drawing key has no scored items')
            controls[case['id']] = table
        elif task == 'maintenance-system-grouping':
            import score_maintenance_systems as systems
            out = systems.evaluate(files['input'], files['key'], case['assets'], {}, case['majority'])
            require(not out['control_problems'], 'Known-answer control failed: ' + '; '.join(out['control_problems']))
            require(out['join']['keyed_with_system'] > 0, 'System key has no scored records')
            # The answer-independent controls; the answer-dependent ones (shuffled, misaligned) are in each run row.
            controls[case['id']] = {name: out['scores'][name]['rates'] for name in ('reference', 'raw-asset-baseline', 'majority-system')}
            controls[case['id']]['_join'] = out['join']
        elif task == 'source-support':
            import source_support
            controls[case['id']] = (files['_artifact_value_review'].controls() if '_artifact_value_review' in files else
                                   source_support.controls(read_json(files['input']), read_json(files['key'])))
            positive = controls[case['id']]['reference']['judgments']
            require(positive['tp'] == positive['predicted'] == positive['truth'] > 0,
                    'Source judgment reference control must match every key label')
        else:
            golden, _ = score_case(task, files, read_json(files['expected']))
            row = golden['facts']
            require(row['truth'] > 0 and row['tp'] == row['truth'] == row['predicted'], 'Expected model does not exactly match the fact key')
            controls[case['id']] = {'expected': golden, 'empty': score_case(task, files, None)[0]}
        cases[case['id']], loaded[case['id']] = case, files
    results, submissions = [], []
    run_ids = set()
    used_artifacts = set()
    for path in suite['runs']:
        run_path = local(root, path)
        run = read_json(run_path)
        text_fields(run, ('id', 'ran_at', 'interface', 'method', 'provenance'), 'run')
        text_fields(run.get('model'), ('provider', 'id', 'version'), 'model')
        require(run['id'] not in run_ids, 'Duplicate run ID')
        run_ids.add(run['id'])
        attempted = run.get('cases')
        require(isinstance(attempted, list) and attempted and all(isinstance(c, str) and c in cases for c in attempted),
                'Run needs declared attempted case IDs')
        require(len(set(attempted)) == len(attempted), 'Duplicate attempted case')
        predictions = run.get('predictions')
        require(isinstance(predictions, dict) and not set(predictions) - set(attempted), 'Prediction is outside the attempted set')
        require(isinstance(run.get('configuration'), dict), 'Run needs a configuration object (unknown values stay explicit)')
        require(isinstance(run.get('recipe'), list) and run['recipe'], 'Run needs pinned prompt/recipe files')
        for ref in run['recipe']:
            reference(root, ref)
        submissions.append({'id': run['id'], 'path': path, 'sha256': file_hash(run_path)})
        buckets = defaultdict(list)
        for cid in sorted(attempted):
            case = cases[cid]
            buckets[(case['family'], case['split'], case['evidence'])].append(cid)
        for (family, split, evidence), ids in sorted(buckets.items()):
            cohort = {'task': task, 'scoring_contract': TASKS[task], 'protocol': suite['protocol'],
                      'scorer_code_sha256': code_hashes, 'cases': [cases[cid] for cid in ids]}
            rows, total = [], {}
            for cid in ids:
                case = cases[cid]
                ref = predictions.get(cid)
                prediction, status = None, 'missing'
                note = None
                recorded_run_at = None
                reported = {'seconds': None, 'cost_usd': None, 'cost_usd_notional': None}
                if ref is not None:
                    # Changed bytes are a provenance error; missing attempted output is a scored failure.
                    artifact = reference(root, ref, missing=True)
                    if artifact:
                        stat = artifact.stat()
                        file_identity = (stat.st_dev, stat.st_ino) if stat.st_ino else str(artifact)
                        identity = (json.dumps(run['model'], sort_keys=True), run['interface'], run['method'],
                                    digest(encoded(run['configuration'])), cid, file_identity)
                        require(identity not in used_artifacts, 'Same answer file reused as a model/method replicate')
                        used_artifacts.add(identity)
                        try:
                            record = read_json(artifact)
                            require(isinstance(record, dict), 'Answer must be a JSON object')
                            metadata = {'schema', 'model', 'tool', 'image_sha256', 'prompt_sha256', 'tiling', 'tracer'}
                            if 'prediction' in record or (task == 'drawing-extraction' and metadata.intersection(record)):
                                check_saved_metadata(record, run, case)
                            reported = {k: record.get(k) for k in reported}
                            recorded_run_at = record.get('ran_at')
                            prediction = record.get('prediction', record)
                            status = 'failed' if prediction is None or record.get('error') or record.get('parse_error') else 'ok'
                            if status != 'ok':
                                prediction = None
                        except ProvenanceError:
                            raise
                        except (ValueError, UnicodeError, RecursionError) as exc:
                            status, note = 'invalid-answer', str(exc)
                try:
                    scored, diagnostics = score_case(task, loaded[cid], prediction)
                except (ValueError, TypeError, KeyError, AttributeError, IndexError, OverflowError) as exc:
                    # Key and inputs were checked above. A malformed attempted answer earns an empty answer's score.
                    scored, diagnostics = score_case(task, loaded[cid], None)
                    status, note = 'invalid-answer', str(exc)
                for metric, row in scored.items():
                    summed = total.setdefault(metric, counts(0, 0, 0))
                    for field in summed:
                        summed[field] += row[field]
                if task == 'maintenance-system-grouping':
                    import score_maintenance_systems as systems
                    out = systems.evaluate(loaded[cid]['input'], loaded[cid]['key'], case['assets'],
                                           system_answer(prediction) if status == 'ok' else {}, case['majority'])
                    diagnostics['controls'] = {n: out['scores'][n]['rates'] for n in systems.CONTROL_ORDER}
                    diagnostics['margin_over_best_wrong_control'] = systems.margin(out['scores'])
                rows.append({'case': cid, 'status': status, 'note': note, 'counts': scored, 'diagnostics': diagnostics,
                             'reported_resources': reported, 'recorded_run_at': recorded_run_at,
                             'prediction_ref': ref})
                if '_artifact_value_review' in loaded[cid]:
                    rows[-1]['artifact_value_review'] = loaded[cid]['_artifact_value_review'].report()
            results.append({'run': run['id'], 'model': run['model'], 'interface': run['interface'],
                            'method': run['method'], 'configuration': run['configuration'], 'recipe': run['recipe'],
                            'ran_at': run['ran_at'], 'provenance': run['provenance'], 'cohort': digest(encoded(cohort)),
                            'family': family, 'split': split, 'evidence': evidence, 'case_count': len(ids),
                            'not_attempted': sorted(set(cases) - set(attempted)), 'rows': rows,
                            'counts': total, 'metrics': metrics(total)})
    groups = defaultdict(list)
    for result in results:
        identity = {k: result[k] for k in ('cohort', 'model', 'interface', 'method', 'configuration', 'recipe')}
        groups[digest(encoded(identity))].append(result)
    summary = []
    for group_id, repeats in sorted(groups.items()):
        first = repeats[0]
        row = {k: first[k] for k in ('model', 'interface', 'method', 'configuration', 'cohort', 'family', 'split', 'evidence', 'case_count')}
        row.update(group=group_id, runs=[r['run'] for r in repeats], replicates=len(repeats), metrics={})
        for metric in first['metrics']:
            values = [r['metrics'][metric]['f1'] for r in repeats]
            values = [v for v in values if v is not None]
            row['metrics'][metric] = {'mean_f1': statistics.mean(values) if values else None,
                                      'min_f1': min(values) if values else None, 'max_f1': max(values) if values else None,
                                      'stdev_f1': statistics.stdev(values) if len(values) > 1 else None}
        summary.append(row)
    return {'schema': 'task-benchmark-1', 'suite': suite['id'], 'suite_version': suite['version'], 'task': task,
            'registration': suite['registration'], 'scoring_contract': TASKS[task],
            'suite_sha256': file_hash(suite_path), 'code_sha256': code_hashes,
            'hash_method': 'SHA256; CRLF normalized to LF for declared text extensions, raw binary otherwise',
            'case_total': len(cases), 'controls': controls, 'submissions': submissions, 'results': results, 'summary': summary,
            'limits': ['Compare only the same cohort and scoring contract; model identity is contributor-declared, not provider-attested.',
                       'Each replicate pools counts over its cases; summary reports mean/range/stdev over replicates, not a significance test or winner.',
                       'Missing/failed attempted answers score empty; unattempted cases remain visible and create different comparison cohorts.',
                       'Public keys and retrospective registration do not establish blindness. Synthetic controls and corrected/development results are separate.',
                       *(['Description facts grade literal selected fields only: no prose names, source validity, dimensions, limits, layout quality or plant truth.']
                         if task not in ('source-support', 'maintenance-system-grouping') else [])] +
                      (['System grouping scores per-record classes against a publisher\'s own system coding, itself made by keyword rules over the same short text: agreement with those rules, not engineering truth, failure diagnosis or repair effectiveness. Records the key gives no system are outside the precision denominator and counted separately.']
                       if task == 'maintenance-system-grouping' else []) +
                      (['Source-support grades labels for fixed supplied claims against a supplied key. It does not judge free-form reasoning, source validity, question usefulness or plant truth; cited IDs are checked structurally.']
                       if task == 'source-support' else [])}


def markdown(report):
    if report['task'] == 'tag-reading':
        import benchmark_tags
        return benchmark_tags.markdown(report)
    def safe(value):
        return str(value).replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')
    lines = ['# Task results: ' + safe(report['suite']), '',
             'Task: `' + report['task'] + '`. ' + safe(report['registration']), '',
             'Only rows with the same cohort are directly comparable. See JSON for exact cases, failures, fingerprints and configurations.', '']
    if report['task'] == 'source-support':
        lines += ['## Fixed-claim label accuracy', '',
                  'Correct / expected is the primary metric. Missing judgments remain in the denominator. '
                  'A case contains several fixed claims; this is not a count of independent source families or model trials. '
                  'Reasons and source support are not automatically assessed.', '',
                  '| Run | Family | Correct / expected claims | Provided / expected claims | Exact label accuracy | Incorrect supported labels |',
                  '|---|---|---|---|---|---|']
        for row in report['results']:
            count = row['counts']['judgments']
            false_supported = row['counts']['supported']['predicted'] - row['counts']['supported']['tp']
            lines.append('| ' + ' | '.join(safe(v) for v in [row['run'], row['family'],
                str(count['tp']) + ' / ' + str(count['truth']),
                str(count['predicted']) + ' / ' + str(count['truth']),
                f"{count['tp'] / count['truth']:.4f}", false_supported]) + ' |')
        artifact_rows = [(run, case) for run in report['results'] for case in run['rows'] if 'artifact_value_review' in case]
        if artifact_rows:
            lines += ['', '## Declared artifact value coverage', '',
                      'Coverage counts describe the reviewed frozen inventory. Reviewer label accuracy is separate from whether the artifact contains contradicted claims. '
                      'A perfect reviewer may correctly report a critical contradiction. Role-only values are not source-accuracy successes; rationale quality and current plant truth remain unscored.', '',
                      '| Run | Case | Model entries | Provided values | Declared groups | Keyed artifact contradictions (ID and pointer) | Missing reviewer judgments |',
                      '|---|---|---|---|---|---|---|']
            for run, case in artifact_rows:
                admission = case['artifact_value_review']
                coverage = admission['coverage']
                contradictions = '; '.join(c['id'] + ': ' + ', '.join(c['pointers']) for c in admission['keyed_artifact_contradictions']) or 'none in declared key'
                lines.append('| ' + ' | '.join(safe(v) for v in [run['run'], case['case'], coverage['model_entries'], coverage['provided_values'],
                    coverage['semantic_groups'], contradictions, ', '.join(case['diagnostics'].get('missing_judgments', [])) or 'none']) + ' |')
        lines += ['', 'The label F1 rows below are companion diagnostics. F1 differs from exact accuracy when judgments are missing. '
                  'Inspect each claim and its reason; a correct label can accompany a false explanation.', '', '## Per-label diagnostics', '']
    if report['task'] == 'maintenance-system-grouping':
        lines += ['## Per-record system classes beside the wrong controls', '',
                  'Per-record precision / recall / F1 for the scored answer and every control on the same keyed records. `reference` is '
                  'the key itself (must be 1.0); `raw-asset-baseline` is the predeclared raw-asset-ID grouping, which has no system; '
                  '`majority-system` gives every record one fixed class; `shuffled-within-asset` permutes the answer\'s own classes; '
                  '`misaligned-key` scores the answer against another record\'s key. Records the key gives no system are outside '
                  'precision and counted in the last column.', '',
                  '| Run | Case / split | Answer or control | Orders P | Orders R | Orders F1 | Membership F1 | Groups F1 | No-system records given a class |',
                  '|---|---|---|---|---|---|---|---|---|']
        def r4(value):
            return 'n/a' if value is None else f'{value:.4f}'
        for run in report['results']:
            for case in run['rows']:
                d = case['diagnostics']
                method = metrics(case['counts'])
                rows_out = [('answer', method, d.get('assigned_without_key_system'))]
                rows_out += [(name, values, '') for name, values in d.get('controls', {}).items()]
                for name, values, extra in rows_out:
                    lines.append('| ' + ' | '.join(safe(v) for v in [run['run'], case['case'] + ' / ' + run['split'], name,
                        r4(values['orders']['precision']),
                        r4(values['orders']['recall']), r4(values['orders']['f1']), r4(values['membership']['f1']),
                        r4(values['groups']['f1']), extra]) + ' |')
                lines.append('| ' + ' | '.join(safe(v) for v in [run['run'], case['case'] + ' / ' + run['split'], 'margin over the best wrong control (orders F1)',
                             '', '', r4(d.get('margin_over_best_wrong_control')), '', '', '']) + ' |')
        lines += ['', 'The group F1 does not separate the answer from the shuffled or misaligned controls: most systems recur on '
                  'every asset under any labelling with the same class counts. Read the per-record and membership columns. '
                  'The model/method summary (one deterministic run per cohort, no replicates) is in the JSON only, so that '
                  'no table here shows the answer without its controls.', '']
    else:
        lines += [
                 '| Model / version | Method / interface | Family / split / evidence | Cohort | Cases | Replicates | Metric | Mean F1 | Min–max | SD |',
                 '|---|---|---|---|---|---|---|---|---|---|']
    def fmt(value):
        return 'unavailable' if value is None else f'{value:.4f}'
    for row in report['summary'] if report['task'] != 'maintenance-system-grouping' else []:
        for metric, values in row['metrics'].items():
            if values['mean_f1'] is None or (report['task'] == 'description-facts' and metric == 'facts') or \
                    (report['task'] == 'source-support' and metric == 'judgments'):
                continue
            model = row['model']['id'] + ' / ' + row['model']['version']
            lines.append('| ' + ' | '.join(safe(v) for v in [model, row['method'] + ' / ' + row['interface'],
                row['family'] + ' / ' + row['split'] + ' / ' + row['evidence'], row['cohort'][:12], row['case_count'],
                row['replicates'], metric, fmt(values['mean_f1']), fmt(values['min_f1']) + '–' + fmt(values['max_f1']), fmt(values['stdev_f1'])]) + ' |')
    lines += ['', '## Coverage and failures', '']
    for row in report['results']:
        bad = [r['case'] + ':' + r['status'] for r in row['rows'] if r['status'] != 'ok']
        lines.append('- ' + safe(row['run']) + ' (' + safe(row['family']) + ' / ' + safe(row['split']) + '): ' +
                     str(row['case_count']) + ' cases in this family/cohort; suite total ' + str(report['case_total']) +
                     '; suite-wide unattempted: ' + safe(', '.join(row['not_attempted']) or 'none') +
                     '; failed attempted answers: ' + safe(', '.join(bad) or 'none') + '.')
        for case in row['rows']:
            for label in ('missing_facts', 'unexpected_facts', 'missing_judgments', 'incorrect_judgments'):
                facts = case['diagnostics'].get(label, [])
                if facts:
                    lines.append('  ' + safe(case['case']) + ' ' + label + ': ' +
                                 safe(json.dumps(facts, ensure_ascii=False)) + '.')
    lines += ['', '## Limits', ''] + ['- ' + limit for limit in report['limits']] + ['']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--suite', type=Path)
    selection.add_argument('--registry', type=Path, help='check every registered suite/report offline')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path, help='new output prefix, or committed prefix with --check')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.registry:
            registry = read_json(args.registry)
            require(isinstance(registry.get('reports'), list) and registry['reports'], 'Registry needs reports')
            for entry in registry['reports']:
                absent = absent_caches(read_json(local(args.root, entry['suite'])), args.root)
                if absent:
                    print('UNVERIFIED: ' + entry['suite'] + ': local original cache absent (' + ', '.join(absent) +
                          '); committed report not recomputed here')
                    continue
                result = main(['--suite', str(local(args.root, entry['suite'])), '--root', str(args.root),
                               '--out', str(local(args.root, entry['report'])), '--check'])
                require(result == 0, 'Registered benchmark report failed: ' + entry['suite'])
            return 0
        require(args.out is not None, '--out is required with --suite')
        report = evaluate(args.suite, args.root)
        payloads = {args.out.with_suffix('.json'): encoded(report), args.out.with_suffix('.md'): markdown(report).encode('utf-8')}
        if args.check:
            changed = [str(p) for p, raw in payloads.items() if not p.is_file() or p.read_bytes().replace(b'\r\n', b'\n') != raw]
            require(not changed, 'Report stale or missing: ' + ', '.join(changed))
        else:
            require(all(not p.exists() and not p.is_symlink() for p in payloads), 'Choose a new report prefix; existing reports are retained')
            require(all(p.parent.is_dir() for p in payloads), 'Output parent must exist')
            protected = {args.suite.resolve()}
            require(not any(p.resolve() in protected for p in payloads), 'Report aliases the suite input')
            for path, raw in payloads.items():
                with path.open('xb') as stream:
                    stream.write(raw)
        print(f'{report["suite"]}: {len(report["results"])} run/cohort results, {len(report["summary"])} model/method groups')
        return 0
    except (ValueError, OSError, UnicodeError, RecursionError, TypeError, KeyError, AttributeError, OverflowError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
