"""Completion observations cannot change the expected text or dispatch another input."""
import unittest
from ui_settle import wait_for_exact


class TextCompletionControls(unittest.TestCase):
    def test_partial_queued_text_can_complete_without_another_action(self):
        values = iter(['', '/wor', '/work/source.dxf']); records = []; now = [0.0]
        result = wait_for_exact(lambda: next(values), '/work/source.dxf', records.append,
                                clock=lambda: now[0], sleep=lambda seconds: now.__setitem__(0, now[0] + seconds))
        self.assertTrue(result); self.assertEqual([r['text'] for r in records], ['', '/wor', '/work/source.dxf'])

    def test_wrong_stable_text_times_out_without_replacing_expected_value(self):
        records = []; now = [0.0]
        result = wait_for_exact(lambda: 'wrong', 'expected', records.append, timeout=.2,
                                clock=lambda: now[0], sleep=lambda seconds: now.__setitem__(0, now[0] + seconds))
        self.assertFalse(result); self.assertTrue(all(r['text'] == 'wrong' for r in records))
        self.assertEqual(records[-1]['elapsed'], .2)

    def test_observation_failure_is_not_retried_or_promoted(self):
        calls = []
        def read(): calls.append('read'); raise ValueError('Native field unavailable')
        with self.assertRaisesRegex(ValueError, 'unavailable'): wait_for_exact(read, 'expected', lambda r: None)
        self.assertEqual(calls, ['read'])


if __name__ == '__main__': unittest.main()
