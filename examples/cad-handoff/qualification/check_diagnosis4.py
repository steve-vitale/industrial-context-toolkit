"""Recheck retained layout diagnoses offline. No native engine/UI, new preservation result or visual approval."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile

import ezdxf
import recheck

HERE = Path(__file__).resolve().parent


def viewports(path):
    doc = ezdxf.readfile(path)
    result = []
    for layout in doc.layouts:
        if layout.name == 'Model':
            continue
        rows = []
        for e in layout:
            if e.dxftype() == 'VIEWPORT':
                rows.append(dict(handle=e.dxf.handle, center=list(e.dxf.center), width=e.dxf.width,
                                 height=e.dxf.height, view_center_point=list(e.dxf.view_center_point),
                                 view_height=e.dxf.view_height, status=e.dxf.status, id=e.dxf.id))
        result.append(dict(name=layout.name, block_name=layout.block_record_name, viewport_records=rows))
    return result


def check_variant_receipt(receipt):
    labels = ['original', 'library-save', 'add-main', 'add-main-restore-current', 'set-current-only', 'activate-only']
    recheck.require(receipt['exit'] == 0 and receipt['input_unchanged'] and
                    [r['id'] for r in receipt['rows']] == labels, 'Incomplete diagnostic variant cohort')
    for row in receipt['rows']:
        recheck.require(not row.get('error'), 'Native variant probe error')
        for role in ('source', 'candidate'):
            block = [b for b in row[role] if b['layout'] == 'Qualification sheet']
            recheck.require(len(block) == 1, 'Missing/ambiguous native diagnostic layout')
            wanted = 1 if row['id'].startswith('add-main') else 0
            recheck.require(len(block[0]['entities']) == wanted, 'Retained layout hypothesis outcome changed')
            if wanted:
                entity = block[0]['entities'][0]
                recheck.require(entity['type'] == 47 and entity['bounds'] == [15, 5, 115, 75],
                                'Original display-viewport bounds not observed')
    return 6


def main():
    recheck.method_bindings()
    frozen = recheck.read(HERE / 'LAYOUT-HYPOTHESES-4-FREEZE.json')
    for path, pin in frozen['inputs'].items():
        recheck.require(recheck.ch.digest(recheck.ROOT / path) == pin, 'Changed frozen diagnostic input')
    recheck.require(recheck.text_hash(HERE / 'native-layout-probe.js') == frozen['probe_sha256_lf'], 'Changed native layout probe')
    with tempfile.TemporaryDirectory(prefix='cad-layout-diagnosis-') as temp:
        base = Path(temp)
        raw, inventory = recheck.unpack(HERE / 'diagnosis-4', base / 'diagnosis')
        prior, _ = recheck.unpack(HERE / 'round-2', base / 'prior')
        def saved(value):
            path = recheck.saved_file(value, raw)
            return path if path.exists() else recheck.saved_file(value, prior)
        cases = recheck.read(prior / 'native-validation-2/edited-manifest.json')['cases']
        recheck.require(recheck.read(raw / 'layout-probe-4/manifest.json')['cases'] == cases,
                        'Replacement probe manifest differs from retained native cohort')
        probe = recheck.read(raw / 'layout-probe-4/receipt.json')
        recheck.require(probe['exit'] == 0 and probe['input_unchanged'] and
                        [r['id'] for r in probe['rows']] == [c['id'] for c in cases], 'Incomplete replacement layout probe')
        recheck.require(probe['helper_sha256'] == recheck.ch.digest(HERE / 'native-layout-probe.js'), 'Native probe binding changed')
        before = recheck.read(raw / 'layout-probe-4/before.json')
        recheck.require(set(before) == {c[r] for c in cases for r in ('source', 'candidate')}, 'Omitted input hash')
        comparison = recheck.read(raw / 'layout-probe-4/layout-comparison.json')
        recheck.require([r['id'] for r in comparison['cases']] == [c['id'] for c in cases], 'Incomplete retained layout comparison')
        losses = 0
        for case, observed, native in zip(cases, comparison['cases'], probe['rows']):
            for role in ('source', 'candidate', 'native_default', 'native_r15'):
                path = recheck.saved_file(case[role], prior)
                recheck.require(recheck.ch.digest(path) == observed['input_pins'][role], 'Changed retained layout source/return')
                recheck.require(viewports(path) == observed['routes'][role], 'Retained viewport fields do not reproduce')
                if role in ('source', 'candidate'):
                    recheck.require(recheck.ch.digest(path) == before[case[role]], 'Before-render input hash differs')
            if case['id'].startswith('validation-') and case['id'] != 'validation-r12':
                layouts = observed['routes']['source']
                display = next(l for l in layouts if l['name'] == 'Qualification sheet')['viewport_records']
                recheck.require(len(display) == 1 and display[0]['id'] != 1, 'Authored source viewport structure changed')
                for role in ('source', 'candidate'):
                    block = [b for b in native[role] if b['layout'] == 'Qualification sheet']
                    recheck.require(len(block)==1 and not block[0]['entities'], 'Blank imported layout no longer reproduces retained observation')
                fields = ('center', 'width', 'height', 'view_center_point', 'view_height')
                original_view = {k: display[0][k] for k in fields}
                for role in ('native_default', 'native_r15'):
                    returned = next(l for l in observed['routes'][role] if l['name'] == 'Qualification sheet')['viewport_records']
                    recheck.require(returned and all({k: v[k] for k in fields} != original_view for v in returned),
                                    'Original authored display viewport unexpectedly retained')
                losses += 1
        recheck.require(losses == 5, 'Omitted authored viewport failure')
        hypotheses = recheck.read(raw / 'layout-hypotheses-4/receipt.json')
        recheck.require(hypotheses['helper_sha256'] == recheck.ch.digest(HERE / 'native-layout-probe.js'),
                        'Diagnostic probe helper changed')
        manifest = recheck.read(raw / 'layout-hypotheses-4/manifest.json')
        recheck.require(manifest == recheck.read(HERE / 'history/layout-diagnosis-4-inputs/manifest.json'),
                        'Diagnostic manifest changed after freeze')
        for case in manifest['cases']:
            recheck.require(case['source'] == case['candidate'] and
                            recheck.ch.digest(saved(case['source'])) == case['sha256'] ==
                            recheck.ch.digest(HERE / 'history/layout-diagnosis-4-inputs' / (case['id'] + '.dxf')),
                            'Native diagnostic input differs from frozen revision')
        check_variant_receipt(hypotheses)
        # A saved-record control must fail if one failed or successful variant disappears.
        altered = json.loads(json.dumps(hypotheses))
        altered['rows'].pop(2)
        try:
            check_variant_receipt(altered)
        except ValueError as error:
            recheck.require('Incomplete diagnostic variant cohort' in str(error), 'Wrong omission refusal')
        else:
            raise ValueError('Omitted diagnostic variant accepted')
        render = recheck.read(raw / 'render-diagnosis-4/receipt.json')
        recheck.require(render['plan']['driver_sha256_lf'] == recheck.text_hash(HERE / 'render_diagnosis4.py'),
                        'Render diagnostic driver changed')
        recheck.require(len(render['results']) == len(render['plan']['jobs']) == 10, 'Omitted render diagnostic')
        for job, result in zip(render['plan']['jobs'], render['results']):
            recheck.require(all(job[k] == result[k] for k in ('id', 'input', 'window', 'block', 'input_sha256')),
                            'Render plan/result changed')
            recheck.require(result['exit'] == 0 and result['input_unchanged'] and
                            recheck.ch.digest(saved(job['input'])) == job['input_sha256'], 'Changed/failed render input')
            image = raw / 'render-diagnosis-4' / (job['id'] + '.png')
            recheck.require(recheck.ch.digest(image) == result['image_sha256'], 'Changed native PNG')
            png = image.read_bytes()
            recheck.require(png[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', png[16:24]) == (3200, 2200), 'Changed image dimensions')
        print(f"{inventory['files']} pinned records; 12 replacement layout comparisons; five retained viewport losses; six hypotheses; ten native PNGs; omission control passes")
    print('Frozen preservation methods unchanged. Display/UI qualification remains incomplete; no native engine rerun.')


if __name__ == '__main__':
    main()
