"""Observe the isolated native Linux accessibility tree; no CAD or UI writes."""
import json
import os
from pathlib import Path

os.environ['DBUS_SESSION_BUS_ADDRESS']=Path('/work/dbus-address.txt').read_text().strip()
import pyatspi

def inspect(node,path='0',depth=0):
    state=node.getState()
    row=dict(path=path,name=node.name,role=node.getRoleName(),children=[],
             enabled=state.contains(pyatspi.STATE_ENABLED),editable=state.contains(pyatspi.STATE_EDITABLE),
             showing=state.contains(pyatspi.STATE_SHOWING),focused=state.contains(pyatspi.STATE_FOCUSED))
    try:
        t=node.queryText();row['text']=t.getText(0,t.characterCount)
    except NotImplementedError:pass
    try:
        r=node.queryComponent().getExtents(pyatspi.DESKTOP_COORDS);row['rectangle']=[r.x,r.y,r.width,r.height]
    except NotImplementedError:pass
    try:
        a=node.queryAction();row['actions']=[a.getName(i)for i in range(a.nActions)]
    except NotImplementedError:pass
    if depth<20:
        for i in range(node.childCount):
            try:row['children'].append(inspect(node.getChildAtIndex(i),path+'.'+str(i),depth+1))
            except Exception as err:row['children'].append(dict(path=path+'.'+str(i),error=str(err)))
    elif node.childCount:row['depth_truncated']=node.childCount
    return row

if __name__=='__main__':
    print(json.dumps(inspect(pyatspi.Registry.getDesktop(0)),indent=2,ensure_ascii=False))
