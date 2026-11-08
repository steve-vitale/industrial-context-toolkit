"""Native Linux accessibility actions and X11 text entry; no QCAD document API."""
import argparse
import json
import os
from pathlib import Path
import subprocess

os.environ['DBUS_SESSION_BUS_ADDRESS']=Path('/work/dbus-address.txt').read_text().strip()
import pyatspi

def at(path):
    indices=path.split('.')
    if indices[0]!='0':raise ValueError('Expected desktop-root path')
    node=pyatspi.Registry.getDesktop(0)
    for index in indices[1:]:node=node.getChildAtIndex(int(index))
    return node

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=['press','focus','type'])
    p.add_argument('path');p.add_argument('text',nargs='?');args=p.parse_args();node=at(args.path);state=node.getState()
    if not(state.contains(pyatspi.STATE_ENABLED)and state.contains(pyatspi.STATE_SHOWING)):
        raise ValueError('Native control is not showing and enabled')
    row=dict(operation=args.operation,path=args.path,name=node.name,role=node.getRoleName(),commands=[])
    if args.operation=='press':
        action=node.queryAction()
        if action.nActions!=1:raise ValueError('Expected one observed native action')
        row['action']=action.getName(0);row['result']=action.doAction(0)
    else:
        row['focus_result']=node.queryComponent().grabFocus()
        if row['focus_result']is not True:raise ValueError('Native control focus refused')
        if args.operation=='type':
            if args.text is None or '\n'in args.text or '\r'in args.text or not args.text.isascii():
                raise ValueError('This development X11 text recipe supports one ASCII line only')
            if not state.contains(pyatspi.STATE_EDITABLE):raise ValueError('Native control is not editable')
            row['text']=args.text
            for command in [['xdotool','key','--clearmodifiers','ctrl+a'],
                            ['xdotool','type','--clearmodifiers','--delay','15','--',args.text],
                            ['xdotool','key','Tab']]:
                result=subprocess.run(command,capture_output=True,text=True)
                row['commands'].append(dict(command=command,exit=result.returncode,stdout=result.stdout,stderr=result.stderr))
                if result.returncode:raise ValueError('Native input failed')
    print(json.dumps(row,indent=2))
if __name__=='__main__':main()
