"""Offline known-answer relationship controls; fictional records, no source download or model calls."""
import copy
import json
from reproduce import relationships


def run():
    fixture = {
        'work-orders': [{'evt_code': '1', 'evt_object': 'A', 'evt_date': '2024-01-02T00:00:00'}],
        'assets': [{'obj_code': 'A'}],
        'transactions': [{'tra_code': '10', 'tra_tocode': '1', 'tra_toentity': 'EVNT'}],
        'details': [{'trl_sqlidentity': '100', 'trl_trans': '10'}],
        'labor': [{'boo_code': '1000', 'boo_event': '1'}],
    }
    observations = {}
    baseline = relationships(fixture)
    assert not baseline['errors']
    assert all(v['unique_match'] == 1 for v in baseline['links'].values())
    observations['correct_relationships'] = 'all four links unique'
    missing = copy.deepcopy(fixture)
    missing['assets'] = []
    result = relationships(missing)
    assert result['links']['work_orders_to_assets']['unmatched'] == 1
    assert not result['errors']  # A real missing asset is a coverage gap, not fabricated from another source.
    observations['missing_asset'] = 'retained as unmatched; no fabricated parent'
    ambiguous = copy.deepcopy(fixture)
    ambiguous['assets'].append({'obj_code': 'A'})
    result = relationships(ambiguous)
    assert result['errors'] and result['links']['work_orders_to_assets']['ambiguous'] == 1
    observations['duplicate_asset'] = 'ambiguous and error; no first-match collapse'
    foreign = copy.deepcopy(fixture)
    foreign['transactions'][0]['tra_toentity'] = 'STOR'
    assert relationships(foreign)['errors']
    observations['wrong_entity_same_identifier'] = 'refused despite matching numeric code'
    for table, field in [('transactions', 'tra_tocode'), ('details', 'trl_trans'), ('labor', 'boo_event')]:
        lost = copy.deepcopy(fixture)
        lost[table][0][field] = '999'
        assert relationships(lost)['errors']
        observations[table + '_foreign_parent'] = 'reported as error'
    outside = copy.deepcopy(fixture)
    outside['work-orders'][0]['evt_date'] = '2024-01-08T00:00:00'
    assert relationships(outside)['errors']
    observations['exclusive_end_date'] = 'refused'
    renamed = copy.deepcopy(fixture)
    renamed['labor'][0]['invented_field'] = 'x'
    assert relationships(renamed)['errors']
    observations['uncontracted_column'] = 'refused'
    empty = {k: [] for k in fixture}
    assert relationships(empty)['errors']
    observations['empty_cohort'] = 'refused'
    print(json.dumps(observations, indent=2))


if __name__ == '__main__':
    run()
