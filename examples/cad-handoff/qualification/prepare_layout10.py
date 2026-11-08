"""Propose a minimal main-viewport source revision; exposed development, not accepted CAD repair."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'scripts'))
import cad_handoff as ch
import cad_value_patch as value_patch
from ezdxf.lldxf.encoding import encode


def records(raw):
    tags = value_patch.source_tags(raw)
    lines = raw.splitlines(keepends=True)
    result, record, offset = [], None, 0
    for i, tag in enumerate(tags):
        if tag[0] == 0:
            if record is not None:
                record['end'] = offset
                result.append(record)
            record = dict(start=offset, kind=tag[1], tags=[], newline=lines[2*i][len(value_patch.body(lines[2*i])):])
        if record is None:
            raise ch.InputError('Tags before the first DXF record')
        record['tags'].append(tag)
        offset += len(lines[2*i]) + len(lines[2*i+1])
    record['end'] = len(raw)
    result.append(record)
    return result


def own_handle(record):
    if record['kind'] in (b'SECTION',b'ENDSEC',b'EOF'):
        return None
    code = 105 if record['kind'] == b'DIMSTYLE' else 5
    tags = record['tags']
    if code == 5:
        tags = tags[:next((i for i,t in enumerate(tags) if t[0] == 100),len(tags))]
    values = [t[1] for t in tags if t[0] == code]
    if len(values) > 1:
        raise ch.InputError('Ambiguous raw record handle')
    if not values:
        return None
    value=values[0].strip()
    if not re.fullmatch(rb'[0-9A-Fa-f]{1,16}',value) or int(value,16)==0:
        raise ch.InputError('Invalid raw record handle')
    return value.decode('ascii').upper()


def owner(record):
    depth, values = 0, []
    for code, value, *_ in record['tags']:
        if code == 100:
            break
        if code == 102:
            depth += 1 if value.startswith(b'{') else -1 if value == b'}' else 0
        if code == 330 and depth == 0:
            values.append(value.strip().decode('ascii').upper())
    if depth or len(values) != 1:
        raise ch.InputError('Missing/ambiguous raw entity ownership')
    return values[0]


def main_fields(layout):
    d = layout.dxf_layout.dxf
    names = ('paper_width','paper_height','left_margin','right_margin','top_margin','bottom_margin',
             'plot_origin_x_offset','plot_origin_y_offset','scale_numerator','scale_denominator')
    values = {name:float(getattr(d,name)) for name in names}
    if (not all(math.isfinite(v) for v in values.values()) or d.plot_paper_units not in (0,1)
            or any(values[n]<=0 for n in ('paper_width','paper_height','scale_numerator','scale_denominator'))
            or any(values[n]<0 for n in ('left_margin','right_margin','top_margin','bottom_margin'))
            or values['left_margin']+values['right_margin'] >= values['paper_width']
            or values['top_margin']+values['bottom_margin'] >= values['paper_height']):
        raise ch.InputError('Nonfinite/invalid paper settings')
    center, size = layout.default_viewport_config()
    if not all(math.isfinite(v) for v in (*center,*size)) or min(size)<=0:
        raise ch.InputError('Invalid derived main viewport bounds')
    return center, size


def propose(source):
    source = Path(source)
    raw = source.read_bytes()
    groups = records(raw)
    doc = ch.load(source)
    if doc.dxfversion < 'AC1015':
        raise ch.InputError('Layout preparation supports text DXF R2000 or later')
    handles = {}
    for record in groups:
        handle = own_handle(record)
        if handle:
            if handle in handles:
                raise ch.InputError('Duplicate source record handle')
            handles[handle] = record
    header = [r for r in groups if r['kind']==b'SECTION' and r['tags'][1][:2]==(2,b'HEADER')]
    if len(header)!=1:
        raise ch.InputError('Missing/ambiguous HEADER')
    tags = header[0]['tags']
    seeds = [tags[i+1] for i,t in enumerate(tags[:-1]) if t[:2]==(9,b'$HANDSEED')]
    if len(seeds)!=1 or seeds[0][0]!=5 or not re.fullmatch(rb'[0-9a-fA-F]{1,16}',seeds[0][1].strip()):
        raise ch.InputError('Missing/ambiguous HANDSEED')
    seed = seeds[0]
    next_handle = max(int(seed[1],16),max((int(h,16)+1 for h in handles),default=1))
    edits, revisions = [], []
    for layout in doc.layouts:
        if layout.name == 'Model':
            continue
        if any(ord(c)<32 or c in '\x7f\x85\u2028\u2029' for c in layout.name):
            raise ch.InputError('Layout name is not a plain single line')
        entities = list(layout)
        viewports = [e for e in entities if e.dxftype()=='VIEWPORT']
        mains = [e for e in viewports if e.dxf.id==1]
        if len(mains)>1:
            raise ch.InputError('Duplicate main viewports')
        if mains:
            if entities[0] is not mains[0]:
                raise ch.InputError('Existing main viewport is not first; no silent reorder')
            continue
        if not viewports:
            continue
        for entity in entities:
            handle = entity.dxf.handle.upper()
            if handle not in handles or owner(handles[handle]) != layout.layout_key.upper():
                raise ch.InputError('Source entity-space/raw ownership differs')
        first = handles[entities[0].dxf.handle.upper()]
        center, size = main_fields(layout)
        if next_handle >= 2**64-1:
            raise ch.InputError('Handle allocation exhausted')
        handle = format(next_handle,'X');next_handle += 1
        pairs = [(0,'VIEWPORT'),(5,handle),(330,layout.layout_key),(100,'AcDbEntity'),
                 (67,1),(8,'0'),(410,layout.name),(100,'AcDbViewport'),
                 (10,center[0]),(20,center[1]),(30,0.0),(40,size[0]),(41,size[1]),
                 (68,1),(69,1),(12,center[0]),(22,center[1]),
                 (16,0.0),(26,0.0),(36,1.0),(17,0.0),(27,0.0),(37,0.0),
                 (45,size[1]),(51,0.0),(90,557088)]
        newline = first['newline']
        addition = b''.join(str(code).encode('ascii')+newline+encode(str(value),doc.output_encoding)+newline
                            for code,value in pairs)
        edits.append(dict(source_start=first['start'],source_end=first['start'],before_hex='',after_hex=addition.hex()))
        revisions.append(dict(layout=layout.name,owner=layout.layout_key,new_main_handle=handle,
                              center=list(center),size=list(size),original_first_handle=entities[0].dxf.handle,
                              original_current_viewport=layout.dxf_layout.dxf.get('viewport_handle')))
    if revisions:
        edits.append(dict(source_start=seed[2],source_end=seed[3],before_hex=seed[1].hex(),
                          after_hex=format(next_handle,'X').encode('ascii').hex()))
    edits.sort(key=lambda e:e['source_start'])
    proposed = value_patch.patch_bytes(raw,edits)
    return proposed,dict(schema='cad-main-viewport-revision-1',source_sha256=hashlib.sha256(raw).hexdigest(),
        prepared_sha256=hashlib.sha256(proposed).hexdigest(),
        status='proposed_source_revision' if revisions else 'exact_noop',layouts=revisions,edits=edits,
        scope='New main viewport(s) and HANDSEED only; original display viewports/current references and all other bytes unchanged',
        authority='Proposed compatibility revision only; original retained; no accepted engineering/company revision',
        native_acceptance='not established')


def apply(source,out):
    source,out = Path(source),Path(out)
    if out.exists():
        raise ch.InputError('Output exists; retain the earlier proposal')
    prepared,receipt = propose(source)
    original = source.read_bytes()
    if hashlib.sha256(original).hexdigest()!=receipt['source_sha256']:
        raise ch.InputError('Source changed during proposal')
    with tempfile.TemporaryDirectory(prefix='ict-layout-proposal-') as temp:
        root=Path(temp)
        (root/'original.dxf').write_bytes(original)
        (root/'prepared.dxf').write_bytes(prepared)
        # Retain, never waive, strict differences from this deliberate source revision.
        before,after = ch.snapshot(root/'original.dxf'),ch.snapshot(root/'prepared.dxf')
        comparison = ch.compare(before,after,{'source_sha256':receipt['source_sha256'],'changes':[]})
        ch.write_json(root/'original-to-prepared-strict.json',comparison)
        ch.write_json(root/'revision.json',receipt)
        if source.read_bytes()!=original:
            raise ch.InputError('Source changed before publication')
        shutil.copytree(root,out)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=apply(args.source,args.out)
    except (ValueError,OSError,ch.ezdxf.DXFError) as error:
        print('ERROR:',error,file=sys.stderr);return 2
    print(result['status'],len(result['layouts']),'new main viewport(s); engineering/native acceptance unproved')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
