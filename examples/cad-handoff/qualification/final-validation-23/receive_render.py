"""Check completed reserved native render provenance and whole-image differences offline."""
import argparse
import hashlib
import sys
from pathlib import Path
from PIL import Image, ImageChops
from campaign import HERE, read, write, sha, binding, require
sys.path.insert(0,str(HERE.parent/'public-validation-11'))
from window import xywh


def changed_pixels(a,b):
    require(a.size==b.size,'Matched render dimensions differ')
    # Compare decoded colors, not palette indices or a difference image's palette.
    channels=ImageChops.difference(a.convert('RGBA'),b.convert('RGBA')).split()
    maximum=channels[0]
    for channel in channels[1:]:maximum=ImageChops.lighter(maximum,channel)
    return a.width*a.height-maximum.histogram()[0]


def receive(folder,host):
    frozen=binding();preparation=read(HERE/'NATIVE-PREPARATION.json')
    require(sha(HERE/'NATIVE-PREPARATION.json')==read(HERE/'NATIVE-LAUNCH.json')['native_preparation_sha256'],'Render launch preparation differs')
    require(sha(host/'SCRIPT.py')==read(HERE/'NATIVE-LAUNCH.json')['host_wrappers']['run_final_api_host.py'],'Original render host wrapper differs')
    for name,pin in preparation['files'].items():
        if name.startswith('render/'):require(sha(folder/name[7:])==pin,'Prepared render input differs: '+name)
    terminal=read(host/'AFTER.json')[0]
    require(read(host/'EXIT.json')['exit']==0 and terminal['State']['Status']=='exited' and terminal['State']['ExitCode']==0 and terminal['Image']==frozen['native_image'] and terminal['HostConfig']['NetworkMode']=='none','Original native render did not finish normally')
    jobs=read(folder/'MANIFEST.json')['jobs'];commands=read(folder/'native/commands.json');rows=[]
    require(len(jobs)==30 and [r['id'] for r in jobs]==[r['id'] for r in commands],'Complete render coverage differs')
    for job,record in zip(jobs,commands):
        command=record['command'];image=folder/'native'/(job['id']+'.png')
        require(record['exit']==0 and record['configuration_sha256_before']==frozen['configuration_sha256'] and sha(image)==record['image_sha256'],'Native render record differs')
        expected=['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances','-config','/home/cad/.config/QCAD/QCAD3.conf',
            '-font-substitution','Standard','DejaVu Sans','-autostart','scripts/Pro/Tools/Dwg2Bmp/Dwg2Bmp.js',
            '-o','/work/native/'+job['id']+'.png','-x','2400','-y','1600',
            '-window='+','.join(str(v) for v in xywh(job['window'])),
            *(['-block='+job['layout']] if job['layout']!='Model' else []),'-b','white','-n','/work/'+job['path']]
        require(command==expected,'Exact original render command/source/frame/layout differs')
        require('absConfigFile: "/home/cad/.config/QCAD/QCAD3.conf"' in (folder/'native'/(job['id']+'.stderr')).read_text(encoding='utf-8'),'Native render configuration not evidenced')
        with Image.open(image) as im:
            require(im.size==(2400,1600),'Native render dimensions differ')
            rows.append(dict(id=job['id'],sha256=sha(image),mode=im.mode,size=list(im.size),pixel_sha256=hashlib.sha256(im.tobytes()).hexdigest()))
    require(read(folder/'native/BEFORE.json')==read(folder/'native/AFTER.json')=={j['path']:j['sha256'] for j in jobs},'Render source changed')
    require(read(folder/'native/COMPLETE.json')['images']==30,'Render complete record differs')
    pairs=[]
    for n in range(0,len(jobs),2):
        left,right=jobs[n:n+2]
        require(left['id'].endswith('source') and right['id'].endswith('candidate') and left['window']==right['window'] and left['layout']==right['layout'],'Matched render pair differs')
        with Image.open(folder/'native'/(left['id']+'.png')) as a,Image.open(folder/'native'/(right['id']+'.png')) as b:
            require(a.mode==b.mode and a.size==b.size,'Matched render dimensions differ')
            changed=changed_pixels(a,b)
        pairs.append(dict(source=left['id'],candidate=right['id'],layout=left['layout'],changed_pixels=changed))
    return dict(images=rows,pairs=pairs,inputs_unchanged=True,whole_cad_qualified=False,visual_inspection='Separate image-bound observations; a successful exporter is not readable delivery')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('folder','host','out'):p.add_argument(name,type=Path)
    a=p.parse_args();require(not a.out.exists(),'New render receipt required');write(a.out,receive(a.folder,a.host))
