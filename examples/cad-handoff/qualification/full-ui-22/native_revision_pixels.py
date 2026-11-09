"""Apply the existing exact camera and per-attribute regions to native concurrent receiving."""
import argparse
import json
from pathlib import Path
from PIL import Image
from native_revisions import HERE, ROOT, read, write, sha, lf, require, receiving
from receive import equal
from compare_views import permitted_regions, pixel_counts


def compare(packet,out):
    require(not out.exists(),'Use a new pixel result folder')
    freeze=read(HERE/'NATIVE-REVISION-PIXELS-1.json')
    for name,pin in freeze['files_sha256_lf'].items():
        require(lf(ROOT/name)==pin,'Frozen revision pixel method changed: '+name)
    receipt=receiving(packet,HERE/'NATIVE-REVISION-PREPARATION-1.json',HERE/'NATIVE-REVISION-METHODS-1.json')
    require(receipt['role']=='receiving','Fresh receiving packet required')
    job=packet/'job';basis=read(job/'job.json');case=basis['case'];short=case.removeprefix('validation-')
    edited_index=read(HERE/'concurrent-development-1'/(short+'-concurrent-edited-1')/'INVENTORY.json')
    require(sha(job/'edited.dxf')==edited_index['files']['attempt/job/returned.dxf']['sha256'],'Receiving edited file differs from complete native return packet')
    actions=read(job/'ui/actions.json');captures=[r for r in actions if r['kind']=='capture']
    out.mkdir(parents=True);rows=[];identities=[]
    for frame in basis['frames']:
        selected={r['label']:r for r in captures if r['frame']==frame};original=selected['source']
        for capture in selected.values():
            require(equal(capture['observation']['view'],original['observation']['view']) and capture['canvas']['rectangle']==original['canvas']['rectangle'],'Exact camera/canvas differs; no registration/tolerance')
        regions=permitted_regions(selected['source']['observation'],selected['candidate']['observation'],basis['changes'])
        def image_path(label):
            return job/'ui'/Path(selected[label]['images'][-1]['path']).with_suffix('.canvas.png')
        for left,right,permitted in [('source','baseline',[]),('source','candidate',regions),('baseline','edited',regions)]:
            name=frame+'-'+left+'-'+right+'.png'
            with Image.open(image_path(left)) as a,Image.open(image_path(right)) as b:
                result=pixel_counts(a,b,permitted,out/name)
            rows.append(dict(frame=frame,left=left,right=right,difference_image=name,**result))
        for left,right in [('source','baseline'),('candidate','edited')]:
            with Image.open(image_path(left)) as a,Image.open(image_path(right)) as b:
                exact=a.mode==b.mode and a.size==b.size and a.tobytes()==b.tobytes()
            identities.append(dict(frame=frame,left=left,right=right,identical_pixels=exact,
                left_sha256=sha(image_path(left)),right_sha256=sha(image_path(right))))
    result=dict(case=case,method='Original exact frame/per-attribute regions; no changed tolerance or registration',
        sources={n:sha(job/(n+'.dxf')) for n in ('source','baseline','edited','candidate')},
        pixel_method_sha256_lf=lf(HERE/'NATIVE-REVISION-PIXELS-1.json'),comparisons=rows,exact_identities=identities,
        outside_pixels=sum(r['outside_permitted_regions'] for r in rows),
        all_exact_identities=all(r['identical_pixels'] for r in identities),agent_visual_review='not established by this code',
        paper_view='unfinished',whole_cad_qualified=False)
    write(out/'RESULT.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('packet',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();result=compare(args.packet,args.out)
    print(json.dumps(dict(case=result['case'],comparisons=len(result['comparisons']),outside_pixels=result['outside_pixels'],exact_identities=result['all_exact_identities'])))
    raise SystemExit(int(result['outside_pixels']!=0 or not result['all_exact_identities']))
