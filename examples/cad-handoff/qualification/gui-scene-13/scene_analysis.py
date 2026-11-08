"""Re-score actual GUI equivalence and retained primitive replays, without native software/network."""
import hashlib
import json
import math
import copy
from pathlib import Path
from PIL import Image,ImageChops
import replay_input
import compare_states

CROP=(114,175,1647,1207)
def require(ok,message):
    if not ok:raise ValueError(message)
def read(path):return json.loads(path.read_bytes())
def sha(data):return hashlib.sha256(data).hexdigest()
def image(path):
    with Image.open(path)as im:return im.convert('RGB')
def changed(im):
    r,g,b=im.split();return sum(ImageChops.lighter(ImageChops.lighter(r,g),b).histogram()[1:])
def pair(root,folder,names,crop=False):
    result=[image(root/folder/n)for n in names]
    return [v.crop(CROP)for v in result]if crop else result
def delta(pair):return ImageChops.difference(*pair)
def canonical_pair(pair):
    result=copy.deepcopy(pair)
    for item in result.values():
        for asset in item['assets'].values():
            attrs=asset['attributes'];require(len(attrs)==len({a['tag']for a in attrs}),'Duplicate native attribute tag')
            attrs.sort(key=lambda a:a['tag'])
    return result
def reassemble(root):
    for index in root.rglob('*-index.json'):
        m=read(index)
        require(0<m['bytes']<=64*1024*1024 and len(m['parts'])<=128,'Unbounded trace index')
        parts=m['parts'];require(len(set(parts))==len(parts),'Duplicated trace part')
        paths=[root/p for p in parts]
        require(all(p.resolve().is_relative_to(root.resolve()) and p.is_file()for p in paths),'Unsafe/missing trace part')
        data=b''.join(p.read_bytes()for p in paths)
        require(len(data)==m['bytes'] and sha(data)==m['sha256'],'Trace reconstruction differs')
        (index.parent/(index.name.removesuffix('-index.json')+'.jsonl')).write_bytes(data)
def outside_points(actual,receipt):
    view=receipt['view'];f=view['factor'];ox,oy=view['offset'];rects=[]
    for item in receipt['pair'].values():
        for asset in item['assets'].values():
            for a in asset['attributes']:
                if a['tag']!='MODEL':continue
                x1,y1,x2,y2=a['bounds'];v=[(x1+ox)*f,view['height']-(y2+oy)*f,(x2+ox)*f,view['height']-(y1+oy)*f]
                rects.append([math.floor(v[0]),math.floor(v[1]),math.ceil(v[2]),math.ceil(v[3])])
    require(len(rects)==2,'MODEL bounds omitted')
    d=delta(actual);bbox=d.getbbox();points=[]
    for y in range(bbox[1],bbox[3]):
        for x in range(bbox[0],bbox[2]):
            if d.getpixel((x,y))!=(0,0,0)and not any(l<=x<=r and t<=y<=b for l,t,r,b in rects):points.append((x,y))
    return points,rects
def compare_pixels(actual,predicted):
    require(all(v.size==(1533,1032)for v in [*actual,*predicted]),'Wrong canvas dimensions')
    return changed(ImageChops.difference(delta(actual),delta(predicted)))
def analyze(root):
    old=pair(root,'reference',['106.png','107.png'],True)
    ordinary=pair(root,'ordinary/views',['106.png','107.png'],True)
    require(all(ImageChops.difference(a,b).getbbox()is None for a,b in zip(old,ordinary)),'Ordinary canvas does not reproduce historical GUI')
    equivalence={}
    for folder in ('observed-3','observed-4'):
        observed=pair(root,folder+'/views',['106.png','107.png'],True)
        values=[changed(ImageChops.difference(a,b))for a,b in zip(ordinary,observed)]
        require(values==[0,0],'Observer changed the GUI canvas');equivalence[folder]=values
    require(read(root/'ordinary/receipts/106.json')['view']==read(root/'reference/106.json')['view'],'Camera differs')
    for folder in ('ordinary','observed-3','observed-4'):
        for seq in (106,107):
            receipt=read(root/folder/'receipts'/f'{seq}.json')
            require(receipt['view']==read(root/'reference'/f'{seq}.json')['view'],'Observed camera differs')
            require(canonical_pair(receipt['pair'])==canonical_pair(read(root/'reference'/f'{seq}.json')['pair']),'Native bounds/fields differ')
    points,rects=outside_points(old,read(root/'reference/106.json'))
    require(len(points)==62 and {p[1]for p in points}=={537},'Original 62-pixel failure changed')
    require(changed(delta(old))==1978 and list(delta(old).getbbox())==[409,537,959,545],'Original GUI delta changed')
    groups=replay_input.select(root)
    require([sum(len(g['rows'])for g in groups if g['role']==role)for role in ('source','candidate')]==[1193,4909],'Incomplete GUI primitive coverage')
    require(not compare_states.compare(root),'Replay changed recorded state or primitive')
    full=pair(root,'replay-4',['source.png','candidate.png'])
    error=compare_pixels(old,full);require(error==0,'Full native replay does not match every GUI delta pixel')
    color_error=sum(a.getpixel(p)!=b.getpixel(p)for a,b in zip(old,full)for p in points)
    require(color_error==0,'Full replay changed outside-pixel colors')
    ablations={}
    for kind in ('lines','stroke'):
        predicted=pair(root,'replay-4',[f'source-{kind}.png',f'candidate-{kind}.png'])
        ablations[kind]=dict(changed_pixels=changed(delta(predicted)),delta_mismatches=compare_pixels(old,predicted),
            outside_changed_pixels=sum(predicted[0].getpixel(p)!=predicted[1].getpixel(p)for p in points),
            outside_color_mismatches=sum(a.getpixel(p)!=b.getpixel(p)for a,b in zip(old,predicted)for p in points))
        for role in ('source','candidate'):
            rows=[r for g in groups if g['role']==role for r in g['rows']if r['kind']==kind]
            require((root/'replay-4'/f'{role}-{kind}.txt').read_text().split()==[str(v)for v in replay_input.tokens(rows)],'Ablation stream differs from recorded primitives')
    require(ablations['lines']['outside_changed_pixels']==0 and ablations['lines']['outside_color_mismatches']==62,'Removing curves did not remove original 62')
    require(ablations['stroke']['outside_color_mismatches']==0,'Curve-only did not reproduce outside colors')
    for role in ('source','candidate'):
        rows=[r for g in groups if g['role']==role for r in g['rows']]
        require((root/'replay-4'/f'{role}-combined.txt').read_text().split()==[str(v)for v in replay_input.tokens(rows)],'Complete replay stream differs')
    for original,fixed in [('control','control'),('control4','control4')]:
        require(ImageChops.difference(image(root/'build'/f'{original}-ordinary.png'),image(root/'build'/f'{original}-observed.png')).getbbox()is None,'Known painter control changed')
    incomplete=pair(root,'replay',['source-fixed.png','candidate-fixed.png'])
    require(compare_pixels(old,incomplete)==857 and not compare_states.compare(root,'observed-3','replay'),'Incomplete trace failure not retained')
    return dict(exposure='Existing long-label source/candidate: exposed development',original_gui_delta_pixels=1978,
        original_outside_geometric_bounds_pixels=62,original_geometric_rectangles=rects,
        observer_canvas_differences=equivalence,complete_yellow_calls=dict(source=1193,candidate=4909),
        replay_state_or_primitive_discrepancies=0,whole_canvas_delta_mismatches=error,outside_color_mismatches=color_error,
        ablations=ablations,incomplete_trace_delta_mismatches=857,
        cause='Separate native cubic strokePath calls paint the changed B glyph ink beyond its geometric bounds; joined-path and line-only replays are different/incomplete rendering methods.',
        original_failure_retained=True,strict_comparator_changed=False,whole_cad_qualified=False,
        remaining=['Native full-save strict differences and unresolved record payloads','Complete readable receiving; fresh native UI/editability and revision qualification','Engineering/company acceptance'])
