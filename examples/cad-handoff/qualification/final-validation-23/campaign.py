"""Bounded final intake and matched software/revision/loss evaluation; no native UI implementation."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(HERE.parent/'full-ui-22'));sys.path.insert(0,str(HERE.parent))
import cad_handoff as ch
import cad_value_patch as patcher
import receive_drawings as receiving
from run_cases import run_case
from verify_bytes import verify
from revision_losses import mutate
from adapt_public import adapt


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def lf(path):return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=True)+'\n',encoding='utf-8',newline='\n')
def require(value,message):
    if not value:raise ValueError(message)


def binding():
    frozen=read(HERE/'FREEZE.json')
    for name,pin in frozen['methods_sha256_lf'].items():require(lf(ROOT/name)==pin,'Frozen final method differs: '+name)
    require(sha(HERE/'SELECTION.json')==frozen['selection_sha256'],'Final public selection differs')
    require(sha(HERE/'authored/MANIFEST.json')==frozen['authored_manifest_sha256'],'Final authored manifest differs')
    return frozen


def intake(out):
    binding();require(not out.exists(),'Fresh final public intake required');out.mkdir(parents=True)
    rows=[]
    for selected in read(HERE/'SELECTION.json')['cases']:
        folder=out/selected['id'];folder.mkdir();row=dict(selected);rows.append(row)
        try:
            url='https://raw.githubusercontent.com/'+selected['repository']+'/'+selected['commit']+'/'+selected['path']
            path=folder/'original.dxf';cmd=['curl.exe','--fail','--location','--silent','--show-error',url,'--output',str(path)]
            result=subprocess.run(cmd,capture_output=True)
            row['transport']=dict(command=cmd,exit=result.returncode,stderr=result.stderr.decode('utf-8',errors='replace'))
            require(result.returncode==0,'Download failed; no replacement')
            raw=path.read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            require(blob==selected['git_blob_sha1'] and len(raw)==selected['bytes'],'Pinned public Git blob differs')
            row['original_sha256']=sha(path)
            try:row['original_admission']=dict(status='pass',assets=len(ch.snapshot(path)['assets']))
            except Exception as error:row['original_admission']=dict(status='refused',error=type(error).__name__+': '+str(error))
            target=folder/'source.dxf';plan,recipe=adapt(path,selected['id'],target)
            write(folder/'plan.json',plan);write(folder/'ADAPTATION.json',recipe)
            row.update(source_sha256=sha(target),plan_sha256=sha(folder/'plan.json'),status='adapted_not_evaluated')
        except Exception as error:row.update(status='failed',error=type(error).__name__+': '+str(error),traceback=traceback.format_exc())
        write(out/'ADMISSION.json',dict(cases=rows,candidate_executed=False,whole_cad_qualified=False))
        print(selected['id'],row['status'],flush=True)
    return rows


def evaluate_case(identity,source,planpath,out):
    original=source.read_bytes();plan=read(planpath);before=ch.snapshot(source)
    result=run_case(identity,source,planpath,out)
    candidate=out/'candidate/candidate.dxf';positive=result['routes']['value-spans']
    if positive.get('strict_status')!='pass' or positive.get('byte_check',{}).get('status')!='pass':
        result['controls_not_run']='Candidate did not pass declared positive gates';return result
    doc=ch.load(candidate);assets={a['id']:a for a in before['assets']};first=plan['changes'][0];asset=assets[first['id']]
    tests=[]
    def refused(label,drawing,proposal,target=None):
        target=target or out/'refusals'/label
        before_files={p.relative_to(target).as_posix():p.read_bytes() for p in target.rglob('*') if p.is_file()} if target.exists() else None
        try:patcher.apply(drawing,proposal,target)
        except Exception as error:
            after_files={p.relative_to(target).as_posix():p.read_bytes() for p in target.rglob('*') if p.is_file()} if target.exists() else None
            tests.append(dict(id=label,refused=True,error=type(error).__name__+': '+str(error),output_preserved=after_files==before_files))
        else:tests.append(dict(id=label,refused=False,output_preserved=False))
    wrong=copy.deepcopy(plan);wrong['source_sha256']='0'*64;refused('stale_hash',source,wrong)
    wrong=copy.deepcopy(plan);wrong['changes'][0]['before']='WRONG-BEFORE';refused('wrong_before',source,wrong)
    wrong=copy.deepcopy(plan);wrong['changes'].append(wrong['changes'][0]);refused('duplicate_edit',source,wrong)
    wrong=copy.deepcopy(plan);wrong['changes'][0].update(attribute='ICT_ID',before=asset['id'],after='OTHER-ID');refused('identity_edit',source,wrong)
    wrong=copy.deepcopy(plan);wrong['changes'][0]['after']='LINE1\nLINE2';refused('newline_value',source,wrong)
    ambiguous,mutation=mutate(original,'ATTRIB',asset['attribute_handles'][first['attribute']],1,b'AMBIGUOUS',extra=True)
    path=out/'ambiguous.dxf';path.write_bytes(ambiguous);wrong=copy.deepcopy(plan);wrong['source_sha256']=sha(path)
    refused('ambiguous_serialization',path,wrong)
    collision=out/'occupied';collision.mkdir();(collision/'KEEP.txt').write_bytes(b'Existing owner work\n');refused('output_collision',source,plan,collision)

    choices=[];geometry=next((e for e in doc.modelspace() if e.dxftype() in ('LINE','CIRCLE','ARC','ELLIPSE','INSERT')),None)
    if geometry:
        choices += [('geometry',geometry.dxftype(),geometry.dxf.handle,10,None),('layer',geometry.dxftype(),geometry.dxf.handle,8,b'UNREQUESTED_LOSS_LAYER')]
    style=doc.styles.get('Standard');choices.append(('style','STYLE',style.dxf.handle,40,None))
    foreign=next((a for a in before['assets'] if 'VENDOR_PRIVATE' in a['attributes']),None)
    if foreign:choices.append(('foreign_attribute','ATTRIB',foreign['attribute_handles']['VENDOR_PRIVATE'],1,b'LOST-FOREIGN'))
    xdata=next((e for e in doc.entitydb.values() if e.is_alive and e.has_xdata('FOREIGN_VENDOR')),None)
    if xdata:choices.append(('xdata',xdata.dxftype(),xdata.dxf.handle,1000,b'LOST-XDATA'))
    losses=[]
    for label,kind,handle,code,replacement in choices:
        row=dict(id=label);losses.append(row)
        try:
            raw,mutation=mutate(candidate.read_bytes(),kind,handle,code,replacement)
            path=out/'losses'/(label+'.dxf');path.parent.mkdir(exist_ok=True);path.write_bytes(raw)
            comparison=ch.compare(before,ch.snapshot(path),plan);write(out/'losses'/(label+'.strict.json'),comparison)
            row.update(mutation=mutation,strict_detected=bool(comparison['unexpected']),strict_differences=len(comparison['unexpected']))
            try:verify(source,path,plan)
            except ValueError as error:row.update(bytes_refused=True,byte_error=str(error))
            else:row['bytes_refused']=False
        except Exception as error:row.update(error=type(error).__name__+': '+str(error),traceback=traceback.format_exc())

    branch=copy.deepcopy(plan);branch['changes'][0]['after']='OTHER-CHOICE'
    other=next((a for a in before['assets'] if a['id']!=asset['id']),asset)
    field='SERIAL' if 'SERIAL' in other['attributes'] else 'TAG'
    collateral=dict(id=other['id'],attribute=field,before=other['attributes'][field],after='FIELD-OBSERVED',reason='Authored concurrent test change; no installed-state authority')
    branch['changes'].append(collateral);write(out/'concurrent-plan.json',branch)
    patcher.apply(source,branch,out/'concurrent');returned=out/'concurrent/candidate.dxf'
    refused('stale_revision_hash',returned,plan)
    wrong=copy.deepcopy(plan);wrong['source_sha256']=sha(returned);refused('stale_revision_before',returned,wrong)
    selected=dict(schema='cad-edit-plan-1',source_sha256=sha(returned),changes=[dict(first,before='OTHER-CHOICE',reason='Explicit test correction; retain collateral; authorized review remains pending')])
    write(out/'selected-plan.json',selected);patcher.apply(returned,selected,out/'selected');corrected=out/'selected/candidate.dxf'
    write(out/'selected-bytes.json',verify(returned,corrected,selected))
    original_scope=ch.compare(before,ch.snapshot(corrected),plan);write(out/'original-scope.json',original_scope)
    for label,path in [('initial',returned),('resubmission',corrected)]:
        job=dict(schema='drawing-receiving-1',id='Final validation '+identity+' '+label,drawings=[dict(id=identity,cad=dict(before=str(source.resolve()),after=str(path.resolve()),plan=str(planpath.resolve())))])
        write(out/(label+'-job.json'),job)
    initial=receiving.run(out/'initial-job.json',out/'initial')
    current=receiving.run(out/'resubmission-job.json',out/'resubmission',out/'initial')
    portable=receiving.run(out/'resubmission/job.json',out/'portable')
    result.update(refusals=tests,losses=losses,losses_not_applicable=sorted(set(('geometry','layer','style','foreign_attribute','xdata'))-{r['id'] for r in losses}),
        revision=dict(original_scope_unexpected=len(original_scope['unexpected']),collateral=collateral,
            basis_changes=current['revision']['basis_changes'],initial_actions=initial['suggested_actions'],current_actions=current['suggested_actions'],
            portable_brief_equal=current==portable,authorized_decision=current['authorized_decision'],release_accepted=current['release_accepted']),
        source_unchanged=source.read_bytes()==original)
    result['software_controls_pass']=all(r['refused'] and r['output_preserved'] for r in tests) and all(r.get('strict_detected') and r.get('bytes_refused') for r in losses) and len(original_scope['unexpected'])==1 and not current['revision']['basis_changes'] and current==portable and not current['release_accepted'] and result['source_unchanged']
    write(out/'EVALUATION.json',result)
    return result


def software(out):
    binding();require(not out.exists(),'Fresh final evaluation required');out.mkdir(parents=True)
    inputs=read(HERE/'INPUTS.json');results=[]
    for row in inputs['cases']:
        result=dict(case=row['id']);results.append(result)
        try:
            require(row['status']=='admitted','Case not admitted: '+row.get('error','see admission'))
            source=ROOT/row['source'];plan=ROOT/row['plan']
            require(sha(source)==row['source_sha256'] and sha(plan)==row['plan_sha256'],'Frozen final input differs')
            result.update(evaluate_case(row['id'],source,plan,out/row['id']))
        except Exception as error:result.update(error=type(error).__name__+': '+str(error),traceback=traceback.format_exc())
        write(out/'RESULT.json',dict(cases=results,whole_cad_qualified=False,scope='Reserved procedural/public-adapted software evaluation; native/UI/rendering evidence separate'))
        print(row['id'],result.get('software_controls_pass',result.get('error','positive gate failed')),flush=True)
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('intake','software'));p.add_argument('out',type=Path)
    a=p.parse_args()
    if a.action=='intake':intake(a.out)
    else:software(a.out)
