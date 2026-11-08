"""Fresh UI receiving with separately retained old and absolute camera controls; no CAD edit/save."""
import copy
import hashlib
from pathlib import Path
import time
import traceback

from original_workflow import Workflow,write,require,ROOT
from PIL import Image

class CameraRepeat(Workflow):
    def record(self,kind,**kw):
        # Preserve the event's values at observation time; do not rewrite earlier expectations later.
        super().record(kind,**copy.deepcopy(kw))
    def capture(self,path,label):
        self.focus_canvas();self.keys('Escape','Escape','t','n');require(not self.observe()['selected'],'Selection not cleared')
        for mode in ('zoom-to','absolute'):
            for name,frame in self.job['frames'].items():
                observation=self.observe(action='frame',frame_mode=mode,expected_path=path,frame=frame);canvas=self.canvas()
                if mode=='absolute':
                    requested=observation['camera_control'];actual=observation['view']
                    require(actual['factor']==requested['factor']and actual['offset']==requested['offset'],'Absolute native camera differs from request')
                self.command(['xdotool','mousemove','--sync','2300','1300']);time.sleep(.6)
                previous=None;images=[]
                for i in range(10):
                    image=self.out/(label+'-'+mode+'-'+name+'-'+str(i)+'.png');self.command(['scrot',str(image)])
                    with Image.open(image)as full:
                        x,y,w,h=canvas['rectangle'];crop=full.crop((x,y,x+w,y+h));pixelsha=hashlib.sha256(crop.tobytes()).hexdigest();crop.save(image.with_suffix('.canvas.png'))
                    images.append(dict(path=image.name,pixel_sha256=pixelsha))
                    if pixelsha==previous:break
                    previous=pixelsha;time.sleep(.5)
                else:raise ValueError('Camera repeat canvas did not stabilize')
                self.record('capture',label=label,frame=name,mode=mode,observation=observation,canvas=canvas,images=images)

if __name__=='__main__':
    w=CameraRepeat()
    try:
        require(w.job['role']=='receiving','Camera control cannot edit/save drawings');w.run()
    except Exception:
        write(w.out/'FAILURE.json',dict(traceback=traceback.format_exc(),scope='Camera control failed; keep same native process'))
        try:w.snapshot('failure')
        except Exception:pass
        raise
