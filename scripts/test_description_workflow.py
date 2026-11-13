"""Description packet regression controls: source preservation, directed topology and generated bundles.

Uses authored illustrative fixtures, Pillow and native generators; no model calls or network.
"""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import description_workflow as workflow
import serve_snapshot

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / 'examples/from-description/assisted'
SCRIPT = ROOT / 'scripts/description_workflow.py'


class DescriptionWorkflowTests(unittest.TestCase):
    def test_committed_bundles_bind_current_producers_and_complete_artifacts(self):
        """Current published bundles need an actual rebuild when a declared producer changes.

        This checks recorded identity/freshness, not transitive dependencies or engineering truth.
        """
        producers = {'description_workflow.py', 'draw_pid_from_model.py', 'generate.py',
                     'question_engine.py', 'graph_export.py'}
        for case in ('assisted', 'mgpi'):
            with self.subTest(case=case):
                result = ROOT / 'examples/from-description' / case / 'result'
                receipt = json.loads((result / 'build.json').read_bytes())
                self.assertEqual(set(receipt['code_sha256']), producers,
                                 f'{case}: declared producer basenames differ')
                for name in sorted(producers):
                    # Producer policy canonicalizes only code CRLF; artifact/source bytes stay raw.
                    code = (ROOT / 'scripts' / name).read_bytes().replace(b'\r\n', b'\n')
                    self.assertEqual(receipt['code_sha256'][name], hashlib.sha256(code).hexdigest(),
                                     f'{case}: stale code_sha256[{name}]; rebuild the bundle')
                artifacts = {p.relative_to(result).as_posix(): p for p in result.rglob('*')
                             if p.is_file() and p.relative_to(result).as_posix() != 'build.json'}
                self.assertEqual(set(receipt['files_sha256']), set(artifacts),
                                 f'{case}: complete artifact path set differs')
                for name, path in sorted(artifacts.items()):
                    self.assertEqual(receipt['files_sha256'][name],
                                     hashlib.sha256(path.read_bytes()).hexdigest(),
                                     f'{case}: artifact bytes differ: {name}')
                self.assertEqual(receipt['source_sha256'],
                                 hashlib.sha256((result / 'source.txt').read_bytes()).hexdigest(),
                                 f'{case}: retained source binding differs')
                self.assertEqual(receipt['answer_sha256'],
                                 hashlib.sha256((result / 'answer.json').read_bytes()).hexdigest(),
                                 f'{case}: retained answer binding differs')
                catalog = receipt['question_catalog']
                self.assertEqual(set(catalog), {'path', 'sha256_raw', 'selection'},
                                 f'{case}: catalog identity fields differ')
                self.assertEqual(catalog['path'], 'question_catalog.json')
                self.assertEqual(catalog['selection'], 'default')
                snapshot = (result / catalog['path']).read_bytes()
                self.assertEqual(catalog['sha256_raw'], hashlib.sha256(snapshot).hexdigest(),
                                 f'{case}: retained question catalog binding differs')
                self.assertEqual(receipt['files_sha256'][catalog['path']], catalog['sha256_raw'])
                self.assertEqual(snapshot, (ROOT / 'data/questions.json').read_bytes(),
                                 f'{case}: stale question catalog; rebuild against current default rules')

    def test_mgpi_source_adaptation_preserves_aliases_evidence_and_scoring_limit(self):
        import benchmark
        case = ROOT / 'examples/from-description/mgpi'
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            workflow.prepare(case / 'source.txt', folder / 'packet')
            result = folder / 'result'
            report = workflow.build(folder / 'packet', case / 'answer.json', result)
            self.assertTrue(report['ok'], report)
            self.assertEqual(report['sheets'], 2)
            graph = json.loads((result / 'graph.json').read_bytes())
            indicator = next(n for n in graph['nodes'] if n['id'] == 'LI_HYPO')
            self.assertEqual(indicator['status'], 'unverified')
            claims = {a['name']: a['value'] for a in indicator['attributes']}
            self.assertIn('no automatic unloading shutdown', claims['alarm_action_basis'])
            text = (result / 'exports/svg/HYPO_BULK.svg').read_text(encoding='utf-8')
            self.assertIn('LI_HYPO', text)
            # The source-policy revision asks about the represented level measurement's purpose.
            # It does not diagnose the incident or establish a shutdown/safeguard requirement.
            questions = json.loads((result / 'questions/questions.json').read_bytes())['questions']
            self.assertEqual([q['id'] for q in questions], ['C2@model'])
            self.assertEqual([a['id'] for a in questions[0]['assets']], ['LI_HYPO'])
            self.assertTrue(questions[0]['data_requests'])
        model = json.loads((case / 'model-expanded-source.json').read_bytes())
        false = json.loads((case / 'controls/false-shutdown.json').read_bytes())
        # Pin the exposed limit: alarm semantics are retained in output but not graded by native-facts-v1.
        self.assertEqual(benchmark.native_facts(model), benchmark.native_facts(false))
        # Every action claim is now visible beside its quote even though legacy selected-field scoring misses it.
        reviews=[]
        for candidate in (model,false):
            packet=workflow.interpretation_review(candidate,(case/'source.txt').read_bytes())
            rows=list(csv.DictReader(io.StringIO(packet['interpretation_review.csv'].decode('utf-8'))))
            row=next(r for r in rows if r['model_pointer']=='/instruments/0/alarm_action_basis')
            self.assertEqual(row['verdict'],'unreviewed')
            self.assertIn('alarm',json.loads(row['source_quote_json']).lower())
            reviews.append(row)
        self.assertNotEqual(reviews[0]['value_json'],reviews[1]['value_json'])
        self.assertEqual(reviews[0]['source_quote_json'],reviews[1]['source_quote_json'])
        initial = json.loads((case / 'v1/facts.json').read_bytes())['facts']
        expanded = json.loads((case / 'v2/facts.json').read_bytes())['facts']
        self.assertEqual({json.dumps(x) for x in expanded} - {json.dumps(x) for x in initial},
                         {json.dumps(['instruments', 'LI_HYPO', 'unit', 'HYPO_BULK'])})

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='description-test-')
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.source = self.folder / 'description.txt'
        self.source.write_bytes(workflow.REFERENCE_SOURCE.encode('utf-8'))
        self.packet = self.folder / 'packet'
        workflow.prepare(self.source, self.packet)

    def answer(self, value):
        path = self.folder / 'answer.json'
        path.write_bytes(workflow.json_bytes(value))
        return path

    def check_value(self, value):
        return workflow.check(self.packet, self.answer(value))

    def test_review_packet_preserves_nested_values_and_exposes_uncited_source(self):
        answer=workflow.reference_answer()
        record=answer['model']['units'][0]
        record['extra']={'a/b~c':[None,False,0,{},[]],'source':'source.txt:L8-L8'}
        record['name']='=SUM(1,2)'
        files=workflow.interpretation_review(answer['model'],workflow.REFERENCE_SOURCE.encode('utf-8'))
        rows=list(csv.DictReader(io.StringIO(files['interpretation_review.csv'].decode('utf-8'))))
        values={r['model_pointer']:json.loads(r['value_json']) for r in rows}
        self.assertEqual([values['/units/0/extra/a~1b~0c/'+str(i)] for i in range(5)],
                         [None,False,0,{},[]])
        self.assertEqual(values['/units/0/name'],'=SUM(1,2)')
        self.assertTrue(all(r['verdict']=='unreviewed' for r in rows))
        self.assertTrue(all(not cell.startswith(('=','+','-','@')) for r in rows for cell in r.values()))
        nested=next(r for r in rows if r['model_pointer']=='/units/0/extra/a~1b~0c/0')
        self.assertEqual(nested['source_locator'],'source.txt:L8-L8')
        self.assertEqual(json.loads(nested['source_quote_json']),workflow.REFERENCE_SOURCE.splitlines()[7])
        coverage=list(csv.DictReader(io.StringIO(files['source_coverage.csv'].decode('utf-8'))))
        self.assertEqual(len(coverage),8)
        self.assertEqual(json.loads(coverage[0]['citing_record_pointers_json']),[])
        self.assertIn('/units/0',json.loads(coverage[7]['citing_record_pointers_json']))
        self.assertTrue(all(r['review_state']=='unreviewed' for r in coverage))

    def test_prepare_runs_without_site_packages_and_preserves_raw_source(self):
        raw = b'\xef\xbb\xbf' + workflow.REFERENCE_SOURCE.replace('\n', '\r\n').encode('utf-8')
        self.source.write_bytes(raw)
        out = self.folder / 'stdlib-packet'
        proc = subprocess.run([sys.executable, '-S', str(SCRIPT), 'prepare', '--source', str(self.source),
                               '--out', str(out)], capture_output=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((out / 'source.txt').read_bytes(), raw)
        answer = workflow.reference_answer()
        answer['model']['meta']['source_sha256'] = workflow.digest(raw)
        answer_path = self.answer(answer)
        answer_raw = answer_path.read_bytes().replace(b'\n', b'\r\n')
        answer_path.write_bytes(answer_raw)
        self.assertTrue(workflow.check(out, answer_path)['ok'])
        bundle = self.folder / 'raw-input-result'
        self.assertTrue(workflow.build(out, answer_path, bundle)['ok'])
        self.assertEqual((bundle / 'source.txt').read_bytes(), raw)
        self.assertEqual((bundle / 'answer.json').read_bytes(), answer_raw)
        for p in bundle.rglob('*'):
            if p.is_file() and p.suffix != '.png' and p.name not in ('source.txt', 'answer.json'):
                self.assertNotIn(b'\r\n', p.read_bytes(), str(p))

    def test_linear_branch_recycle_and_offpage_bundles(self):
        fixtures = [('linear', 'source.txt', 'result/answer.json'),
                    ('branch', 'branch-source.txt', 'branch-answer.json'),
                    ('offpage', 'source.txt', 'offpage-answer.json')]
        for name, source, answer in fixtures:
            with self.subTest(name=name):
                packet = self.folder / (name + '-packet')
                workflow.prepare(EXAMPLE / source, packet)
                out = self.folder / (name + '-result')
                report = workflow.build(packet, EXAMPLE / answer, out)
                self.assertTrue(report['ok'], report)
                self.assertEqual((out / 'source.txt').read_bytes(), (EXAMPLE / source).read_bytes())
                manifest = json.loads((out / 'build.json').read_bytes())
                self.assertIn('interpretation_review.csv',manifest['files_sha256'])
                self.assertIn('source_coverage.csv',manifest['files_sha256'])
                self.assertIn('REVIEW.md', manifest['files_sha256'])
                self.assertEqual(set(manifest['files_sha256']),
                                 {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()} - {'build.json'})
                for path, sha in manifest['files_sha256'].items():
                    self.assertEqual(workflow.digest((out / path).read_bytes()), sha, path)
                model = json.loads((out / 'model.json').read_bytes())
                graph = json.loads((out / 'graph.json').read_bytes())
                self.assertEqual(len(list((out / 'pid').glob('*.png'))), report['sheets'])
                self.assertEqual({n['id'] for n in graph['nodes'] if n['kind'] == 'equipment'},
                                 {u['id'] for u in model['units']})
                edges = {(e['type'], e['from'], e['to']) for e in graph['edges']}
                self.assertEqual({e for e in edges if e[0] == 'connects'},
                                 {('connects', s['from'], s['to']) for s in model['streams']})
                for controller in model.get('controllers', []):
                    self.assertIn(('controls', controller['measurement'], controller['tag']), edges)
                    self.assertIn(('controls', controller['tag'], controller['output']['final_element']), edges)
                self.assertTrue((out / 'questions/screen.md').is_file())
                self.assertTrue((out / 'exports/ignition/tags.json').is_file())
                snapshot = serve_snapshot.Snapshot(out / 'graph.json')
                self.assertEqual(snapshot.asset('P-1')['result']['id'], 'P-1')
                self.assertTrue(snapshot.question_list('P-1')['result']['questions'])
                before = {p: (out / p).read_bytes() for p in manifest['files_sha256']}
                with self.assertRaisesRegex(workflow.InputError, 'new output directory'):
                    workflow.build(packet, EXAMPLE / answer, out)
                self.assertTrue(all((out / p).read_bytes() == raw for p, raw in before.items()))

    def test_model_and_drawing_cannot_disagree_or_invent_a_stream(self):
        for mutate, expected in (
            (lambda a: a['layout']['sheets'][0]['routes'][1].update(to={'unit': 'TK-1'}), 'model stream S2.to'),
            (lambda a: a['layout']['sheets'][0]['routes'][1].update(stream='NO-SUCH-STREAM'), 'must name a model stream'),
            (lambda a: a['layout']['sheets'][0]['routes'][1].update(pts=[[950, 900], [1655, 900]]), 'touch the named equipment'),
            (lambda a: a['layout']['sheets'][0]['routes'][1].update(to={'net': 'guess'}), 'ambiguous net'),
        ):
            answer = workflow.reference_answer()
            mutate(answer)
            report = self.check_value(answer)
            self.assertFalse(report['ok'])
            self.assertIn(expected, '\n'.join(report['errors']))

    def test_off_outline_endpoint_diagnostic_names_the_outline_it_missed(self):
        """A419: three assistant replicates spent four rounds each on a mixer route the diagnostic never located."""
        answer = workflow.reference_answer()
        answer['layout']['sheets'][0]['routes'][1].update(pts=[[950, 900], [1655, 900]])
        errors = '\n'.join(self.check_value(answer)['errors'])
        self.assertIn('route endpoint [950, 900] must touch the named equipment outline', errors)
        self.assertIn('TK-1 outline x 700-900, y 760-1040', errors)

    def test_contract_states_the_fixed_mixer_outline(self):
        """The check ignores a mixer's r (fixed 35-pixel half-size); the contract must not say it is used."""
        self.assertNotIn('mixer uses at/r', workflow.CONTRACT)
        self.assertIn('mixer uses at only', workflow.CONTRACT)
        answer = workflow.reference_answer()
        model, sheet = answer['model'], answer['layout']['sheets'][0]
        model['units'].append({'id': 'MX-1', 'name': 'Feed mixer', 'type': 'feed_header',
                               'source': 'source.txt:L2-L2'})
        sheet['units']['MX-1'] = {'shape': 'mixer', 'at': [500, 1300], 'r': 40}
        model['streams'].append({'id': 'S4', 'name': 'Mixer feed', 'from': 'BL', 'to': 'MX-1',
                                 'source': 'source.txt:L4-L4'})
        sheet['flags']['IN2'] = {'stream': 'S4', 'label': 'MIXER FEED', 'at': [120, 1300], 'dir': 'right'}
        route = {'id': 'S4', 'stream': 'S4', 'from': {'flag': 'IN2'}, 'to': {'unit': 'MX-1'}}
        sheet['routes'].append(dict(route, pts=[[350, 1300], [460, 1300]]))  # stops at r=40: misses the outline
        errors = '\n'.join(self.check_value(answer)['errors'])
        self.assertIn('MX-1 outline x 465-535, y 1265-1335', errors)
        sheet['routes'][-1] = dict(route, pts=[[350, 1300], [465, 1300]])
        self.assertTrue(self.check_value(answer)['ok'], self.check_value(answer))

    def test_contract_keeps_source_named_equipment_and_order_based_connections_reviewable(self):
        """A419: replicates dropped a source-named turbine (no supported type) and every connection the source gives
        only by process order. The contract asks for both, each recorded in meta.assumptions for review."""
        text = ' '.join(workflow.CONTRACT.split())
        self.assertIn('Do not drop equipment the source names', text)
        self.assertIn('closest supported type', text)
        self.assertIn('order in which material passes through', text)
        self.assertIn('meta.assumptions', text)
        self.assertIn('Never connect units whose order the source does not give', text)

    def test_controller_output_contract_has_typed_targets(self):
        for output in ({'unsupported_key': 'FV-101'}, {'final_element': 'FT-101'},
                       {'final_element': 'FV-101', 'setpoint_of': 'FIC-101'},
                       {'split_range': ['FV-101', 'FV-101']}, {'setpoint_of': 'FIC-101'}):
            with self.subTest(output=output):
                answer = workflow.reference_answer()
                answer['model']['controllers'][0]['output'] = output
                report = self.check_value(answer)
                self.assertFalse(report['ok'])
                self.assertIn('model.controllers.FIC-101.output', '\n'.join(report['errors']))

    def test_extreme_geometry_refused_before_rendering(self):
        answer = workflow.reference_answer()
        answer['layout']['sheets'][0]['units']['TK-1'].update(shape='column', top=-100000000,
                                                           bottom=100000000, trays=True)
        proc = subprocess.run([sys.executable, str(SCRIPT), 'check', '--packet', str(self.packet),
                               '--answer', str(self.answer(answer))], capture_output=True, timeout=10)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertIn('units.TK-1.top', '\n'.join(report['errors']))
        self.assertFalse((self.folder / 'pid').exists())

    def test_equipment_type_and_symbol_agree(self):
        answer = workflow.reference_answer()
        answer['layout']['sheets'][0]['units']['TK-1'] = {'shape': 'pump', 'at': [800, 900], 'r': 45}
        report = self.check_value(answer)
        self.assertFalse(report['ok'])
        self.assertIn('does not match the model equipment type', '\n'.join(report['errors']))

    def test_drawing_cannot_discard_its_draft_disclaimers(self):
        answer = workflow.reference_answer()
        answer['layout']['title_block'].update(revision='APPROVED', notes=['APPROVED FOR OPERATION'])
        report = self.check_value(answer)
        self.assertFalse(report['ok'])
        self.assertIn('layout.title_block.revision', '\n'.join(report['errors']))
        self.assertIn('layout.title_block.notes', '\n'.join(report['errors']))

    def test_source_locator_is_exact_but_does_not_establish_interpretation(self):
        answer = workflow.reference_answer()
        answer['evidence']['source.txt:L2-L2'] = 'Different source text'
        self.assertFalse(self.check_value(answer)['ok'])
        answer = workflow.reference_answer()
        answer['model']['units'][0]['name'] = 'A deliberately incorrect interpretation'
        # This is the essential limit: matching a real quotation cannot prove its interpretation.
        self.assertTrue(self.check_value(answer)['ok'])
        answer['model']['units'][0]['verification'] = {'status': 'confirmed'}
        self.assertFalse(self.check_value(answer)['ok'])

    def test_changed_source_duplicate_json_and_unsafe_ids_refused(self):
        path = self.answer(workflow.reference_answer())
        path.write_bytes(b'{"model":{},"model":{},"layout":{},"evidence":{}}')
        with self.assertRaisesRegex(workflow.InputError, 'Duplicate JSON'):
            workflow.check(self.packet, path)
        answer = workflow.reference_answer()
        answer['layout']['sheets'][0]['id'] = '../escape'
        self.assertFalse(self.check_value(answer)['ok'])
        (self.packet / 'source.txt').write_bytes(b'Changed evidence')
        with self.assertRaisesRegex(workflow.InputError, 'prepared source changed'):
            self.check_value(workflow.reference_answer())

    def test_tee_and_continuation_conflicts_refused(self):
        branch = json.loads((EXAMPLE / 'branch-answer.json').read_bytes())
        self.packet = self.folder / 'branch-packet'
        workflow.prepare(EXAMPLE / 'branch-source.txt', self.packet)
        branch['layout']['sheets'][0]['routes'][4]['from']['at'] = [1900, 910]
        self.assertFalse(self.check_value(branch)['ok'])
        offpage = json.loads((EXAMPLE / 'offpage-answer.json').read_bytes())
        self.packet = self.folder / 'packet'
        offpage['layout']['sheets'][1]['routes'][0].update(to={'flag': 'IN'}, **{'from': {'unit': 'P-1'}})
        self.assertFalse(self.check_value(offpage)['ok'])


class CatalogProvenanceTests(unittest.TestCase):
    """Synthetic rule copies test provenance, not source authority or engineering adequacy."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='catalog-controls-')
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.packet = self.folder / 'packet'
        workflow.prepare(EXAMPLE / 'source.txt', self.packet)
        self.answer = EXAMPLE / 'result/answer.json'
        self.controls = ROOT / 'examples/from-description/assisted/catalog-controls'

    def catalog(self, label='A', raw=None, name='selected.json'):
        path = self.folder / name
        path.write_bytes((self.controls / f'catalog-{label}.json').read_bytes() if raw is None else raw)
        return path

    def build(self, name, catalog=None):
        out = self.folder / name
        report = workflow.build(self.packet, self.answer, out, catalog=catalog)
        self.assertTrue(report['ok'], report)
        return out

    def snapshot(self, out, raw, selection):
        receipt = json.loads((out / 'build.json').read_bytes())
        sha = hashlib.sha256(raw).hexdigest()
        self.assertEqual(receipt['question_catalog'], {
            'path': 'question_catalog.json', 'sha256_raw': sha, 'selection': selection})
        self.assertEqual((out / 'question_catalog.json').read_bytes(), raw)
        self.assertEqual(receipt['files_sha256']['question_catalog.json'], sha)
        doc = json.loads((out / 'questions/questions.json').read_bytes())
        # shown_path is ROOT-relative for an in-ROOT temp profile, basename otherwise.
        self.assertEqual(Path(doc['catalog']).name, 'question_catalog.json')
        self.assertIn(f"Questions: `{doc['catalog']}`", (out / 'questions/screen.md').read_text(encoding='utf-8'))
        return doc

    def typed(self, value):
        return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(',', ':'))

    def without_path_labels(self, doc):
        return {key: value for key, value in doc.items() if key not in ('catalog', 'source_model')}

    def test_default_snapshot_identity_and_complete_inventory(self):
        raw = (ROOT / 'data/questions.json').read_bytes()
        out = self.build('default')
        self.snapshot(out, raw, 'default')
        receipt = json.loads((out / 'build.json').read_bytes())
        actual = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in out.rglob('*') if p.is_file() and p.name != 'build.json'}
        self.assertEqual(receipt['files_sha256'], actual)
        self.assertEqual((ROOT / 'data/questions.json').read_bytes(), raw)

    def test_custom_catalog_revision_and_retained_replay(self):
        selected = self.catalog()
        a_raw = selected.read_bytes()
        a = self.build('A', selected)
        a_doc = self.snapshot(a, a_raw, 'custom')
        b_raw = (self.controls / 'catalog-B.json').read_bytes()
        selected.write_bytes(b_raw)
        b = self.build('B', selected)
        b_doc = self.snapshot(b, b_raw, 'custom')
        self.assertNotEqual(hashlib.sha256(a_raw).digest(), hashlib.sha256(b_raw).digest())
        e1_a = [q for q in a_doc['questions'] if q['question_id'] == 'E1']
        self.assertTrue(e1_a)
        self.assertTrue(all(q['question'] == 'N104 synthetic catalog A: review the pump basis?' for q in e1_a))
        expected = copy.deepcopy(self.without_path_labels(a_doc))
        for q in expected['questions']:
            if q['question_id'] == 'E1':
                q['question'] = 'N104 synthetic catalog B: review the pump basis?'
        self.assertEqual(self.typed(expected), self.typed(self.without_path_labels(b_doc)))
        selected.unlink()
        replay = self.folder / 'replay'
        proc = subprocess.run([sys.executable, '-B', '-S', str(ROOT / 'scripts/question_engine.py'),
                               '--model', str(a / 'model.json'), '--catalog', str(a / 'question_catalog.json'),
                               '--out', str(replay)], cwd=ROOT, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        replay_doc = json.loads((replay / 'questions.json').read_bytes())
        self.assertEqual(self.typed(self.without_path_labels(replay_doc)),
                         self.typed(self.without_path_labels(a_doc)))
        old_header = f"Model: `{a_doc['source_model']}`. Questions: `{a_doc['catalog']}`."
        new_header = f"Model: `{replay_doc['source_model']}`. Questions: `{replay_doc['catalog']}`."
        screen = (a / 'questions/screen.md').read_text(encoding='utf-8')
        self.assertEqual(screen.count(old_header), 1)
        # Apply exactly the existing bundle's two packaging transforms, not arbitrary cleanup.
        replay_md = (replay / 'screen.md').read_bytes().replace(b'\r\n', b'\n')
        replay_md = replay_md.replace(b'  \n', b'\\\n').decode('utf-8')
        self.assertEqual(screen.replace(old_header, new_header, 1), replay_md)
        self.snapshot(a, a_raw, 'custom')

    def test_crlf_catalog_is_preserved_raw(self):
        raw = (self.controls / 'catalog-A.json').read_bytes().replace(b'\r\n', b'\n')
        crlf = raw.replace(b'\n', b'\r\n')
        self.assertNotEqual(raw, crlf)
        self.assertEqual(self.typed(json.loads(raw)), self.typed(json.loads(crlf)))
        out = self.build('crlf', self.catalog(raw=crlf))
        self.snapshot(out, crlf, 'custom')
        self.assertIn(b'\r\n', (out / 'question_catalog.json').read_bytes())
        self.assertNotIn(b'\r\n', (out / 'questions/screen.md').read_bytes())

    def test_upstream_swap_or_removal_does_not_change_consumed_snapshot(self):
        from unittest.mock import patch
        original_inspect = workflow.inspect_answer
        for remove in (False, True):
            with self.subTest(remove=remove):
                selected = self.catalog(name=f'upstream-{remove}.json')
                a_raw = selected.read_bytes()
                def change_upstream(*args):
                    if remove:
                        selected.unlink()
                    else:
                        selected.write_bytes((self.controls / 'catalog-B.json').read_bytes())
                    return original_inspect(*args)
                with patch.object(workflow, 'inspect_answer', side_effect=change_upstream) as inspected:
                    out = self.build(f'snapshot-{remove}', selected)
                self.assertEqual(inspected.call_count, 1)
                doc = self.snapshot(out, a_raw, 'custom')
                self.assertTrue(any(q['question'] == 'N104 synthetic catalog A: review the pump basis?'
                                    for q in doc['questions']))

    def test_invalid_catalogs_refuse_before_inspection_without_path_or_payload(self):
        from unittest.mock import patch
        invalid = [
            (b'{"SENSITIVE-CONTENT":', 'Question catalog must contain valid finite UTF-8 JSON'),
            (b'{"x":{"a":1,"a":2}}', 'Question catalog must contain valid finite UTF-8 JSON'),
            (b'{"x":NaN}', 'Question catalog must contain valid finite UTF-8 JSON'),
            (b'{"x":1e9999}', 'Question catalog must contain valid finite UTF-8 JSON'),
            (b'{"x":"\xff"}', 'Question catalog must contain valid finite UTF-8 JSON'),
            (b'{"x":"\\ud800"}', 'Question catalog must contain valid finite UTF-8 JSON'),
            (b'\xef\xbb\xbf{}', 'Question catalog must be UTF-8 without a BOM'),
            (b'[]', 'Question catalog must be a JSON object'),
            (b'null', 'Question catalog must be a JSON object'),
            (b'false', 'Question catalog must be a JSON object'),
            (b'0', 'Question catalog must be a JSON object')]
        for i, (raw, message) in enumerate(invalid):
            with self.subTest(i=i):
                selected = self.catalog(raw=raw, name='PRIVATE-SOURCE-NAME.json')
                out = self.folder / f'invalid-{i}'
                with patch.object(workflow, 'inspect_answer') as inspected:
                    with self.assertRaises(workflow.InputError) as raised:
                        workflow.build(self.packet, self.answer, out, catalog=selected)
                    inspected.assert_not_called()
                self.assertEqual(str(raised.exception), message)
                self.assertNotIn('PRIVATE-SOURCE-NAME', str(raised.exception))
                self.assertNotIn(str(self.folder), str(raised.exception))
                self.assertFalse(out.exists())
                self.assertEqual(selected.read_bytes(), raw)

    def test_acquisition_failures_are_safe_before_inspection(self):
        from unittest.mock import patch
        selected = self.catalog(name='PRIVATE-SOURCE-NAME.json')
        original_open = Path.open
        message = 'Cannot read the selected question catalog; check the file and permissions'
        class BrokenRead(io.BytesIO):
            def __init__(self, payload):
                super().__init__(payload)
                self.reads = 0
            def read(self, size=-1):
                self.reads += 1
                if self.reads == 1:
                    return b'{'
                raise OSError('PRIVATE-MIDREAD-PAYLOAD')
        def failed_open(path, *args, **kwargs):
            if Path(path) == selected:
                raise PermissionError('PRIVATE-PERMISSION-PAYLOAD')
            return original_open(path, *args, **kwargs)
        def broken_open(path, *args, **kwargs):
            return BrokenRead(b'{') if Path(path) == selected else original_open(path, *args, **kwargs)
        for kind in ('missing', 'directory', 'permission', 'read'):
            with self.subTest(kind=kind):
                path = self.folder / 'missing-PRIVATE.json' if kind == 'missing' else selected
                if kind == 'directory':
                    path = self.folder
                opener = failed_open if kind == 'permission' else broken_open if kind == 'read' else original_open
                out = self.folder / f'acquisition-{kind}'
                with patch.object(Path, 'open', opener), patch.object(workflow, 'inspect_answer') as inspected:
                    with self.assertRaises(workflow.InputError) as raised:
                        workflow.build(self.packet, self.answer, out, catalog=path)
                    inspected.assert_not_called()
                self.assertEqual(str(raised.exception), message)
                self.assertIsNone(raised.exception.__cause__)
                self.assertTrue(raised.exception.__suppress_context__)
                self.assertFalse(out.exists())

    def test_catalog_limit_positive_short_reads_and_eof(self):
        from unittest.mock import patch
        cap = 8 * 1024 * 1024
        selected = self.catalog()
        raw = selected.read_bytes()
        original_open = Path.open
        class InspectionReached(Exception):
            pass
        class ShortRead(io.BytesIO):
            def __init__(self, payload):
                super().__init__(payload)
                self.requests = []
                self.delivered = 0
                self.eof_seen = False
            def read(stream, size=-1):
                self.assertGreater(size, 0)
                self.assertLessEqual(size, 65536)
                stream.requests.append(size)
                result = super(ShortRead, stream).read(min(size, 17003))
                stream.delivered += len(result)
                stream.eof_seen |= result == b''
                return result
        for size in (len(raw), cap, cap + 1):
            with self.subTest(size=size):
                payload = raw + b' ' * (size - len(raw))
                reader = ShortRead(payload)
                opens = []
                def selected_open(path, *args, **kwargs):
                    if Path(path) == selected:
                        opens.append(path)
                        return reader
                    return original_open(path, *args, **kwargs)
                out = self.folder / f'limit-{size}'
                with patch.object(Path, 'open', selected_open), patch.object(
                        workflow, 'inspect_answer', side_effect=InspectionReached) as inspected:
                    if size > cap:
                        with self.assertRaisesRegex(workflow.InputError, '^Question catalog exceeds the input limit \\(8388608 bytes\\)$'):
                            workflow.build(self.packet, self.answer, out, catalog=selected)
                        inspected.assert_not_called()
                    else:
                        with self.assertRaises(InspectionReached):
                            workflow.build(self.packet, self.answer, out, catalog=selected)
                        self.assertEqual(inspected.call_count, 1)
                self.assertEqual(len(opens), 1)
                self.assertEqual(reader.delivered, size)
                self.assertEqual(reader.eof_seen, size <= cap)
                self.assertFalse(out.exists())

    def test_build_cli_custom_catalog_and_early_refusal(self):
        selected = self.catalog(name='PRIVATE-SOURCE-NAME space Ω `.json')
        raw = selected.read_bytes()
        out = self.folder / 'cli-result'
        args = [sys.executable, '-B', str(SCRIPT), 'build', '--packet', str(self.packet),
                '--answer', str(self.answer), '--catalog', str(selected), '--out', str(out)]
        proc = subprocess.run(args, cwd=ROOT, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(json.loads(proc.stdout)['ok'])
        self.snapshot(out, raw, 'custom')
        for relative in ('build.json', 'questions/questions.json', 'questions/screen.md', 'REVIEW.md'):
            text = (out / relative).read_text(encoding='utf-8')
            if relative.endswith('.json'):
                # Check decoded JSON strings too: escaped spelling must not hide source-path metadata.
                text = json.dumps(json.loads(text), ensure_ascii=False)
            self.assertNotIn(selected.name, text, relative)
            self.assertNotIn(str(selected), text, relative)
        selected.write_bytes(b'\xef\xbb\xbf{}')
        failed = self.folder / 'cli-refused'
        proc = subprocess.run([*args[:-1], str(failed)], cwd=ROOT, capture_output=True)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertFalse(report['ok'])
        self.assertEqual(report['errors'], ['Question catalog must be UTF-8 without a BOM'])
        self.assertNotIn(b'PRIVATE-SOURCE-NAME', proc.stdout + proc.stderr)
        self.assertFalse(failed.exists())
        import contextlib
        for action, extra in (
                ('prepare', ['--source', str(EXAMPLE / 'source.txt'), '--out', str(self.folder / 'unused-prepare')]),
                ('check', ['--packet', str(self.packet), '--answer', str(self.answer)])):
            with self.subTest(action=action), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as refused:
                    workflow.main([action, *extra, '--catalog', str(selected)])
                self.assertEqual(refused.exception.code, 2)
        self.assertFalse((self.folder / 'unused-prepare').exists())

    def test_native_refusal_and_existing_destination_preserve_inputs(self):
        from unittest.mock import patch
        selected = self.catalog()
        before = {p: p.read_bytes() for p in (selected, self.answer, self.packet / 'source.txt')}
        out = self.folder / 'native-refused'
        results = [subprocess.CompletedProcess([], 0, b'', b''),
                   subprocess.CompletedProcess([], 2, b'Controlled native refusal', b'')]
        with patch.object(workflow.subprocess, 'run', side_effect=results):
            report = workflow.build(self.packet, self.answer, out, catalog=selected)
        self.assertFalse(report['ok'])
        self.assertFalse(out.exists())
        import contextlib
        timeout_out = self.folder / 'timeout-refused'
        captured = io.StringIO()
        with patch.object(workflow.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['synthetic'], 60)):
            with contextlib.redirect_stdout(captured):
                rc = workflow.main(['build', '--packet', str(self.packet), '--answer', str(self.answer),
                                    '--catalog', str(selected), '--out', str(timeout_out)])
        self.assertEqual(rc, 2)
        self.assertEqual(json.loads(captured.getvalue()), {'ok': False, 'errors': [
            'A native generation step exceeded 60 seconds; no output was published.']})
        self.assertFalse(timeout_out.exists())
        existing = self.folder / 'existing'
        existing.mkdir()
        sentinel = existing / 'sentinel.bin'
        sentinel.write_bytes(b'KEEP EXISTING DESTINATION')
        with patch.object(workflow, 'inspect_answer') as inspected:
            with self.assertRaises(workflow.InputError):
                workflow.build(self.packet, self.answer, existing, catalog=selected)
            inspected.assert_not_called()
        self.assertEqual({p.name: p.read_bytes() for p in existing.iterdir()},
                         {'sentinel.bin': b'KEEP EXISTING DESTINATION'})
        for path, raw in before.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_current_default_freshness_and_snapshot_tampering(self):
        from unittest.mock import patch
        import shutil
        out = self.build('default-for-freshness')
        shadow = self.folder / 'publication-control'
        (shadow / 'scripts').mkdir(parents=True)
        (shadow / 'data').mkdir()
        # Synthetic checker fixture: the same self-consistent bundle fills both named slots.
        # It is not represented as a new actual MGPI build.
        for name in ('description_workflow.py', 'draw_pid_from_model.py', 'generate.py',
                     'question_engine.py', 'graph_export.py'):
            shutil.copyfile(ROOT / 'scripts' / name, shadow / 'scripts' / name)
        shutil.copyfile(ROOT / 'data/questions.json', shadow / 'data/questions.json')
        for case in ('assisted', 'mgpi'):
            shutil.copytree(out, shadow / 'examples/from-description' / case / 'result')
        validator = DescriptionWorkflowTests('test_committed_bundles_bind_current_producers_and_complete_artifacts')
        with patch.dict(globals(), {'ROOT': shadow}):
            validator.test_committed_bundles_bind_current_producers_and_complete_artifacts()
            (shadow / 'data/questions.json').write_bytes((self.controls / 'catalog-B.json').read_bytes())
            with self.assertRaisesRegex(AssertionError, 'stale question catalog'):
                validator.test_committed_bundles_bind_current_producers_and_complete_artifacts()
            shutil.copyfile(out / 'question_catalog.json', shadow / 'data/questions.json')
            artifact = shadow / 'examples/from-description/assisted/result/question_catalog.json'
            artifact.write_bytes(artifact.read_bytes() + b' ')
            with self.assertRaises(AssertionError):
                validator.test_committed_bundles_bind_current_producers_and_complete_artifacts()



if __name__ == '__main__':
    unittest.main()
