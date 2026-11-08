"""Re-score the frozen constructor intervention, without treating it as CAD qualification."""
import hashlib
import itertools
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def equal(left, right):
    return encoded(left) == encoded(right)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(path, prefix):
    text = path.read_text(encoding='utf-8')
    require('ICT_LAYOUT17_FATAL ' not in text, 'Native fatal retained')
    return [json.loads(line[len(prefix):]) for line in text.splitlines() if line.startswith(prefix)]


def changes(left, right, path=''):
    if equal(left, right):
        return []
    if isinstance(left, dict) and isinstance(right, dict):
        result = []
        for key in sorted(left.keys() | right.keys()):
            child = path + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in left or key not in right:
                result.append(dict(path=child, before_present=key in left, after_present=key in right,
                                   before=left.get(key), after=right.get(key)))
            else:
                result.extend(changes(left[key], right[key], child))
        return result
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        return [row for i, (a, b) in enumerate(zip(left, right)) for row in changes(a, b, path + '/' + str(i))]
    return [dict(path=path, before=left, after=right)]


def named(rows, key, label):
    require(len({encoded(row[key]) for row in rows}) == len(rows), 'Duplicate ' + label)
    return {str(row[key]): row for row in rows}


def inventory(state, keys):
    require(set(state) == {'file_version', 'variables', 'headers', 'objects'}, 'Native inventory fields differ')
    headers = state['headers']
    require(set(headers) == {'known_variables', 'dimension_variables', 'layouts'}, 'Native header coverage differs')
    require([r['name'] for r in headers['known_variables']] == keys['known_variables'], 'Native known-variable observation omitted')
    require([r['name'] for r in headers['dimension_variables']] == [r['name'] for r in keys['dimension_variables']],
            'Native dimension observation omitted')
    layouts = named(headers['layouts'], 'id', 'layout id')
    require(bool(layouts), 'Native layouts omitted')
    for layout in layouts.values():
        require([r['getter'] for r in layout['properties']] == keys['layout_getters'], 'Native layout getter omitted')
    # Only set traversal becomes keyed. IDs, handles, parents, values and property order remain literal.
    objects = named(state['objects'], 'id', 'object id')
    for row in objects.values():
        custom = row['custom']
        require(len({(r['title'], r['key']) for r in custom}) == len(custom), 'Duplicate custom property')
    return dict(file_version=state['file_version'], variables=named(state['variables'], 'name', 'variable name'),
                headers=dict(known_variables=headers['known_variables'], dimension_variables=headers['dimension_variables'], layouts=layouts),
                objects={k: dict(v, custom=sorted(v['custom'], key=lambda r: (r['title'], r['key']))) for k, v in objects.items()})


def constructor_rows(rows, fields, mode):
    require(rows and sorted(r['sequence'] for r in rows) == list(range(1, len(rows) + 1)), 'Constructor sequence omitted/duplicated')
    variants = {'_ZN7RLayoutC1Ev', '_ZN7RLayoutC2Ev', '_ZN7RLayoutC1EP9RDocumentRK7QString', '_ZN7RLayoutC2EP9RDocumentRK7QString'}
    for row in rows:
        require(row['mode'] == mode and row['variant'] in variants, 'Constructor mode/variant differs')
        require([f['getter'] for f in row['fields']] == [f['getter'] for f in fields], 'Constructor field omitted')
        for actual, expected in zip(row['fields'], fields):
            require(actual['offset'] == expected['offset'] and actual['size'] == expected['size'], 'Constructor field ABI differs')
            for phase in ('original', 'before_library', 'after_library'):
                value = actual[phase]
                require(len(value) == 2 * expected['size'] and bytes.fromhex(value).hex() == value, 'Malformed constructor bytes')
            before = expected['expected_before'].get(mode, actual['original'])
            after = expected['expected_after_constructor'].get(mode, before)
            require(actual['before_library'] == before, 'Undeclared pre-construction write')
            require(actual['after_library'] == after, 'Constructor retention/reset expectation failed')
    return dict(calls=len(rows), variants={v: sum(r['variant'] == v for r in rows) for v in sorted({r['variant'] for r in rows})},
                field_observations=len(rows) * len(fields))


def detached(row, fields, keys, mode):
    props = row['properties']
    # The frozen observer records getTabOrder twice; retain and check both observations.
    require([r['getter'] for r in props] == keys['layout_getters'] + ['getTabOrder'], 'Detached getter omitted')
    for field in fields:
        if mode not in field['expected_detached']:
            continue
        value = field['expected_detached'][mode]
        expected = dict(type='boolean' if type(value) is bool else 'number', value=value)
        found = [p['value'] for p in props if p['getter'] == field['getter']]
        require(found and all(equal(p, expected) for p in found), 'Detached native getter differs from independent preset')


def analyze(root):
    freeze, fields, keys = read(root / 'FREEZE.json'), read(root / 'FIELDS.json'), read(root / 'KEYS.json')
    require(freeze['whole_cad_qualified'] is False, 'Unsupported CAD qualification claim')
    for name, pin in freeze['inputs'].items():
        require(sha(root / name) == pin, 'Frozen input differs: ' + name)
    jobs = read(root / 'jobs.json')['jobs']
    commands = read(root / 'native/commands.json')
    require([r['mode'] for r in commands] == freeze['modes'], 'Native process coverage differs')
    modes, ctors = {}, {}
    filters = dict(OpenDesign='All CAD Files [OpenDesign] (*.dxf *.dwg *.dwt *.dxb *.dgn *.dwf)', dxflib='DXF Files [dxflib] (*.dxf)')
    for command in commands:
        mode = command['mode']
        require(command['exit'] == 0 and command['configuration_before'] == freeze['configuration_sha256'] and
                command['configuration_after'] == freeze['configuration_sha256'], 'Native exit/settings differ')
        require(command['environment'] == dict(LD_PRELOAD='/work/layout_ctor.so', ICT_LAYOUT17_MODE=mode), 'Native intervention differs')
        require(command['command'] == ['/opt/qcad/qcad', '-platform', 'offscreen', '-no-gui', '-allow-multiple-instances',
                '-config', '/home/cad/.config/QCAD/QCAD3.conf', '-font-substitution', 'Standard', 'DejaVu Sans',
                '-autostart', '/work/native_layouts.js'], 'Native command differs')
        stdout, stderr = root / 'native' / (mode + '.stdout'), root / 'native' / (mode + '.stderr')
        profiles = records(stdout, 'ICT_LAYOUT17_PROFILE ')
        require(profiles == [dict(configuration_file='/home/cad/.config/QCAD/QCAD3.conf', qt='5.14.2', observer='native-getters')],
                'Selected native profile differs')
        ctor = records(stderr, 'ICT_LAYOUT17_CTOR ')
        ctors[mode] = constructor_rows(ctor, fields, mode)
        alone = records(stdout, 'ICT_LAYOUT17_DETACHED ')
        require(len(alone) == freeze['detached_per_mode'], 'Detached coverage differs')
        detached(alone[0], fields, keys, mode)
        rows = records(stdout, 'ICT_LAYOUT17_JOB ')
        require([r['id'] for r in rows] == [j['id'] for j in jobs] and len(rows) == freeze['jobs_per_mode'], 'Native job coverage differs')
        for row, job in zip(rows, jobs):
            require('error' not in row and row['filter'] == filters[job['importer']] and
                    row['import_code'] == (None if job['input'] is None else 0), 'Native import failed/changed')
        modes[mode] = {r['id']: {phase: inventory(r[phase], keys) for phase in ('initial', 'imported')} for r in rows}
    comparisons = []
    targets = {f['getter'] for f in fields if f['type'] != 'tab'}
    for left, right in itertools.combinations(freeze['modes'], 2):
        for job in jobs:
            for phase in ('initial', 'imported'):
                delta = changes(modes[left][job['id']][phase], modes[right][job['id']][phase])
                def target(change):
                    parts = change['path'].split('/')
                    if len(parts) < 8 or parts[1:3] != ['headers', 'layouts'] or parts[4] != 'properties':
                        return False
                    props = modes[left][job['id']][phase]['headers']['layouts'].get(parts[3], {}).get('properties', [])
                    return parts[5].isdigit() and int(parts[5]) < len(props) and props[int(parts[5])]['getter'] in targets
                comparisons.append(dict(left=left, right=right, id=job['id'], phase=phase,
                                        target_differences=sum(target(c) for c in delta),
                                        non_target_differences=sum(not target(c) for c in delta), differences=delta))
    attribution = []
    for job in jobs:
        for phase in ('initial', 'imported'):
            # Names identify only the attribution table; the full comparison above preserves IDs and all other differences.
            layouts = {}
            for mode in freeze['modes']:
                layouts[mode] = {}
                for layout in modes[mode][job['id']][phase]['headers']['layouts'].values():
                    props = {p['getter']: p['value'] for p in layout['properties']}
                    name = encoded(props['getName'])
                    require(name not in layouts[mode], 'Ambiguous layout name in attribution')
                    layouts[mode][name] = props
            require(all(set(v) == set(layouts['observe']) for v in layouts.values()), 'Layout names differ across modes')
            for name in sorted(layouts['observe']):
                for field in fields[:-1]:
                    getter = field['getter']
                    values = {mode: layouts[mode][name][getter] for mode in freeze['modes']}
                    follows = all(equal(values[mode], dict(type='boolean' if field['type'] == 'bool' else 'number',
                                                          value=field['expected_detached'][mode])) for mode in ('preset-a', 'preset-b'))
                    attribution.append(dict(id=job['id'], phase=phase, layout=json.loads(name), getter=getter,
                                            follows_presets=follows, all_modes_equal=all(equal(values['observe'], v) for v in values.values()), values=values))
    require(read(root / 'native/COMPLETE.json') == dict(processes=4, inputs_unchanged=True, whole_cad_qualified=False,
            scope='Diagnostic construction/import observations; no CAD file was saved'), 'Native completion claim differs')
    summary = dict(processes=len(commands), document_jobs=len(jobs) * len(commands), constructors=ctors,
                   constructor_causality_confirmed=True, detached_getters_confirmed=True,
                   observed_constructor_variants=sorted({v for row in ctors.values() for v in row['variants']}),
                   inventory_comparisons=len(comparisons), target_differences=sum(r['target_differences'] for r in comparisons),
                   non_target_differences=sum(r['non_target_differences'] for r in comparisons),
                   attribution_observations=len(attribution),
                   follows_presets={phase: sum(r['follows_presets'] for r in attribution if r['phase'] == phase) for phase in ('initial', 'imported')},
                   all_modes_equal={phase: sum(r['all_modes_equal'] for r in attribution if r['phase'] == phase) for phase in ('initial', 'imported')},
                   whole_cad_qualified=False, cad_files_saved=0, strict_comparison_run=False,
                   exposure=freeze['exposure'])
    return summary, dict(comparisons=comparisons, attribution=attribution)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    summary, detail = analyze(args.root)
    out = args.root / 'analysis'
    out.mkdir(exist_ok=True)
    for name, value in [('summary.json', summary), ('detail.json', detail)]:
        (out / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(summary, indent=2))
