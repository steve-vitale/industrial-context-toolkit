"""Literal record-path and public document-variable receiving; no preservation waiver."""
import importlib.util
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('ict_record15_boundary14',HERE.parent/'save-boundaries-14/analyze.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
KEYS=('ICT15_STRING','ICT15_INTEGER','ICT15_REAL','ICT15_ORDERED','ICT15_PRIVATE_STRING')

def native_rows(path,jobs,allow_errors=False):
    lines=path.read_text(encoding='utf-8').splitlines()
    b.require(not any(s.startswith('ICT_RECORD15_FATAL ')for s in lines),'Native fatal recorded')
    profiles=[json.loads(s.split(' ',1)[1])for s in lines if s.startswith('ICT_RECORD15_PROFILE ')]
    b.require(len(profiles)==1 and profiles[0]['configuration_file']=='/home/cad/.config/QCAD/QCAD3.conf'and
        profiles[0]['qt_version']=='5.14.2','Wrong native profile/runtime')
    rows=[json.loads(s.split(' ',1)[1])for s in lines if s.startswith('ICT_RECORD15 ')]
    b.require([r['id']for r in rows]==[j['id']for j in jobs]and(allow_errors or not any('error'in r for r in rows)),'Native job coverage/error differs')
    for row,job in zip(rows,jobs):
        expected='All CAD Files [OpenDesign] (*.dxf *.dwg *.dwt *.dxb *.dgn *.dwf)'if job['importer']=='OpenDesign'else'DXF Files [dxflib] (*.dxf)'
        b.require(row['import_filter']==expected and expected in profiles[0]['importer_filters'],'Selected importer differs')
        b.require(row['export_filter']in profiles[0]['exporter_filters']and row['export_filter'].startswith(job['version']+' [')and
            '['+job['exporter']+']'in row['export_filter']and'*.dxf'in row['export_filter'],'Selected exporter differs')
        for stage in(s for s in('initial','imported','after_export','reopened')if s in row):
            names=[r['name']for r in row[stage]['variables']]
            b.require(names==sorted(set(names)),'Duplicate/unordered public document variables')
    return rows

def records(doc):
    """Keep every named dictionary path, handle, owner and ordered tag. No remapping."""
    rows=[];pending=[(doc.rootdict,[],frozenset())]
    while pending:
        dictionary,path,ancestors=pending.pop();handle=dictionary.dxf.handle
        b.require(len(path)<64 and len(rows)<20000,'Unbounded dictionary record traversal')
        if handle in ancestors:continue
        for name,obj in dictionary.items():
            link=obj if isinstance(obj,str)else obj.dxf.handle
            if isinstance(obj,str):obj=doc.entitydb.get(obj)
            where=path+[str(name)]
            if obj is None:
                rows.append(dict(path=where,handle=link,owner=None,cloning=None,dictionary_handle=handle,
                    ordered_tags=None,type='dangling-reference'));continue
            if obj.dxftype()in('DICTIONARY','ACDBDICTIONARYWDFLT'):pending.append((obj,where,ancestors|{handle}))
            elif obj.dxftype()=='XRECORD':
                rows.append(dict(path=where,handle=obj.dxf.handle,owner=obj.dxf.owner,cloning=obj.dxf.cloning,
                    dictionary_handle=handle,ordered_tags=[[t.code,b.ch.plain(t.value)]for t in obj.tags],type='XRECORD'))
    return sorted(rows,key=lambda r:r['path'])

def observations(rows):
    return {key:[r for r in rows if r['path'][-1]==key]for key in KEYS}

def analyze(root):
    jobs=b.read(root/'export.json')['jobs'];rows=native_rows(root/'native/export.stdout',jobs,allow_errors=True)
    successful_jobs=[job for job,row in zip(jobs,rows)if 'error'not in row]
    fresh_manifest=b.read(root/'native/fresh-success.json')
    b.require(fresh_manifest==dict(jobs=successful_jobs,read_only=True),'Fresh subset differs from complete successful export observations')
    fresh=native_rows(root/'native/fresh.stdout',successful_jobs);fresh_by_id={r['id']:r for r in fresh}
    b.require(len(jobs)==48 and len(fresh)==len(successful_jobs),'Wrong crossed cohort')
    cases=b.read(root/'CASES.json');bycase={r['id']:r for r in cases}
    b.require(len(cases)==len(bycase)==12,'Wrong paired cohort')
    for identity in b.IDS:
        folder=root/'cases'/identity;a=(folder/'qcad/source.dxf').read_bytes();c=(folder/'foreign/source.dxf').read_bytes()
        b.require(a.count(b'QCAD_OBJECTS')==1 and c==a.replace(b'QCAD_OBJECTS',b'ICT15_FOREIGN_OBJECTS',1),'Pair differs beyond declared raw namespace span')
    sources={};source_records={}
    for case in cases:
        folder=root/'cases'/case['id'];plan=b.read(folder/'plan.json');b.verify(folder/'source.dxf',folder/'candidate.dxf',plan)
        candidate_report=b.ch.compare(b.ch.snapshot(folder/'source.dxf'),b.ch.snapshot(folder/'candidate.dxf'),plan)
        b.require(candidate_report['status']=='pass','Exact candidate strict comparison fails')
        source_records[case['id']]=records(b.ch.load(folder/'source.dxf'));source_observations=observations(source_records[case['id']])
        for key,tags in case['records'].items():
            expected=source_observations[key];b.require(len(expected)==1 and expected[0]['path']==[case['dictionary_name'],key]and
                expected[0]['ordered_tags']==tags,'Authored record key differs')
        sources[case['id']]=b.ch.snapshot(folder/'source.dxf')
    results=[];reports={}
    for job,row in zip(jobs,rows):
        identity=job['id'].rsplit('/',1)[0];case=bycase[identity];folder=root/'cases'/identity
        target=root/job['output'].removeprefix('/work/')
        if 'error'in row:
            report=dict(status='native_failed',error=row['error'],strict_comparison='not_run',
                retained_partial_file=dict(sha256=b.sha(target),bytes=target.stat().st_size)if target.exists()else None)
            reports[job['id']]=report
            results.append(dict(id=job['id'],namespace=case['namespace'],importer=job['importer'],exporter=job['exporter'],
                strict_status='native_failed',strict_differences=None,error=row['error'],
                native_variables={s:row[s]['variables']for s in('initial','imported','after_export','reopened')if s in row}))
            continue
        doc=b.ch.load(target);second=fresh_by_id[job['id']]
        expected_version=case['source_version']if job['exporter']=='OpenDesign'else'AC1015'
        b.require(doc.dxfversion==expected_version,'Actual written ACADVER differs')
        b.require(b.canonical_inventory(row['reopened'])==b.canonical_inventory(second['imported']),'Fresh public native inventory differs')
        returned_records=records(doc);chosen=observations(returned_records);checks={}
        for key in KEYS:
            before=case['records'][key];after=chosen[key]
            checks[key]=dict(source_tags=before,returned=after,ordered_tags_equal=len(after)==1 and after[0]['ordered_tags']==before,
                source_path=[case['dictionary_name'],key],same_path=len(after)==1 and after[0]['path']==[case['dictionary_name'],key])
        try:
            report=b.ch.compare(sources[identity],b.ch.snapshot(target))
        except b.ch.InputError as error:
            report=dict(status='refused',error=str(error),boundary='Original strict asset-profile guard; not a zero-difference comparison')
        reports[job['id']]=report
        results.append(dict(id=job['id'],namespace=case['namespace'],importer=job['importer'],exporter=job['exporter'],
            actual_version=doc.dxfversion,strict_status=report['status'],
            strict_differences=len(report['unexpected'])if 'unexpected'in report else None,record_checks=checks,
            inherited_source_records=[r for r in source_records[identity]if r['path'][-1]in case['inherited_names']],
            returned_dictionary_records=returned_records,native_variables={stage:row[stage]['variables']for stage in('initial','imported','after_export','reopened')}))
    return dict(cases=len(cases),attempted_exports=len(rows),exports=len(successful_jobs),fresh_public_inventory_repeats=len(fresh),comparisons=results,
        whole_cad_qualified=False,exposure='All exposed authored development; no fresh holdout'),reports

def partial(root):
    jobs=b.read(root/'export.json')['jobs']
    lines=(root/'native/export.stdout').read_text(encoding='utf-8').splitlines()
    rows=[json.loads(s.split(' ',1)[1])for s in lines if s.startswith('ICT_RECORD15 ')]
    b.require(len(rows)==27 and [r['id']for r in rows]==[j['id']for j in jobs[:27]]and
        [r['id']for r in rows if 'error'in r]==[jobs[26]['id']]and
        lines[-1]=='ICT_RECORD15_FATAL Error: Stop after failed job','Earlier terminal prefix/failure differs')
    reports={}
    for job,row in zip(jobs,rows):
        if 'error'in row:continue
        target=root/job['output'].removeprefix('/work/');source=root/job['input'].removeprefix('/work/')
        try:report=b.ch.compare(b.ch.snapshot(source),b.ch.snapshot(target))
        except b.ch.InputError as error:report=dict(status='refused',error=str(error))
        reports[job['id']]=report
    return dict(observed_jobs=27,successful_exports=len(reports),failed_job=rows[-1]['id'],
        error=rows[-1]['error'],fresh_phase='not_run',whole_cad_qualified=False),reports

if __name__=='__main__':
    root=Path(sys.argv[1]);result,reports=analyze(root);out=root/'analysis';out.mkdir(exist_ok=False)
    b.write(out/'diagnosis.json',result)
    for key,value in reports.items():b.write(out/(key.replace('/','--')+'.json'),value)
    print('Re-scored',len(reports),'crossed native returns')
    for importer in('OpenDesign','dxflib'):
        for namespace in('qcad','foreign'):
            selected=[r for r in result['comparisons']if r['importer']==importer and r['namespace']==namespace and 'record_checks'in r]
            print(importer,namespace,{k:sum(r['record_checks'][k]['ordered_tags_equal']for r in selected)for k in KEYS})
