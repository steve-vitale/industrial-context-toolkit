"""Actual native UI workflow. Controller failure leaves the same native process live for inspection."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

ROOT=Path('/work')
os.environ['DBUS_SESSION_BUS_ADDRESS']=(ROOT/'dbus-address.txt').read_text().strip()
import pyatspi
from PIL import Image
from inspect_ui import inspect
from ui_control import at

def write(path,value):path.write_text(json.dumps(value,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def require(test,message):
    if not test:raise ValueError(message)
def walk(node):
    yield node
    for child in node.get('children',[]):yield from walk(child)
def tree():return inspect(pyatspi.Registry.getDesktop(0))
def matching(t,role=None,name=None):
    return [n for n in walk(t) if n.get('showing') and (role is None or n.get('role')==role) and (name is None or n.get('name')==name)]
def one(t,role,name):
    rows=matching(t,role,name);require(len(rows)==1,'Ambiguous/missing native control: '+str((role,name,len(rows))));return rows[0]

class Workflow:
    def __init__(self):
        self.job=json.loads((ROOT/'job.json').read_bytes());self.seq=0;self.event=0;self.phase=0
        self.out=ROOT/'ui';self.out.mkdir();self.actions=[]
    def record(self,kind,**kw):
        self.event+=1;row=dict(event=self.event,at=time.time(),kind=kind,**kw);self.actions.append(row)
        write(self.out/'actions.json',self.actions)
    def snapshot(self,label):
        self.phase+=1;t=tree();write(self.out/(str(self.phase).zfill(3)+'-'+label+'.json'),t);return t
    def command(self,args):
        r=subprocess.run(args,capture_output=True,text=True);self.record('command',command=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr)
        require(r.returncode==0,'Native command failed');return r.stdout
    def keys(self,*keys):self.command(['xdotool','key','--clearmodifiers',*keys]);time.sleep(.35)
    def control(self,operation,node,text=None):
        require(node['enabled'] and node['showing'],'Control not enabled/showing')
        self.record('control',operation=operation,observed=node,text=text)
        args=['python3','/work/ui_control.py',operation,node['path']]
        if text is not None:args.append(text)
        self.command(args);time.sleep(.35)
    def wait(self,predicate,description,seconds=35):
        start=time.monotonic()
        while time.monotonic()-start<seconds:
            t=tree()
            if predicate(t):return t
            time.sleep(.4)
        self.snapshot('timeout');raise ValueError('Observation timeout, native not restarted: '+description)
    def observe(self,**kw):
        self.seq+=1;r=dict(seq=self.seq,action='status');r.update(kw);tmp=ROOT/'request.tmp';write(tmp,r);tmp.replace(ROOT/'request.json')
        target=ROOT/'replies'/(str(self.seq)+'.json');start=time.monotonic()
        while not target.exists() and time.monotonic()-start<20:time.sleep(.2)
        require(target.exists(),'Native observation timeout; keep same process')
        result=json.loads(target.read_bytes());self.record('native_observation',reply=result)
        require('error' not in result,'Native read-only observation failed: '+str(result.get('error')));return result
    def canvas(self):return one(tree(),'filler','Drawing View')
    def focus_canvas(self):self.control('focus',self.canvas())
    def dialog(self,title):
        t=self.wait(lambda t:len(matching(t,'dialog',title))==1,title)
        visible=[n['name'] for n in matching(t,'dialog')]
        require(visible==[title],'Unexpected native dialog(s): '+str(visible));return one(t,'dialog',title)
    def startup(self):
        t=self.wait(lambda t:bool(matching(t,'dialog','Trial')),'Trial',60)
        self.snapshot('trial')
        t=self.wait(lambda t:any(n['enabled'] for n in matching(one(t,'dialog','Trial'),'push button','OK')),'Trial OK enabled',40)
        self.control('press',one(one(t,'dialog','Trial'),'push button','OK'))
        self.wait(lambda t:not matching(t,'dialog'),'Trial dismissed');self.snapshot('ready')
        require(self.observe()['filename']=='','Unexpected startup document')
    def open_file(self,path):
        self.focus_canvas();self.keys('Escape','Escape','ctrl+o');dialog=self.dialog('Open Drawing')
        self.snapshot('open-dialog');combos=matching(dialog,'combo box')
        require(any(n.get('name')=='All Files (*)' for n in combos),'Unexpected Open filter')
        self.control('type',one(dialog,'text','File name:'),path)
        dialog=self.dialog('Open Drawing');self.control('press',one(dialog,'push button','Open'))
        self.wait(lambda t:not matching(t,'dialog'),'Open completed');self.snapshot('opened')
        require(self.observe()['filename']==path,'Wrong opened native filename')
    def select_and_verify(self,path,expected,original=False):
        observed=self.observe();require(observed['filename']==path,'Wrong drawing before selection')
        identity=self.job['attributes']['ICT_ID'];ids=[a for a in observed['attributes'] if a['tag']=='ICT_ID' and a['text']==identity]
        require(len(ids)==1,'Native identity is missing/ambiguous');handle=ids[0]['parent_handle']
        if original:require(handle==self.job['handle'],'Original handle changed; refuse selection')
        self.record('selection_binding',source_handle=self.job['handle'],observed_handle=handle,identity=identity)
        self.focus_canvas();self.keys('Escape','Escape','t','h');dialog=self.dialog('Selection by Handle')
        self.snapshot('handle-dialog');fields=matching(dialog,'text');require(len(fields)==1,'Ambiguous handle input')
        self.control('type',fields[0],handle);dialog=self.dialog('Selection by Handle')
        self.control('press',one(dialog,'push button','OK'));self.wait(lambda t:not matching(t,'dialog'),'Handle dialog dismissed')
        self.snapshot('selected');return self.fields(expected)
    def fields(self,expected):
        t=tree();found={}
        for n in walk(t):
            children=n.get('children',[])
            if n.get('role')=='panel' and children and children[0].get('name')=='Attributes' and children[0].get('role')=='label':
                for label,field in zip(children[1::2],children[2::2]):
                    require(label.get('role')=='label' and label['name'].endswith(':'),'Missing native attribute label')
                    tag=label['name'][:-1];require(tag not in found,'Duplicate native field');found[tag]=field
        require(set(found)==set(expected),'Native field set differs: '+str(list(found)))
        require(all(n.get('text')==expected[tag] and n['enabled'] and n['editable'] for tag,n in found.items()),'Native displayed values/editability differ')
        self.record('native_fields',expected=expected,observed=found);return found
    def capture(self,path,label):
        self.focus_canvas();self.keys('Escape','Escape','t','n')
        require(not self.observe()['selected'],'Native selection not cleared')
        for name,frame in self.job['frames'].items():
            obs=self.observe(action='frame',expected_path=path,frame=frame);canvas=self.canvas()
            self.command(['xdotool','mousemove','--sync','2300','1300']);time.sleep(.6)
            previous=None;images=[]
            for i in range(10):
                image=self.out/(label+'-'+name+'-'+str(i)+'.png');self.command(['scrot',str(image)])
                with Image.open(image) as full:
                    x,y,w,h=canvas['rectangle'];crop=full.crop((x,y,x+w,y+h));pixels=crop.tobytes();pixelsha=hashlib.sha256(pixels).hexdigest()
                    crop.save(image.with_suffix('.canvas.png'))
                images.append(dict(path=image.name,pixel_sha256=pixelsha))
                if pixelsha==previous:break
                previous=pixelsha;time.sleep(.5)
            else:raise ValueError('Native canvas did not stabilize')
            self.record('capture',label=label,frame=name,observation=obs,canvas=canvas,images=images)
    def save_as(self,path):
        require(not Path(path).exists(),'Output collision')
        self.focus_canvas();self.keys('Escape','Escape','ctrl+shift+s');dialog=self.dialog('Save As');self.snapshot('save-dialog')
        require(any(n.get('name')=='R27 [2013] DXF Drawing [OpenDesign] (*.dxf)' for n in matching(dialog,'combo box')),'Unexpected Save As format')
        self.control('type',one(dialog,'text','File name:'),path);dialog=self.dialog('Save As')
        self.control('press',one(dialog,'push button','Save'));self.wait(lambda t:not matching(t,'dialog'),'Save completed')
        self.snapshot('saved');obs=self.observe();require(obs['filename']==path and obs['modified'] is False and Path(path).is_file(),'Native save/readback failed')
        self.record('returned_file',path=path,sha256=sha(Path(path)))
    def close_doc(self):
        obs=self.observe();require(obs['modified'] is False,'Refuse close with uncommitted changes')
        self.focus_canvas();self.keys('Escape','Escape','ctrl+w');self.wait(lambda t:not matching(t,'dialog'),'Document closed')
        self.snapshot('closed');require(self.observe()['filename']=='','Closed document remains active')
    def finish(self):
        require(self.observe()['modified'] is False,'Refuse exit with modified document')
        windows=self.command(['wmctrl','-l']).splitlines();main=[r for r in windows if ' - QCAD Professional Trial' in r]
        require(len(main)==1,'Ambiguous main window for normal close');self.command(['wmctrl','-ic',main[0].split()[0]])
    def run(self):
        self.startup();expected=dict(self.job['attributes']);role=self.job['role']
        if role in ('baseline','edited'):
            path='/work/source.dxf';self.open_file(path);fields=self.select_and_verify(path,expected,True)
            self.capture(path,'source')
            if role=='edited':
                fields=self.select_and_verify(path,expected,True);self.control('type',fields['MANUFACTURER'],'QUAL-AFTER')
                expected['MANUFACTURER']='QUAL-AFTER';self.snapshot('edited');self.fields(expected)
            self.save_as('/work/returned.dxf');self.close_doc();self.open_file('/work/returned.dxf')
            self.select_and_verify('/work/returned.dxf',expected);self.capture('/work/returned.dxf','returned');self.close_doc()
        else:
            require(role=='receiving','Unknown job role')
            for name in ('source','baseline','edited','candidate'):
                path='/work/'+name+'.dxf';values=dict(expected)
                if name in ('edited','candidate'):values['MANUFACTURER']='QUAL-AFTER'
                self.open_file(path);self.select_and_verify(path,values,name in ('source','candidate'));self.capture(path,name);self.close_doc()
        self.finish();write(self.out/'RESULT.json',dict(status='controller-complete',role=role,case=self.job['case'],whole_cad_qualified=False))

if __name__=='__main__':
    workflow=Workflow()
    try:workflow.run()
    except Exception:
        write(workflow.out/'FAILURE.json',dict(traceback=traceback.format_exc(),scope='Controller failed; inspect same live native process, do not restart'))
        try:workflow.snapshot('failure')
        except Exception:pass
        raise
