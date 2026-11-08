"""Exercise semantic corruption and source-retention controls for the proposed layout revision."""
import argparse
import copy
import json
from pathlib import Path
import tempfile

import prepare_layout10 as p
from verify_layout10 import verify

HERE=Path(__file__).resolve().parent


def check(out):
    if out.exists():raise ValueError('Retain earlier controls')
    out.mkdir(parents=True)
    source=HERE/'validation-2/authored/validation-foreign.dxf'
    raw=source.read_bytes();sha=p.ch.digest(source)
    proposed,receipt=p.propose(source)
    good=out/'good.dxf';good.write_bytes(proposed)
    result=verify(source,good,sha)
    no_op,again=p.propose(good)
    assert no_op==proposed and again['status']=='exact_noop'
    rows=[]
    new=next(r for r in p.records(proposed) if p.own_handle(r)==receipt['layouts'][0]['new_main_handle'])
    doc=p.ch.load(source)
    def replace_tag(data,handle,code,value):
        record=next(r for r in p.records(data) if p.own_handle(r)==handle)
        tag=next(t for t in record['tags'] if t[0]==code)
        return data[:tag[2]]+str(value).encode('utf-8')+data[tag[3]:]
    model_line=next(e for e in doc.modelspace() if e.dxftype()=='LINE')
    display=next(v for l in doc.layouts if l.name!='Model' for v in l.query('VIEWPORT'))
    vendor=next(a for e in doc.modelspace() if e.dxftype()=='INSERT' for a in e.attribs if a.dxf.tag=='VENDOR_PRIVATE')
    xdata_record=next(r for r in p.records(proposed) if any(t[0]==1000 for t in r['tags']))
    mutations={
        'wrong_id':replace_tag(proposed,p.own_handle(new),69,2),
        'wrong_owner':replace_tag(proposed,p.own_handle(new),330,doc.modelspace().layout_key),
        'wrong_size':replace_tag(proposed,p.own_handle(new),40,12345),
        'wrong_layer':replace_tag(proposed,p.own_handle(new),8,'LABEL'),
        'missing_main':proposed[:new['start']]+proposed[new['end']:],
        'existing_geometry':replace_tag(proposed,model_line.dxf.handle,10,12345),
        'existing_display':replace_tag(proposed,display.dxf.handle,45,12345),
        'foreign_attribute':replace_tag(proposed,vendor.dxf.handle,1,'lost'),
        'foreign_xdata':replace_tag(proposed,p.own_handle(xdata_record),1000,'lost'),
    }
    # Move the new main record past the first original viewport, retaining both bodies.
    groups=p.records(proposed);pos=groups.index(new);following=groups[pos+1]
    mutations['wrong_order']=proposed[:new['start']]+proposed[following['start']:following['end']]+proposed[new['start']:new['end']]+proposed[following['end']:]
    for name,data in mutations.items():
        path=out/(name+'.dxf');path.write_bytes(data)
        try:verify(source,path,sha)
        except ValueError as error:rows.append(dict(id=name,result='refused',reason=str(error)))
        else:raise ValueError('Semantic corruption accepted: '+name)
    try:verify(source,good,'0'*64)
    except ValueError as error:rows.append(dict(id='stale_identity',result='refused',reason=str(error)))
    else:raise ValueError('Stale source accepted')
    bad_sources={
        'binary':b'AutoCAD Binary DXF\r\n\x1a\0',
        'missing_seed':raw.replace(b'$HANDSEED',b'$OTHERSEED',1),
    }
    layout=doc.layouts.get('Qualification sheet')
    bad_sources['zero_paper_width']=replace_tag(raw,layout.dxf_layout.dxf.handle,44,0)
    bad_sources['duplicate_main']=replace_tag(proposed,display.dxf.handle,69,1)
    # A second source handle becomes an existing handle without altering other records.
    record_handles=[p.own_handle(r) for r in p.records(raw) if p.own_handle(r)]
    bad_sources['duplicate_handle']=replace_tag(raw,record_handles[1],5,record_handles[0])
    for name,data in bad_sources.items():
        path=out/(name+'-source.dxf');path.write_bytes(data)
        try:p.propose(path)
        except (ValueError,p.ch.ezdxf.DXFError) as error:rows.append(dict(id=name,result='refused',reason=str(error)))
        else:raise ValueError('Unsupported source accepted: '+name)
    p.apply(source,out/'packet')
    before={str(f.relative_to(out/'packet')):p.ch.digest(f) for f in (out/'packet').iterdir()}
    try:p.apply(source,out/'packet')
    except ValueError as error:rows.append(dict(id='output_collision',result='refused',reason=str(error)))
    else:raise ValueError('Output collision accepted')
    assert before=={str(f.relative_to(out/'packet')):p.ch.digest(f) for f in (out/'packet').iterdir()}
    assert source.read_bytes()==raw
    report=dict(role='Exposed software controls, not fresh validation or native execution',
                positive=result,prepared_again='exact_noop',controls=rows,
                source_unchanged=True,collision_packet_unchanged=True)
    p.ch.write_json(out/'controls.json',report)
    print(len(rows),'semantic/input controls refused; source and existing packet exact')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    check(parser.parse_args().out)
