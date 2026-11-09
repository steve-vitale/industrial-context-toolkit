"""Recheck complete waiting receivers, exact model pixels and bound visual records offline."""
import json
from pathlib import Path
import tempfile
from PIL import Image
from evidence import unpack
from receive import HERE, read, require, digest, equal, receive
from compare_views import compare
from native_io import FOLDERS


def check_case(case,files=None):
    label=case+'-receiving-wait-1';packet=HERE/'waiting-development-1'/label
    if files is None: files=unpack(packet)
    identity=read(HERE/'WAITING-RETAINED-1.json')[label]
    for name,pin in identity['original_identity'].items():require(digest(files[name])==pin,'Original waiting attempt identity differs: '+name)
    require(json.loads(files['attempt/job/JOB-FREEZE.json'])==identity['freeze'],'Original waiting freeze differs')
    require(json.loads(files['methods/SELECTED-METHODS.json'])==read(HERE/'WAITING-METHODS-3.json'),'Selected native waiting method differs')
    require(digest(files['methods/receive.py'])==read(HERE/'WAITING-ANALYSIS-2.json')['files']['receive.py'],'Corrected offline receiving method differs')
    require(json.loads(files['execution/EXIT.json'])['exit']==json.loads(files['receiving/EXIT.json'])['exit']==0,'Actual waiting execution/receipt differs')
    if identity['failed_receiving_message']:
        require(json.loads(files['failed-receiving/EXIT.json'])['exit']==1 and
                identity['failed_receiving_message'].encode('ascii') in files['failed-receiving/stderr.txt'] and
                digest(files['failed-receiving/receive.py'])==read(HERE/'WAITING-ANALYSIS-1.json')['files']['receive.py'],'Original host-glob receiver refusal lost')
    else:require(not any(n.startswith('failed-receiving/') for n in files),'Unexpected failed receiver history')
    with tempfile.TemporaryDirectory(prefix='ict-waiting-recheck22-') as temporary:
        root=Path(temporary);attempt=root/'attempt'
        for name,value in files.items():
            if not name.startswith('attempt/'):continue
            path=root/name;require(path.resolve().is_relative_to(root.resolve()),'Unsafe waiting attempt path')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
        for folder in FOLDERS:
            (attempt/'mailbox'/folder).mkdir(parents=True,exist_ok=True)
            (attempt/'mailbox/staging'/folder).mkdir(parents=True,exist_ok=True)
        actual=receive(attempt,HERE/'PREPARATION-1.json',HERE/'WAITING-METHODS-3.json')
        require(equal(actual,json.loads(files['receiving/RESULT.json'])) and equal(actual,json.loads(files['receiving/stdout.txt'])) and
                equal(actual,read(packet/'RESULT.json')),'Complete waiting receipt differs')
        returns=root/'returns'
        for role in ('baseline','edited'):
            prior=unpack(HERE/'development-1'/(case+'-'+role+'-1'))
            value=prior['attempt/job/returned.dxf']
            require(files['attempt/job/'+role+'.dxf']==value,'Receiving file differs from original matched native return')
            path=returns/('validation-'+case+'-'+role)/'job/returned.dxf';path.parent.mkdir(parents=True);path.write_bytes(value)
        pixels=compare(attempt,returns,root/'pixels',HERE/'WAITING-METHODS-3.json')
        saved=HERE/'analysis/waiting-pixels-1'/case
        require(equal(pixels,read(saved/'RESULT.json')),'Full frozen pixel result differs')
        for row in pixels['comparisons']:
            with Image.open(root/'pixels'/row['difference_image']) as a,Image.open(saved/row['difference_image']) as z:
                require(a.mode==z.mode and a.size==z.size and a.tobytes()==z.tobytes(),'Retained difference-image pixels differ')
        visual=HERE/'analysis/waiting-visual-1'
        for row in read(visual/'OBSERVATIONS.json')['inspected_views']:
            if row['case']==case:require(digest(files['attempt/job/ui/'+row['file']])==row['sha256'],'Inspected view bytes differ')
        identities=[r for r in read(visual/'EQUIVALENT-VIEWS.json')['comparisons'] if r['case']==case]
        require(len(identities)==10,'Equivalent visual view coverage differs')
        for row in identities:
            for name,pin,pixel_pin in zip((row['left'],row['right']),row['files_sha256'],row['pixel_sha256']):
                path=attempt/'job/ui'/name
                require(digest(path.read_bytes())==pin,'Equivalent view file differs')
                with Image.open(path) as image:require(digest(image.tobytes())==pixel_pin,'Equivalent view pixel digest differs')
            require(row['pixels_identical'] and row['pixel_sha256'][0]==row['pixel_sha256'][1],'Visual equivalence changed')
    return dict(receipt={k:v for k,v in actual.items() if k!='native_strict'},pixel_comparisons=len(pixels['comparisons']),
                outside_pixels=sum(r['outside_permitted_regions'] for r in pixels['comparisons']),
                visual_scope='Bound same-agent model-view observations; paper and engineering review unfinished',whole_cad_qualified=False)


if __name__=='__main__':print(json.dumps({case:check_case(case) for case in ('cp1251','braces')},indent=2))
