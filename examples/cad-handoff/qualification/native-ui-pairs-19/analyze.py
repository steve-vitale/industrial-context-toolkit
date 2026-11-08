"""Recompute exposed UI comparisons from retained native observations, never launch CAD or waive differences."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(HERE.parent))
import cad_handoff as ch
from verify_bytes import verify
from PIL import Image,ImageChops

def read(p):return json.loads(p.read_bytes())
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def require(test,message):
    if not test:raise ValueError(message)
def image_pair(left,right,region,destination):
    with Image.open(left)as a,Image.open(right)as b:
        require(a.size==b.size,'Changed native canvas dimensions')
        diff=ImageChops.difference(a.convert('RGB'),b.convert('RGB'));diff.save(destination)
        total=outside=0
        for y in range(diff.height):
            for x in range(diff.width):
                if diff.getpixel((x,y))!=(0,0,0):
                    total+=1
                    if region is None or not(region[0]<=x<region[2]and region[1]<=y<region[3]):outside+=1
        return dict(changed_pixels=total,outside_region=outside,permitted_region=region,size=list(a.size))
def capture(job,label,frame):
    rows=[a for a in read(job/'ui/actions.json')if a['kind']=='capture'and a['label']==label and a['frame']==frame]
    require(len(rows)==1,'Missing/duplicate native capture')
    c=rows[0];require(len(c['images'])>=2 and c['images'][-1]['pixel_sha256']==c['images'][-2]['pixel_sha256'],'Unstable native image')
    image=job/'ui'/c['images'][-1]['path'];canvas=image.with_suffix('.canvas.png')
    with Image.open(image)as full,Image.open(canvas)as saved:
        x,y,w,h=c['canvas']['rectangle'];actual=full.crop((x,y,x+w,y+h))
        require(actual.tobytes()==saved.tobytes()and hashlib.sha256(actual.tobytes()).hexdigest()==c['images'][-1]['pixel_sha256'],'Native crop differs')
    return c,canvas
def pixels(job,destination):
    result=[];basis=read(job/'job.json')
    for frame in basis['frames']:
        captures={k:capture(job,k,frame)for k in ('source','baseline','edited','candidate')}
        original=captures['source'][0]
        for c,_ in captures.values():
            require(c['observation']['request']['frame']==basis['frames'][frame],'Native frame differs')
            require(c['observation']['view']==original['observation']['view']and c['canvas']['rectangle']==original['canvas']['rectangle'],'Native camera/canvas changed')
        boxes=[]
        for name in ('source','candidate'):
            attrs=captures[name][0]['observation']['attributes']
            ids=[a['parent_id']for a in attrs if a['tag']=='ICT_ID'and a['text']==basis['attributes']['ICT_ID']]
            require(len(ids)==1,'Missing/ambiguous projected identity')
            fields=[a for a in attrs if a['parent_id']==ids[0]and a['tag']=='MANUFACTURER']
            require(len(fields)==1 and len(fields[0]['projected'])==4,'Missing/ambiguous projected label')
            boxes.append(fields[0]['projected'])
        region=[math.floor(min(b[0]for b in boxes))-2,math.floor(min(b[1]for b in boxes))-2,
                math.ceil(max(b[2]for b in boxes))+2,math.ceil(max(b[3]for b in boxes))+2]
        for left,right,permitted in [('source','baseline',None),('source','candidate',region),('baseline','edited',region)]:
            name=frame+'-'+left+'-'+right
            row=image_pair(captures[left][1],captures[right][1],permitted,destination/(name+'.png'))
            result.append(dict(frame=frame,left=left,right=right,**row))
    return result
def analyze(cases,jobs,out):
    out.mkdir();results=[]
    for case in sorted(p for p in cases.iterdir()if p.is_dir()):
        source=case/'source.dxf';plan=read(case/'plan.json');before=ch.snapshot(source);row=dict(case=case.name,native={},whole_cad_qualified=False)
        require(ch.digest(source)==plan['source_sha256'],'Source changed')
        candidate=case/'software/candidate/candidate.dxf';row['candidate_byte_check']=verify(source,candidate,plan)
        row['candidate_strict']=ch.compare(before,ch.snapshot(candidate),plan)
        for role in ('baseline','edited','receiving'):
            job=jobs/(case.name+'-'+role)
            if not job.exists():row['native'][role]=dict(status='not-run');continue
            require((job/'source.dxf').read_bytes()==source.read_bytes(),'Staged source changed')
            item=dict(status='incomplete',input_freeze=read(job/'JOB-FREEZE.json'))
            if (job/'native/PROCESS.json').exists():item['process']=read(job/'native/PROCESS.json')
            if (job/'ui/FAILURE.json').exists():item.update(status='controller-failed',failure=read(job/'ui/FAILURE.json'))
            if (job/'ui/RESULT.json').exists():
                item['controller_result']=read(job/'ui/RESULT.json');p=item['process']
                item['status']='complete' if p.get('controller_exit')==0 and p.get('exit')==0 else 'awaiting-native-exit'
            returned=job/'returned.dxf'
            if returned.exists():
                after=ch.snapshot(returned);comparison=ch.compare(before,after,plan if role=='edited'else None)
                write(out/(case.name+'-'+role+'-strict.json'),comparison)
                item.update(returned_sha256=ch.digest(returned),strict_differences=len(comparison['unexpected']),strict_status=comparison['status'],stored_assets=after['assets'])
            row['native'][role]=item
        baseline=jobs/(case.name+'-baseline/returned.dxf');edited=jobs/(case.name+'-edited/returned.dxf')
        if baseline.exists()and edited.exists():
            pairplan=dict(plan,source_sha256=ch.digest(baseline));comparison=ch.compare(ch.snapshot(baseline),ch.snapshot(edited),pairplan)
            write(out/(case.name+'-paired-strict.json'),comparison);row['paired_strict_differences']=len(comparison['unexpected'])
        receiver=jobs/(case.name+'-receiving')
        if row['native']['receiving']['status']=='complete':
            folder=out/case.name;folder.mkdir();row['pixels']=pixels(receiver,folder)
        results.append(row)
    write(out/'summary.json',dict(scope='Exposed development; partial coverage stays explicit',whole_cad_qualified=False,results=results))
    return results
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('cases',type=Path);p.add_argument('jobs',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    for r in analyze(a.cases,a.jobs,a.out):print(r['case'],json.dumps({k:v['status']for k,v in r['native'].items()}))
