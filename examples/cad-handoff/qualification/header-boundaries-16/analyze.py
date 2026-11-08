"""Exact native/public header receiving; descriptive associations never waive strict rows."""
import copy
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('ict_header16_boundary14',HERE.parent/'save-boundaries-14/analyze.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def typed(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)

def canonical(value):
    out=copy.deepcopy(b.canonical_inventory(value));layouts=out['headers']['layouts']
    b.require(len(layouts)==len({r['id']for r in layouts}),'Duplicate native layout ID')
    out['headers']['layouts']=sorted(layouts,key=lambda r:int(r['id']))
    return out

def native_rows(path,jobs,keys,allow_errors=False):
    lines=path.read_text(encoding='utf-8').splitlines()
    b.require(not any(s.startswith('ICT_HEADER16_FATAL ')for s in lines),'Native fatal recorded')
    profiles=[json.loads(s.split(' ',1)[1])for s in lines if s.startswith('ICT_HEADER16_PROFILE ')]
    b.require(len(profiles)==1 and profiles[0]['configuration_file']=='/home/cad/.config/QCAD/QCAD3.conf'and
        profiles[0]['qt_version']=='5.14.2','Wrong native header profile/runtime')
    rows=[json.loads(s.split(' ',1)[1])for s in lines if s.startswith('ICT_HEADER16 ')]
    b.require([r['id']for r in rows]==[j['id']for j in jobs]and(allow_errors or not any('error'in r for r in rows)),'Native header job coverage/error differs')
    for row,job in zip(rows,jobs):
        expected='All CAD Files [OpenDesign] (*.dxf *.dwg *.dwt *.dxb *.dgn *.dwf)'if job['importer']=='OpenDesign'else'DXF Files [dxflib] (*.dxf)'
        b.require(row['import_filter']==expected and expected in profiles[0]['importer_filters'],'Header importer differs')
        b.require(row['export_filter']in profiles[0]['exporter_filters']and row['export_filter'].startswith(job['version']+' [')and
            '['+job['exporter']+']'in row['export_filter'],'Header exporter differs')
        for stage in(s for s in('initial','imported','after_operation','after_export','reopened')if s in row):
            state=row[stage];known=state['headers']['known_variables'];dims=state['headers']['dimension_variables']
            b.require([(r['name'],r['enum_id'])for r in known]==list(zip(keys['known_variables'],range(len(keys['known_variables'])))),'Native known-variable observation omitted/reordered')
            b.require([r['name']for r in dims]==[r['name']for r in keys['dimension_variables']],'Native dimension observation omitted/reordered')
            b.require(all(type(r['present'])is bool for r in known)and all(type(r['has_override'])is bool for r in dims),'Native presence observation differs')
            b.require([r['name']for r in state['variables']]==sorted({r['name']for r in state['variables']}),'Native ordinary-variable names differ')
            for layout in state['headers']['layouts']:
                b.require([p['getter']for p in layout['properties']]==keys['layout_getters'],'Native layout observation omitted/reordered')
            canonical(state)
    return rows

def raw_header(path):
    lines=path.read_bytes().splitlines(keepends=True)
    b.require(len(lines)%2==0,'Incomplete raw DXF pairs')
    starts=[i for i in range(0,len(lines)-3,2)if lines[i].strip()==b'0'and lines[i+1].strip()==b'SECTION'and
        lines[i+2].strip()==b'2'and lines[i+3].strip()==b'HEADER']
    b.require(len(starts)==1,'Missing/ambiguous raw HEADER')
    start=starts[0];ends=[i for i in range(start+4,len(lines)-1,2)if lines[i].strip()==b'0'and lines[i+1].strip()==b'ENDSEC']
    b.require(bool(ends),'Unterminated raw HEADER');end=ends[0];records=[];current=None
    for i in range(start+4,end,2):
        code=int(lines[i].strip());value=lines[i+1].rstrip(b'\r\n')
        if code==9:
            current=dict(name=value.decode('ascii'),tags=[]);records.append(current)
        else:
            b.require(current is not None,'Raw header value has no name');current['tags'].append([code,value.hex()])
    return dict(raw_hex=b''.join(lines[start:end+2]).hex(),records=records)

def decoded_header(path):
    doc=b.ch.load(path)
    # Preserve the original comparator's metadata boundary. Complete raw metadata
    # above avoids the library substituting current time for a literal zero.
    return {k:b.ch.plain(doc.header[k])for k in doc.header.varnames()if k not in b.ch.SAVE_HEADERS}

def changes(before,after):
    return [dict(name=k,before_present=k in before,after_present=k in after,
        before=before.get(k),after=after.get(k))for k in sorted(set(before)|set(after))
        if k not in before or k not in after or typed(before[k])!=typed(after[k])]

def known_changes(before,after):
    left={r['name']:r for r in before['headers']['known_variables']};right={r['name']:r for r in after['headers']['known_variables']}
    return changes(left,right)

def leaves(before,after,path=''):
    if type(before)is not type(after):return [dict(path=path,before=before,after=after)]
    if isinstance(before,dict):
        return [r for key in sorted(set(before)|set(after))for r in leaves(before.get(key),after.get(key),path+'/'+str(key))]
    if isinstance(before,list):
        if len(before)!=len(after):return [dict(path=path,before=before,after=after)]
        return [r for index,(left,right)in enumerate(zip(before,after))for r in leaves(left,right,path+'/'+str(index))]
    return []if typed(before)==typed(after)else[dict(path=path,before=before,after=after)]

def raw_number(header,name,code):
    rows=[r for r in header['records']if r['name']==name]
    b.require(len(rows)==1 and len(rows[0]['tags'])==1 and rows[0]['tags'][0][0]==code,'Missing/ambiguous raw numeric header '+name)
    value=bytes.fromhex(rows[0]['tags'][0][1]).decode('ascii').strip()
    return int(value)if code==70 else float(value)

def receive_rows(root):
    jobs=b.read(root/'export.json')['jobs'];keys=b.read(root/'KEYS.json');rows=native_rows(root/'native/export.stdout',jobs,keys,True)
    successful=[j for j,r in zip(jobs,rows)if 'error'not in r]
    b.require(b.read(root/'native/fresh-success.json')==dict(jobs=successful,read_only=True),'Header fresh subset differs')
    fresh={r['id']:r for r in native_rows(root/'native/fresh.stdout',successful,keys)}
    differences={row['id']:leaves(canonical(row['reopened']),canonical(fresh[row['id']]['imported']))for row in rows if 'error'not in row}
    return jobs,rows,fresh,differences

def strict(source,target):
    try:return b.ch.compare(b.ch.snapshot(source),b.ch.snapshot(target))
    except b.ch.InputError as error:return dict(status='refused',error=str(error),boundary='Original asset-profile guard; not zero differences')

def analyze(root):
    jobs,rows,fresh,repeats=receive_rows(root);reports={};observations=[]
    b.require(len(jobs)==26,'Wrong header cohort')
    for job,row in zip(jobs,rows):
        identity=job['id'].split('/')[0];item=dict(id=job['id'],native_error=row.get('error'))
        if 'error'in row:
            reports[job['id']]=dict(status='native_failed',error=row['error']);observations.append(item);continue
        output=root/job['output'].removeprefix('/work/');raw=raw_header(output);returned=decoded_header(output)
        if identity=='empty':
            report=dict(status='not_applicable',reason='Predeclared empty/unprofiled descriptive control; no asset comparator run')
            original={};source_raw=None
        else:
            source=root/job['input'].removeprefix('/work/');report=strict(source,output)
            original=decoded_header(source);source_raw=raw_header(source)
        reports[job['id']]=report
        item.update(strict_status=report['status'],strict_differences=len(report['unexpected'])if 'unexpected'in report else None,
            source_raw_header=source_raw,returned_raw_header=raw,decoded_header_changes=changes(original,returned),
            native_known_import_changes=known_changes(row['initial'],row['imported']),
            native_known_export_changes=known_changes(row['imported'],row['after_export']),
            native_dimensions={s:row[s]['headers']['dimension_variables']for s in('initial','imported','after_export','reopened')},
            raw_DIMASZ=raw_number(raw,'$DIMASZ',40),fresh_public_inventory_equal=not repeats[job['id']],fresh_public_inventory_differences=repeats[job['id']])
        observations.append(item)
    return dict(attempted_jobs=26,exports=len(fresh),fresh_imports=len(fresh),fresh_public_inventory_repeats=sum(not d for d in repeats.values()),
        strict_statuses=dict(Counter(r['status']for r in reports.values())),observations=observations,whole_cad_qualified=False),reports

def operation(before,after,label):
    expected=canonical(before)
    if label in('known','unrelated'):
        name='DIMASZ'if label=='known'else'USERI5';value=9.875 if label=='known'else 1234
        row=next(r for r in expected['headers']['known_variables']if r['name']==name)
        row.update(present=True,value=dict(type='number',value=value))
    elif label=='style':
        row=next(r for r in expected['headers']['dimension_variables']if r['name']=='DIMASZ')
        row.update(has_override=True,value=dict(type='number',value=9.875))
    else:b.require(label=='unchanged','Unknown dimensional operation')
    b.require(typed(expected)==typed(canonical(after)),'Undeclared recorded change during dimensional operation')

def dimensions(root):
    jobs,rows,fresh,repeats=receive_rows(root);reports={};observations=[]
    cases=b.read(root/'CASES.json');expected=[c['id']+'/'+label+'-'+writer for c in cases
        for label in('unchanged','known','style','unrelated')for writer in('OpenDesign','dxflib')]
    b.require([j['id']for j in jobs]==expected and len(jobs)==48 and len(fresh)==48,'Dimensional cohort differs')
    b.require(not any(repeats.values()),'Dimensional control fresh inventory differs')
    for job,row in zip(jobs,rows):
        label=job['operation'];operation(row['imported'],row['after_operation'],label)
        source=root/job['input'].removeprefix('/work/');output=root/job['output'].removeprefix('/work/');raw=raw_header(output)
        before=next(r['value']for r in row['imported']['headers']['dimension_variables']if r['name']=='DIMASZ')
        b.require(before['type']=='number','Non-numeric original dimension style')
        expected_value=9.875 if label=='style'else before['value'];actual=raw_number(raw,'$DIMASZ',40)
        b.require(actual==expected_value,'Dimensional-store directional hypothesis failed')
        if label=='unrelated':b.require(raw_number(raw,'$USERI5',70)==1234,'Unrelated native header not retained')
        report=strict(source,output);reports[job['id']]=report
        observations.append(dict(id=job['id'],operation_exact=True,source_style_DIMASZ=before,
            raw_returned_DIMASZ=actual,raw_returned_USERI5=raw_number(raw,'$USERI5',70),returned_raw_header=raw,
            native_known_export_changes=known_changes(row['after_operation'],row['after_export']),strict_status=report['status'],
            strict_differences=len(report['unexpected'])if 'unexpected'in report else None,fresh_public_inventory_equal=True))
    return dict(attempted_jobs=48,exports=48,fresh_public_inventory_repeats=48,
        strict_statuses=dict(Counter(r['status']for r in reports.values())),observations=observations,whole_cad_qualified=False),reports

if __name__=='__main__':
    root=Path(sys.argv[1]);result,reports=dimensions(root)if root.name=='dimension-2'else analyze(root)
    out=root/'analysis';out.mkdir(exist_ok=False);b.write(out/'diagnosis.json',result)
    for key,report in reports.items():b.write(out/(key.replace('/','--')+'.json'),report)
    print('Received',len(reports),'header results;',result['strict_statuses'])
