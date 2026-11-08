"""Pure selection of observed native controls; no UI or CAD actions."""
import re

def walk(node):
    yield node
    for child in node.get('children',[]):yield from walk(child)

def active_canvas(tree,filename):
    basename=filename.rsplit('/',1)[-1]
    frames=[n for n in walk(tree) if n.get('role')=='frame' and n.get('showing') and
            (n.get('name','').strip()==basename if filename else re.fullmatch(r'Untitled [0-9]+',n.get('name','').strip()))]
    if len(frames)!=1:raise ValueError('Ambiguous/missing active native document frame')
    canvases=[n for n in walk(frames[0]) if n.get('role')=='filler' and n.get('name')=='Drawing View' and n.get('showing')]
    if len(canvases)!=1:raise ValueError('Ambiguous/missing active native drawing canvas')
    return frames[0],canvases[0]
