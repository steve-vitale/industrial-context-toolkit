"""Prepare, receive and replay declared second revisions using the existing native procedure."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
from native_revisions import HERE, ROOT, read, write, sha, lf, require, files
from prepare import frame
from run_cases import run_case
from receive import receive, equal
from evidence import unpack, MAX_RAW, MAX_FILE, MAX_FILES
from recheck_native_revisions import restore, check_packet
from compare_views import permitted_regions, pixel_counts
from PIL import Image
import cad_handoff as ch

METHODS=HERE/'NATIVE-REVISION-METHODS-1.json'


def binding():
    frozen=read(HERE/'SECOND-REVISION-FREEZE-1.json')
    for name,pin in frozen['files_sha256_lf'].items():require(lf(ROOT/name)==pin,'Frozen second-revision method/input differs: '+name)
    require(lf(METHODS)==frozen['selected_methods_sha256_lf'],'Selected native methods differ')
    catalog=read(HERE/'SECOND-REVISION-INPUTS.json')
    for row in catalog['cases']:
        for name in ('source','plan','candidate'):require(sha(ROOT/row[name])==row[name+'_sha256'],'Declared second revision '+name+' differs')
        packet=ROOT/row['native_packet'];pins=row['native_packet_pins']
        require(lf(packet/'INVENTORY.json')==pins['inventory_sha256_lf'] and lf(packet/'RESULT.json')==pins['result_sha256_lf'] and sha(packet/'evidence.tar.xz')==pins['archive_sha256'],'Original concurrent native packet differs')
    return catalog


def prepare(out):
    catalog=binding();require(not out.exists(),'New second preparation required')
    parent=read(HERE/'PREPARATION-1.json');out.mkdir(parents=True);(out/'cases').mkdir()
    prepared=dict(scope='Exposed second revisions; original preparation metadata is retained parent lineage, not the new producer',
        preparation=parent['preparation'],configuration_sha256=parent['configuration_sha256'],
        derivation=dict(producer_sha256_lf=lf(__file__),parent_preparation_sha256_lf=lf(HERE/'PREPARATION-1.json'),
            inputs_sha256_lf=lf(HERE/'SECOND-REVISION-INPUTS.json'),freeze_sha256_lf=lf(HERE/'SECOND-REVISION-FREEZE-1.json')),cases={})
    for row in catalog['cases']:
        packet=ROOT/row['native_packet'];original=check_packet(packet)
        require(original['role']=='edited' and original['committed_edits']==3,'Incomplete original concurrent edit')
        saved=unpack(packet)
        require(hashlib.sha256(saved['attempt/job/returned.dxf']).hexdigest()==row['source_sha256'],'New source is not the actual native concurrent return')
        folder=out/'cases'/row['case'];folder.mkdir()
        for name,file in [('source','source.dxf'),('plan','plan.json')]:shutil.copyfile(ROOT/row[name],folder/file)
        source=folder/'source.dxf';plan=read(folder/'plan.json');snapshot=ch.snapshot(source);ch.validate_plan(snapshot,plan)
        require(len(snapshot['assets'])==2 and len(plan['changes'])==1,'Second revision needs two retained assets and one selected edit')
        change=plan['changes'][0]
        require(change['id']==snapshot['assets'][0]['id'] and change['attribute']=='MODEL' and change['before']=='OTHER-CHOICE' and
            snapshot['assets'][1]['attributes']['SERIAL']=='FIELD-OBSERVED','Selected second-revision story differs')
        result=run_case(row['case'],source,folder/'plan.json',folder/'software');write(folder/'SOFTWARE.json',result)
        candidate=folder/'software/candidate/candidate.dxf'
        require(result['routes']['value-spans']['strict_status']=='pass' and result['routes']['value-spans']['byte_check']['status']=='pass' and
            candidate.read_bytes()==(ROOT/row['candidate']).read_bytes(),'Exact selected candidate strict/byte gate differs')
        docs=[ch.load(source),ch.load(candidate)];frames=dict(overview=frame([e for d in docs for e in d.modelspace()]))
        for number,asset in enumerate(snapshot['assets'],1):
            inserts=[d.entitydb[asset['handle']] for d in docs];attrs=[a for insert in inserts for a in insert.attribs]
            frames['asset-'+str(number)]=frame(inserts+attrs);frames['labels-'+str(number)]=frame(attrs)
        basis=dict(case=row['case'],source_sha256=sha(source),plan_sha256=sha(folder/'plan.json'),assets=snapshot['assets'],changes=plan['changes'],frames=frames,
            scope='Explicit second revision of an exposed native return; fictional SERIAL retained; original preservation and engineering disposition pending')
        write(folder/'basis.json',basis);prepared['cases'][row['case']]=dict(basis=basis,files=files(folder));write(out/'PREPARATION.json',prepared)
    return prepared


def receiving(attempt):
    catalog=binding();prepared=HERE/'SECOND-REVISION-PREPARATION-1.json'
    value=read(prepared);parent=read(HERE/'PREPARATION-1.json')
    require(value['derivation']==dict(producer_sha256_lf=lf(__file__),parent_preparation_sha256_lf=lf(HERE/'PREPARATION-1.json'),
        inputs_sha256_lf=lf(HERE/'SECOND-REVISION-INPUTS.json'),freeze_sha256_lf=lf(HERE/'SECOND-REVISION-FREEZE-1.json')),'Derived preparation lineage differs')
    require(equal(value['preparation'],parent['preparation']) and value['configuration_sha256']==parent['configuration_sha256'],'Parent preparation/configuration differs')
    require(set(value['cases'])=={r['case'] for r in catalog['cases']},'Second revision cohort omitted/extra')
    for row in catalog['cases']:
        case=value['cases'][row['case']];basis=case['basis']
        require(basis['source_sha256']==row['source_sha256'] and basis['plan_sha256']==row['plan_sha256'] and basis['changes']==read(ROOT/row['plan'])['changes'] and
            case['files']['software/candidate/candidate.dxf']==row['candidate_sha256'],'Declared second preparation differs')
    basis=read(attempt/'job/job.json')
    if basis['role']=='receiving':
        returns=read(HERE/'SECOND-NATIVE-RETURNS-1.json')['cases'][basis['case']]
        for role in ('baseline','edited'):require(sha(attempt/'job'/(role+'.dxf'))==returns[role+'_sha256'],'Fresh receiver native return differs')
    return receive(attempt,prepared,METHODS)


def package(attempt,execution,out):
    require(not out.exists(),'New second-revision packet required');result=receiving(attempt)
    require(read(execution/'EXIT.json')['exit']==0,'Original native host failed')
    saved={}
    for prefix,folder in [('attempt',attempt),('execution',execution)]:
        for p in folder.rglob('*'):
            if p.is_file():saved[prefix+'/'+p.relative_to(folder).as_posix()]=p.read_bytes()
    for name in ('second_revisions.py','SECOND-REVISION-INPUTS.json','SECOND-REVISION-FREEZE-1.json','SECOND-REVISION-PREPARATION-1.json'):
        saved['receiving/'+name]=(HERE/name).read_bytes()
    saved['receiving/RESULT.json']=(json.dumps(result,indent=2)+'\n').encode()
    require(len(saved)<=MAX_FILES and sum(map(len,saved.values()))<=MAX_RAW and max(map(len,saved.values()))<=MAX_FILE,'Second packet exceeds unchanged archive bounds')
    out.mkdir(parents=True)
    with tarfile.open(out/'evidence.tar.xz','w:xz',preset=6) as archive:
        for name,raw in sorted(saved.items()):
            member=tarfile.TarInfo(name);member.size=len(raw);member.mode=0o644;member.mtime=0;archive.addfile(member,io.BytesIO(raw))
    write(out/'INVENTORY.json',dict(archive_sha256=sha(out/'evidence.tar.xz'),files={n:dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()) for n,raw in sorted(saved.items())}))
    write(out/'RESULT.json',result)
    return dict(case=result['case'],role=result['role'],files=len(saved),raw_bytes=sum(map(len,saved.values())),archive_bytes=(out/'evidence.tar.xz').stat().st_size)


def check(packet):
    saved=unpack(packet)
    for name in ('second_revisions.py','SECOND-REVISION-INPUTS.json','SECOND-REVISION-FREEZE-1.json','SECOND-REVISION-PREPARATION-1.json'):
        require(saved['receiving/'+name].replace(b'\r\n',b'\n')==(HERE/name).read_bytes().replace(b'\r\n',b'\n'),'Retained second-revision method/preparation differs')
    with tempfile.TemporaryDirectory(prefix='ict-second-native-replay-') as temporary:
        root=Path(temporary);restore(saved,root);result=receiving(root/'attempt')
        require(equal(result,read(root/'receiving/RESULT.json')) and equal(result,read(packet/'RESULT.json')) and read(root/'execution/EXIT.json')['exit']==0,'Original second revision receipt/host differs')
    return dict(case=result['case'],role=result['role'],edits=result['committed_edits'],strict=result['native_strict'].get('unexpected'),whole_cad_qualified=False)


def pixels(attempt,out):
    require(not out.exists(),'New second pixel folder required');receipt=receiving(attempt)
    require(receipt['role']=='receiving','Fresh four-file receiver required')
    job=attempt/'job';basis=read(job/'job.json');captures=[r for r in read(job/'ui/actions.json') if r['kind']=='capture']
    out.mkdir(parents=True);comparisons=[];identities=[]
    for name in basis['frames']:
        selected={r['label']:r for r in captures if r['frame']==name};original=selected['source']
        for row in selected.values():require(equal(row['observation']['view'],original['observation']['view']) and row['canvas']['rectangle']==original['canvas']['rectangle'],'Exact camera/canvas differs; no registration')
        regions=permitted_regions(selected['source']['observation'],selected['candidate']['observation'],basis['changes'])
        def path(label):return job/'ui'/Path(selected[label]['images'][-1]['path']).with_suffix('.canvas.png')
        for left,right,mask in [('source','baseline',[]),('source','candidate',regions),('baseline','edited',regions)]:
            filename=name+'-'+left+'-'+right+'.png'
            with Image.open(path(left)) as a,Image.open(path(right)) as b:result=pixel_counts(a,b,mask,out/filename)
            comparisons.append(dict(frame=name,left=left,right=right,difference_image=filename,**result))
        for left,right in [('source','baseline'),('candidate','edited')]:
            with Image.open(path(left)) as a,Image.open(path(right)) as b:identical=a.mode==b.mode and a.size==b.size and a.tobytes()==b.tobytes()
            identities.append(dict(frame=name,left=left,right=right,identical_pixels=identical,left_sha256=sha(path(left)),right_sha256=sha(path(right))))
    result=dict(case=basis['case'],sources={n:sha(job/(n+'.dxf')) for n in ('source','baseline','edited','candidate')},comparisons=comparisons,exact_identities=identities,
        outside_pixels=sum(r['outside_permitted_regions'] for r in comparisons),all_exact_identities=all(r['identical_pixels'] for r in identities),
        agent_visual_review='separate unfinished gate',paper_view='unfinished',whole_cad_qualified=False)
    write(out/'RESULT.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('prepare');p.add_argument('out',type=Path)
    p=sub.add_parser('receive');p.add_argument('attempt',type=Path);p.add_argument('out',type=Path)
    p=sub.add_parser('package')
    for name in ('attempt','execution','out'):p.add_argument(name,type=Path)
    p=sub.add_parser('check');p.add_argument('packet',type=Path)
    p=sub.add_parser('pixels');p.add_argument('attempt',type=Path);p.add_argument('out',type=Path)
    args=parser.parse_args()
    if args.action=='prepare':print('Prepared',len(prepare(args.out)['cases']),'exposed second revisions')
    elif args.action=='receive':
        require(not args.out.exists(),'New second receipt required');r=receiving(args.attempt);write(args.out,r)
        print(json.dumps({k:r[k] for k in ('case','role','observations','editable_field_checks','committed_edits')}|dict(strict=r['native_strict'].get('unexpected'))))
    elif args.action=='package':print(json.dumps(package(args.attempt,args.execution,args.out)))
    elif args.action=='check':print(json.dumps(check(args.packet)))
    else:
        r=pixels(args.attempt,args.out);print(json.dumps(dict(case=r['case'],comparisons=len(r['comparisons']),outside_pixels=r['outside_pixels'],exact=r['all_exact_identities'])))


if __name__=='__main__':main()
