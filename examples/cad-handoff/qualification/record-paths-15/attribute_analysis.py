"""Retain raw attribute sequences and public native parent targets without repair."""
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('ict_record15_attributes_analysis',HERE/'record_analysis.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);b=a.b
def raw_sequences(path):
    lines=path.read_bytes().splitlines();b.require(len(lines)%2==0,'Incomplete raw DXF pairs')
    pairs=[(int(lines[i].strip()),lines[i+1])for i in range(0,len(lines),2)]
    active=False;current=[];result=[]
    def flush():
        if current and current[0][1]in(b'INSERT',b'ATTRIB',b'SEQEND'):
            result.append(dict(type=current[0][1].decode('ascii'),tags=[[code,value.hex()]for code,value in current]))
    for i,(code,value)in enumerate(pairs):
        if code==0 and value==b'SECTION':
            active=i+1<len(pairs)and pairs[i+1]==(2,b'ENTITIES');continue
        if not active:continue
        if code==0:
            flush();current=[]
            if value==b'ENDSEC':active=False;continue
        current.append((code,value))
    return result
def native_parents(inventory):
    objects={o['id']:o for o in inventory['objects']};result=[]
    for obj in inventory['objects']:
        if obj['attribute']is not None:
            attr=obj['attribute'];parent=objects.get(attr['parent'])
            result.append(dict(id=obj['id'],attribute=attr,parent_target=None if parent is None else
                dict(id=parent['id'],type=parent['type'],name=parent['name'],handle=parent['handle'])))
    return sorted(result,key=lambda r:(r['attribute']['parent'],r['attribute']['tag'],r['id']))
def analyze(root):
    jobs=b.read(root/'export.json')['jobs'];rows=a.native_rows(root/'native/export.stdout',jobs,allow_errors=True);out=[]
    for job,row in zip(jobs,rows):
        result=dict(id=job['id'],native_parents={stage:native_parents(row[stage])for stage in('initial','imported','after_export','reopened')if stage in row})
        if 'error'in row:result['native_error']=row['error']
        else:
            path=root/job['output'].removeprefix('/work/');doc=b.ch.load(path)
            result.update(raw_entity_sequences=raw_sequences(path),decoded_modelspace_inserts=[dict(handle=e.dxf.handle,name=e.dxf.name,
                attributes=[dict(handle=t.dxf.handle,tag=t.dxf.tag,text=t.dxf.text)for t in e.attribs])for e in doc.modelspace().query('INSERT')])
        out.append(result)
    return dict(jobs=48,observations=out,whole_cad_qualified=False)
if __name__=='__main__':
    import sys
    root=Path(sys.argv[1]);b.write(root/'analysis/attribute-diagnosis.json',analyze(root));print('Retained raw attribute sequences and native parent targets for all48 jobs')
