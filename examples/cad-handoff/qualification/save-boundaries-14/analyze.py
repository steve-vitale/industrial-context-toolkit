"""Re-score unchanged strict comparisons and descriptive native/default-resource boundaries."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parents[3]/'scripts'),str(HERE.parent)]
import cad_handoff as ch
from verify_bytes import verify

IDS=('libre-air-water','libre-power','libre-motion','qcad-hydraulic','qcad-mechanical','qcad-template')
def require(ok,message):
    if not ok:raise ValueError(message)
def read(path):return json.loads(path.read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
def native_rows(path,manifest):
    lines=path.read_text(encoding='utf-8').splitlines()
    require(not any(s.startswith('ICT_BOUND14_FATAL ')for s in lines),'Native fatal recorded')
    profiles=[json.loads(s.split(' ',1)[1])for s in lines if s.startswith('ICT_BOUND14_PROFILE ')]
    require(len(profiles)==1 and profiles[0]['configuration_file']=='/home/cad/.config/QCAD/QCAD3.conf','Wrong native profile')
    rows=[json.loads(s.split(' ',1)[1])for s in lines if s.startswith('ICT_BOUND14 ')]
    require([r['id']for r in rows]==[j['id']for j in manifest['jobs']]and not any('error'in r for r in rows),'Native job coverage/error differs')
    return rows
def canonical_inventory(v):
    result=dict(v);objects=[]
    for row in v['objects']:
        item=dict(row);item['custom']=sorted(row['custom'],key=lambda p:(p['title'],p['key']))
        require(len({(p['title'],p['key'])for p in item['custom']})==len(item['custom']),'Duplicate custom property')
        objects.append(item)
    require(len({r['id']for r in objects})==len(objects),'Duplicate native object ID')
    result['objects']=sorted(objects,key=lambda r:int(r['id']))
    return result
def named_paths(doc):
    """Literal identities for diagnostics only. No case folding or handle/payload normalization."""
    paths={};seen={};pending=[(doc.rootdict,('dictionary',),frozenset())]
    def put(obj,path):
        if obj is None or not obj.is_alive:return
        h=obj.dxf.handle
        if not h:return
        paths.setdefault(tuple(path),set()).add(h)
    for table in doc.tables.tables():
        name=table.head.dxf.name;put(table.head,('table',name))
        for obj in table:put(obj,('table',name,str(obj.dxf.get('name',''))))
    for block in doc.blocks:
        put(block.block,('block',block.name,'BLOCK'));put(block.endblk,('block',block.name,'ENDBLK'))
    while pending:
        obj,path,ancestors=pending.pop();put(obj,path)
        h=obj.dxf.handle
        require(len(path)<=64 and len(paths)<=20000,'Unbounded named dictionary paths')
        if h in ancestors:continue
        if obj.dxftype()not in('DICTIONARY','ACDBDICTIONARYWDFLT'):continue
        for name,child in obj.items():
            if isinstance(child,str):child=doc.entitydb.get(child)
            if child is not None:pending.append((child,(*path,str(name)),ancestors|{h}))
    return {json.dumps(list(k),ensure_ascii=False):sorted(v)for k,v in sorted(paths.items())}
def diagnostic_inventory(path):
    # Empty native controls deliberately have no asset profile. Project their
    # generic records for description only; the strict asset comparator stays unchanged.
    doc=ch.load(path);entities={}
    for entity in doc.entitydb.values():
        if not entity.is_alive:continue
        collector=ch.TagCollector(dxfversion=max(doc.dxfversion,'AC1015'));entity.export_dxf(collector)
        tags=[[t.code,ch.plain(t.value)]for t in collector.tags]
        end=next((i for i,t in enumerate(tags)if i and t[0]==0),len(tags))
        entities[entity.dxf.handle]=dict(type=entity.dxftype(),tags=tags[:end])
    return dict(version=doc.dxfversion,raw_sha256=sha(path),records=len(entities),
        types=dict(sorted(Counter(r['type']for r in entities.values()).items())),
        paths=named_paths(doc),entities=entities,header={k:ch.plain(doc.header[k])for k in doc.header.varnames()})
def named_comparison(source,output,empty):
    rows=[]
    for path,handles in output['paths'].items():
        before=source['paths'].get(path,[]);control=empty['paths'].get(path,[])
        if before:continue
        row=dict(path=json.loads(path),output_handles=handles,empty_handles=control,
            status='same literal path in empty native export'if len(handles)==len(control)==1 else 'not uniquely associated with empty control')
        if len(handles)==len(control)==1:
            a=output['entities'][handles[0]];b=empty['entities'][control[0]]
            row.update(output_record=a,empty_record=b,exact_record_equal=a==b,
                literal_tag_changes=ch.field_changes(dict(tags=b['tags']),dict(tags=a['tags'])))
        rows.append(row)
    return rows
def analyze(root):
    export=native_rows(root/'native/export.stdout',read(root/'export.json'))
    fresh=native_rows(root/'native/fresh.stdout',read(root/'fresh.json'))
    for a,b in zip(export,fresh):
        require(canonical_inventory(a['reopened'])==canonical_inventory(b['imported']),'Fresh public native inventory differs')
    observations={r['id']:r for r in export};comparisons=[];resources=[];reports={};cases=read(root/'CASES.json')
    empty={fmt:diagnostic_inventory(root/'empty'/(fmt+'.dxf'))for fmt in ('default','R15','R21','R24')}
    require([empty[x]['version']for x in ('default','R15','R21','R24')]==['AC1024','AC1015','AC1021','AC1024'],'Actual empty export versions differ')
    for c in cases:
        identity=c['id'];folder=root/'cases'/identity;source=diagnostic_inventory(folder/'source.dxf')
        require(source['version']==c['version'],'Source version changed')
        verify(folder/'source.dxf',folder/'candidate.dxf',read(folder/'plan.json'))
        snapshots={r:ch.snapshot(folder/'returns'/(r+'.dxf'))for r in ('default','original','repeat')}
        before=ch.snapshot(folder/'source.dxf')
        for label,left,right in [('source_to_default',before,snapshots['default']),('source_to_original',before,snapshots['original']),
                                ('original_to_repeat',snapshots['original'],snapshots['repeat']),
                                ('historical_default_to_current',ch.snapshot(folder/'history/noop-default.dxf'),snapshots['default'])]:
            report=ch.compare(left,right);key=identity+'/'+label;reports[key]=report
            comparisons.append(dict(id=identity,comparison=label,strict_status=report['status'],strict_differences=len(report['unexpected'])))
        for route in ('default','original','repeat'):
            output=diagnostic_inventory(folder/'returns'/(route+'.dxf'));obs=observations[identity+'/'+route]
            require(output['version']==('AC1024'if route=='default'else c['version']),'Actual source-version export differs')
            paths=named_comparison(source,output,empty['default'if route=='default'else c['format']])
            source_doc=ch.load(folder/'source.dxf');output_doc=ch.load(folder/'returns'/(route+'.dxf'))
            source_names={e.dxf.name for e in source_doc.linetypes};added={e.dxf.name for e in output_doc.linetypes}-source_names
            initial_names={o['name']for o in obs['initial']['objects']if o['type']==2 and o['name_accessor']}
            imported_names={o['name']for o in obs['imported']['objects']if o['type']==2 and o['name_accessor']}
            resources.append(dict(id=identity,route=route,source_version=c['version'],output_version=output['version'],
                public_objects_initial=len(obs['initial']['objects']),public_objects_imported=len(obs['imported']['objects']),
                public_objects_reopened=len(obs['reopened']['objects']),serialized_records=output['records'],
                serialized_types=output['types'],added_linetype_names=sorted(added),
                added_linetypes_in_initial=sorted(added&initial_names),added_linetypes_in_imported=sorted(added&imported_names),
                new_named_paths=paths))
    return dict(comparisons=comparisons,resources=resources,empty_controls=empty,
        jobs=len(export),fresh_public_inventory_repeats=len(fresh),whole_cad_qualified=False,
        boundary='Named paths associate observations, not equivalence; all strict rows and every record/tag difference remain visible.'),reports

if __name__=='__main__':
    root=Path(sys.argv[1]);result,reports=analyze(root);out=root/'analysis';out.mkdir(exist_ok=False)
    write(out/'diagnosis.json',result)
    for key,r in reports.items():write(out/(key.replace('/','--')+'.json'),r)
    print('Re-scored',len(reports),'strict comparisons and',result['fresh_public_inventory_repeats'],'complete public native inventories')
