"""Run supplied drawing-return checks and assemble one source-linked engineer/manager brief.

Uses the existing markup and DXF reviewers; never reads images, edits drawings or releases them.
Markup-only jobs use the standard library. See docs/DRAWING_HANDOFF.md.
"""
import argparse
import copy
import hashlib
import html
import json
from pathlib import Path
import shutil
import sys
import tempfile
import check_pid_markups as markup


def require(value,message):
    if not value:raise ValueError(message)
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def cell(value):return html.escape(str(value)).replace('|','&#124;').replace('\n',' ')
def value(value):return json.dumps(value,ensure_ascii=False,sort_keys=True)
def observation(record):return value(record['value']) if record['state']=='known' else record['state']+': '+record.get('reason','source review required')


def run(manifest_path,out):
    manifest_path=Path(manifest_path).resolve();out=Path(out).resolve()
    require(not out.exists(),'Output exists; retain the earlier receiving packet')
    captured={manifest_path:manifest_path.read_bytes()};job=markup.parse(captured[manifest_path])
    require(isinstance(job,dict) and job.get('schema')=='drawing-receiving-1','Expected drawing-receiving-1 job')
    require(set(job)=={'schema','id','drawings'},'Job fields must be schema, id and drawings')
    markup.text(job['id'],'Job id')
    require(isinstance(job['drawings'],list) and job['drawings'],'Supply at least one drawing')
    prepared=[];ids=set();cad=None
    def path(value):
        markup.text(value,'Local input path');p=(manifest_path.parent/value).resolve()
        require(p.is_file(),'Input is not a local file: '+value)
        raw=p.read_bytes();require(p not in captured or captured[p]==raw,'Input changed during preparation')
        captured[p]=raw;return p
    for drawing in job['drawings']:
        require(isinstance(drawing,dict) and set(drawing)<= {'id','markup_manifest','cad'},'Unsupported drawing fields')
        identity=markup.text(drawing.get('id'),'Drawing id');require(identity not in ids,'Duplicate drawing id');ids.add(identity)
        require('markup_manifest' in drawing or 'cad' in drawing,'Drawing needs a markup or CAD check')
        entry=dict(id=identity)
        if 'markup_manifest' in drawing:
            entry['markup_manifest']=path(drawing['markup_manifest'])
            source=markup.prepare(entry['markup_manifest'])
            for p,raw in source[6].items():
                require(p not in captured or captured[p]==raw,'Markup source changed during preparation');captured[p]=raw
        if 'cad' in drawing:
            if cad is None:
                try:import cad_handoff as cad
                except ModuleNotFoundError as error:raise ValueError('DXF checks need the pinned CAD requirements: pip install -r requirements.txt') from error
            rule=drawing['cad'];require(isinstance(rule,dict) and {'before','after'}<=set(rule)<= {'before','after','plan'},'CAD needs before, after and optional plan')
            entry['cad']={k:path(v) for k,v in rule.items()}
            before=cad.snapshot(entry['cad']['before']);cad.snapshot(entry['cad']['after'])
            plan=markup.parse(captured[entry['cad']['plan']]) if 'plan' in rule else None
            if plan is not None:cad.validate_plan(before,plan)
            entry['plan']=plan
        prepared.append(entry)
    require(all(out!=p and out not in p.parents for p in captured),'Output would contain/overwrite an input')
    out.parent.mkdir(parents=True,exist_ok=True)
    portable=copy.deepcopy(job);rows=[];check_results=[]
    with tempfile.TemporaryDirectory(prefix='.drawing-receiving-',dir=out.parent) as temporary:
        root=Path(temporary)/'packet';root.mkdir();(root/'drawings').mkdir()
        for number,drawing in enumerate(prepared,1):
            folder=root/'drawings'/f'{number:03d}';folder.mkdir();base=folder.relative_to(root).as_posix();identity=drawing['id']
            def add(kind,status,finding,action,role,evidence,detail,priority='normal'):
                rows.append(dict(drawing=identity,kind=kind,status=status,finding=finding,next_action=action,
                    suggested_role=role,owner=None,disposition='pending',priority=priority,evidence=evidence,
                    detail=detail,review_required=True,needs_attention=status!='supported' or priority=='safety'))
            if 'markup_manifest' in drawing:
                report=markup.run(drawing['markup_manifest'],folder/'markup');link=base+'/markup/REPORT.html'
                portable['drawings'][number-1]['markup_manifest']=base+'/markup/manifest.json'
                actions={'supported':'Confirm the supplied reading and technical intent.','partly_supported':'Return the unmet checks for correction.',
                    'not_supported':'Return the missing or different checks for correction.','not_verifiable':'Obtain clear, source-bound instructions/readings.',
                    'baseline_mismatch':'Resolve the original baseline and requested intent.'}
                for item in report['markups']:
                    require(item['status'] in actions,'Unknown markup outcome')
                    action=actions[item['status']]
                    if item['priority']=='safety':action='Engineering safety review remains required. '+action
                    finding=item['id']+': '+item['text']
                    for check in item['checks']:
                        if check['status']=='baseline_mismatch':
                            finding+='; '+markup.describe_key(check['key'])+': original '+observation(check['original'])+', returned '+observation(check['returned'])
                    add('request',item['status'],finding,action,'Responsible engineer / drawing author',link,item,item['priority'])
                for kind,key,action in [('other_change','other_observed_changes','Assess the unrequested change and document its disposition.'),
                                        ('coverage_gap','other_fact_coverage_gaps','Obtain the missing/conflicting source evidence; retain unknown.')]:
                    for item in report[key]:
                        finding=markup.describe_key(item['key'])+': '+observation(item['original'])+' → '+observation(item['returned'])
                        add(kind,'needs_assessment',finding,action,'Responsible engineer',link,item)
                check_results.append(dict(drawing=identity,kind='markup',counts=report['counts'],report=link))
            if 'cad' in drawing:
                rule=drawing['cad'];report=cad.review(rule['before'],rule['after'],drawing['plan'],folder/'cad');link=base+'/cad/REPORT.html'
                portable['drawings'][number-1]['cad']={k:base+'/cad/originals/'+name for k,name in [('before','before.dxf'),('after','after.dxf')]}
                if drawing['plan'] is not None:portable['drawings'][number-1]['cad']['plan']=base+'/cad/originals/plan.json'
                statuses={'planned edit observed':'supported','planned edit missing or different':'not_supported','unexpected':'other_observed_change'}
                for item in report['asset_attributes']:
                    if item['status']=='unchanged':continue
                    require(item['status'] in statuses,'Unknown CAD attribute outcome');status=statuses[item['status']]
                    action='Confirm the value and technical intent.' if status=='supported' else 'Resolve the requested or unrequested field change against its source evidence.'
                    before=value(item['before']) if item['before_present'] else '(absent)'
                    after=value(item['after']) if item['after_present'] else '(absent)'
                    finding=item['id']+' / '+item['attribute']+': '+before+' → '+after
                    if item['planned_after'] is not None:finding+='; requested '+value(item['planned_after'])
                    add('cad_attribute',status,finding,action,'Responsible engineer / drawing custodian',link,item)
                for item in report['asset_changes']:
                    add('cad_identity','needs_assessment',item['id']+': '+item['status'],'Reconcile the identity/block/handle change; do not infer physical asset addition/removal.','Drawing custodian',link,item)
                add('cad_preservation','supported' if report['strict_status']=='pass' else 'preservation_differences',
                    str(report['strict_difference_count'])+' unexpected strict drawing differences',
                    'Review the complete strict queue and required receiving-editor/layout/editability checks.',
                    'Drawing custodian / responsible engineer',link,dict(strict_status=report['strict_status'],strict_difference_count=report['strict_difference_count'],
                        complete_queue=base+'/cad/strict-comparison.json',boundary=report['boundary']))
                check_results.append(dict(drawing=identity,kind='cad',strict_status=report['strict_status'],strict_difference_count=report['strict_difference_count'],report=link))
            if 'cad' in drawing and 'markup_manifest' in drawing:
                add('representation_correspondence','not_verified','Readable sheets and CAD were associated by the supplied job.',
                    'Confirm that these exact readable sheets and CAD revisions correspond; software has not established that equivalence.',
                    'Responsible engineer / drawing custodian',base+'/',dict(basis='Supplied association only; no inferred cross-format equivalence'))
        rows.sort(key=lambda r:(r['priority']!='safety',not r['needs_attention'],r['drawing']))
        suggestions=[]
        if any(r['status'] in ('not_supported','partly_supported') for r in rows):suggestions.append('return_for_correction')
        if any(r['needs_attention'] and r['status'] not in ('not_supported','partly_supported') for r in rows):suggestions.append('escalate_for_clarification_or_technical_review')
        if not suggestions:suggestions.append('present_for_authorized_receiving_review')
        brief=dict(schema='drawing-receiving-brief-1',job_id=job['id'],checks=check_results,items=rows,suggested_actions=suggestions,
            authorized_decision='pending',release_accepted=False,automatic_drawing_reading=False,
            boundary='Findings reflect supplied source-bound readings and supported DXF checks. Readability, complete coverage, geometry/functional interpretation and organizational release remain review responsibilities.')
        write(root/'brief.json',brief);write(root/'job.json',portable);(root/'input-job.json').write_bytes(captured[manifest_path])
        lines=['# Drawing receiving brief','',job['id'],'','Suggested actions: '+', '.join(suggestions)+'. Authorized decision: **pending**.','',
            '| Drawing | Finding | Next action | Suggested role | Evidence |','|---|---|---|---|---|']
        for row in rows:lines.append('| '+' | '.join([cell(row['drawing']),cell(row['finding']+' — '+row['status']),cell(row['next_action']),cell(row['suggested_role']),'[Source checks]('+row['evidence']+')'])+' |')
        lines+=['','Owners and dispositions remain pending. Complete values, source checks and locations are retained in [brief.json](brief.json).','',brief['boundary']]
        (root/'BRIEF.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
        require(all(p.read_bytes()==raw for p,raw in captured.items()),'Input changed before publication')
        write(root/'receipt.json',dict(schema='drawing-receiving-receipt-1',input_job_sha256=sha(captured[manifest_path]),
            tool_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')),
            files={p.relative_to(root).as_posix():sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}))
        shutil.copytree(root,out)
    return brief


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    try:r=run(a.manifest,a.out)
    except (ValueError,OSError,KeyError,TypeError) as error:print('REFUSED: '+str(error),file=sys.stderr);return 2
    print('Receiving packet written:',len(r['checks']),'checks;',len(r['items']),'review items; authorized decision pending.');return 0


if __name__=='__main__':raise SystemExit(main())
