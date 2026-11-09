"""Review an actually received native concurrent return and retain an explicit second proposal."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import traceback
from native_revisions import HERE, ROOT, read, write, sha, lf, require, receiving
import cad_handoff as ch
from verify_bytes import verify


def command(out,label,args,expected=0,message=None):
    folder=out/'commands'/label;folder.mkdir(parents=True)
    argv=[sys.executable]+[str(a) for a in args]
    write(folder/'COMMAND.json',dict(argv=['python']+[v.replace(str(out),'$OUT').replace(str(ROOT),'$ROOT') for v in argv[1:]],expected_exit=expected))
    result=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=120)
    (folder/'stdout.txt').write_bytes(result.stdout);(folder/'stderr.txt').write_bytes(result.stderr)
    write(folder/'EXIT.json',dict(exit=result.returncode))
    require(result.returncode==expected,label+': unexpected command exit')
    if message:require(message.encode() in result.stderr,label+': missing intended refusal')


def review(attempt,out):
    require(not out.exists(),'Use a new engineering review folder')
    freeze=read(HERE/'NATIVE-REVISION-REVIEW-1.json')
    for name,pin in freeze['files_sha256_lf'].items():require(lf(ROOT/name)==pin,'Frozen review method changed: '+name)
    native=receiving(attempt,HERE/'NATIVE-REVISION-PREPARATION-1.json',HERE/'NATIVE-REVISION-METHODS-1.json')
    require(native['role']=='edited' and native['committed_edits']==3,'Complete three-edit native return required')
    basis=read(attempt/'job/job.json');label=basis['case'];original=ROOT/'examples/cad-handoff/qualification/validation-2/authored'/(label+'.dxf')
    initial_plan=read(original.with_suffix('.plan.json'));returned=attempt/'job/returned.dxf'
    out.mkdir(parents=True)
    try:
        (out/'native-return.dxf').write_bytes(returned.read_bytes());returned=out/'native-return.dxf'
        write(out/'original-plan.json',initial_plan)
        cli=ROOT/'scripts/cad_handoff.py';patch=ROOT/'scripts/cad_value_patch.py';project=ROOT/'examples/cad-handoff/project_to_map.py';map_cli=ROOT/'scripts/one_map.py'
        command(out,'original-review',[cli,'review',original,returned,'--plan',out/'original-plan.json','--out',out/'original-review'],1)
        original_review=read(out/'original-review/review.json');assets=ch.snapshot(original)['assets'];a,b=assets
        fields={(v['id'],v['attribute']):v for v in original_review['asset_attributes']}
        conflict=fields[(a['id'],'MODEL')];serial=fields[(b['id'],'SERIAL')]
        require(conflict['status']=='planned edit missing or different' and conflict['after']=='OTHER-CHOICE','Actual native MODEL disagreement missing')
        require(serial['before']=='UNCHANGED-1' and serial['after']=='FIELD-OBSERVED','Actual native SERIAL change missing')
        require(fields[(b['id'],'MODEL')]['after']==initial_plan['changes'][1]['after'],'Actual supported MODEL missing')
        write(out/'stale-before-plan.json',dict(initial_plan,source_sha256=sha(returned)))
        for name,request,message in [('stale-hash','original-plan.json','exact current source SHA-256'),('stale-before','stale-before-plan.json','Before-value mismatch')]:
            command(out,name,[patch,returned,out/request,'--out',out/name],2,message)
            require(not (out/name).exists(),'Stale native proposal published output')
        selected=dict(initial_plan,source_sha256=sha(returned),changes=[dict(id=a['id'],attribute='MODEL',before='OTHER-CHOICE',
            after=initial_plan['changes'][0]['after'],reason='Explicit fictional technical selection; preserve concurrent SERIAL; original preservation/scope review and authorized acceptance remain pending')])
        write(out/'second-plan.json',selected)
        command(out,'second-proposal',[patch,returned,out/'second-plan.json','--out',out/'second'])
        candidate=out/'second/candidate.dxf';byte_result=verify(returned,candidate,selected);write(out/'second-bytes.json',byte_result)
        command(out,'original-v-selected',[cli,'review',original,candidate,'--plan',out/'original-plan.json','--out',out/'original-v-selected'],1)
        selected_review=read(out/'original-v-selected/review.json')
        changed={(v['id'],v['attribute']):v for v in selected_review['asset_attributes']}
        require(changed[(b['id'],'SERIAL')]['after']=='FIELD-OBSERVED' and changed[(a['id'],'MODEL')]['after']==initial_plan['changes'][0]['after'],'Selected scope/field history lost')
        mapping=dict(site='S',plant='P',unit='U',assets=[dict(id=v['id'],tag=v['attributes']['TAG'],section='instruments') for v in assets]);write(out/'mapping.json',mapping)
        for name,packet in [('original',HERE/'revision-loss-1'/label/'proposal'),('selected',out/'second/candidate-context')]:
            projection=out/('map-'+name)
            command(out,'project-'+name,[project,packet,out/'mapping.json','--out',projection])
            command(out,'build-'+name,[map_cli,'build',projection/'site.json','--out',projection/'map'])
            expected=original if name=='original' else candidate
            require((projection/'cad-source.dxf').read_bytes()==expected.read_bytes(),'Draft map lost exact source')
        command(out,'map-changes',[map_cli,'changes',out/'map-original/map/graph.json',out/'map-selected/map/graph.json','--out',out/'map-changes'])
        result=dict(case=label,native_source_sha256=sha(returned),original_sha256=sha(original),native_receipt=native,
            original_request_strict=original_review['strict_difference_count'],findings=[conflict,serial],stale_refusals=2,
            second_candidate_sha256=sha(candidate),second_candidate_bytes=byte_result,second_candidate_strict=read(out/'second/comparison.json')['status'],
            original_request_selected_strict=selected_review['strict_difference_count'],retained_serial='FIELD-OBSERVED',
            cli_commands=len(list((out/'commands').iterdir())),authorized_disposition='pending',
            boundary='Selected candidate preserves this actual native return; original native-save differences and original scope remain unresolved. Second revision native receiving is separate.')
        write(out/'RESULT.json',result);return result
    except Exception:
        (out/'FAILURE.txt').write_text(traceback.format_exc(),encoding='utf-8',newline='\n');raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('attempt',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    r=review(a.attempt,a.out);print(json.dumps(dict(case=r['case'],original_strict=r['original_request_strict'],selected_original_strict=r['original_request_selected_strict'],second_strict=r['second_candidate_strict'],cli_commands=r['cli_commands'])))
