"""Stage exact exposed paper inputs; no CAD process, repair, save or model call."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from native_revisions import HERE, ROOT, read, write, sha, lf, require
from evidence import unpack
import cad_handoff as ch


def window(path, name):
    layout = ch.load(path).layouts.get(name)
    viewports = [v for v in layout.query('VIEWPORT') if v.dxf.id > 1]
    require(bool(viewports), 'Source paper control/frame has no display viewport')
    boxes = [(v.dxf.center.x-v.dxf.width/2, v.dxf.center.y-v.dxf.height/2,
              v.dxf.center.x+v.dxf.width/2, v.dxf.center.y+v.dxf.height/2) for v in viewports]
    x, y = min(b[0] for b in boxes), min(b[1] for b in boxes)
    right, top = max(b[2] for b in boxes), max(b[3] for b in boxes)
    pad = max(2, .2*max(right-x, top-y))
    return [x-pad, y-pad, right+pad, top+pad]


def prepare(out):
    require(not out.exists(), 'Fresh paper preparation folder required')
    out.mkdir(parents=True)
    (out/'inputs').mkdir()
    first = read(HERE/'NATIVE-REVISION-FREEZE-1.json')['inputs']
    second = read(HERE/'SECOND-REVISION-INPUTS.json')['cases']
    audit = read(HERE/'paper-records-1/RESULT.json')['cases']
    jobs = []

    def add(identity, raw, layout, frame, provenance, expected):
        require(hashlib.sha256(raw).hexdigest() == expected, 'Declared paper input differs')
        relative = 'inputs/'+identity+'.dxf'
        (out/relative).write_bytes(raw)
        jobs.append(dict(id=identity, path=relative, sha256=expected, layout=layout,
                         window=frame, provenance=provenance))

    for source in first:
        case = source['case']
        short = case.removeprefix('validation-')
        later = next(row for row in second if row['case'] == case)
        records = next(row for row in audit if row['case'] == case)['documents']
        frame = window(ROOT/source['source'], 'Qualification sheet')
        for role, path, expected in [
            ('original', source['source'], source['source_sha256']),
            ('original_value_candidate', source['candidate'], source['candidate_sha256']),
            ('concurrent_native', later['source'], later['source_sha256']),
            ('selected_second_candidate', later['candidate'], later['candidate_sha256'])]:
            require(records[role]['sha256'] == expected, 'Paper record audit source differs')
            add(short+'-'+role, (ROOT/path).read_bytes(), 'Qualification sheet', frame,
                dict(repository_path=path, record_audit='paper-records-1/RESULT.json'), expected)
        packet = (ROOT/source['baseline_inventory']).parent
        require(lf(packet/'INVENTORY.json') == source['baseline_inventory_sha256_lf'], 'Baseline inventory differs')
        raw = unpack(packet)['attempt/job/returned.dxf']
        add(short+'-noedit_native', raw, 'Qualification sheet', frame,
            dict(packet=packet.relative_to(ROOT).as_posix(), member='attempt/job/returned.dxf',
                 archive_sha256=sha(packet/'evidence.tar.xz')), records['noedit_native']['sha256'])
        path = ROOT/'examples/drawing-handoff/native-second-revision/native-returns'/('validation-'+short+'.dxf')
        provenance = read(path.parent/'PROVENANCE.json') if (path.parent/'PROVENANCE.json').exists() else read(path.parent.parent/'PROVENANCE.json')
        add(short+'-second_native', path.read_bytes(), 'Qualification sheet', frame,
            dict(repository_path=path.relative_to(ROOT).as_posix(), binding=provenance), sha(path))

    control = ROOT/'examples/cad-handoff/qualification/validation-2/public-adapted/text_in_viewports/adapted.dxf'
    manifest = control.parent.parent/'MANIFEST.json'
    row = next(c for c in read(manifest)['cases'] if c['id']=='text_in_viewports')
    require(sha(control)==row['source_sha256'], 'Public-adapted positive control differs')
    for repeat in (1, 2):
        add('public-control-'+str(repeat), control.read_bytes(), 'Layout1', window(control, 'Layout1'),
            dict(repository_path=control.relative_to(ROOT).as_posix(),
                 public_manifest=manifest.relative_to(ROOT).as_posix(), declared_provenance=row,
                 role='Previously exposed derived public positive/repeatability control'), sha(control))
    for name, path in [('render_paper.py', HERE/'render_paper.py'),
                       ('window.py', HERE.parent/'public-validation-11/window.py')]:
        (out/name).write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
    value = dict(scope='Fourteen exposed paper observations; no fresh reserved result',
        image='sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8',
        configuration_sha256=read(HERE/'SECOND-REVISION-PREPARATION-1.json')['configuration_sha256'],
        jobs=jobs, methods_sha256_lf={p.relative_to(ROOT).as_posix():lf(p) for p in
            (HERE/'prepare_paper.py', HERE/'render_paper.py', HERE/'PAPER-RENDER-PLAN.md', HERE.parent/'public-validation-11/window.py')})
    write(out/'MANIFEST.json', value)
    return value


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    args=parser.parse_args()
    result=prepare(args.out)
    print(json.dumps(dict(jobs=len(result['jobs']), configuration_sha256=result['configuration_sha256'])))
