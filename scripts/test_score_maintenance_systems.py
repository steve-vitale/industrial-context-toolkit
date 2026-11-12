"""The system-grouping scorer: its join, counts and deliberately wrong controls on authored rows (no public records)."""
import csv
import tempfile
import unittest
from pathlib import Path

import score_maintenance_systems as s

RAW = [  # BscStartDate, Asset, OriginalShorttext, PMType, Cost
    ('2001-01-01', 'A', 'renew authored bucket tooth set', 'PM01', '1'),
    ('2001-01-02', 'A', 'hyd hose leaking', 'PM01', '1'),
    ('2001-01-02', 'A', 'hyd hose leaking', 'PM01', '1'),
    ('2001-01-03', 'A', 'swap \\o\\" ring"', 'PM01', '1'),
    ('2001-01-04', 'A', 'grease rounds', 'PM01', '1'),
    ('2001-01-05', 'A', 'only in the raw file', 'PM01', '1'),
    ('2001-01-06', 'A', 'engine hose', 'PM01', '1'),
    ('2001-01-01', 'B', 'bucket lip', 'PM01', '1'),
]
CLEANED = [  # the publisher's cleaned rows: same rows less one, with MajorSystem
    ('2001-01-01', 'A', 'renew authored bucket tooth set', 'Bucket'),
    ('2001-01-02', 'A', 'hyd hose leaking', 'Hydraulic System'),
    ('2001-01-02', 'A', 'hyd hose leaking', 'Hydraulic System'),
    ('2001-01-03', 'A', 'swap o" ring"""', 'Hydraulic System'),
    ('2001-01-04', 'A', 'grease rounds', 'NA'),
    ('2001-01-06', 'A', 'engine hose', 'Engine_Hydraulic System'),
    ('2001-01-01', 'B', 'bucket lip', 'Bucket'),
]


def write(root):
    raw, cleaned = root / 'raw.csv', root / 'cleaned.csv'
    with raw.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['BscStartDate', 'Asset', 'OriginalShorttext', 'PMType', 'Cost']); w.writerows(RAW)
    with cleaned.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['BscStartDate', 'Asset', 'OriginalShorttext', 'PMType', 'Cost', 'MajorSystem'])
        w.writerows((d, a, t, 'PM01', '1', m) for d, a, t, m in CLEANED)
    return raw, cleaned


class ScorerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.raw, self.cleaned = write(Path(self.temp.name))

    def test_join_matches_in_order_drops_unkeyed_and_other_assets(self):
        key, join = s.keyed_records(self.raw, self.cleaned, ['A'])
        self.assertEqual(sorted(key, key=int), ['2', '3', '4', '5', '6', '8'])
        self.assertEqual(key['5'], ('A', ('Hydraulic System',)))  # backslash/quote text joined after normalizing
        self.assertEqual(key['6'], ('A', ()))  # NA is no system
        self.assertEqual(key['8'], ('A', ('Engine', 'Hydraulic System')))
        self.assertEqual(join, dict(raw_records=7, cleaned_records=6, keyed=6, unkeyed_raw=1, unmatched_cleaned=0,
                                    keyed_with_system=5))

    def test_counts_controls_and_the_no_system_denominator(self):
        answer = {'2': 'Bucket', '3': 'Hydraulic System', '4': 'Engine', '5': '', '6': 'Bucket', '7': 'Engine', '8': 'Hydraulic System'}
        out = s.evaluate(self.raw, self.cleaned, ['A'], answer, 'Hydraulic System')
        method = out['scores']['method']
        self.assertEqual(method['counts']['orders'], dict(tp=3, predicted=4, truth=5))
        self.assertEqual(method['assigned_without_key_system'], 1)
        # Groups: the key has (A, Hydraulic System) x4 only; the answer adds (A, Bucket) from records 2 and 6.
        self.assertEqual(method['counts']['groups'], dict(tp=1, predicted=2, truth=1))
        self.assertEqual(out['control_problems'], [])
        ref = out['scores']['reference']['rates']
        self.assertTrue(all(ref[m]['f1'] == 1.0 for m in s.METRICS))
        self.assertEqual(out['scores']['raw-asset-baseline']['counts']['orders']['predicted'], 0)
        self.assertEqual(out['scores']['majority-system']['counts']['orders'], dict(tp=4, predicted=5, truth=5))
        self.assertEqual(s.margin(out['scores']), round(method['rates']['orders']['f1'] - 0.8, 4))

    def test_answer_outside_the_selected_rows_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'outside the selected raw rows'):
            s.evaluate(self.raw, self.cleaned, ['A'], {'9': 'Bucket'}, 'Bucket')

    def test_misaligned_key_moves_half_an_asset_away(self):
        key = {str(n): ('A', (c,)) for n, c in zip(range(2, 6), 'wxyz')}
        self.assertEqual({k: v[1][0] for k, v in s.misaligned(key).items()}, {'2': 'y', '3': 'z', '4': 'w', '5': 'x'})


    def test_posthoc_strict_rates_and_class_name_control_vocabulary(self):
        import maintenance_system_posthoc as ph
        answer = {'2': 'Bucket', '3': 'Hydraulic System', '4': 'Engine', '5': '', '6': 'Bucket', '7': 'Engine', '8': 'Hydraulic System'}
        method = s.evaluate(self.raw, self.cleaned, ['A'], answer, 'Hydraulic System')['scores']['method']
        self.assertEqual(ph.strict_rates(method), {'precision': 0.6, 'recall': 0.6, 'f1': 0.6})
        rules = ph.classname_rules({'rules': [{'value': 'Induction and Exhaust', 'terms': ['MUFFLER']},
                                              {'value': 'Hydraulic Cylinders', 'terms': ['CYL']}]})
        self.assertEqual(rules, [{'value': 'Induction and Exhaust', 'terms': ['INDUCTION', 'EXHAUST']},
                                 {'value': 'Hydraulic Cylinders', 'terms': ['HYDRAULIC', 'CYLINDERS']}])

if __name__ == '__main__':
    unittest.main()
