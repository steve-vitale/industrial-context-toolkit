"""Author declared CAD test profiles without running the preservation candidate.

This is a qualification fixture adapter, not asset extraction. Originals are retained;
library serialization during adaptation is not claimed byte-preserving.
"""
import argparse
import hashlib
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import cad_handoff as ch

LAYER = 'ICT_QUAL_TEST_ONLY'
FIELDS = ('MANUFACTURER', 'MODEL', 'SERIAL', 'SIZE')


def text_sha(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def adapt(source, identity, target):
    doc = ch.load(source)
    if LAYER in doc.layers:
        raise ch.InputError('Reserved authored-test layer already exists; do not alter it')
    doc.layers.new(LAYER, dxfattribs={'color': 7})
    refs = sorted(doc.modelspace().query('INSERT'), key=lambda e: e.dxf.handle)
    anchor = False
    if not refs:
        name = 'ICT_QUAL_TEST_ANCHOR'
        if name in doc.blocks:
            raise ch.InputError('Reserved authored-test block already exists')
        block = doc.blocks.new(name)
        block.add_circle((0, 0), 2, dxfattribs={'layer': LAYER})
        refs = [doc.modelspace().add_blockref(name, (0, 0), dxfattribs={'layer': LAYER})]
        anchor = True
    changes, additions = [], []
    for index, ref in enumerate(refs, 1):
        attrs = {}
        for a in ref.attribs:
            if a.dxf.tag in attrs:
                raise ch.InputError('Duplicate original attribute: ' + a.dxf.tag)
            attrs[a.dxf.tag] = a.dxf.text
        for key in ('ICT_ID', 'TAG'):
            if key in attrs and not attrs[key].strip():
                raise ch.InputError('Existing empty identity/tag is not overwritten')
        field = next((key for key in FIELDS if key not in attrs), None)
        if field is None:
            raise ch.InputError('No unused editable field for an authored test; existing values not replaced')
        authored = {field: 'QUAL-BEFORE'}
        if 'ICT_ID' not in attrs:
            authored['ICT_ID'] = 'AUTHORED-QUAL/' + identity + '/' + str(index)
        if 'TAG' not in attrs:
            authored['TAG'] = 'QA-' + str(index)
        point = ref.dxf.insert
        for offset, (key, value) in enumerate(authored.items()):
            ref.add_attrib(key, value, (point.x + 3, point.y - 3 * offset, point.z),
                           dxfattribs={'height': 1.5, 'layer': LAYER})
        stable_id = attrs.get('ICT_ID', authored.get('ICT_ID'))
        additions.append(dict(handle=ref.dxf.handle, attributes=authored))
        changes.append(dict(id=stable_id, attribute=field, before='QUAL-BEFORE', after='QUAL-AFTER',
                            reason='Authored preservation-test value only; not installed equipment information'))
    # Detect duplicate retained identities before emitting a derived fixture.
    ch.assets(doc)
    doc.modelspace().add_text('AUTHORED QUALIFICATION ANNOTATIONS - NO INSTALLED IDENTITY',
        dxfattribs={'height': 1.5, 'layer': LAYER, 'insert': (0, -15)})
    doc.saveas(target)
    plan = dict(schema='cad-edit-plan-1', source_sha256=ch.digest(target), changes=changes)
    return plan, dict(authored_anchor=anchor, added_layer=LAYER, additions=additions,
                     boundary='Library-reserialized derived fixture; no byte preservation from public original claimed')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--selection', type=Path, required=True)
    ap.add_argument('--freeze', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        ap.error('Output exists; keep prior evidence')
    freeze = json.loads(args.freeze.read_bytes())
    for method in (Path(__file__), ROOT / 'scripts/cad_handoff.py'):
        rel = method.resolve().relative_to(ROOT).as_posix()
        if freeze['methods'].get(rel) != text_sha(method):
            ap.error('Method differs from prior freeze: ' + rel)
    relative = args.selection.resolve().relative_to(ROOT).as_posix()
    if freeze['manifests'].get(relative) != text_sha(args.selection):
        ap.error('Selection differs from prior freeze')
    selected = json.loads(args.selection.read_bytes())
    args.out.mkdir(parents=True)
    records = []
    for item in selected['cases']:
        source = args.selection.parent / item['source']
        record = dict(id=item['id'], split='public-adapted', original_sha256=item['source_sha256'])
        folder = args.out / item['id']
        folder.mkdir()
        try:
            raw = source.read_bytes()
            if ch.digest(source) != item['source_sha256']:
                raise ch.InputError('Selected original hash changed')
            (folder / 'original.dxf').write_bytes(raw)
            try:
                snap = ch.snapshot(source)
                record['original_admission'] = dict(status='pass', profiled_assets=len(snap['assets']))
            except Exception as error:
                record['original_admission'] = dict(status='refused', error=f'{type(error).__name__}: {error}')
            target = folder / 'adapted.dxf'
            plan, recipe = adapt(source, item['id'], target)
            planpath = folder / 'edit-plan.json'
            ch.write_json(planpath, plan)
            ch.write_json(folder / 'adaptation.json', recipe)
            record.update(source=target.relative_to(args.out).as_posix(), source_sha256=ch.digest(target),
                          plan=planpath.relative_to(args.out).as_posix(), plan_sha256=ch.digest(planpath))
        except Exception as error:
            record.update(admission_error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
        records.append(record)
        print(item['id'], record.get('admission_error', 'adapted; candidate not run'), flush=True)
    manifest = dict(schema='cad-authored-public-adaptation-2',
                    adaptation=dict(selection=relative, selection_sha256_lf=text_sha(args.selection),
                                    recipe_sha256_lf=text_sha(Path(__file__)), freeze_sha256_lf=text_sha(args.freeze)),
                    cases=records,
                    scope='Public geometry with explicitly authored annotations, not untouched plant truth; no candidate run')
    ch.write_json(args.out / 'MANIFEST.json', manifest)
    return int(any(row.get('admission_error') for row in records))


if __name__ == '__main__':
    raise SystemExit(main())
