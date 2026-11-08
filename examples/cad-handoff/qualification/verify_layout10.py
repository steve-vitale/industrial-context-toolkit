"""Verify minimal viewport revisions from source/output, without the producer or its span receipt."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

import ezdxf
from ezdxf.lldxf.encoding import decode_dxf_unicode


def require(value,message):
    if not value:
        raise ValueError(message)


def scan(raw):
    require(not raw.startswith(b'AutoCAD Binary DXF') and b'\0' not in raw,'Binary output/source')
    lines=raw.splitlines(keepends=True)
    require(len(lines)%2==0,'Incomplete raw tags')
    groups=[];offset=0
    for n in range(0,len(lines),2):
        require(re.fullmatch(rb'\s*[0-9]{1,4}\s*',lines[n]),'Invalid code line')
        code=int(lines[n]);value=lines[n+1].rstrip(b'\r\n')
        if code==0:
            if groups:groups[-1]['end']=offset
            groups.append(dict(start=offset,tags=[]))
        require(bool(groups),'Tags before record')
        groups[-1]['tags'].append((code,value))
        offset+=len(lines[n])+len(lines[n+1])
    require(groups and groups[-1]['tags']==[(0,b'EOF')],'Missing explicit EOF')
    groups[-1]['end']=offset
    return lines,groups


def handle(group):
    tags=group['tags'];kind=tags[0][1]
    if kind in (b'SECTION',b'ENDSEC',b'EOF'):return None
    if kind==b'DIMSTYLE':values=[v for c,v in tags if c==105]
    else:
        stop=next((i for i,(c,v) in enumerate(tags) if c==100),len(tags))
        values=[v for c,v in tags[:stop] if c==5]
    require(len(values)<=1,'Ambiguous handle')
    return values[0].strip().decode('ascii').upper() if values else None


def header_seed(lines):
    entries=[];in_header=False
    for i in range(0,len(lines),2):
        code,value=int(lines[i]),lines[i+1].rstrip(b'\r\n')
        if code==0 and value==b'SECTION':
            in_header=i+3<len(lines) and int(lines[i+2])==2 and lines[i+3].rstrip(b'\r\n')==b'HEADER'
        elif code==0 and value==b'ENDSEC':in_header=False
        if in_header and code==9 and value==b'$HANDSEED':
            require(i+3<len(lines) and int(lines[i+2])==5,'Wrong HANDSEED code')
            entries.append(i+3)
    require(len(entries)==1,'Missing/ambiguous HEADER HANDSEED')
    return entries[0]


def expected_geometry(layout):
    d=layout.dxf_layout.dxf
    unit=25.4 if d.plot_paper_units==0 else 1.0
    scale=d.scale_denominator/d.scale_numerator/unit
    width=d.paper_width*scale;height=d.paper_height*scale
    cx=(d.paper_width-d.left_margin-d.right_margin)*scale/2-d.plot_origin_x_offset*scale
    cy=(d.paper_height-d.top_margin-d.bottom_margin)*scale/2-d.plot_origin_y_offset*scale
    return {10:cx,20:cy,30:0.,40:width*1.1,41:height*1.1,12:cx,22:cy,
            16:0.,26:0.,36:1.,17:0.,27:0.,37:0.,45:height*1.1,51:0.}


def verify(source,prepared,source_sha256):
    source,prepared=Path(source),Path(prepared)
    original,proposed=source.read_bytes(),prepared.read_bytes()
    require(hashlib.sha256(original).hexdigest()==source_sha256,'Stale source identity')
    slines,sgroups=scan(original);plines,pgroups=scan(proposed)
    source_doc=ezdxf.readfile(source);prepared_doc=ezdxf.readfile(prepared)
    require(source_doc.dxfversion>='AC1015' and source_doc.dxfversion==prepared_doc.dxfversion,'Changed/unsupported DXF version')
    source_handles=[handle(g) for g in sgroups if handle(g)]
    output_handles=[handle(g) for g in pgroups if handle(g)]
    require(len(set(source_handles))==len(source_handles) and len(set(output_handles))==len(output_handles),'Duplicate handles')
    expected={}
    for layout in source_doc.layouts:
        if layout.name=='Model':continue
        viewports=list(layout.query('VIEWPORT'))
        if viewports and not any(v.dxf.id==1 for v in viewports):expected[layout.layout_key.upper()]=layout
    new=[(i,g) for i,g in enumerate(pgroups) if handle(g) and handle(g) not in source_handles]
    require(len(new)==len(expected),'Wrong number of new source records')
    seed_index=header_seed(slines)
    initial=max(int(slines[seed_index].strip(),16),max((int(h,16)+1 for h in source_handles),default=1))
    require({int(handle(g),16) for i,g in new}==set(range(initial,initial+len(new))),'Wrong handle allocation')
    seen=set()
    allowed={0,5,330,100,67,8,410,10,20,30,40,41,68,69,12,22,16,26,36,17,27,37,45,51,90}
    for index,group in new:
        tags=group['tags'];by_code={c:[v for k,v in tags if k==c] for c,_ in tags}
        require(set(by_code)==allowed and all(len(v)==(2 if c==100 else 1) for c,v in by_code.items()),
                'New viewport has omitted/extra/duplicate fields')
        require(by_code[0]==[b'VIEWPORT'] and by_code[100]==[b'AcDbEntity',b'AcDbViewport'], 'Wrong new record kind/subclass')
        owner=by_code[330][0].decode('ascii').upper()
        require(owner in expected and owner not in seen,'Wrong/duplicated viewport owner')
        seen.add(owner);layout=expected[owner]
        name=decode_dxf_unicode(by_code[410][0].decode(source_doc.output_encoding))
        require(name==layout.name,'Wrong new viewport layout name')
        require(by_code[8]==[b'0'] and int(by_code[67][0])==1 and int(by_code[68][0])==1
                and int(by_code[69][0])==1 and int(by_code[90][0])==557088,'Wrong main viewport/layer/status/flags')
        for code,wanted in expected_geometry(layout).items():
            value=float(by_code[code][0])
            require(math.isfinite(value) and abs(value-wanted)<1e-9*max(1,abs(wanted)), 'Wrong main viewport geometry')
        first=list(layout)[0].dxf.handle.upper()
        require(index+1<len(pgroups) and handle(pgroups[index+1])==first,'Main viewport not inserted before first original entity')
        entities=list(prepared_doc.layouts.get(layout.name))
        require(entities[0].dxftype()=='VIEWPORT' and entities[0].dxf.handle.upper()==handle(group)
                and entities[0].dxf.owner.upper()==owner,'Prepared entity-space order/owner differs')
    require(seen==set(expected),'Missing layout revision')
    # Strip only the newly verified records. No producer offsets or receipt are consumed.
    restored=proposed
    for _,group in reversed(new):restored=restored[:group['start']]+restored[group['end']:]
    rlines,_=scan(restored)
    require(len(rlines)==len(slines) and header_seed(rlines)==seed_index,'Existing raw structure changed')
    if new:
        require(int(rlines[seed_index].strip(),16)==initial+len(new),'Wrong final HANDSEED')
        require(rlines[seed_index][len(rlines[seed_index].rstrip(b'\r\n')):]==
                slines[seed_index][len(slines[seed_index].rstrip(b'\r\n')):],'HANDSEED line ending changed')
        rlines[seed_index]=slines[seed_index]
    require(b''.join(rlines)==original,'Original bytes outside declared main records/HANDSEED changed')
    require(source.read_bytes()==original,'Source changed during verification')
    return dict(status='pass',new_main_viewports=len(new),source_sha256=source_sha256,
                prepared_sha256=hashlib.sha256(proposed).hexdigest(),
                unplanned_byte_changes=0,original_reconstruction='exact',
                check='Source/output discovery, fields/order/allocation and raw reconstruction; no producer span receipt')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source');parser.add_argument('prepared');parser.add_argument('--source-sha256',required=True)
    args=parser.parse_args()
    print(json.dumps(verify(args.source,args.prepared,args.source_sha256),indent=2))


if __name__=='__main__':main()
