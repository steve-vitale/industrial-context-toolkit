"""Recheck complete read-only native camera evidence; never execute CAD or waive save losses."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import check_ui19 as ui
from ui19_archive import read,sha,require,equal,unpack
from PIL import Image

BASE=HERE/'camera-repeat-20'
LABELS=('source','baseline','edited','candidate')
MODES=('zoom-to','absolute')
CASES=('libre-air-water','libre-motion','libre-power','qcad-hydraulic','qcad-mechanical','qcad-template')

def drawing_pins(case):
    inv=read(HERE/'native-ui-pairs-19/evidence'/case/'INVENTORY.json')['files']
    prefix='raw/cases/'+case+'/'
    return {label:inv[prefix+('source.dxf'if label=='source'else'software/candidate/candidate.dxf')]['sha256']
            if label in ('source','candidate')else inv['raw/jobs/'+case+'-'+label+'/returned.dxf']['sha256']for label in LABELS}

def absolute_request(observation,frame):
    c=observation['camera_control'];v=observation['view']
    require(type(c['high_resolution'])is bool,'Unknown native high-resolution setting')
    W,H=v['width'],v['height'];margin=48 if c['high_resolution']else 24
    require(c['width']==W and c['height']==H and c['margin']==margin,'Absolute camera dimensions differ')
    xmin,ymin,xmax,ymax=frame
    require(W>2*margin and H>2*margin and xmax>xmin and ymax>ymin,'Invalid absolute frame')
    factor=min((W-2*margin)/(xmax-xmin),(H-2*margin)/(ymax-ymin))
    offset=[W/(2*factor)-(xmin+xmax)/2,H/(2*factor)-(ymin+ymax)/2]
    require(math.isfinite(factor)and 1e-6<=factor<=1e6 and all(map(math.isfinite,offset)),'Unsupported absolute factor/offset')
    require(c['factor']==factor and c['offset']==offset,'Absolute request differs from frozen formula')
    require(v['factor']==factor and v['offset']==offset,'Actual native camera differs from absolute request')

def captures(job,actions,basis,observations):
    rows=[r for r in actions if r['kind']=='capture']
    expected=[(label,mode,frame)for label in LABELS for mode in MODES for frame in basis['frames']]
    require([(r['label'],r['mode'],r['frame'])for r in rows]==expected,'Camera view coverage missing/reordered')
    images=set()
    for row in rows:
        obs=row['observation'];request=obs['request'];view=obs['view'];canvas=row['canvas']
        require(any(equal(obs,o)for o in observations),'Camera capture not bound to actual reply')
        require(request['action']=='frame'and request['frame_mode']==row['mode']and request['frame']==basis['frames'][row['frame']]
                and request['expected_path']==obs['filename']=='/work/'+row['label']+'.dxf','Camera filename/frame/mode differs')
        require(obs['selected']==[],'Camera view has selection highlighting')
        x,y,w,h=canvas['rectangle']
        require([w,h]==[view['width'],view['height']]and x>=0 and y>=0 and w>0 and h>0,'Camera canvas dimensions differ')
        require(canvas['showing']is True and canvas['enabled']is True,'Camera canvas hidden/disabled')
        if row['mode']=='absolute':absolute_request(obs,request['frame'])
        require(2<=len(row['images'])<=10 and row['images'][-1]['pixel_sha256']==row['images'][-2]['pixel_sha256'],'Camera canvas not stable')
        for image in row['images']:
            name=image['path'];require(Path(name).name==name and name.endswith('.png')and'\\'not in name,'Unsafe camera image path')
            cropname=Path(name).with_suffix('.canvas.png').name
            require(name not in images and cropname not in images,'Camera image reused');images.update((name,cropname))
            with Image.open(job/'ui'/name)as full,Image.open(job/'ui'/cropname)as crop:
                require(full.size==(2400,1400)and crop.size==(w,h),'Camera screenshot dimensions differ')
                require(full.crop((x,y,x+w,y+h)).tobytes()==crop.tobytes(),'Camera full/crop pixels differ')
                require(hashlib.sha256(crop.tobytes()).hexdigest()==image['pixel_sha256'],'Camera pixel digest differs')
    require({p.name for p in(job/'ui').glob('*.png')}==images,'Camera image omitted/unregistered')
    return rows,len(images)

def pixels(job,rows,basis,out):
    out.mkdir();result=[]
    for mode in MODES:
        for frame in basis['frames']:
            chosen={r['label']:r for r in rows if r['mode']==mode and r['frame']==frame}
            source=chosen['source'];different=[]
            for label,row in chosen.items():
                if row['observation']['view']!=source['observation']['view']or row['canvas']['rectangle']!=source['canvas']['rectangle']:
                    different.append(dict(label=label,source_view=source['observation']['view'],observed_view=row['observation']['view'],source_canvas=source['canvas']['rectangle'],observed_canvas=row['canvas']['rectangle']))
            boxes=[]
            for label in ('source','candidate'):
                attrs=chosen[label]['observation']['attributes'];ids=[a['parent_id']for a in attrs if a['tag']=='ICT_ID'and a['text']==basis['attributes']['ICT_ID']]
                require(len(ids)==1,'Projected camera identity missing/ambiguous')
                fields=[a for a in attrs if a['parent_id']==ids[0]and a['tag']=='MANUFACTURER']
                require(len(fields)==1 and len(fields[0]['projected'])==4,'Projected camera label missing/ambiguous');boxes.append(fields[0]['projected'])
            region=[math.floor(min(b[0]for b in boxes))-2,math.floor(min(b[1]for b in boxes))-2,math.ceil(max(b[2]for b in boxes))+2,math.ceil(max(b[3]for b in boxes))+2]
            for left,right,permitted in [('source','baseline',None),('source','candidate',region),('baseline','edited',region)]:
                a,b=chosen[left],chosen[right]
                ai=job/'ui'/Path(a['images'][-1]['path']).with_suffix('.canvas.png');bi=job/'ui'/Path(b['images'][-1]['path']).with_suffix('.canvas.png')
                measures=ui.analysis.image_pair(ai,bi,permitted,out/(mode+'-'+frame+'-'+left+'-'+right+'.png'))
                result.append(dict(mode=mode,frame=frame,left=left,right=right,exact_camera_status='failed'if different else'pass',camera_differences=different,diagnostic_only=bool(different),pixel_status='pass'if measures['outside_region']==0 else'failed',**measures))
    return result

def receive_job(job,out):
    basis=read(job/'job.json');case=basis['case']
    require(case in CASES and basis['role']=='receiving','Camera case/role differs')
    original=read(HERE/'native-ui-pairs-19/evidence'/case/'INVENTORY.json')['files']
    # Retain original bytes, including CRLF; reserialization is not a source digest.
    original_basis=BASE/'bases'/(case+'.json')
    require(sha(original_basis)==original['raw/cases/'+case+'/basis.json']['sha256'],'Original camera basis bytes changed')
    require(equal(read(original_basis),{k:v for k,v in basis.items()if k!='role'}),'Camera source basis changed')
    process=ui.environment(job);require(equal(process['job'],basis),'Camera actual process basis differs')
    require(read(job/'ui/RESULT.json')==dict(status='controller-complete',role='receiving',case=case,whole_cad_qualified=False)and not(job/'ui/FAILURE.json').exists(),'Camera controller incomplete/failed')
    frozen=read(job/'JOB-FREEZE.json');methods=read(BASE/'METHODS.json')
    expected=set(methods['job_methods'])|{'job.json','.configuration/QCAD3.conf'}|{label+'.dxf'for label in LABELS}
    require(set(frozen['files'])==expected,'Camera frozen input coverage differs')
    require(frozen['preparation_sha256']==methods['preparer_sha256']==sha(HERE/'prepare_camera19.py'),'Camera preparer changed')
    for name,pin in frozen['files'].items():
        if name=='.configuration/QCAD3.conf':require(pin==process['configuration_before'],'Camera settings changed')
        else:require(sha(job/name)==pin,'Camera frozen input changed: '+name)
    for name,pin in methods['job_methods'].items():require(frozen['files'][name]==pin,'Camera frozen method differs: '+name)
    for label,pin in drawing_pins(case).items():require(sha(job/(label+'.dxf'))==pin,'Camera original drawing/return changed: '+label)
    require(not(job/'returned.dxf').exists(),'Camera-only job wrote a CAD return')
    actions=read(job/'ui/actions.json')
    require([r['event']for r in actions]==list(range(1,len(actions)+1))and[r['at']for r in actions]==sorted(r['at']for r in actions),'Camera action missing/reordered')
    commands=[r for r in actions if r['kind']=='command'];require(commands and all(r['exit']==0 for r in commands),'Camera native command failed')
    ui.control_trace(actions,basis,'receiving')
    require(any(r['command']==['ps','-eo','pid,ppid,stat,etime,args']and'/opt/qcad/qcad-bin -platform xcb'in r['stdout']for r in commands),'Camera actual native binary missing')
    require(not any(r['kind']=='returned_file'for r in actions),'Read-only camera job saved a drawing')
    observations=[r['reply']for r in actions if r['kind']=='native_observation']
    require([r['request']['seq']for r in observations]==list(range(1,len(observations)+1)),'Camera observation missing/reordered')
    require({p.name for p in(job/'replies').glob('*.json')}=={str(r['request']['seq'])+'.json'for r in observations},'Camera reply coverage differs')
    before=basis['attributes'];after=dict(before,MANUFACTURER='QUAL-AFTER')
    for r in observations:
        require(equal(r,read(job/'replies'/(str(r['request']['seq'])+'.json'))),'Camera raw reply differs from actions')
        require('error'not in r and r['qt']=='5.14.2'and r['configuration_file']=='/home/cad/.config/QCAD/QCAD3.conf'and r['modified']is False,'Camera read-only observation failed/changed')
        path=r['filename']
        if not path:require(r['attributes']==[],'Camera untitled document changed')
        else:
            require(path in ['/work/'+label+'.dxf'for label in LABELS],'Camera wrong native filename')
            ui.native_values(r,after if path in ('/work/edited.dxf','/work/candidate.dxf')else before)
    fields=[r for r in actions if r['kind']=='native_fields'];trees=sorted((job/'ui').glob('*-selected.json'))
    require(len(fields)==len(trees)==4,'Camera field/tree coverage differs')
    for row,tree,expected_values in zip(fields,trees,(before,before,after,after)):
        require(equal(row['expected'],expected_values),'Camera field expectation metadata changed')
        ui.values(row['observed'],expected_values);actual=ui.fields(read(tree));ui.values(actual,expected_values)
        require(equal(actual,row['observed']),'Camera actual field tree differs')
    rows,image_count=captures(job,actions,basis,observations)
    comparisons=pixels(job,rows,basis,out)
    return dict(case=case,scope='Exposed read-only camera repeat; original native save failures unchanged',whole_cad_qualified=False,
                fields=len(fields),observations=len(observations),views=len(rows),images=image_count,native_exit=process['exit'],controller_exit=process['controller_exit'],pixels=comparisons)

def receive_packet(packet,out):
    manifest=read(packet/'INVENTORY.json')
    require(manifest['packager_sha256']==sha(HERE/'package_ui19.py'),'Camera archive writer changed')
    root=unpack(packet,out/'unpacked');job=root/'job';case=read(job/'job.json')['case']
    require(manifest['kind']==dict(route='exposed-camera-repeat',case=case),'Camera packet kind differs')
    assembly=read(root/'ASSEMBLY.json');env=read(job/'ENVIRONMENT.json')
    require(assembly['case']==case and assembly['container']==env['container']and assembly['assembly_sha256']==sha(HERE/'package_camera20.py')
            and assembly['archive_writer_sha256']==sha(HERE/'package_ui19.py'),'Camera assembly provenance differs')
    batch=root/'batch'
    if case=='libre-air-water':
        require({p.name for p in batch.iterdir()}=={'LAUNCH.json','TERMINAL-INSPECT.json'},'Original air launch coverage differs')
        launch=read(batch/'LAUNCH.json');inspection=read(batch/'TERMINAL-INSPECT.json')[0]
    else:
        require({p.name for p in batch.iterdir()}=={'FREEZE.json',case+'-stage.json',case+'-launch.json',case+'-inspection.json'},'Camera batch coverage differs')
        launch=read(batch/(case+'-launch.json'));inspection_record=read(batch/(case+'-inspection.json'))
        require(inspection_record['exit']==0,'Camera terminal inspect failed');inspection=json.loads(inspection_record['stdout'])[0]
        frozen=read(batch/'FREEZE.json')
        require(frozen['cases']==list(CASES[1:])and frozen['image']==env['image']and frozen['max_running']==3,'Remaining camera cohort changed')
        for suffix,path in [('camera-repeat-20/batch.py',BASE/'batch.py'),('camera-repeat-20/PLAN.md',BASE/'PLAN.md'),('prepare_camera19.py',HERE/'prepare_camera19.py'),('native-ui-pairs-19/camera_repeat.py',HERE/'native-ui-pairs-19/camera_repeat.py')]:
            pins=[pin for name,pin in frozen['methods'].items()if name.replace('\\','/').endswith('/'+suffix)]
            require(pins==[sha(path)],'Camera frozen batch method differs: '+suffix)
        require(read(batch/(case+'-stage.json'))['exit']==0,'Camera staging failed')
    require(launch['exit']==0 and launch['stdout'].strip()==inspection['Id']and inspection['Name']=='/'+env['container']
            and inspection['Image']==env['image']and inspection['State']==env['state'],'Camera original launch/terminal identity differs')
    require(inspection['Config']['User']==env['user']and inspection['HostConfig']['NetworkMode']==env['network'],'Camera original launch environment differs')
    command=launch['command']
    # Verify the full declared command rather than inferring execution from a success marker.
    mounts=inspection['Mounts'];require(len(mounts)==1 and mounts[0]['Destination']=='/work','Camera original mount differs')
    expected=['docker','run','-d','--name',env['container'],'--network','none','--user','1001:1001','--memory','3g','--cpus','2','--shm-size','256m','--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges','--mount','type=bind,source='+mounts[0]['Source']+',target=/work','--entrypoint','dbus-run-session',env['image'],'--','python3','/work/launch_case.py']
    # Docker Desktop reports the mounted Windows source as /run/desktop/mnt/host/c/...
    # The submitted launch records its Windows spelling; bind it to the inspection mount.
    mount_arg=command[command.index('--mount')+1]
    submitted=mount_arg.removeprefix('type=bind,source=').removesuffix(',target=/work')
    actual=mounts[0]['Source']
    normalized='/run/desktop/mnt/host/'+submitted[0].lower()+submitted[2:]if len(submitted)>2 and submitted[1:3]==':/'else submitted
    require(actual in (submitted,normalized),'Camera launch mount is not the observed directory')
    expected[expected.index('--mount')+1]=mount_arg
    require(command==expected,'Camera actual launch command differs')
    return receive_job(job,out/'pixels')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);p.add_argument('out',type=Path);p.add_argument('--packet',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True)
    result=receive_packet(a.job,a.out)if a.packet else receive_job(a.job,a.out/'pixels')
    (a.out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items()if k!='pixels'}))
if __name__=='__main__':main()
