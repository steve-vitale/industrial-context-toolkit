"""Semantic loss controls beyond the archive's outer byte inventory."""
import copy
import json
import unittest
import recheck_evidence as evidence


class NativeCapabilityEvidence(unittest.TestCase):
    def setUp(self):
        self.freezes = json.loads((evidence.HERE / 'FROZEN-INPUTS.json').read_bytes())

    def files(self, kind):
        path = evidence.HERE / ('probes/' + kind if kind.startswith('binding') else kind)
        return evidence.unpack(path)

    def changed(self, files, path, fn):
        value = json.loads(files[path]); fn(value)
        files[path] = json.dumps(value, ensure_ascii=False).encode('utf-8')

    def test_all_original_failures_and_probe_outcomes_remain_distinct(self):
        result = evidence.check()
        self.assertEqual(len(result['attempts']), 4)
        self.assertFalse(result['whole_cad_qualified'])
        self.assertEqual(result['attempts'][0]['status'], 'original-failed-attempt-retained')
        self.assertEqual(result['attempts'][1]['status'], 'original-failed-attempt-retained')
        self.assertEqual(result['attempts'][2]['status'], 'probe-complete-with-retained-codec-refusal')
        self.assertEqual(result['attempts'][3]['status'], 'probe-observed-process-and-utf8-stream-capabilities')

    def test_source_or_method_changes_refuse_after_outer_inventory_bypass(self):
        kind = 'binding-probe-2'; original = self.files(kind)
        for name in ('source.dxf', 'observe_case.js', 'workflow.py'):
            with self.subTest(name=name):
                files = dict(original); files['attempt/job/' + name] += b'changed'
                with self.assertRaises(ValueError): evidence.check_files(files, self.freezes[kind], kind)

    def test_failed_attempt_cannot_be_promoted_by_editing_exit_or_losing_console(self):
        for kind in ('development-1', 'development-2'):
            original = self.files(kind)
            files = dict(original)
            self.changed(files, 'attempt/job/native/PROCESS.json', lambda r: r.update(controller_exit=0))
            with self.assertRaises(ValueError): evidence.check_files(files, self.freezes[kind], kind)
            files = dict(original)
            files['attempt/job/native/stdout.txt'] = b''; files['attempt/job/native/stderr.txt'] = b''
            with self.assertRaises(ValueError): evidence.check_files(files, self.freezes[kind], kind)

    def test_matching_report_tampering_still_fails_installed_capability_checks(self):
        kind = 'binding-probe-2'; original = self.files(kind)
        for fault in ('uid', 'unicode', 'missing_class', 'collision'):
            with self.subTest(fault=fault):
                files = dict(original)
                report = json.loads(files['attempt/job/native/BINDINGS.json'])
                if fault == 'uid': report['checks']['decode_stdout']['value'] = '{"uid":0,"value":"µ valve"}\n'
                if fault == 'unicode': report['checks']['decode_stdout']['value'] = '{"uid":1001,"value":"u valve"}\n'
                if fault == 'missing_class': report['checks']['classes']['value']['QFileDevice'] = 'function'
                if fault == 'collision': report['checks']['new_only_collision']['value'] = True
                files['attempt/job/native/BINDINGS.json'] = json.dumps(report).encode('utf-8')
                self.changed(files, 'attempt/job/ui/RESULT.json', lambda r: r.update(report=report))
                with self.assertRaises(ValueError): evidence.check_files(files, self.freezes[kind], kind)

    def test_original_codec_refusal_cannot_be_replaced_by_success(self):
        kind = 'binding-probe-1'; files = self.files(kind)
        report = json.loads(files['attempt/job/native/BINDINGS.json'])
        report['checks']['process_roundtrip'] = dict(ok=True, value=dict(exit=0))
        files['attempt/job/native/BINDINGS.json'] = json.dumps(report).encode('utf-8')
        self.changed(files, 'attempt/job/ui/RESULT.json', lambda r: r.update(report=report))
        with self.assertRaises(ValueError): evidence.check_files(files, self.freezes[kind], kind)


if __name__ == '__main__': unittest.main()
