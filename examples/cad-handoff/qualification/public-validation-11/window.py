"""Convert canonical native min/max bounds to QCAD Dwg2Bmp X,Y,width,height."""
import math


def xywh(bounds):
    if len(bounds)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in bounds):
        raise ValueError('Four finite numeric bounds required')
    x,y,right,top=bounds
    if right<=x or top<=y:raise ValueError('Bounds must have positive width and height')
    return [x,y,right-x,top-y]
