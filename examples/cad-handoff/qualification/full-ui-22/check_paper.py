"""Replay exact exposed paper commands, sources and full-image comparisons offline."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

from native_revisions import HERE, ROOT, read, write, sha, lf, require
from prepare_paper import prepare
from PIL import Image, ImageChops

spec=importlib.util.spec_from_file_location('paper_window', HERE.parent/'public-validation-11/window.py')
window=importlib.util.module_from_spec(spec)
spec.loader.exec_module(window)


def compare(left, right):
    with Image.open(left) as a, Image.open(right) as b:
        require(a.mode==b.mode and a.size==b.size, 'Paper pixel formats differ')
        difference=ImageChops.difference(a.convert('RGB'), b.convert('RGB'))
        return sum(pixel!=(0,0,0) for pixel in difference.getdata())


def check(folder):
    launch=read(HERE/'PAPER-RENDER-LAUNCH-1.json')
    manifest=read(folder/'MANIFEST.json')
    require(sha(folder/'MANIFEST.json')==launch['manifest_sha256'], 'Paper manifest differs from pre-execution pin')
    require(manifest['image']==launch['image'] and manifest['configuration_sha256']==launch['configuration_sha256'], 'Paper launch scope differs')
    for name,pin in manifest['methods_sha256_lf'].items():
        require(lf(ROOT/name)==pin, 'Declared paper method differs: '+name)
    for name,pin in [('render_paper.py',launch['driver_sha256']),('window.py',launch['window_sha256'])]:
        require(sha(folder/name)==pin, 'Actual native driver differs')
    with tempfile.TemporaryDirectory(prefix='ict-paper-input-replay-') as temporary:
        regenerated=prepare(Path(temporary)/'inputs')
        require(regenerated==manifest, 'Paper source/archive provenance or frames do not reproduce')
        for row in manifest['jobs']:
            require((Path(temporary)/'inputs'/row['path']).read_bytes()==(folder/row['path']).read_bytes(), 'Retained paper input differs')
    before={j['path']:j['sha256'] for j in manifest['jobs']}
    require(read(folder/'native/BEFORE.json')==before==read(folder/'native/AFTER.json'), 'Paper input changed across native execution')
    require(read(folder/'host/EXIT.json')['exit']==0, 'Original paper host failed')
    require(sha(folder/'host/SCRIPT.py')==launch['host_wrapper_sha256'], 'Original paper host wrapper differs')
    inspection=read(folder/'host/AFTER.json')
    require(len(inspection)==1, 'Ambiguous paper terminal container')
    container=inspection[0]
    require(container['State']['Status']=='exited' and container['State']['ExitCode']==0 and
            container['Image']==launch['image'] and container['HostConfig']['NetworkMode']=='none' and
            container['Config']['User']=='1001:1001', 'Paper native container did not terminate normally in declared environment')
    commands=read(folder/'native/commands.json')
    require([r['id'] for r in commands]==[j['id'] for j in manifest['jobs']], 'Paper native commands omitted/reordered')
    config='/home/cad/.config/QCAD/QCAD3.conf'
    images=[]
    for job,row in zip(manifest['jobs'],commands):
        command=['/opt/qcad/qcad','-platform','offscreen','-no-gui','-allow-multiple-instances','-config',config,
            '-font-substitution','Standard','DejaVu Sans','-autostart','scripts/Pro/Tools/Dwg2Bmp/Dwg2Bmp.js',
            '-o','/work/native/'+job['id']+'.png','-x','2400','-y','1600',
            '-window='+','.join(str(v) for v in window.xywh(job['window'])),
            '-block='+job['layout'],'-b','white','-n','/work/'+job['path']]
        require(row['command']==command and row['exit']==0 and row['started'] and row['finished'] and
                row['configuration_sha256_before']==manifest['configuration_sha256'], 'Paper command/window/profile/terminal differs')
        require(('absConfigFile: "'+config+'"').encode() in (folder/'native'/(job['id']+'.stderr')).read_bytes(), 'Selected native paper profile not evidenced')
        path=folder/'native'/(job['id']+'.png')
        require(sha(path)==row['image_sha256'], 'Paper native image changed')
        with Image.open(path) as image:
            require(image.size==(2400,1600), 'Paper image dimensions differ')
            images.append(dict(id=job['id'],sha256=sha(path),pixel_sha256=hashlib.sha256(image.tobytes()).hexdigest(),size=list(image.size),mode=image.mode))
    completion=read(folder/'native/COMPLETE.json')
    require(completion['images']==14 and completion['input_unchanged'] is True and completion['whole_cad_qualified'] is False, 'Paper completion scope differs')
    pairs=[]
    for case in ('cp1251','braces'):
        for left,right in [('original','original_value_candidate'),('noedit_native','concurrent_native'),
                           ('concurrent_native','selected_second_candidate'),('concurrent_native','second_native'),
                           ('original','noedit_native')]:
            pairs.append(dict(case=case,left=left,right=right,different_pixels=compare(folder/'native'/(case+'-'+left+'.png'),folder/'native'/(case+'-'+right+'.png'))))
    controls=compare(folder/'native/public-control-1.png',folder/'native/public-control-2.png')
    require(controls==0, 'Positive paper control is not repeatable')
    return dict(scope='Complete offline source/provenance/command replay and full-image pixel comparison; no CAD/model calls',
        images=images,pairs=pairs,control_repeat_different_pixels=controls,
        control_vs_original_different_pixels=compare(folder/'native/public-control-1.png',folder/'native/cp1251-original.png'),
        whole_cad_qualified=False,readable_paper_acceptance='Requires actual image observations; blank equality never establishes readable delivery')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--expect',type=Path)
    args=parser.parse_args()
    result=check(args.folder)
    if args.out:
        require(not args.out.exists(), 'Fresh paper result required')
        write(args.out,result)
    if args.expect:
        require(result==read(args.expect), 'Complete paper replay result differs')
    print(json.dumps(dict(images=len(result['images']),pairs=len(result['pairs']),control_repeat_different_pixels=result['control_repeat_different_pixels'],whole_cad_qualified=False)))
