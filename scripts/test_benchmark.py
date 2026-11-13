"""Community benchmark controls: failures, frozen cohorts, source integrity and reproducible scores."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

import benchmark as b

ROOT = Path(__file__).resolve().parent.parent


class BenchmarkTests(unittest.TestCase):
    def test_historical_recipe_relocation_preserves_saved_attempts(self):
        """Current registration may relocate frozen recipes; it must not rewrite what the old attempt did."""
        for stem in ('description-controls', 'mgpi-development'):
            with self.subTest(suite=stem):
                original = b.read_json(ROOT / f'benchmarks/{stem}.json')
                current = b.read_json(ROOT / f'benchmarks/{stem}-recipe-preserved.json')
                self.assertEqual({k:v for k,v in original.items() if k != 'runs'},
                                 {k:v for k,v in current.items() if k != 'runs'})
                self.assertEqual(len(original['runs']), len(current['runs']))
                for old_path, new_path in zip(original['runs'], current['runs']):
                    self.assertNotEqual(old_path, new_path)
                    old, new = b.read_json(ROOT / old_path), b.read_json(ROOT / new_path)
                    self.assertEqual({k:v for k,v in old.items() if k not in ('recipe','provenance')},
                                     {k:v for k,v in new.items() if k not in ('recipe','provenance')})
                    self.assertTrue(new['provenance'].startswith(old['provenance']))
                    self.assertIn('metadata relocation', new['provenance'])
                    self.assertEqual(len(old['recipe']), len(new['recipe']))
                    for before, after in zip(old['recipe'], new['recipe']):
                        self.assertEqual({k:v for k,v in before.items() if k != 'path'},
                                         {k:v for k,v in after.items() if k != 'path'})
                        # The scorer itself validates the archived content against the historical fingerprint.
                        b.reference(ROOT, after)
                        if before['path'] != after['path']:
                            self.assertTrue(after['path'].startswith('benchmarks/recipes/'))
                            self.assertTrue(after['path'].endswith('.txt'))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='benchmark-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.answer = {'units': [{'id': 'TK-1', 'type': 'tank'}],
                       'streams': [{'id': 'S1', 'from': 'BL', 'to': 'TK-1'}]}
        self.save('input.txt', {'description': 'TK-1 tank, S1 from BL to TK-1. Synthetic.'})
        self.save('expected.json', self.answer)
        self.save('key.json', {'facts': [json.loads(f) for f in sorted(b.native_facts(self.answer))]})
        self.save('prompt.json', {'instructions': 'Use source-backed literal native fields.'})
        self.save('answer.json', self.answer)
        self.case = {'id': 'case1', 'family': 'synthetic', 'split': 'synthetic-control',
                     'evidence': 'authored scorer control', 'source_url': 'repository:fixture',
                     'license': 'synthetic fixture', 'key_author': 'test author',
                     'files': {k: self.ref(p) for k, p in [('input', 'input.txt'), ('key', 'key.json'), ('expected', 'expected.json')]}}
        self.run = {'id': 'run1', 'model': {'provider': 'none', 'id': 'test-model', 'version': 'test-v1'},
                    'interface': 'fixture', 'method': 'reference', 'configuration': {}, 'ran_at': '2026-10-30',
                    'provenance': 'No model call.', 'recipe': [self.ref('prompt.json')], 'cases': ['case1'],
                    'predictions': {'case1': self.ref('answer.json')}}
        self.suite = {'id': 'test', 'version': '1', 'task': 'description-facts', 'protocol': 'literal fields',
                      'registration': 'synthetic software control', 'cases': [self.case], 'runs': ['run.json']}

    def save(self, path, value):
        target = self.root / path
        target.write_bytes(b.encoded(value))
        return target

    def ref(self, path):
        return {'path': path, 'sha256': b.file_hash(self.root / path)}

    def evaluate(self):
        self.save('run.json', self.run)
        return b.evaluate(self.save('suite.json', self.suite), self.root)

    def test_perfect_empty_wrong_and_unscored_names(self):
        perfect = self.evaluate()['results'][0]
        self.assertEqual(perfect['metrics']['facts']['f1'], 1)
        self.assertEqual(perfect['rows'][0]['status'], 'ok')
        wrong = copy.deepcopy(self.answer)
        wrong['streams'][0]['to'] = 'NO-SUCH-UNIT'
        self.save('answer.json', wrong)
        self.run['predictions']['case1'] = self.ref('answer.json')
        self.assertLess(self.evaluate()['results'][0]['metrics']['facts']['f1'], 1)
        self.save('answer.json', {'units': []})
        self.run['predictions']['case1'] = self.ref('answer.json')
        self.assertEqual(self.evaluate()['results'][0]['metrics']['facts']['f1'], 0)
        answer = copy.deepcopy(self.answer)
        answer['units'][0]['name'] = 'Deliberately incorrect, outside this scoring subset'
        self.save('answer.json', answer)
        self.run['predictions']['case1'] = self.ref('answer.json')
        self.assertEqual(self.evaluate()['results'][0]['metrics']['facts']['f1'], 1)

    def test_failed_missing_and_malformed_attempts_are_not_dropped(self):
        for value in ({'prediction': None, 'error': 'failed'}, {'units': 'invalid'}, {'a': 1, 'prediction': []}):
            with self.subTest(value=value):
                self.save('answer.json', value)
                self.run['predictions']['case1'] = self.ref('answer.json')
                row = self.evaluate()['results'][0]
                self.assertEqual(row['metrics']['facts']['f1'], 0)
                self.assertNotEqual(row['rows'][0]['status'], 'ok')
        self.run['predictions'] = {}
        self.assertEqual(self.evaluate()['results'][0]['rows'][0]['status'], 'missing')
        self.assertEqual(self.evaluate()['results'][0]['metrics']['facts']['f1'], 0)

    def test_new_unattempted_case_retains_old_cohort(self):
        before = self.evaluate()['results'][0]
        new = copy.deepcopy(self.case)
        new['id'] = 'case2'
        self.suite['cases'].append(new)
        after = self.evaluate()['results'][0]
        self.assertEqual(before['cohort'], after['cohort'])
        self.assertEqual(after['not_attempted'], ['case2'])
        self.run['cases'].append('case2')
        self.run['predictions']['case2'] = self.ref('answer.json')
        expanded = self.evaluate()['results'][0]
        self.assertNotEqual(before['cohort'], expanded['cohort'])
        self.assertEqual(expanded['case_count'], 2)

    def test_changed_keys_prompt_and_answers_refuse(self):
        for name in ('key.json', 'prompt.json', 'answer.json'):
            original = (self.root / name).read_bytes()
            (self.root / name).write_bytes(original + b' ')
            with self.assertRaisesRegex(ValueError, 'Stale file fingerprint'):
                self.evaluate()
            (self.root / name).write_bytes(original)

    def test_source_newlines_preserve_cohort_and_report(self):
        from unittest.mock import patch
        sources = ['benchmark.py', 'score_pid2graph.py', 'evaluate_vendor.py',
                   'replicate_stats.py', 'score_tags.py', 'test_scorer_controls.py']
        variants = []
        for newline, folder in ((b'\n', 'lf'), (b'\r\n', 'crlf')):
            directory = self.root / folder
            directory.mkdir()
            for name in sources:
                raw = (ROOT / 'scripts' / name).read_bytes().replace(b'\r\n', b'\n')
                (directory / name).write_bytes(raw.replace(b'\n', newline))
            with patch.object(b, '__file__', str(directory / 'benchmark.py')):
                variants.append(b.evaluate(ROOT / 'benchmarks/open100-validation.json', ROOT))
        self.assertEqual(b.encoded(variants[0]), b.encoded(variants[1]))
        self.assertEqual(b.markdown(variants[0]), b.markdown(variants[1]))
        for name in sources:
            self.assertEqual(b.file_hash(self.root / 'lf' / name), b.file_hash(self.root / 'crlf' / name))
        # Source edits still change the fingerprint; binary newlines stay significant.
        source = self.root / 'crlf' / 'score_tags.py'
        source.write_bytes(source.read_bytes() + b'# changed\r\n')
        self.assertNotEqual(b.file_hash(source), b.file_hash(self.root / 'lf' / source.name))
        for directory, raw in (('lf', b'a\nb'), ('crlf', b'a\r\nb')):
            (self.root / directory / 'binary.png').write_bytes(raw)
        self.assertNotEqual(b.file_hash(self.root / 'lf/binary.png'), b.file_hash(self.root / 'crlf/binary.png'))

    def test_replicate_identity_model_versions_and_configuration_stay_separate(self):
        run2 = copy.deepcopy(self.run)
        run2['id'] = 'run2'
        self.suite['runs'].append('run2.json')
        self.save('run2.json', run2)
        with self.assertRaisesRegex(ValueError, 'reused'):
            self.evaluate()
        self.save('answer2.json', self.answer)
        run2['predictions']['case1'] = self.ref('answer2.json')
        self.save('run2.json', run2)
        self.assertEqual(self.evaluate()['summary'][0]['replicates'], 2)
        run2['model']['version'] = 'test-v2'
        self.save('run2.json', run2)
        self.assertEqual(len(self.evaluate()['summary']), 2)
        run2['model']['version'] = 'test-v1'
        run2['configuration'] = {'different_prompt_mode': True}
        self.save('run2.json', run2)
        self.assertEqual(len(self.evaluate()['summary']), 2)

    def test_family_split_and_evidence_are_not_pooled(self):
        new = copy.deepcopy(self.case)
        new.update(id='case2', family='another-family', split='development', evidence='different truth')
        self.suite['cases'].append(new)
        self.run['cases'].append('case2')
        self.run['predictions']['case2'] = self.ref('answer.json')
        report = self.evaluate()
        self.assertEqual(len(report['results']), 2)
        self.assertEqual(len({r['cohort'] for r in report['results']}), 2)

    def test_bad_key_and_path_escape_refuse_before_scoring(self):
        self.save('key.json', {'facts': [['not-a-section', 'x', 'y', 1]]})
        self.case['files']['key'] = self.ref('key.json')
        with self.assertRaisesRegex(ValueError, 'Fact key'):
            self.evaluate()
        with self.assertRaisesRegex(ValueError, 'escapes'):
            b.local(self.root, '../outside.json')

    def test_schema_label_cannot_disable_recorded_metadata_binding(self):
        case = {'files': {'input': {'sha256': 'input-fingerprint'}}}
        self.run.update(recorded_tool='test-cli', configuration={'tiles': '2x2', 'overlap': 0.15, 'trace': 'replace'})
        self.run['recipe'][0]['role'] = 'main_prompt'
        self.save('preface.json', {'instructions': 'Tile-specific preface'})
        preface = dict(self.ref('preface.json'), role='tile_preface')
        self.run['recipe'].append(preface)
        good = {'prediction': self.answer, 'model': 'test-model', 'tool': 'test-cli',
                'image_sha256': 'input-fingerprint', 'prompt_sha256': self.run['recipe'][0]['sha256'],
                'tiling': {'grid': '2x2', 'overlap': 0.15, 'preface_sha256': preface['sha256']}, 'tracer': {'mode': 'replace'}}
        for schema in ('pid-prediction/1', 'unsupported-schema', None):
            record = copy.deepcopy(good)
            if schema:
                record['schema'] = schema
            b.check_saved_metadata(record, self.run, case)
            for field, value in [('model', 'other-model'), ('tool', 'other-cli'),
                                 ('image_sha256', 'wrong-input'), ('prompt_sha256', 'wrong-prompt'),
                                 ('tiling', {'grid': '1x1'}), ('tracer', {'mode': 'augment'})]:
                wrong = dict(record, **{field: value})
                with self.subTest(schema=schema, field=field), self.assertRaises(b.ProvenanceError):
                    b.check_saved_metadata(wrong, self.run, case)
            for wrong_preface in ('0' * 64, self.run['recipe'][0]['sha256']):
                wrong = dict(record, tiling=dict(record['tiling'], preface_sha256=wrong_preface))
                with self.assertRaisesRegex(b.ProvenanceError, 'tile preface'):
                    b.check_saved_metadata(wrong, self.run, case)
        # A failed attempt before metadata was captured still scores as failed, not omitted.
        b.check_saved_metadata({'schema': 'pid-prediction/1', 'prediction': None, 'error': 'timeout'}, self.run, case)
        with self.assertRaisesRegex(b.ProvenanceError, 'envelope needs prediction'):
            b.check_saved_metadata({'schema': 'pid-prediction/1', 'symbols': [], 'connections': []}, self.run, case)

    def test_flattened_drawing_envelope_cannot_bypass_saved_identity(self):
        suite = b.read_json(ROOT / 'benchmarks/open100-validation.json')
        case = copy.deepcopy(suite['cases'][0])
        run = b.read_json(ROOT / suite['runs'][0])
        record = b.read_json(ROOT / run['predictions'][case['id']]['path'])
        for kind, ref in case['files'].items():
            name = kind + Path(ref['path']).suffix
            (self.root / name).write_bytes((ROOT / ref['path']).read_bytes())
            case['files'][kind] = self.ref(name)
        recipe = []
        for i, ref in enumerate(run['recipe']):
            name = 'recipe-' + str(i) + '.md'
            (self.root / name).write_bytes((ROOT / ref['path']).read_bytes())
            recipe.append(dict(self.ref(name), **({'role': ref['role']} if 'role' in ref else {})))
        run.update(cases=[case['id']], recipe=recipe, predictions={})
        self.run = run
        self.suite = dict(suite, cases=[case], runs=['run.json'])
        flat = dict(record)
        flat.update(flat.pop('prediction'))
        flat.update(model='wrong-model', image_sha256='wrong-input', prompt_sha256='wrong-prompt')
        for schema in ('pid-prediction/1', 'vendor-unknown', None):
            candidate = dict(flat)
            if schema:
                candidate['schema'] = schema
            else:
                candidate.pop('schema', None)
            self.save('flat.json', candidate)
            self.run['predictions'] = {case['id']: self.ref('flat.json')}
            with self.subTest(schema=schema), self.assertRaises(b.ProvenanceError):
                self.evaluate()
        self.save('flat.json', record['prediction'])
        self.run['predictions'] = {case['id']: self.ref('flat.json')}
        result = self.evaluate()['results'][0]
        self.assertEqual(result['rows'][0]['status'], 'ok')
        self.assertGreater(result['counts']['symbols_rough']['tp'], 0)

    def test_same_file_hardlink_is_not_another_replicate(self):
        alias = self.root / 'answer-alias.json'
        try:
            os.link(self.root / 'answer.json', alias)
        except OSError as exc:
            self.skipTest('This filesystem cannot create a hardlink: ' + str(exc))
        run2 = copy.deepcopy(self.run)
        run2['id'] = 'hardlink-run'
        run2['predictions']['case1'] = self.ref(alias.name)
        self.save('run2.json', run2)
        self.suite['runs'].append('run2.json')
        with self.assertRaisesRegex(ValueError, 'reused'):
            self.evaluate()

    def test_report_check_refuses_changed_report_and_does_not_overwrite(self):
        self.evaluate()
        args = ['--suite', str(self.root / 'suite.json'), '--root', str(self.root), '--out', str(self.root / 'report')]
        self.assertEqual(b.main(args), 0)
        original = (self.root / 'report.json').read_bytes()
        self.assertEqual(b.main(args + ['--check']), 0)
        self.assertEqual(b.main(args), 2)
        self.assertEqual((self.root / 'report.json').read_bytes(), original)
        (self.root / 'report.md').write_text('Changed report', encoding='utf-8')
        self.assertEqual(b.main(args + ['--check']), 2)

    def test_historical_drawing_counts_match_existing_frozen_scorer(self):
        suite = b.read_json(ROOT / 'benchmarks/open100-validation.json')
        # Two separate drawings make an accidental last-case fingerprint reuse observable.
        suite['cases'] = suite['cases'][:2]
        suite['runs'] = suite['runs'][:1]
        run = b.read_json(ROOT / suite['runs'][0])
        run['cases'] = [c['id'] for c in suite['cases']]
        run['predictions'] = {k: v for k, v in run['predictions'].items() if k in run['cases']}
        local_run = ROOT / 'benchmarks/runs' / Path(run['id'] + '.json')
        # Evaluate an in-memory selected run using mock only for run-file lookup; scores read real keys/answers.
        from unittest.mock import patch
        original = b.read_json
        suite_path = self.save('historical-suite.json', suite)
        def read(path):
            return run if path == (ROOT / suite['runs'][0]).resolve() else original(path)
        with patch.object(b, 'read_json', side_effect=read):
            report = b.evaluate(suite_path, ROOT)
        import score_pid2graph as scorer
        for row, case in zip(report['results'][0]['rows'], suite['cases']):
            pred = original(ROOT / run['predictions'][case['id']]['path'])['prediction']
            expected = scorer.score(ROOT / case['files']['key']['path'], pred, ROOT / case['files']['input']['path'])
            self.assertEqual(row['counts']['networks']['tp'], expected['connections']['tp'])
            self.assertEqual(row['counts']['symbols_rough']['tp'], expected['rough']['classified']['tp'])


class TagBenchmarkTests(unittest.TestCase):
    """New task controls; legacy benchmark tests above remain unchanged."""

    def setUp(self):
        import struct
        self.tmp = tempfile.TemporaryDirectory(prefix='tag-benchmark-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'input.png').write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + struct.pack('>II', 1000, 1000))
        (self.root / 'LICENSE').write_bytes(b'Synthetic software-control material.\r\n')
        (self.root / 'recipe.txt').write_bytes(b'Synthetic fixture; no inference.\n')
        head = '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">'
        head += ''.join(f'<key id="{k}" for="node" attr.name="{k}"/>' for k in ('label','xmin','xmax','ymin','ymax')) + '<graph>'
        self.symbols = [('V1','valve',[10,10,20,20],'FV-101'), ('I1','instrumentation',[100,10,110,20],'FIC 101'),
                        ('P1','pump',[200,10,210,20],'P4711')]
        nodes = ''
        for ident, cls, box, tag in self.symbols:
            fields = dict(label=cls,xmin=box[0],ymin=box[1],xmax=box[2],ymax=box[3])
            nodes += f'<node id="{ident}">' + ''.join(f'<data key="{k}">{v}</data>' for k,v in fields.items()) + '</node>'
        (self.root / 'key.graphml').write_text(head + nodes + '</graph></graphml>',encoding='utf-8')
        self.save('tags.json', {'tags': {ident:tag for ident,cls,box,tag in self.symbols}})
        self.save('list.json', {'items': [{'identifier':'P0020','class':'instrumentation','list':'instrument'},
            {'identifier':'AB020','class':'valve','list':'valve'}, {'identifier':'BA100','class':'tank','list':'equipment'}]})
        self.answer = {'symbols':[{'id':ident,'class':cls,'box':box,'tag':tag} for ident,cls,box,tag in self.symbols]}
        self.save('answer.json',self.answer)
        self.case = {'id':'one','family':'synthetic','split':'synthetic-control','evidence':'authored software control',
            'source_url':'repository:synthetic','license':'synthetic','key_author':'explicit synthetic boxes/text',
            'tag_key_kind':'geometry','files':{role:self.ref(name) for role,name in [('input','input.png'),('key','key.graphml'),('tags','tags.json')]}}
        self.run = {'id':'one','model':{'provider':'none','id':'fixture','version':'1'},'interface':'saved fixture',
            'method':'synthetic reference','configuration':{},'ran_at':'2026-10-31','provenance':'No model call.',
            'recipe':[dict(self.ref('recipe.txt'),role='main_prompt')],'cases':['one'],'predictions':{'one':self.ref('answer.json')}}
        self.suite = {'id':'tags','version':'1','task':'tag-reading','protocol':'Synthetic fixed controls',
            'registration':'synthetic-control, no model capability claim','cases':[self.case],'runs':['run.json']}
        self.refresh()

    def save(self,name,value):
        path=self.root/name;path.write_bytes(b.encoded(value));return path

    def ref(self,name):
        return {'path':name,'sha256':b.file_hash(self.root/name)}

    def refresh(self):
        import hashlib
        artifacts=[]
        for role,ref in self.case['files'].items():
            ref['sha256']=b.file_hash(self.root/ref['path'])
            raw=(self.root/ref['path']).read_bytes()
            artifacts.append({'path':ref['path'],'role':role,'raw_sha256':hashlib.sha256(raw).hexdigest(),
                'size_bytes':len(raw),'source_paths':['synthetic-source']})
        raw=(self.root/'LICENSE').read_bytes()
        self.provenance={'schema':'tag-source-provenance-1','source':{'repository':'repository:synthetic','revision':'1',
            'license':'synthetic','attribution':'Authored fixture, not a model result.','originals':[{'path':'synthetic-source',
                'url':'repository:synthetic','raw_sha256':'0'*64,'size_bytes':0}]},
            'license':{'path':'LICENSE','raw_sha256':hashlib.sha256(raw).hexdigest(),'size_bytes':len(raw)},
            'artifacts':artifacts,'derivation':{'historical_producing_converter':'not applicable, synthetic',
                'original_historical_key_bytes':'not applicable, synthetic','limits':'Software controls only.',
                'render_parameters':{'dimensions':[1000,1000]},'current_associated_files':[self.ref('recipe.txt')]}}
        self.save('provenance.json',self.provenance)
        self.case['source_provenance']=self.ref('provenance.json')

    def evaluate(self):
        self.save('run.json',self.run)
        return b.evaluate(self.save('suite.json',self.suite),self.root)

    def replace_answer(self,value):
        self.save('answer.json',value);self.run['predictions']['one']=self.ref('answer.json')

    def use_list(self):
        self.case['tag_key_kind']='taglist'
        self.case['files']={role:self.ref(name) for role,name in [('input','input.png'),('key','list.json')]}
        self.refresh()

    def test_geometry_exact_counts_and_null_found_accuracy(self):
        row=self.evaluate()['results'][0]
        self.assertEqual(row['counts']['strict'],{'correct':3,'wrong':0,'no_tag':0,'missed':0,'found':3,'with_truth':3})
        self.assertEqual(row['metrics']['strict_end_to_end_recall'],1)
        self.run['predictions']={}
        row=self.evaluate()['results'][0]
        self.assertEqual(row['rows'][0]['status'],'missing')
        self.assertEqual(row['counts']['strict']['missed'],3)
        self.assertIsNone(row['metrics']['strict_accuracy_on_found'])
        values=self.evaluate()['summary'][0]['metrics']['strict_accuracy_on_found']
        self.assertIsNone(values['mean']);self.assertEqual((values['defined_replicates'],values['total_replicates']),(0,1))

    def test_wrong_no_tag_and_class_agnostic_matching(self):
        answer=copy.deepcopy(self.answer)
        answer['symbols'][0]['tag']='FV-999'
        answer['symbols'][1]['tag']=None
        answer['symbols'][2]['class']='tank'
        self.replace_answer(answer)
        row=self.evaluate()['results'][0]
        self.assertEqual((row['counts']['strict']['correct'],row['counts']['strict']['wrong'],row['counts']['strict']['no_tag']),(1,1,1))

    def test_geometry_ids_refuse_across_all_rows_without_repair(self):
        for extra in ({'id':'V1','class':'connector','tag':'FV-101'}, {'id':1,'tag':'FV-101'},
                      {'id':'','tag':'FV-101'}, {'id':'  ','tag':'FV-101'}, {'class':'connector'}):
            with self.subTest(extra=extra):
                answer=copy.deepcopy(self.answer);answer['symbols'].append(extra);self.replace_answer(answer)
                raw=(self.root/'answer.json').read_bytes();row=self.evaluate()['results'][0]
                self.assertEqual(row['rows'][0]['status'],'invalid-answer')
                self.assertEqual(row['counts']['strict']['missed'],3)
                self.assertEqual((self.root/'answer.json').read_bytes(),raw)

    def test_taglist_substring_class_share_and_no_id_restriction(self):
        self.use_list()
        self.replace_answer({'symbols':[{'id':'','tag':'PI P0020 AB-020 BA100','class':'general'},
                                       {'id':'','tag':None,'class':'tank'}]})
        row=self.evaluate()['results'][0]
        self.assertEqual(row['counts']['all'],{'listed':3,'found':3,'found_with_list_class':0})
        self.assertEqual(row['metrics'],{'identifier_recall':1,'found_identifier_class_agreement':0})
        text=b.markdown(self.evaluate())
        self.assertNotIn('Mean F1',text);self.assertNotIn('precision',row['metrics'])

    def test_pooled_rates_and_mode_buckets_never_mix(self):
        import benchmark_tags as tag
        first={'strict':dict(correct=1,wrong=0,no_tag=0,missed=0,found=1,with_truth=1),
               'lenient':dict(correct=1,wrong=0,no_tag=0,missed=0,found=1,with_truth=1)}
        second={'strict':dict(correct=0,wrong=0,no_tag=0,missed=3,found=0,with_truth=3),
                'lenient':dict(correct=0,wrong=0,no_tag=0,missed=3,found=0,with_truth=3)}
        rates,_=tag.rates('geometry',tag.pooled('geometry',[first,second]))
        self.assertEqual(rates['strict_end_to_end_recall'],0.25)
        self.assertEqual(rates['strict_accuracy_on_found'],1)
        suite=b.read_json(ROOT/'benchmarks/tag-reading-development.json')
        self.assertEqual({case['tag_key_kind'] for case in suite['cases']},{'geometry','taglist'})

    def test_keys_validate_before_any_model_answer(self):
        from unittest.mock import patch
        for value in (17,{},'   '):
            with self.subTest(value=value):
                self.save('tags.json',{'tags':{'V1':value}});self.refresh()
                self.run['predictions']={}
                with self.assertRaises(ValueError):self.evaluate()
        self.save('tags.json',{'tags':{'V1':'FV-101','I1':None,'P1':'','missing':'OUTSIDE'}});self.refresh()
        report=self.evaluate()
        self.assertEqual(report['controls']['one']['key_admission']['eligible_truth'],1)
        self.assertEqual(len(report['controls']['one']['key_admission']['excluded_truth']),3)

    def test_non_scored_zero_area_does_not_enter_truth(self):
        path=self.root/'key.graphml';text=path.read_text()
        connector='<node id="J"><data key="label">connector</data><data key="xmin">0</data><data key="ymin">0</data><data key="xmax">0</data><data key="ymax">0</data></node>'
        path.write_text(text.replace('</graph>',connector+'</graph>'))
        self.refresh()
        row=self.evaluate()['results'][0]
        self.assertEqual(row['counts']['strict']['correct'],3)

    def test_list_bad_keys_and_explicit_cross_list_overlap(self):
        self.use_list()
        for items in ([],[{'identifier':'---','list':'x','class':'valve'}],
                      [{'identifier':'A','list':'x','class':'valve'}]*2):
            self.save('list.json',{'items':items});self.refresh()
            with self.assertRaises(ValueError):self.evaluate()
        self.save('list.json',{'items':[{'identifier':'AB001','class':'valve','list':'valve'},
                                      {'identifier':'AB001','class':'instrumentation','list':'instrument'}]})
        self.refresh()
        with self.assertRaises(ValueError):self.evaluate()
        self.case['taglist_overlap_note']='Explicit same identifier in two sourced list roles; not two physical assets.'
        self.replace_answer({'symbols':[{'tag':'AB001','class':'valve'}]})
        self.assertEqual(self.evaluate()['results'][0]['counts']['all'],{'listed':2,'found':2,'found_with_list_class':1})

    def test_failed_and_malformed_attempts_keep_truth_denominators(self):
        for answer,status in (({'prediction':self.answer,'error':'failed'},'failed'),
                              ({'prediction':None,'parse_error':'unreadable'},'failed'),
                              ({'symbols':[None]},'invalid-answer'),({'symbols':'bad'},'invalid-answer')):
            self.replace_answer(answer)
            row=self.evaluate()['results'][0]
            self.assertEqual(row['rows'][0]['status'],status)
            self.assertEqual(row['counts']['strict']['missed'],3)
        (self.root/'answer.json').write_bytes(b'{"symbols":[],"symbols":[]}')
        self.run['predictions']['one']=self.ref('answer.json')
        self.assertEqual(self.evaluate()['results'][0]['rows'][0]['status'],'invalid-answer')

    def test_flat_unknown_schema_metadata_is_still_bound(self):
        for schema in (None,'unrecognized'):
            value=dict(self.answer,model='other',schema=schema)
            self.replace_answer(value)
            with self.assertRaisesRegex(b.ProvenanceError,'Saved model'):self.evaluate()

    def test_raw_license_and_key_corruption_cannot_hide_behind_LF_refs(self):
        for name in ('LICENSE','tags.json'):
            raw=(self.root/name).read_bytes()
            if b'\r\n' not in raw:
                raw=raw.replace(b'\n',b'\r\n');(self.root/name).write_bytes(raw);self.refresh()
            (self.root/name).write_bytes(raw.replace(b'\r\n',b'\n'))
            for role,ref in self.case['files'].items():ref['sha256']=b.file_hash(self.root/ref['path'])
            with self.assertRaisesRegex(ValueError,'Raw source artifact'):self.evaluate()
            (self.root/name).write_bytes(raw);self.refresh()

    def test_source_provenance_reference_and_case_roles_are_required(self):
        ref=self.case.pop('source_provenance')
        with self.assertRaises(ValueError):self.evaluate()
        self.case['source_provenance']=ref
        self.provenance['artifacts'][0]['role']='key';self.save('provenance.json',self.provenance)
        self.case['source_provenance']=self.ref('provenance.json')
        with self.assertRaisesRegex(ValueError,'role mismatch'):self.evaluate()

    def test_adding_unattempted_case_preserves_selected_cohort(self):
        old=self.evaluate()['results'][0]
        other=copy.deepcopy(self.case);other['id']='two';self.suite['cases'].append(other)
        new=self.evaluate()['results'][0]
        self.assertEqual(old['cohort'],new['cohort']);self.assertEqual(new['not_attempted'],['two'])

    def test_no_answers_or_references_are_mutated(self):
        original=self.evaluate()
        before={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        b.evaluate(self.root/'suite.json',self.root)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()})

    def test_real_frozen_raw_fixture_set_and_historical_modes(self):
        import hashlib
        manifest=b.read_json(ROOT/'benchmarks/tag-reading/PROVENANCE.json')
        self.assertEqual(len(manifest['artifacts']),13)
        for row in [*manifest['artifacts'],manifest['license']]:
            raw=(ROOT/row['path']).read_bytes()
            self.assertEqual((hashlib.sha256(raw).hexdigest(),len(raw)),(row['raw_sha256'],row['size_bytes']))
        report=b.evaluate(ROOT/'benchmarks/tag-reading-development.json',ROOT)
        self.assertEqual(len(report['results']),20);self.assertEqual(len(report['summary']),4)
        for row in report['results']:
            self.assertTrue(all(r['status']=='ok' for r in row['rows']))
            if row['tag_key_kind']=='geometry':
                self.assertEqual(row['counts']['strict']['with_truth'],33)
                self.assertEqual(row['counts']['strict']['correct'],28 if row['model']['provider']=='Anthropic' else 29)
            else:self.assertEqual(row['counts']['all']['listed'],145)

    def test_source_provenance_refuses_physical_escaping_symlink(self):
        import errno
        external = tempfile.TemporaryDirectory(prefix='tag-external-')
        self.addCleanup(external.cleanup)
        original = self.root / 'provenance.json'
        target = Path(external.name) / 'provenance.json'
        target.write_bytes(original.read_bytes())
        alias = self.root / 'outside-provenance.json'
        try:
            alias.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            if isinstance(exc, NotImplementedError) or getattr(exc, 'winerror', None) == 1314 or \
                    getattr(exc, 'errno', None) in (errno.EPERM, errno.EACCES, errno.ENOSYS, errno.ENOTSUP):
                self.skipTest('File symlinks unavailable: ' + str(exc))
            raise
        self.case['source_provenance'] = {'path': alias.name, 'sha256': b.file_hash(original)}
        with self.assertRaisesRegex(ValueError, 'escapes'):
            self.evaluate()
        self.assertEqual(target.read_bytes(), original.read_bytes())

    def test_compact_markdown_retains_nulls_groups_and_escaped_metadata(self):
        self.run['predictions'] = {}
        report = self.evaluate()
        first = report['summary'][0]
        first['model']['id'] = 'model|name\nnext'
        first['method'] = 'read|only\nmethod'
        first['configuration'] = {'variant': 'one'}
        second = copy.deepcopy(first)
        second['configuration'] = {'variant': 'two'}
        second['group'] = 'f' * 64
        report['summary'].append(second)
        original = b.encoded(report)
        text = b.markdown(report)
        self.assertEqual(b.encoded(report), original)
        self.assertEqual(text.count('| Rate | Mean | Range | SD | Defined / total |'), 2)
        self.assertNotIn('| Model / version | Method / interface |', text)
        self.assertIn('model\\|name next', text)
        self.assertIn('read\\|only method', text)
        self.assertIn('**Configuration:** {"variant": "one"}', text)
        self.assertIn('**Configuration:** {"variant": "two"}', text)
        self.assertEqual(text.count('| strict_accuracy_on_found | undefined | undefined–undefined | undefined | 0 / 1 |'), 2)
        self.assertEqual(text.count('| strict_end_to_end_recall | 0.0000 | 0.0000–0.0000 | undefined | 1 / 1 |'), 2)
        self.assertIn('one: missing', text)
        self.assertIn('Per-run counts and coverage (1 run/cohort records)', text)
        self.assertIn('## Limits', text)


    def test_git_exact_raw_fixture_checkout_and_narrow_whitespace_policy(self):
        import shutil
        import subprocess
        self.assertIsNotNone(shutil.which('git'),'Git is required for raw fixture checkout controls')
        rows=b.read_json(ROOT/'benchmarks/tag-reading/PROVENANCE.json')
        def command(cwd,*args):
            return subprocess.run(['git',*args],cwd=cwd,capture_output=True)
        for setting in ('true','false'):
            repo=self.root/setting;repo.mkdir()
            self.assertEqual(command(repo,'init').returncode,0)
            for key,value in (('user.name','Fixture control'),('user.email','fixture@example.invalid'),('core.autocrlf',setting)):
                self.assertEqual(command(repo,'config',key,value).returncode,0)
            (repo/'.gitattributes').write_bytes((ROOT/'.gitattributes').read_bytes())
            for row in [*rows['artifacts'],rows['license']]:
                dst=repo/row['path'];dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes((ROOT/row['path']).read_bytes())
            for suffix in ('.json','.md','.py'):
                (repo/('benchmarks/probe'+suffix)).write_bytes(b'{"line":1}\r\n')
            ordinary_paths=['benchmarks/probe.json','benchmarks/probe.md','benchmarks/probe.py',
                            'examples/source-handoff/fixture/preserved.xml','examples/source-handoff/worked/native.model.json']
            candidate_attrs=(ROOT/'.gitattributes').read_bytes()
            rule=b'/benchmarks/tag-reading/fixtures/dexpi/** -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n'
            (repo/'.gitattributes').write_bytes(candidate_attrs.replace(rule,b''))
            before_attrs=command(repo,'check-attr','text','eol','--',*ordinary_paths).stdout
            (repo/'.gitattributes').write_bytes(candidate_attrs)
            self.assertEqual(command(repo,'check-attr','text','eol','--',*ordinary_paths).stdout,before_attrs)
            sample=rows['artifacts'][0]['path']
            attrs=command(repo,'check-attr','text','eol','--',sample).stdout.decode('utf-8')
            self.assertIn(sample+': text: unset',attrs)
            self.assertIn(sample+': eol: lf',attrs)
            self.assertEqual(command(repo,'add','.').returncode,0)
            self.assertEqual(command(repo,'diff','--cached','--check').returncode,0)
            self.assertEqual(command(repo,'commit','-m','raw fixture control').returncode,0)
            target=self.root/('checkout-'+setting)
            self.assertEqual(command(self.root,'-c','core.autocrlf='+setting,'clone','--no-local',str(repo),str(target)).returncode,0)
            for row in [*rows['artifacts'],rows['license']]:
                expected=(ROOT/row['path']).read_bytes()
                self.assertEqual(command(repo,'cat-file','blob','HEAD:'+row['path']).stdout,expected)
                self.assertEqual((target/row['path']).read_bytes(),expected)
            for suffix in ('.json','.md','.py'):
                self.assertEqual(command(repo,'cat-file','blob','HEAD:benchmarks/probe'+suffix).stdout,b'{"line":1}\n')
            for i,(content,should_pass) in enumerate(((b'good\r\n',True),(b'bad \n',False),(b'bad\t\n',False),(b' \tX\n',False),(b'line\n\n',False))):
                bad=self.root/(setting+'-whitespace-'+str(i));bad.mkdir();command(bad,'init')
                (bad/'.gitattributes').write_bytes((ROOT/'.gitattributes').read_bytes())
                file=bad/'benchmarks/tag-reading/fixtures/dexpi/probe.txt';file.parent.mkdir(parents=True);file.write_bytes(content)
                self.assertEqual(command(bad,'add','.').returncode,0)
                self.assertEqual(command(bad,'diff','--cached','--check').returncode==0,should_pass)


class SystemGroupingBenchmarkTests(unittest.TestCase):
    """maintenance-system-grouping: controls in every row, and a fetch-by-hash cache that may be absent."""

    def setUp(self):
        import importlib.util
        self.tmp = tempfile.TemporaryDirectory(prefix='system-benchmark-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        spec = importlib.util.spec_from_file_location('system_scorer_fixture', ROOT / 'scripts/test_score_maintenance_systems.py')
        fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
        cache = self.root / 'data/external/demo-group'
        cache.mkdir(parents=True)
        fixture.write(cache)
        (self.root / 'recipe.txt').write_bytes(b'Authored vocabulary; no inference.\n')
        self.save('answer.json', {'assigned': {'2': 'Bucket', '3': 'Hydraulic System', '4': 'Engine', '5': '', '6': 'Bucket',
                                               '7': 'Engine', '8': 'Hydraulic System'}})
        ref = lambda rel: {'path': rel, 'sha256': b.file_hash(self.root / rel)}
        case = {'id': 'demo-a', 'family': 'demo', 'split': 'development', 'evidence': 'authored software control',
                'source_url': 'https://example.invalid/demo', 'license': 'authored', 'key_author': 'authored',
                'assets': ['A'], 'majority': 'Hydraulic System',
                'files': {'input': ref('data/external/demo-group/raw.csv'), 'key': ref('data/external/demo-group/cleaned.csv')}}
        self.save('run.json', {'id': 'demo-run', 'ran_at': '2026-11-12', 'interface': 'test', 'method': 'authored answer',
                               'provenance': 'authored', 'model': {'provider': 'none', 'id': 'authored', 'version': '1'},
                               'configuration': {}, 'recipe': [ref('recipe.txt')], 'cases': ['demo-a'],
                               'predictions': {'demo-a': ref('answer.json')}})
        self.save('suite.json', {'id': 'demo-systems', 'version': '1', 'task': 'maintenance-system-grouping', 'optional_cache': True,
                                 'protocol': 'system-groups-v1', 'registration': 'authored software control',
                                 'cases': [case], 'runs': ['run.json']})
        self.save('registry.json', {'schema': 'benchmark-registry-1', 'reports': [{'suite': 'suite.json', 'report': 'report'}]})

    def save(self, name, value):
        (self.root / name).write_text(json.dumps(value, indent=2), encoding='utf-8')

    def test_answer_rows_carry_every_control_and_reference_is_perfect(self):
        report = b.evaluate(self.root / 'suite.json', self.root)
        row = report['results'][0]['rows'][0]
        self.assertEqual(row['counts']['orders'], {'tp': 3, 'predicted': 4, 'truth': 5})
        self.assertEqual(set(row['diagnostics']['controls']), {'reference', 'raw-asset-baseline', 'majority-system',
                                                                'shuffled-within-asset', 'misaligned-key'})
        self.assertEqual(report['controls']['demo-a']['reference']['orders']['f1'], 1.0)
        # No-key records given a class count as false positives in the strict columns: record 6 (key NA, answered Bucket).
        self.assertEqual(row['diagnostics']['orders_no_key_as_fp'], {'precision': 0.6, 'recall': 0.6, 'f1': 0.6})
        self.assertIn('no-key as FP', b.markdown(report))
        text = b.markdown(report)
        for name in ('answer', 'reference', 'raw-asset-baseline', 'majority-system', 'shuffled-within-asset', 'misaligned-key'):
            self.assertIn('| ' + name + ' |', text)
        self.assertNotIn('| Model / version |', text)

    def test_absent_cache_is_unverified_but_a_present_changed_cache_fails(self):
        import contextlib
        import io
        import shutil
        self.assertEqual(b.main(['--suite', str(self.root / 'suite.json'), '--root', str(self.root), '--out', str(self.root / 'report')]), 0)
        registry = ['--registry', str(self.root / 'registry.json'), '--root', str(self.root)]
        self.assertEqual(b.main(registry), 0)
        (self.root / 'data/external/demo-group/cleaned.csv').write_text('changed', encoding='utf-8')
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(b.main(registry), 2)
        shutil.rmtree(self.root / 'data/external/demo-group')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(b.main(registry), 0)
        self.assertIn('UNVERIFIED: suite.json', out.getvalue())
        # Only a suite that opts in may be skipped: without optional_cache the same absent cache fails.
        suite = json.loads((self.root / 'suite.json').read_text(encoding='utf-8')); suite.pop('optional_cache')
        self.save('suite.json', suite)
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(b.main(registry), 2)


if __name__ == '__main__':
    unittest.main()
