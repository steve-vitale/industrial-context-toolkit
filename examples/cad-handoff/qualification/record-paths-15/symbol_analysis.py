"""Receive the predeclared native-name counterfactual without repairing its returns."""
import copy
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ict_symbol15_records', HERE / 'record_analysis.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
b = a.b


def operation(before, after, rename):
    """Exact recorded public inventory, except the single declared block name."""
    expected = copy.deepcopy(b.canonical_inventory(before))
    if rename is not None:
        matches = [r for r in expected['objects'] if r['type'] == 4 and r['name'] == rename['before']]
        b.require(len(matches) == 1, 'Rename must select one exact block')
        matches[0]['name'] = rename['after']
    b.require(expected == b.canonical_inventory(after), 'Undeclared public inventory change during rename')


def analyze(root):
    jobs = b.read(root / 'export.json')['jobs']
    expected = [(namespace + '/' + label, rename) for namespace in ('qcad', 'foreign')
        for label, rename in [('unchanged', None),
            ('target', dict(before='2/2-directional valve', after='2_2-directional valve')),
            ('unrelated', dict(before='ICT_QUAL_TEST_ANCHOR', after='ICT_QUAL_TEST_CONTROL'))]]
    b.require([(j['id'], j['rename']) for j in jobs] == expected, 'Name-control cohort differs')
    for job in jobs:
        namespace, label = job['id'].split('/')
        b.require(job == dict(id=job['id'], input='/work/cases/' + namespace + '/source.dxf',
            output='/work/cases/' + namespace + '/returns/' + label + '.dxf', importer='dxflib',
            exporter='OpenDesign', version='R15', rename=job['rename']), 'Name-control job differs')
    rows = a.native_rows(root / 'native/export.stdout', jobs, allow_errors=True)
    successful = [j for j, r in zip(jobs, rows) if 'error' not in r]
    b.require([j['id'] for j in successful] == ['qcad/target', 'foreign/target'], 'Causal export pattern differs')
    b.require(b.read(root / 'native/fresh-success.json') == dict(jobs=successful, read_only=True), 'Name fresh subset differs')
    fresh = {r['id']: r for r in a.native_rows(root / 'native/fresh.stdout', successful)}
    results = []
    for job, row in zip(jobs, rows):
        operation(row['imported'], row['after_operation'], job['rename'])
        output = root / job['output'].removeprefix('/work/')
        source = root / job['input'].removeprefix('/work/')
        item = dict(id=job['id'], intended_operation_exact=True, native_export='failed' if 'error' in row else 'completed')
        if 'error' in row:
            item.update(error=row['error'], retained_partial_file=dict(bytes=output.stat().st_size, sha256=b.sha(output)) if output.exists() else None)
        else:
            b.require(b.canonical_inventory(row['reopened']) == b.canonical_inventory(fresh[job['id']]['imported']), 'Name fresh public inventory differs')
            # This tests the observed operation only. Export may still lose other data.
            names = [r['name'] for r in row['reopened']['objects'] if r['type'] == 4]
            b.require('2_2-directional valve' in names and '2/2-directional valve' not in names and
                'ICT_QUAL_TEST_ANCHOR' in names and 'ICT_QUAL_TEST_CONTROL' not in names, 'Returned block identity differs')
            doc = b.ch.load(output)
            b.require(doc.dxfversion == 'AC1015', 'Name return version differs')
            try:
                report = b.ch.compare(b.ch.snapshot(source), b.ch.snapshot(output))
            except b.ch.InputError as error:
                report = dict(status='refused', error=str(error), boundary='Original strict asset-profile guard')
            item.update(fresh_public_inventory_equal=True, strict_report=report,
                raw_return=dict(bytes=output.stat().st_size, sha256=b.sha(output)))
        results.append(item)
    return dict(attempted_jobs=6, successful_exports=2, unchanged_failed=2, unrelated_rename_failed=2,
        target_rename_exported=2, fresh_public_inventory_repeats=2, observations=results,
        cause='Retained slash in block name 2/2-directional valve prevents this dxflib-to-OpenDesign export; target-only native rename permits it',
        whole_cad_qualified=False, exposure='Two exposed hydraulic sources; predeclared matched native rename, no fresh qualification')


if __name__ == '__main__':
    root = Path(sys.argv[1])
    result = analyze(root)
    (root / 'analysis').mkdir(exist_ok=True)
    b.write(root / 'analysis/symbol-diagnosis.json', result)
    print('Received six matched name controls, two exports; whole CAD remains unqualified')
