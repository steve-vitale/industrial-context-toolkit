"""Recompute retained exposed font/camera controls; no GUI execution or qualification."""
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import zlib

from PIL import Image, ImageChops, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_linux7 as old
import check_receiver8

BASE = HERE / 'font-views-9'
require, read, ch = old.require, old.read, old.ch
CROP = (114, 175, 1647, 1207)
CASES = ('validation-cp1251', 'validation-long', 'validation-unicode')
CORRECTED = 'cd38b40cd3c492c40865d48c4f5615c1da320cc30fefc0e25e2f00d3e69d41c9'
IMAGE = 'sha256:bb4390214744897de88b2198f0cbf812aec4be42923311298e7a5e3a5646bef8'


def close(a, b):
    if isinstance(a, list):
        require(len(a) == len(b), 'Native bounds/camera length differs')
        for x, y in zip(a, b):
            close(x, y)
    else:
        require(math.isfinite(a) and math.isfinite(b) and abs(a-b) < 1e-7,
                'Native numerical bounds/projection differs')


def union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def projected(box, view):
    x1, y1, x2, y2 = box
    ox, oy = view['offset']
    f, h = view['factor'], view['height']
    return [(x1+ox)*f, h-(y2+oy)*f, (x2+ox)*f, h-(y1+oy)*f]


def camera(receipt):
    asset_id = receipt['request']['asset_id']
    boxes = []
    for role in ('source', 'candidate'):
        item = receipt['pair'][role]
        if asset_id == '__ALL__':
            boxes.append(item['all_bounds'])
        else:
            asset = item['assets'][asset_id]
            boxes += [asset['insert_bounds']] + [a['bounds'] for a in asset['attributes']]
    united = union(boxes)
    pad = max(2, .2*max(united[2]-united[0], united[3]-united[1]))
    frame = [united[0]-pad, united[1]-pad, united[2]+pad, united[3]+pad]
    close(receipt['union'], united)
    close(receipt['frame'], frame)
    view = receipt['view']
    require((view['width'], view['height']) == (1533, 1032) and view['factor'] > 0,
            'Native canvas size/factor differs')
    corners = [projected(box, view) for box in boxes]
    close(receipt['projected'], corners)
    require(all(0 <= x1 <= x2 < view['width'] and 0 <= y1 <= y2 < view['height']
                for x1, y1, x2, y2 in corners), 'Requested native bounds clipped')
    require(receipt['loaded_file'] == receipt['request'][receipt['request']['role']],
            'Wrong active native document')


def attributes(item, expected, mapped):
    require(set(item['assets']) == set(expected), 'Native asset identity differs')
    for identity, wanted in expected.items():
        attrs = item['assets'][identity]['attributes']
        require(len(attrs) == len(wanted) and len({a['tag'] for a in attrs}) == len(attrs),
                'Native field omitted/duplicated')
        require({a['tag']:a['text'] for a in attrs} == wanted,
                'Native planned or foreign attribute value differs')
        require(len({a['parent'] for a in attrs}) == 1, 'Native parent binding differs')
        for attr in attrs:
            font = attr['font']
            require(font['requested'] == 'Standard', 'Unexpected requested font')
            if mapped:
                require(font['mapped'] == font['resolved_family'] == 'DejaVu Sans'
                        and font['cad_font'] is False and font['missing_characters'] == []
                        and font['glyph_check'] == 'QFontMetrics.inFont'
                        and 'glyph_check_error' not in font, 'Native mapped glyph probe failed')
            else:
                require(font['mapped'] == 'Standard' and font['cad_font'] is True
                        and font['cad_path'] == '/opt/qcad/fonts/Standard.cxf', 'Default font differs')


def change_field(receipt, tag, text):
    attrs = receipt['pair']['candidate']['assets']['validation-cp1251/asset-1']['attributes']
    next(a for a in attrs if a['tag'] == tag)['text'] = text


def decoded(path):
    with Image.open(path) as image:
        require(image.size == (2400, 1400), 'Full native desktop size differs')
        return image.convert('RGB')


def filtered_hash(path):
    raw, pos, chunks = path.read_bytes(), 8, []
    while pos < len(raw):
        length = struct.unpack('>I', raw[pos:pos+4])[0]
        if raw[pos+4:pos+8] == b'IDAT':
            chunks.append(raw[pos+8:pos+8+length])
        pos += length + 12
    return hashlib.sha256(zlib.decompress(b''.join(chunks))).hexdigest()


def stable(work, seqs, directory='views-corrected'):
    views = work / directory
    actions = read(views / 'actions.json')
    require(all(a['exit'] == 0 for a in actions if 'command' in a), 'Failed native capture command')
    finals = {p.name for p in views.glob('*.png') if '-frame-' not in p.name}
    require(finals == {f'{s}.png' for s in seqs}, 'Native view coverage differs')
    for seq in seqs:
        frames = sorted(views.glob(f'{seq}-frame-*.png'))
        require(2 <= len(frames) <= 10, 'Stable frame observations missing')
        for path in frames:
            require(any(a.get('frame') == path.name and a['filtered_image_sha256'] == filtered_hash(path)
                        for a in actions), 'Image-data hash receipt differs')
        require(ImageChops.difference(decoded(frames[-2]), decoded(frames[-1])).getbbox() is None,
                'Consecutive final native frames differ')
        require((views/f'{seq}.png').read_bytes() == frames[-1].read_bytes(), 'Final frame differs')
    motion = [a['command'] for a in actions if a.get('command', [''])[0] == 'xdotool']
    inside = '1220' if directory == 'views' else '1180'
    require(motion == [['xdotool','mousemove','1590',inside], ['xdotool','mousemove','2380','1380']]*len(seqs),
            'Pointer traversal differs')


def pixel_diagnostic(a, b, receipt):
    delta = ImageChops.difference(a, b)
    mask = Image.new('1', a.size)
    boxes = []
    for item in receipt['pair'].values():
        for asset in item['assets'].values():
            for attr in asset['attributes']:
                if attr['tag'] == 'MODEL':
                    box = projected(attr['bounds'], receipt['view'])
                    boxes.append([math.floor(box[0]), math.floor(box[1]), math.ceil(box[2]), math.ceil(box[3])])
    raw = delta.tobytes()
    changed = [(i//3 % a.width, i//3 // a.width) for i in range(0,len(raw),3) if any(raw[i:i+3])]
    counts = {}
    for padding in (0,2):
        draw = ImageDraw.Draw(mask)
        draw.rectangle((0,0,a.width-1,a.height-1),fill=0)
        for x1,y1,x2,y2 in boxes:
            draw.rectangle((x1-padding,y1-padding,x2+padding,y2+padding),fill=1)
        counts[str(padding)] = sum(not mask.getpixel(point) for point in changed)
    return dict(different_pixels=len(changed), bbox=list(delta.getbbox()) if delta.getbbox() else None,
                outside_model_bounds=counts)


def check():
    old.recheck.method_bindings()
    freeze = read(BASE/'FREEZE.json')
    require(read(HERE/'linux-native-7/INVENTORY.json')['archive']['sha256'] == freeze['input_archive_sha256'],
            'Earlier input archive differs')
    require(old.recheck.text_hash(HERE/'package_font9.py') == read(BASE/'INVENTORY.json')['packager_sha256_lf'],
            'Evidence packager differs')
    for name in ('native_views.js','desktop.sh'):
        require(old.recheck.text_hash(BASE/name) == freeze['methods_lf'][name], 'Frozen native recipe differs')
    require(old.recheck.text_hash(BASE/'capture.py') == CORRECTED, 'Corrected capture differs')
    rows, native_count, refusals = [], 0, []
    with tempfile.TemporaryDirectory(prefix='ict-font9-replay-') as temporary:
        root = Path(temporary)
        raw = old.unpack(BASE,root/'evidence')
        expected = {}
        for case in CASES:
            source = HERE/'validation-2/authored'/f'{case}.dxf'
            plan = read(source.with_suffix('.plan.json'))
            old.cad_value_patch.apply(source,plan,root/case)
            candidate = root/case/'candidate.dxf'
            require(old.verify(source,candidate,plan)['unplanned_byte_changes'] == 0, 'Unplanned bytes')
            require(ch.compare(ch.snapshot(source),ch.snapshot(candidate),plan)['unexpected'] == [], 'Strict failure')
            expected[case] = {role:{a['id']:a['attributes'] for a in ch.snapshot(path)['assets']}
                              for role,path in (('source',source),('candidate',candidate))}
            for folder in ('default','default-replay-2','substitute'):
                for role,path in (('source',source),('candidate',candidate)):
                    name = f'{case}-{role}.dxf'
                    pin = freeze['inputs']['raw/visual-inputs/'+name]
                    actual = raw/folder/name
                    require(actual.read_bytes() == path.read_bytes() and ch.digest(actual) == pin['sha256']
                            and actual.stat().st_size == pin['bytes'], 'Native viewed input differs')
        environments = {}
        for folder in ('default','default-replay-2','substitute'):
            work = raw/folder
            env, notes, setup = (read(work/name) for name in ('environment.json','HOST-NOTES.json','SETUP.json'))
            environments[folder] = env
            require(env['Image'] == IMAGE and env['State'] == read(work/'terminal.json'), 'Receiver identity/state differs')
            check_receiver8.normal_exit(env['State'])
            require(notes['capture_exit'] == (1 if folder=='default' else 0) and
                    notes['premature_quit'] == (folder=='default'), 'Capture terminal evidence differs')
            require(setup['plan_commit'] == '5767878' and setup['method_commit'] == '9c64546'
                    and setup['profile_sha256'] == '5d2fe06c831c2c8032d446d51801a73f754cd120a2c0b415e051483c81b14550',
                    'Declared profile identity differs')
            require('FONT_PROFILE='+('substitute' if folder=='substitute' else 'default') in env['Config']['Env'],
                    'Native font environment differs')
            for name in ('native_views.js','desktop.sh','capture.py'):
                require((work/name).read_bytes() == (BASE/name).read_bytes().replace(b'\r\n',b'\n'),
                        'Executed method differs: '+name)
            require(read(work/'CORRECTED-METHOD.json')['capture_sha256_lf'] == CORRECTED, 'Correction binding differs')
        require(environments['default-replay-2']['State']['FinishedAt'] < environments['substitute']['State']['StartedAt'],
                'Matched native batches overlapped')
        failed = raw/'default'
        require(old.recheck.text_hash(failed/'capture-initial.py') == freeze['methods_lf']['capture.py'],
                'Initial failed recipe omitted')
        stable(failed,range(18),'views')
        require(not (failed/'views-corrected/actions.json').exists()
                and len(list((failed/'views-corrected').glob('*.png'))) == 42,
                'Incomplete corrected batch upgraded/omitted')
        require({p.stem for p in (failed/'receipts').glob('*.json')} ==
                {str(n) for n in range(18)} | {str(n) for n in range(100,114)}, 'Failed receipts differ')
        for folder in ('default-replay-2','substitute'):
            work, mapped = raw/folder, folder=='substitute'
            requests = read(work/'requests-corrected.json')
            require([r['seq'] for r in requests] == list(range(100,118)), 'Matched request cohort differs')
            stable(work,range(100,118))
            require({p.stem for p in (work/'receipts').glob('*.json')} == {str(n) for n in range(100,118)},
                    'Receipt coverage differs')
            seen = {}
            for request in requests:
                receipt = read(work/'receipts'/f"{request['seq']}.json")
                require(receipt['request'] == request, 'Request binding differs')
                case = request['case_id']
                require(case in CASES, 'Unexpected case')
                if case in seen:
                    require(seen[case] == receipt['pair'], 'Repeated native import metadata differs')
                else:
                    seen[case] = receipt['pair']
                    for role in ('source','candidate'):
                        attributes(receipt['pair'][role],expected[case][role],mapped)
                        native_count += sum(len(a) for a in expected[case][role].values())
                camera(receipt)
            expected_jobs = [(case,asset,role) for case in CASES
                             for asset in ['__ALL__']+sorted(expected[case]['source'])
                             for role in ('source','candidate')]
            require([(r['case_id'],r['asset_id'],r['role']) for r in requests] == expected_jobs,
                    'Case/asset/role coverage differs')
            for a,b in zip(requests[::2],requests[1::2]):
                left, right = [read(work/'receipts'/f"{r['seq']}.json") for r in (a,b)]
                require(left['frame'] == right['frame'] and left['view'] == right['view'], 'Matched cameras differ')
                diagnostic = pixel_diagnostic(decoded(work/'views-corrected'/f"{a['seq']}.png").crop(CROP),
                                              decoded(work/'views-corrected'/f"{b['seq']}.png").crop(CROP),left)
                rows.append(dict(profile=folder,case=a['case_id'],asset=a['asset_id'],
                                 source_seq=a['seq'],candidate_seq=b['seq'],**diagnostic))
            manifest = read(work/'font-manifest.json')
            chars = sorted(set(''.join(value for case in expected.values() for role in case.values()
                                      for asset in role.values() for value in asset.values())))
            require(manifest['required_characters'] == chars, 'Font coverage characters differ')
            missing = [c for c in chars if not c.isspace() and ord(c) not in manifest['standard_cxf_header_codes']]
            require(missing == manifest['standard_cxf_missing_characters'] and len(missing)==13,
                    'Default missing-glyph evidence differs')
            require([f['sha256'] for f in manifest['fonts']] ==
                    ['6e482dd6c45bd3738d6e8cc3661d82193b6385eac613b2d15730bf91a303b18a',
                     'ae7b7855e115a5966d8b1b3f80f254ccc117ec86f9965e202ee2940453837280'], 'Font identities differ')
            require(manifest['fontconfig_match'] == ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','DejaVu Sans'],
                    'Font resolution differs')
            require((work/'font_manifest.py').read_bytes() == (BASE/'font_manifest.py').read_bytes().replace(b'\r\n',b'\n'),
                    'Font observer differs')
        require(rows == read(BASE/'pixel-diagnostic.json'), 'Pixel diagnostic does not reproduce')
        require(native_count == 144, 'Unique attribute count differs')
        require(all(r['outside_model_bounds']['0']==0 for r in rows if r['profile']=='substitute'),
                'Mapped canvas differences outside exact planned label bounds')
        geometry = read(raw/'substitute/canvas-geometry.json')
        require(any(g['name']=='Drawing View' and g['rectangle']==[114,175,1533,1032] for g in geometry),
                'Actual native canvas geometry differs')
        require((raw/'substitute/canvas_geometry.py').read_bytes() ==
                (BASE/'canvas_geometry.py').read_bytes().replace(b'\r\n',b'\n'), 'Geometry observer differs')
        review = read(BASE/'VISUAL-REVIEW.json')
        require(review['original_typography_fidelity'] is False and
                [v['path'] for v in review['views']] ==
                [f'{folder}/views-corrected/{seq}.png' for folder in ('default-replay-2','substitute')
                 for seq in range(100,118)], 'Direct inspection coverage differs')
        for name,member in read(BASE/'summary.json')['published_images'].items():
            require((BASE/name).read_bytes() == (raw/member).read_bytes(), 'Published native screenshot differs')
        # Semantic controls bypass archive hashes and exercise the actual acceptance functions.
        sample = read(raw/'substitute/receipts/102.json')
        for name,mutate in (
            ('planned_value',lambda r:change_field(r,'MODEL','wrong')),
            ('foreign_value',lambda r:change_field(r,'VENDOR_PRIVATE','lost')),
            ('missing_glyph',lambda r:r['pair']['candidate']['assets']['validation-cp1251/asset-1']['attributes'][0]['font'].update(missing_characters=['Ж'])),
            ('clipped_camera',lambda r:r['view'].update(offset=[10000,10000])),
            ('wrong_document',lambda r:r.update(loaded_file=r['request']['candidate'])),
        ):
            bad=copy.deepcopy(sample);mutate(bad)
            try:
                attributes(bad['pair']['candidate'],expected['validation-cp1251']['candidate'],True)
                camera(bad)
            except ValueError:
                refusals.append(name)
            else:
                raise ValueError('Planted receiving error accepted: '+name)
        a=decoded(raw/'substitute/views-corrected/102.png').crop(CROP)
        b=decoded(raw/'substitute/views-corrected/103.png').crop(CROP)
        pixel=b.getpixel((0,0));b.putpixel((0,0),(255-pixel[0],255-pixel[1],255-pixel[2]))
        require(pixel_diagnostic(a,b,sample)['outside_model_bounds']['0'] > 0, 'Unplanned canvas pixel accepted')
        refusals.append('unplanned_canvas_pixel')
        try:
            stable(raw/'substitute',range(100,117))
        except ValueError:
            refusals.append('omitted_view')
        else:
            raise ValueError('Omitted native view accepted')
    summary = read(BASE/'summary.json')
    require(summary['whole_cad_qualified'] is False and summary['native_views']==36
            and summary['unique_native_attributes']==native_count and summary['receiving_refusals']==refusals,
            'Summary differs or partial evidence promoted to qualification')
    print('PASS: 3 exact candidates, 36 stable native views, 144 unique native fields, 18 pixel diagnostics, 7 receiving controls')
    print('Exposed display development only; default glyph/62-pixel, original layout/full-save and fresh-validation gates remain')
    return summary


if __name__ == '__main__':
    check()
