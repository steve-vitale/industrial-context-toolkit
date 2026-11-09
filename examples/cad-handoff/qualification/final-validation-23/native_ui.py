"""Bind final reserved inputs to the unchanged native UI receiver and pixel recipe."""
import argparse
import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
from campaign import HERE, ROOT, read, write, sha, lf, require, binding
from receive import receive, equal
from evidence import unpack, MAX_RAW, MAX_FILE, MAX_FILES
from recheck_native_revisions import restore
from compare_views import permitted_regions, pixel_counts
from PIL import Image

METHODS=HERE.parent/'full-ui-22/NATIVE-REVISION-METHODS-1.json'


def receiving(attempt):
    binding();preparation=read(HERE/'UI-PREPARATION.json')
    require(preparation['derivation']==dict(producer_sha256_lf=lf(HERE/'native_inputs.py'),final_freeze_sha256_lf=lf(HERE/'FREEZE.json')),'Final UI preparation lineage differs')
    inputs={row['id']:row for row in read(HERE/'INPUTS.json')['cases']}
    require(set(preparation['cases'])=={'public-air-water','final-foreign'},'Predetermined UI cohort differs')
    for identity,row in preparation['cases'].items():
        require(row['basis']['source_sha256']==inputs[identity]['source_sha256'] and row['basis']['plan_sha256']==inputs[identity]['plan_sha256'],'Final UI input differs from reserved admission')
    basis=read(attempt/'job/job.json')
    if basis['role']=='receiving':
        returns=read(HERE/'UI-RETURNS.json')['cases'][basis['case']]
        for role in ('baseline','edited'):require(sha(attempt/'job'/(role+'.dxf'))==returns[role+'_sha256'],'Final fresh UI return differs')
    return receive(attempt,HERE/'UI-PREPARATION.json',METHODS)


def package(attempt,execution,out):
    require(not out.exists(),'Fresh final native packet required');result=receiving(attempt)
    require(read(execution/'EXIT.json')['exit']==0,'Original final native host failed')
    saved={}
    for prefix,folder in [('attempt',attempt),('execution',execution)]:
        for p in folder.rglob('*'):
            if p.is_file():saved[prefix+'/'+p.relative_to(folder).as_posix()]=p.read_bytes()
    saved['receiving/RESULT.json']=(json.dumps(result,indent=2)+'\n').encode()
    require(len(saved)<=MAX_FILES and sum(map(len,saved.values()))<=MAX_RAW and max(map(len,saved.values()))<=MAX_FILE,'Final packet exceeds unchanged bounds')
    out.mkdir(parents=True)
    with tarfile.open(out/'evidence.tar.xz','w:xz',preset=6) as archive:
        for name,raw in sorted(saved.items()):
            item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o644;item.mtime=0;archive.addfile(item,io.BytesIO(raw))
    write(out/'INVENTORY.json',dict(archive_sha256=sha(out/'evidence.tar.xz'),files={n:dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()) for n,raw in sorted(saved.items())}))
    write(out/'RESULT.json',result)
    return dict(case=result['case'],role=result['role'],strict=result['native_strict'].get('unexpected'),files=len(saved),whole_cad_qualified=False)


def check(packet):
    saved=unpack(packet)
    with tempfile.TemporaryDirectory(prefix='ict-final-ui-') as temporary:
        root=Path(temporary);restore(saved,root);result=receiving(root/'attempt')
        require(equal(result,read(root/'receiving/RESULT.json')) and equal(result,read(packet/'RESULT.json')) and read(root/'execution/EXIT.json')['exit']==0,'Final native packet replay differs')
    return result


def pixels(attempt,out):
    require(not out.exists(),'New final model pixel folder required');receipt=receiving(attempt)
    require(receipt['role']=='receiving','Fresh final four-file receiver required')
    job=attempt/'job';basis=read(job/'job.json');captures=[r for r in read(job/'ui/actions.json') if r['kind']=='capture']
    out.mkdir(parents=True);comparisons=[];identities=[]
    for frame in basis['frames']:
        selected={r['label']:r for r in captures if r['frame']==frame};original=selected['source']
        for row in selected.values():require(equal(row['observation']['view'],original['observation']['view']) and row['canvas']['rectangle']==original['canvas']['rectangle'],'Exact final camera/canvas differs')
        regions=permitted_regions(selected['source']['observation'],selected['candidate']['observation'],basis['changes'])
        def path(label):return job/'ui'/Path(selected[label]['images'][-1]['path']).with_suffix('.canvas.png')
        for left,right,mask in [('source','baseline',[]),('source','candidate',regions),('baseline','edited',regions)]:
            name=frame+'-'+left+'-'+right+'.png'
            with Image.open(path(left)) as a,Image.open(path(right)) as b:value=pixel_counts(a,b,mask,out/name)
            comparisons.append(dict(frame=frame,left=left,right=right,difference_image=name,**value))
        for left,right in [('source','baseline'),('candidate','edited')]:
            with Image.open(path(left)) as a,Image.open(path(right)) as b:identical=a.mode==b.mode and a.size==b.size and a.tobytes()==b.tobytes()
            identities.append(dict(frame=frame,left=left,right=right,identical_pixels=identical,left_sha256=sha(path(left)),right_sha256=sha(path(right))))
    value=dict(case=basis['case'],comparisons=comparisons,exact_identities=identities,outside_pixels=sum(r['outside_permitted_regions'] for r in comparisons),
        all_exact_identities=all(r['identical_pixels'] for r in identities),visual_inspection='separate gate',whole_cad_qualified=False)
    write(out/'RESULT.json',value);return value


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('package')
    for name in ('attempt','execution','out'):a.add_argument(name,type=Path)
    a=sub.add_parser('check');a.add_argument('packet',type=Path)
    a=sub.add_parser('pixels');a.add_argument('attempt',type=Path);a.add_argument('out',type=Path)
    a=p.parse_args()
    if a.action=='package':print(package(a.attempt,a.execution,a.out))
    elif a.action=='check':
        r=check(a.packet);print(r['case'],r['role'],r['native_strict'].get('unexpected'))
    else:
        r=pixels(a.attempt,a.out);print(r['case'],len(r['comparisons']),r['outside_pixels'],r['all_exact_identities'])
