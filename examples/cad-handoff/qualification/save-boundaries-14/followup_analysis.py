"""Literal metadata survival and matched Qt hash-seed diagnostics; no equivalence waiver."""
import importlib.util
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('ict_boundary14_analysis',HERE/'analyze.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def payload(path,case):
    doc=b.ch.load(path);assets={a['id']:a for a in b.ch.assets(doc)}
    entity=doc.entitydb[assets[case['asset_id']]['handle']]
    name='ICT_BOUND14_USED'
    xdata=[[t.code,b.ch.plain(t.value)]for t in entity.get_xdata(name)]if entity.has_xdata(name)else []
    record=doc.rootdict.get('ICT_BOUND14_FOREIGN')
    if isinstance(record,str):record=doc.entitydb.get(record)
    return dict(appids={n:n in doc.appids for n in(name,'ICT_BOUND14_UNUSED')},
        xdata=xdata,xrecord=[[t.code,b.ch.plain(t.value)]for t in record.tags]if record is not None else None,
        useri5=doc.header.get('$USERI5'),attributes={a['id']:a['attributes']for a in b.ch.assets(doc)})

def analyze_payload(root):
    rows=b.native_rows(root/'native/export.stdout',b.read(root/'export.json'))
    fresh=b.native_rows(root/'native/fresh.stdout',b.read(root/'fresh.json'))
    cases=b.read(root/'CASES.json');out=[];reports={}
    for case,observed,reopened in zip(cases,rows,fresh):
        identity=case['id'];folder=root/'cases'/identity
        b.require(b.canonical_inventory(observed['reopened'])==b.canonical_inventory(reopened['imported']),'Fresh payload native inventory differs')
        b.verify(folder/'source.dxf',folder/'candidate.dxf',b.read(folder/'plan.json'))
        source=payload(folder/'source.dxf',case);candidate=payload(folder/'candidate.dxf',case)
        b.require(source['appids']=={'ICT_BOUND14_USED':True,'ICT_BOUND14_UNUSED':True}and source['xdata']==case['xdata']and
            source['xrecord']==[[1,case['marker']],[90,31415926],[40,2.718281828]]and source['useri5']==case['useri5'],'Authored sentinels differ')
        b.require({k:v for k,v in source.items()if k!='attributes'}=={k:v for k,v in candidate.items()if k!='attributes'},'Candidate changed foreign sentinel')
        returned=payload(folder/'returned.dxf',case)
        report=b.ch.compare(b.ch.snapshot(folder/'source.dxf'),b.ch.snapshot(folder/'returned.dxf'))
        reports[identity]=report
        out.append(dict(id=identity,source=source,candidate=candidate,returned=returned,
            literal_equal={k:source[k]==returned[k]for k in source},strict_status=report['status'],strict_differences=len(report['unexpected']),
            known_native={stage:observed[stage]['known']for stage in('initial','imported','after_export','reopened')},
            custom_native={stage:[dict(id=o['id'],type=o['type'],custom=o['custom'])for o in observed[stage]['objects']if o['custom']]
                for stage in('initial','imported','after_export','reopened')}))
    return dict(jobs=len(rows),fresh_public_inventory_repeats=len(fresh),cases=out,whole_cad_qualified=False),reports

def analyze_seeds(a,c,unseeded):
    observations=[]
    for root in(a,c):
        rows=b.native_rows(root/'native/export.stdout',b.read(root/'export.json'))
        fresh=b.native_rows(root/'native/fresh.stdout',b.read(root/'fresh.json'))
        b.require(len(rows)==6,'Seed case coverage differs')
        for left,right in zip(rows,fresh):
            b.require(b.canonical_inventory(left['reopened'])==b.canonical_inventory(right['imported']),'Fresh seeded inventory differs')
        observations.append(rows)
    out=[];reports={}
    for identity in b.IDS:
        paths=[r/'cases'/identity for r in(a,c,unseeded)]
        for p in paths[1:]:b.require(b.sha(p/'source.dxf')==b.sha(paths[0]/'source.dxf'),'Seed source differs')
        for name,left,right in [('seed0a_to_seed0b',paths[0]/'returns/default.dxf',paths[1]/'returns/default.dxf'),
                                ('unseeded_to_seed0a',paths[2]/'returns/default.dxf',paths[0]/'returns/default.dxf')]:
            report=b.ch.compare(b.ch.snapshot(left),b.ch.snapshot(right));reports[identity+'/'+name]=report
            out.append(dict(id=identity,comparison=name,strict_status=report['status'],strict_differences=len(report['unexpected']),
                difference_kinds=dict(b.Counter(r['kind']for r in report['unexpected']))))
    return dict(comparisons=out,jobs=12,fresh_public_inventory_repeats=12,whole_cad_qualified=False),reports

if __name__=='__main__':
    root=Path(sys.argv[1]);out=root/'followup-analysis'
    p,pr=analyze_payload(root/'payload-3');s,sr=analyze_seeds(root/'seed-0-a',root/'seed-0-b',root/'attempt-1')
    out.mkdir(exist_ok=True)
    b.write(out/'payload.json',p);b.write(out/'seeds.json',s)
    for prefix,reports in [('payload',pr),('seeds',sr)]:
        for key,value in reports.items():b.write(out/(prefix+'--'+key.replace('/','--')+'.json'),value)
    print('Payload',[(r['id'],r['literal_equal'])for r in p['cases']])
    print('Seeds',s['comparisons'])
