"""Recompute all full-GUI boundary differences; no CAD calls or accepted default profile."""
import importlib.util
import itertools
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('open18_layout_analysis',HERE.parent/'layout-construction-17/analyze.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
STAGES=('opened','noop','after_print')
GETTERS=['getPaperWidth','getPaperHeight','getPaperUnit','getPaperSizeMM','getPaperSizeName',
         'getPageOrientationString','getScale','getOffset']

def records(path,prefix):
    s=path.read_text(encoding='utf-8');a.require('ICT_OPEN18_FATAL 'not in s,'Native fatal retained')
    return [json.loads(l[len(prefix):])for l in s.splitlines()if l.startswith(prefix)]

def targeted(change,keys,fields):
    parts=change['path'].split('/')
    return (len(parts)>=7 and parts[1:3]==['headers','layouts']and parts[4]=='properties'and
            parts[5].isdigit()and int(parts[5])<len(keys['layout_getters'])and
            keys['layout_getters'][int(parts[5])]in fields and parts[6]=='value')

def analyze(root):
    frozen=a.read(root/'FREEZE.json');keys=a.read(root/'KEYS.json');fields=a.read(root/'FIELDS.json')
    a.require(frozen['whole_cad_qualified']is False,'Unsupported CAD qualification claim')
    for name,pin in frozen['inputs'].items():a.require(a.sha(root/name)==pin,'Frozen input differs: '+name)
    jobs=a.read(root/'jobs.json')['jobs'];a.require(len(jobs)==14,'Incorrect declared jobs')
    commands=a.read(root/'native/commands.json')
    a.require([{k:r[k]for k in ('route','mode')}for r in commands]==frozen['processes'],'Process coverage differs')
    cohort={};constructors={};profiles=[]
    for cmd in commands:
        route,mode=cmd['route'],cmd['mode'];name=route+'-'+mode
        a.require(cmd['exit']==0 and cmd['configuration_before']==frozen['configuration_sha256'],'Native exit/settings differ')
        a.require(cmd['command']==['/opt/qcad/qcad','-allow-multiple-instances','-config','/home/cad/.config/QCAD/QCAD3.conf',
                  '-font-substitution','Standard','DejaVu Sans','-exec','/work/native_complete.js'],'Wrong native startup')
        a.require(cmd['environment']==dict(LD_PRELOAD='/work/layout_ctor.so',LD_LIBRARY_PATH='/opt/qcad',ICT_LAYOUT17_MODE=mode),
                  'Different native observation environment')
        a.require(len(cmd['configuration_after'])==64 and cmd['pid']>0 and cmd['finished']>=cmd['started'],'Process terminal metadata missing')
        path=root/('native/'+name+'.stdout')
        profile=records(path,'ICT_OPEN18_PROFILE ')
        a.require(len(profile)==1 and profile[0]==dict(configuration_file='/home/cad/.config/QCAD/QCAD3.conf',
                  qt='5.14.2',gui=True,route=route,mode=mode),'Native selected runtime profile differs')
        profiles.extend(profile)
        a.require(records(path,'ICT_OPEN18_DONE ')==[dict(jobs=14,route=route,mode=mode)],'Native completion missing')
        rows=records(path,'ICT_OPEN18_JOB ')
        a.require([r['id']for r in rows]==[j['id']for j in jobs],'Native job coverage differs')
        states={}
        for job,row in zip(jobs,rows):
            a.require('error'not in row and row['route']==route,'Native job failed')
            a.require(row['filter']==('All CAD Files [OpenDesign] (*.dxf *.dwg *.dwt *.dxb *.dgn *.dwf)'if job['importer']=='OpenDesign'
                      else 'DXF Files [dxflib] (*.dxf)'),'Native importer filter differs')
            # MDI close accepts immediately but wrapper removal is deferred until the timer returns.
            # Keep the raw count; it is not an interactive close/reopen acceptance criterion.
            a.require(row['windows_after']==row['windows_open'],'Unexpected window-count observation')
            a.require(row['windows_open']==row['windows_before']+(route=='mdi'),'Wrong native open route')
            a.require(row['has_view']==(route=='mdi'),'Wrong native view availability')
            a.require(job['input']is None or row['loaded_file']==job['input'],'Wrong native input file')
            if route=='bare':a.require(row['import_code']==(None if job['input']is None else 0),'Native import failed')
            else:a.require(row['close_result']is True,'Native close was refused')
            a.require([p['getter']for p in row['print_values']]==GETTERS,'Print observation omitted')
            states[job['id']]={stage:a.inventory(row[stage],keys)for stage in STAGES}
        cohort[name]=dict(rows=rows,states=states)
        constructors[name]=a.constructor_rows(a.records(root/('native/'+name+'.stderr'),'ICT_LAYOUT17_CTOR '),fields,mode)
    target_fields={f['getter']for f in fields if f['type']!='tab'}
    comparisons=[]
    def compare(kind,left_name,right_name,job,left_stage,right_stage):
        delta=a.changes(cohort[left_name]['states'][job][left_stage],cohort[right_name]['states'][job][right_stage])
        comparisons.append(dict(kind=kind,left=left_name,right=right_name,job=job,left_stage=left_stage,right_stage=right_stage,
                           target=sum(targeted(c,keys,target_fields)for c in delta),non_target=sum(not targeted(c,keys,target_fields)for c in delta),changes=delta))
    for name in cohort:
        for job in jobs:
            compare('noop',name,name,job['id'],'opened','noop')
            compare('print',name,name,job['id'],'noop','after_print')
    for route in ('bare','mdi'):
        for left,right in itertools.combinations(('observe','preset-a','preset-b'),2):
            for job in jobs:
                for stage in STAGES:compare('mode',route+'-'+left,route+'-'+right,job['id'],stage,stage)
    for mode in ('observe','preset-a','preset-b'):
        for job in jobs:
            for stage in STAGES:compare('route','bare-'+mode,'mdi-'+mode,job['id'],stage,stage)
    attribution=[]
    for route in ('bare','mdi'):
        for job in jobs:
            for stage in STAGES:
                aa=cohort[route+'-preset-a']['states'][job['id']][stage]['headers']['layouts']
                bb=cohort[route+'-preset-b']['states'][job['id']][stage]['headers']['layouts']
                a.require(set(aa)==set(bb),'Preset layout identity changed')
                for identity in aa:
                    ap={p['getter']:p['value']for p in aa[identity]['properties']}
                    bp={p['getter']:p['value']for p in bb[identity]['properties']}
                    for f in fields:
                        if f['type']=='tab':continue
                        values=[f['expected_detached'][m]for m in ('preset-a','preset-b')]
                        expected=[dict(type='boolean'if type(v)is bool else 'number',value=v)for v in values]
                        attribution.append(dict(route=route,job=job['id'],stage=stage,layout=identity,getter=f['getter'],
                            preset_a=ap[f['getter']],preset_b=bp[f['getter']],follows_presets=a.equal([ap[f['getter']],bp[f['getter']]],expected),
                            equal_across_presets=a.equal(ap[f['getter']],bp[f['getter']])))
    print_deltas=[]
    for route in ('bare','mdi'):
        for job in jobs:
            left=next(r for r in cohort[route+'-preset-a']['rows']if r['id']==job['id'])['print_values']
            right=next(r for r in cohort[route+'-preset-b']['rows']if r['id']==job['id'])['print_values']
            print_deltas.append(dict(route=route,job=job['id'],changes=a.changes(left,right)))
    summary=dict(processes=6,document_jobs=84,constructors=constructors,inventory_comparisons=len(comparisons),
        differences={kind:dict(comparisons=sum(r['kind']==kind for r in comparisons),
                     target=sum(r['target']for r in comparisons if r['kind']==kind),
                     non_target=sum(r['non_target']for r in comparisons if r['kind']==kind))for kind in ('noop','print','mode','route')},
        attribution={route:{stage:dict(observations=sum(r['route']==route and r['stage']==stage for r in attribution),
                      follows_presets=sum(r['follows_presets']for r in attribution if r['route']==route and r['stage']==stage),
                      equal_across_presets=sum(r['equal_across_presets']for r in attribution if r['route']==route and r['stage']==stage))
                      for stage in STAGES}for route in ('bare','mdi')},
        print_value_changed_leaves=sum(len(r['changes'])for r in print_deltas),
        mdi_closes_accepted=sum(r.get('close_result')is True for n,c in cohort.items()if n.startswith('mdi-')for r in c['rows']),
        mdi_wrappers_still_counted=sum(r['windows_after']>r['windows_before']for n,c in cohort.items()if n.startswith('mdi-')for r in c['rows']),
        cad_files_saved=0,strict_comparison_run=False,whole_cad_qualified=False)
    a.require(a.read(root/'native/COMPLETE.json')==dict(processes=6,jobs=84,inputs_unchanged=True,cad_files_saved=0,whole_cad_qualified=False),
              'Native completion differs')
    return summary,dict(comparisons=comparisons,attribution=attribution,print_differences=print_deltas,profiles=profiles)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);args=p.parse_args()
    result,detail=analyze(args.root);out=args.root/'analysis';out.mkdir(exist_ok=False)
    for name,obj in [('summary',result),('detail',detail)]:
        (out/(name+'.json')).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result,indent=2))
