"""Select complete observed yellow-stroke cycles at the pinned GUI camera; no pixel masking."""
import json
from pathlib import Path
import sys

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def select(root,observation='observed-4'):
    view=read(root/'ordinary/receipts/106.json')['view'];f=view['factor'];ox,oy=view['offset']
    world=[f,0,0,0,-f,0,ox*f,view['height']-oy*f,1]
    rows=[json.loads(line)for line in(root/observation/'paint.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [r['serial']for r in rows]==list(range(1,len(rows)+1))
    live={};groups=[]
    for r in rows:
        k=r['painter']
        if r['kind']=='begin':
            assert k not in live,'Missing painter end'
            live[k]=[]
        elif r['kind']=='end':
            cycle=live.pop(k,[])
            selected=[v for v in cycle if v['kind']in('lines','path','stroke') and
                v['pen']['brush']['color']==[255,255,0,255] and v['world']==world]
            if selected:
                assert all(x['epoch']['role']==r['epoch']['role']for x in selected)
                groups.append(dict(role=r['epoch']['role'],end=r['serial'],rows=selected))
        elif k in live:live[k].append(r)
    return groups

def tokens(rows):
    out=[1533,1032,len(rows)]
    def brush(b):
        assert b['style']<=14,'Gradient/texture not supported by replay'
        return [b['style'],*b['color'],*b['transform']]
    for r in rows:
        assert r['device']==[1533,1032,3,1]
        assert r['world']==r['device_transform'],'Additional device transform'
        assert r['window']==r['viewport']==[0,0,1533,1032]
        p=r['pen']
        if r['kind']=='stroke':assert r['stroke_pen']==p,'Different explicit stroke pen needs separate support'
        out += [dict(lines=0,path=1,fill=2,stroke=3)[r['kind']],*r['world'],r['hints'],r['opacity'],r['composition'],
            p['width'],int(p['cosmetic']),p['style'],p['cap'],p['join'],p['miter'],p['dash_offset'],len(p['dashes']),*p['dashes'],
            *brush(p['brush']),*brush(r['brush']),r['background_mode'],*brush(r['background']),int(r['clipping']),len(r['clip']),r['clip_fill']]
        for e in r['clip']:out+=e
        if r['kind']=='lines':
            out.append(len(r['lines']))
            for line in r['lines']:out+=line
        else:
            out += [len(r['elements']),r['fill_rule']]
            for e in r['elements']:out+=e
            if r['kind']=='fill':out+=brush(r['fill_brush'])
    return out

def main(root,observation='observed-4',output='replay-4'):
    groups=select(root,observation);print([(g['role'],g['end'],len(g['rows']))for g in groups])
    out=root/output;out.mkdir(exist_ok=False)
    for i,g in enumerate(groups):
        name=f"{g['role']}-{g['end']}"
        (out/(name+'.txt')).write_text(' '.join(str(v)for v in tokens(g['rows']))+'\n',encoding='ascii')
        (out/(name+'.json')).write_text(json.dumps(g,indent=2)+'\n',encoding='utf-8')
    for role in ('source','candidate'):
        combined=[r for g in groups if g['role']==role for r in g['rows']]
        (out/(role+'-combined.txt')).write_text(' '.join(str(v)for v in tokens(combined))+'\n',encoding='ascii')
    (out/'groups.json').write_text(json.dumps([dict(role=g['role'],end=g['end'],calls=len(g['rows']))for g in groups],indent=2)+'\n',encoding='utf-8')
    assert {g['role']for g in groups}=={'source','candidate'}

if __name__=='__main__':main(Path(sys.argv[1]),*sys.argv[2:])
