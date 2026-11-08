"""Apply the predeclared exact model-frame and per-attribute mask recipe; retain every changed pixel."""
import argparse
import json
import math
from pathlib import Path
from PIL import Image, ImageChops
from receive import HERE, read, require, equal, receive, sha
from contract import group_native


def permitted_regions(source,candidate,changes):
    regions = []
    for change in changes:
        boxes = []
        for observation in (source,candidate):
            group = group_native(observation)[change['id']]
            fields = [r for r in observation['attributes'] if r['parent_id'] == group['parent_id'] and r['tag'] == change['attribute']]
            require(len(fields) == 1 and len(fields[0]['projected']) == 4 and all(math.isfinite(x) for x in fields[0]['projected']), 'Missing/nonfinite planned label projection')
            boxes.append(fields[0]['projected'])
        regions.append(dict(id=change['id'],attribute=change['attribute'],rectangle=[math.floor(min(b[0] for b in boxes))-2,math.floor(min(b[1] for b in boxes))-2,math.ceil(max(b[2] for b in boxes))+2,math.ceil(max(b[3] for b in boxes))+2]))
    return regions


def pixel_counts(left,right,regions,destination):
    require(left.size == right.size and left.mode == right.mode == 'RGB', 'Pixel comparison dimensions/mode differ')
    diff = ImageChops.difference(left,right); changed = outside = 0
    for y in range(diff.height):
        for x in range(diff.width):
            if diff.getpixel((x,y)) == (0,0,0): continue
            changed += 1
            if not any(r['rectangle'][0] <= x < r['rectangle'][2] and r['rectangle'][1] <= y < r['rectangle'][3] for r in regions): outside += 1
    if destination is not None: diff.save(destination)
    return dict(changed_pixels=changed,outside_permitted_regions=outside,permitted_regions=regions,pixel_status='pass' if outside == 0 else 'failed',size=list(left.size))


def compare(packet,returns,out):
    require(not out.exists(), 'New pixel comparison destination required')
    receipt = receive(packet,HERE/'PREPARATION-1.json',HERE/'METHODS-1.json')
    require(receipt['role'] == 'receiving', 'Fresh receiving role required')
    job = packet/'job'; basis = read(job/'job.json'); case = basis['case']
    for role in ('baseline','edited'):
        require((job/(role+'.dxf')).read_bytes() == (returns/(case+'-'+role)/'job/returned.dxf').read_bytes(), 'Fresh receiver return differs from matched retained native file')
    actions = read(job/'ui/actions.json'); captures = [r for r in actions if r['kind'] == 'capture']; out.mkdir(parents=True); rows = []
    for frame in basis['frames']:
        selected = {r['label']:r for r in captures if r['frame'] == frame}; original = selected['source']
        for capture in selected.values():
            require(equal(capture['observation']['view'],original['observation']['view']) and capture['canvas']['rectangle'] == original['canvas']['rectangle'], 'Exact camera/canvas gate failed; no registered/tolerant pixel comparison')
        regions = permitted_regions(selected['source']['observation'],selected['candidate']['observation'],basis['changes'])
        for left,right,permitted in [('source','baseline',[]),('source','candidate',regions),('baseline','edited',regions)]:
            paths = [job/'ui'/Path(selected[label]['images'][-1]['path']).with_suffix('.canvas.png') for label in (left,right)]
            name = frame+'-'+left+'-'+right+'.png'
            with Image.open(paths[0]) as a,Image.open(paths[1]) as b: result = pixel_counts(a,b,permitted,out/name)
            rows.append(dict(frame=frame,left=left,right=right,difference_image=name,**result))
    result = dict(case=case,method='Frozen METHOD.md exact cameras and separate source/candidate planned-label regions; no registration/tolerance',
                  sources={name:sha(job/(name+'.dxf')) for name in ('source','baseline','edited','candidate')},comparisons=rows,
                  agent_visual_review='separate unfinished gate',paper_view='unfinished',whole_cad_qualified=False)
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('packet',type=Path); parser.add_argument('returns',type=Path); parser.add_argument('--out',type=Path,required=True);args = parser.parse_args()
    result = compare(args.packet,args.returns,args.out); print(json.dumps(dict(case=result['case'],comparisons=len(result['comparisons']),outside_pixels=sum(r['outside_permitted_regions'] for r in result['comparisons']),whole_cad_qualified=False)))
