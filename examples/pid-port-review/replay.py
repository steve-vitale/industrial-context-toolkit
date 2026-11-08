"""Prepare fictional source-bound port readings and replay the separate exposed acceptance key.

CSV parsing is deterministic record preparation, not visual interpretation. Fixed source CSVs and the
key were committed before the checker. No drawing renderer or generated answer key is used.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_pid_connections as ports
import check_pid_markups as markups

HERE = Path(__file__).resolve().parent


def prepare(out, corrected=False):
    out = Path(out)
    if out.exists():
        raise ValueError('Retain previous input: output exists')
    out.mkdir()
    (out / 'source').mkdir()
    for name in ('catalog.json', 'original.csv', 'markup.txt', 'corrected.csv' if corrected else 'returned.csv'):
        shutil.copyfile(HERE / 'source' / name, out / 'source' / name)
    returned_name = 'corrected.csv' if corrected else 'returned.csv'
    pins = {}
    for role, name, revision in [('original', 'original.csv', 'A'), ('markup', 'markup.txt', 'A-M1'),
                                 ('returned', returned_name, 'C' if corrected else 'B')]:
        rel = 'source/' + name
        pins[role] = {'id': role, 'role': role, 'path': rel, 'revision': revision,
                      'sha256': ports.sha((out / rel).read_bytes())}

    def evidence(role, description):
        return [{'document': role, 'sha256': pins[role]['sha256'], 'page': 1,
                 'box_0_1000': [0, 0, 1000, 1000], 'description': description}]

    def edge(identity, number, target_port='PV', role='markup'):
        return {'id': identity, 'from': {'tag': 'PT-' + str(number), 'port': 'OUT'},
                'to': {'tag': 'PIC-' + str(number), 'port': target_port}, 'relation': 'signal',
                'medium': 'electric', 'evidence': evidence(role, identity + ': exact endpoints in retained record')}

    records = {'schema': 'pid-port-records-1', 'sheet': 'fictional WT/01', 'identity': 'confirmed',
               'method': 'Author-prepared endpoint records from exact CSV columns and manually transcribed instructions. '
                         'Whole-record locators, not drawing regions. Same assistant authored sources/key/code; '
                         'no independent review or image reading. Assets are an authored fixture inventory.',
               'assets': [{'tag': prefix + str(n), 'symbol': symbol, 'evidence': evidence('returned', 'Fixture asset inventory')}
                          for n in range(101, 107) for prefix, symbol in [('PT-', 'transmitter'), ('PIC-', 'controller')]],
               'connections': [], 'requirements': [edge('R1', 102), edge('R2', 104), edge('R3', 103, 'SP'), edge('R4', 105)],
               'allowed_connections': [edge('O1', 101, role='original')], 'coverage': []}
    with (out / 'source' / returned_name).open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            records['connections'].append({'id': row['connection'], 'from': {'tag': row['from_tag'], 'port': row['from_port']},
                'to': {'tag': row['to_tag'], 'port': row['to_port']}, 'relation': row['relation'], 'medium': row['medium'],
                'state': 'known', 'evidence': evidence('returned', row['connection'] + ': complete exact CSV row')})
    for req in records['requirements']:
        records['coverage'].append({'from': req['from'], 'relation': req['relation'], 'medium': req['medium'],
             'complete': req['id'] != 'R4', 'basis': 'Complete fictional schedule for selector' if req['id'] != 'R4'
             else 'Declared unreadable area, no observation; do not infer absence',
             'evidence': evidence('returned', 'Declared scope; this is a fixture assumption, not verified visual coverage')})
    ports.write(out / 'records.json', records)
    manifest = {'schema': 'pid-port-review-1', 'documents': list(pins.values()),
                'catalog': {'path': 'source/catalog.json', 'sha256': ports.sha((out / 'source/catalog.json').read_bytes())},
                'records': {'path': 'records.json', 'sha256': ports.sha((out / 'records.json').read_bytes())}}
    ports.write(out / 'manifest.json', manifest)
    return out / 'manifest.json'


def matched_baseline():
    # Identical wrong-input observation: tag-only cannot represent the terminal distinction.
    common = {'sheet': 'fictional WT/01', 'subject': 'PT-103', 'relation': 'signal', 'to': 'PIC-103'}
    old = dict(common, kind='connection')
    new = dict(common, kind='port_connection', port='OUT', to_port='SP', medium='electric')
    wrong = dict(new, to_port='PV')
    return {'schema': 'pid-port-baseline-1',
            'tag_only_wrong_input_supported': markups.fact_key(old) == markups.fact_key(old),
            'port_aware_wrong_input_supported': markups.fact_key(new) == markups.fact_key(wrong),
            'requested': new, 'observed': wrong,
            'scope': 'Exact fact-key equivalence using the same wrong-input endpoint observation. '
                     'The old representation drops both ports and medium; it cannot express that distinction. '
                     'Supported here means endpoint identity match, not a markup acceptance or accuracy measurement.'}


def run(out):
    out = Path(out)
    if out.exists():
        raise ValueError('Retain previous replay: output exists')
    out.mkdir()
    results = {}
    for label in ('initial', 'corrected'):
        manifest = prepare(out / (label + '-inputs'), label == 'corrected')
        result = ports.run(manifest, out / label)
        results[label] = {'requirements': {r['id']: r['status'] for r in result['requirements']},
                          'other_connections': [r['id'] for r in result['other_connections']]}
    results['baseline'] = matched_baseline()
    ports.write(out / 'replay.json', results)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.out), indent=2))
