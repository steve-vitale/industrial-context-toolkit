"""Re-score causal branches with the unchanged strict comparator; never normalizes entity payloads."""
import copy
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[3]/'scripts'))
import cad_handoff as ch

IDS=('libre-air-water','libre-power','libre-motion','qcad-hydraulic','qcad-mechanical','qcad-template')
ROUTES=('noop','patched','edited','repeat')
CONFIG='/home/cad/.config/QCAD/QCAD3.conf'
def require(ok,message):
    if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')

def native_rows(path,expected):
    lines=path.read_text(encoding='utf-8').splitlines()
    require(not any('ICT_ROOT12_FATAL ' in s for s in lines),'Native fatal recorded')
    profiles=[json.loads(s.split(' ',1)[1]) for s in lines if s.startswith('ICT_ROOT12_PROFILE ')]
    require(len(profiles)==1 and profiles[0]['configuration_file']==CONFIG,'Wrong native profile')
    rows=[json.loads(s.split(' ',1)[1]) for s in lines if s.startswith('ICT_ROOT12 ')]
    require([r['id'] for r in rows]==expected and all('error' not in r for r in rows),'Native case/route omitted, duplicated or failed')
    return rows

def fields(rows):
    groups={}
    for row in rows:
        group=groups.setdefault(row['parent'],{})
        require(row['tag'] not in group,'Duplicate native tag')
        group[row['tag']]=row['text']
    result={}
    for group in groups.values():
        require('ICT_ID' in group and group['ICT_ID'] not in result,'Missing/duplicate native identity')
        result[group['ICT_ID']]=group
    return result

def expected_fields(snapshot,plan=None):
    result={a['id']:dict(a['attributes']) for a in snapshot['assets']}
    for c in (plan or {}).get('changes',[]):
        require(result[c['id']][c['attribute']]==c['before'],'Plan before-value mismatch')
        result[c['id']][c['attribute']]=c['after']
    return result

def operation_state(imported,after,plan):
    expected=copy.deepcopy(imported)
    groups={r['parent']:r['text'] for r in expected if r['tag']=='ICT_ID'}
    for c in (plan or {}).get('changes',[]):
        hits=[r for r in expected if groups[r['parent']]==c['id'] and r['tag']==c['attribute']]
        require(len(hits)==1 and hits[0]['text']==c['before'],'Ambiguous native operation target')
        hits[0]['text']=c['after']
    require(after==expected,'Native operation changed an unplanned observed property')

def comparison(before,after,plan=None):
    report=ch.compare(before,after,plan)
    kinds=Counter(r['kind'] for r in report['unexpected'])
    pairs=Counter(((r['before'] or {}).get('type','absent')+' -> '+(r['after'] or {}).get('type','absent'))
        for r in report['unexpected'] if r['kind']=='entity')
    return dict(strict_differences=len(report['unexpected']),strict_status=report['status'],
        kinds=dict(sorted(kinds.items())),entity_type_pairs=dict(sorted(pairs.items())),
        strict_rows_sha256=hashlib.sha256(json.dumps(report['unexpected'],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest(),
        before_sha256=before['sha256'],after_sha256=after['sha256'])

def analyze(root):
    frozen=read(root/'FREEZE.json')
    for name,pin in frozen['inputs'].items():require(sha(root/name)==pin,'Frozen input changed: '+name)
    jobs=read(root/'export.json')['jobs']
    wanted=[identity+'/'+route+'-'+fmt for identity in IDS for fmt in ('default','r15') for route in ROUTES]
    require([j['id'] for j in jobs]==wanted,'Frozen job cohort differs')
    require(read(root/'fresh.json')==dict(jobs=jobs,read_only=True),'Fresh-process job cohort differs')
    commands=read(root/'native/commands.json')
    require([c['id'] for c in commands]==['export','fresh'] and all(c['exit']==0 for c in commands),'Native process not successful')
    previous=frozen['configuration_sha256']
    for row in commands:
        expected=['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances','-config',CONFIG,
            '-font-substitution','Standard','DejaVu Sans','-autostart','/work/native_probe.js','-m','/work/'+row['id']+'.json']
        require(row['command']==expected and row['configuration_sha256_before']==previous,'Native command/profile chain differs')
        previous=row['configuration_sha256_after']
        require(('absConfigFile: "'+CONFIG+'"').encode() in (root/'native'/(row['id']+'.stderr')).read_bytes(),'Selected configuration stderr missing')
    require(read(root/'native/COMPLETE.json')==dict(commands=2,jobs=48,inputs_unchanged=True,whole_cad_qualified=False),'Incomplete producer receipt')
    native=native_rows(root/'native/export.stdout',wanted);fresh=native_rows(root/'native/fresh.stdout',wanted)
    snapshots={}
    for identity in IDS:
        base=root/'cases'/identity
        for name in ('source','candidate'):
            snapshots[(identity,name)]=ch.snapshot(base/(name+'.dxf'))
        for fmt in ('default','r15'):
            for route in ROUTES:snapshots[(identity,route+'-'+fmt)]=ch.snapshot(base/'returns'/(route+'-'+fmt+'.dxf'))
    observations=0;state_repeats=0;property_repeats=0
    for job,row,reread in zip(jobs,native,fresh):
        identity,routefmt=job['id'].split('/');route,fmt=routefmt.split('-')
        plan=read(root/'cases'/identity/'plan.json')
        source_key='candidate' if route=='patched' else 'noop-'+fmt if route=='repeat' else 'source'
        source=snapshots[(identity,source_key)];expected=expected_fields(source,plan if route=='edited' else None)
        require(fields(row['imported'])==expected_fields(source),'Native imported field differs')
        operation_state(row['imported'],row['before_export'],plan if route=='edited' else None)
        for stage in ('before_export','after_export','reopened'):
            require(fields(row[stage])==expected,'Native stored field differs at '+job['id']+'/'+stage)
        require(fields(reread['imported'])==expected,'Fresh-process stored field differs')
        require(expected_fields(snapshots[(identity,routefmt)])==expected,'Saved-file decoded attribute differs')
        observations+=sum(len(v) for v in expected.values())
        state_repeats+=int(row['reopened']==reread['imported'])
        # QSet traversal order is not a property of a CAD attribute. Check every complete keyed row,
        # retaining the separate literal array-repeat count above rather than concealing order changes.
        key=lambda v:(v['parent'],v['tag'])
        property_repeats+=int(sorted(row['reopened'],key=key)==sorted(reread['imported'],key=key))
    require(property_repeats==48,'Fresh-process observed attribute property differs')
    rows=[]
    for identity in IDS:
        source=snapshots[(identity,'source')];candidate=snapshots[(identity,'candidate')]
        plan=read(root/'cases'/identity/'plan.json');ch.validate_plan(source,plan)
        require(comparison(source,candidate,plan)['strict_differences']==0,'Original exact candidate no longer passes')
        for fmt in ('default','r15'):
            noop=snapshots[(identity,'noop-'+fmt)];edited=snapshots[(identity,'edited-'+fmt)]
            rebound=dict(plan,source_sha256=noop['sha256'])
            for name,left,right,edits in (
                ('source_to_noop',source,noop,None),('source_to_edited',source,edited,plan),
                ('noop_to_edited',noop,edited,rebound),
                ('patched_to_edited',snapshots[(identity,'patched-'+fmt)],edited,None),
                ('first_to_second',noop,snapshots[(identity,'repeat-'+fmt)],None)):
                rows.append(dict(id=identity,format=fmt,comparison=name,**comparison(left,right,edits)))
    return dict(cases=len(IDS),exports=len(jobs),native_fields_per_stage=observations,
        fresh_state_exact_repeats=state_repeats,fresh_keyed_property_repeats=property_repeats,comparisons=rows,whole_cad_qualified=False,
        scope='Exposed development causal controls; original strict comparison; no UI/render/plant acceptance')

if __name__=='__main__':
    result=analyze(Path(sys.argv[1]));write(Path(sys.argv[2]),result)
    for name in ('source_to_noop','source_to_edited','noop_to_edited','patched_to_edited','first_to_second'):
        rows=[r for r in result['comparisons'] if r['comparison']==name]
        print(name,[r['strict_differences'] for r in rows])
