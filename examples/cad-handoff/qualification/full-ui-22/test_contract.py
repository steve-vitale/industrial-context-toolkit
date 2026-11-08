"""Wrong-asset and lost-foreign-field controls for the multi-asset observation gate."""
import copy
import unittest
from contract import verify_inventory, verify_selection


def fixture():
    expected = {'one': {'ICT_ID': 'one', 'TAG': 'P-1', 'MODEL': 'same', 'FOREIGN': '\u0416 {x}'},
                'two': {'ICT_ID': 'two', 'TAG': 'P-2', 'MODEL': 'same', 'FOREIGN': 'retain \\P'}}
    rows = []
    for parent, (identity, attrs) in zip((10, 20), expected.items()):
        for offset, (tag, value) in enumerate(attrs.items(), 1):
            rows.append(dict(parent_id=str(parent), parent_handle=hex(parent), id=str(parent + offset),
                             handle=hex(parent + offset), tag=tag, text=value))
    return dict(attributes=rows, selected=[10, 11, 12, 13, 14]), expected


class MultiAssetControls(unittest.TestCase):
    def test_complete_foreign_values_and_exact_selection_pass(self):
        observed, expected = fixture(); groups = verify_inventory(observed, expected)
        verify_selection(observed, groups['one'])

    def test_wrong_asset_edit_cannot_hide_behind_same_before_value(self):
        observed, expected = fixture(); expected['one']['MODEL'] = 'after'
        next(r for r in observed['attributes'] if r['parent_id'] == '20' and r['tag'] == 'MODEL')['text'] = 'after'
        with self.assertRaisesRegex(ValueError, 'attributes differ'): verify_inventory(observed, expected)

    def test_lost_or_changed_foreign_field_refuses(self):
        for variant in ('lost', 'changed'):
            with self.subTest(variant=variant):
                observed, expected = fixture(); row = observed['attributes'][-1]
                if variant == 'lost': observed['attributes'].remove(row)
                else: row['text'] = 'changed'
                with self.assertRaises(ValueError): verify_inventory(observed, expected)

    def test_missing_asset_or_duplicate_identity_refuses(self):
        for variant in ('missing', 'duplicate'):
            with self.subTest(variant=variant):
                observed, expected = fixture()
                if variant == 'missing': observed['attributes'] = observed['attributes'][:4]
                else: next(r for r in observed['attributes'] if r['parent_id'] == '20' and r['tag'] == 'ICT_ID')['text'] = 'one'
                with self.assertRaises(ValueError): verify_inventory(observed, expected)

    def test_wrong_or_extra_selected_asset_children_refuse(self):
        for selected in ([20, 21, 22, 23, 24], [10, 11, 12, 13, 14, 20], [10, 11, 12, 13, 13], [True, 11, 12, 13, 14]):
            with self.subTest(selected=selected):
                observed, expected = fixture(); groups = verify_inventory(observed, expected); observed['selected'] = selected
                with self.assertRaises(ValueError): verify_selection(observed, groups['one'])

    def test_duplicate_tag_or_native_id_refuses(self):
        for key in ('tag', 'id', 'handle'):
            with self.subTest(key=key):
                observed, expected = fixture(); observed['attributes'][1][key] = observed['attributes'][0][key]
                with self.assertRaises(ValueError): verify_inventory(observed, expected)


if __name__ == '__main__': unittest.main()
