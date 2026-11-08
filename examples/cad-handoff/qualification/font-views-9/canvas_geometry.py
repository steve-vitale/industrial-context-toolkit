"""Read native accessible component bounds to locate the actual canvas; no UI input."""
import json
import os
from pathlib import Path
os.environ['DBUS_SESSION_BUS_ADDRESS']=Path('/work/dbus-address.txt').read_text().strip()
import pyatspi
rows=[]
def walk(node,path='0'):
    try:
        box=node.queryComponent().getExtents(pyatspi.DESKTOP_COORDS)
        if box.width>1000 and box.height>600:
            rows.append(dict(path=path,role=node.getRoleName(),name=node.name,
                             rectangle=[box.x,box.y,box.width,box.height]))
    except Exception:pass
    for i in range(node.childCount):
        try:walk(node.getChildAtIndex(i),path+'.'+str(i))
        except Exception:pass
walk(pyatspi.Registry.getDesktop(0))
Path('/work/canvas-geometry.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
