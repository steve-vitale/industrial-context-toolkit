"""Compare isolated native raster predictions against the actual retained GUI difference, with no mask waiver."""
from collections import Counter
import json
import math
from pathlib import Path
import sys
from PIL import Image,ImageChops
import analyze as a

CROP=(114,175,1647,1207)
def image(path):
    with Image.open(path) as im:return im.convert('RGB')
def projected(box,view):
    x1,y1,x2,y2=box;ox,oy=view['offset'];f,h=view['factor'],view['height']
    return [(x1+ox)*f,h-(y2+oy)*f,(x2+ox)*f,h-(y1+oy)*f]
def changed(delta):
    bands=delta.split();mask=ImageChops.lighter(ImageChops.lighter(bands[0],bands[1]),bands[2]);return sum(mask.histogram()[1:])

def analyze(root):
    reference=root/'reference';receipt=a.read(reference/'106.json');spec=a.read(root/'pixels-2/PIXEL-INPUTS.json')
    left=image(reference/'106.png').crop(CROP);right=image(reference/'107.png').crop(CROP);actual=ImageChops.difference(left,right)
    a.require(spec['view']==receipt['view'],'Isolated / GUI camera differs')
    boxes=[];floats=[]
    for item in receipt['pair'].values():
        for asset in item['assets'].values():
            for attr in asset['attributes']:
                if attr['tag']=='MODEL':
                    v=projected(attr['bounds'],receipt['view']);floats.append(v)
                    boxes.append([math.floor(v[0]),math.floor(v[1]),math.ceil(v[2]),math.ceil(v[3])])
    bbox=actual.getbbox();points=[]
    for y in range(bbox[1],bbox[3]):
        for x in range(bbox[0],bbox[2]):
            if actual.getpixel((x,y))!=(0,0,0) and not any(l<=x<=r and t<=y<=b for l,t,r,b in boxes):points.append((x,y))
    results=[]
    for profile in spec['profiles']:
        source=image(root/'pixels-2/images'/('source-'+profile['id']+'.png'))
        candidate=image(root/'pixels-2/images'/('candidate-'+profile['id']+'.png'))
        a.require(source.size==candidate.size==left.size,'Raster dimensions differ')
        predicted=ImageChops.difference(source,candidate);error=ImageChops.difference(actual,predicted)
        results.append(dict(profile=profile['id'],**{k:v for k,v in profile.items()if k!='id'},
            whole_canvas_delta_mismatching_pixels=changed(error),
            outside_pixel_color_mismatches=sum(source.getpixel(p)!=left.getpixel(p) or candidate.getpixel(p)!=right.getpixel(p)for p in points),
            predicted_different_pixels=changed(predicted),predicted_delta_bbox=list(predicted.getbbox()) if predicted.getbbox() else None))
    return dict(original_different_pixels=changed(actual),original_delta_bbox=list(bbox),
        exact_geometric_rectangles=boxes,projected_float_rectangles=floats,
        original_outside_pixels=len(points),outside_pixel_rows={str(k):v for k,v in sorted(Counter(y for x,y in points).items())},
        outside_pixel_x_range=[min(x for x,y in points),max(x for x,y in points)],profiles=results,
        original_62_pixel_failure_retained=True,whole_cad_qualified=False)

if __name__=='__main__':
    result=analyze(Path(sys.argv[1]));a.write(Path(sys.argv[2]),result)
    for row in result['profiles']:print(row['profile'],row['whole_canvas_delta_mismatching_pixels'],row['outside_pixel_color_mismatches'])
