"""Stage a separate six-case camera repeat without changing original native methods or evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent;BASE=HERE/'native-ui-pairs-19'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('work',type=Path);p.add_argument('case');p.add_argument('destination',type=Path);p.add_argument('configuration',type=Path);a=p.parse_args()
    original=a.work/'jobs-5'/(a.case+'-receiving');case=a.work/'cases-1'/a.case
    # Independent originals/returns can be staged before the old receiving process finishes.
    for role in ('baseline','edited'):
        proc=json.loads((a.work/'jobs-5'/(a.case+'-'+role)/'native/PROCESS.json').read_bytes())
        if proc.get('controller_exit')!=0 or proc.get('exit')!=0:raise ValueError('Source native save is not complete')
    a.destination.mkdir(parents=True);(a.destination/'.configuration').mkdir();shutil.copyfile(a.configuration,a.destination/'.configuration/QCAD3.conf')
    basis=json.loads((case/'basis.json').read_bytes());basis['role']='receiving';write(a.destination/'job.json',basis)
    shutil.copyfile(case/'source.dxf',a.destination/'source.dxf');shutil.copyfile(case/'software/candidate/candidate.dxf',a.destination/'candidate.dxf')
    for role in ('baseline','edited'):shutil.copyfile(a.work/'jobs-5'/(a.case+'-'+role)/'returned.dxf',a.destination/(role+'.dxf'))
    for name in ('launch_case.py','inspect_ui.py','ui_control.py','native_controls.py','METHOD.md','PLAN.md','CAMERA-REPEAT-PLAN.md'):
        shutil.copyfile(original/name if(original/name).exists()else BASE/name,a.destination/name)
    shutil.copyfile(original/'workflow.py',a.destination/'original_workflow.py');shutil.copyfile(BASE/'camera_repeat.py',a.destination/'workflow.py')
    old=(original/'observe_case.js').read_text(encoding='utf-8')
    before="   di.zoomTo(new RBox(new RVector(b[0],b[1]),new RVector(b[2],b[3])),24);di.repaintViews();"
    after="""   var cameraView=di.getLastKnownViewWithFocus();if(isNull(cameraView))throw new Error('No native camera view');
   if(r.frame_mode==='zoom-to')di.zoomTo(new RBox(new RVector(b[0],b[1]),new RVector(b[2],b[3])),24);
   else if(r.frame_mode==='absolute'){
    var high=RSettings.getHighResolutionGraphicsView(),margin=high?48:24,W=cameraView.getWidth(),H=cameraView.getHeight();
    var f=Math.min((W-2*margin)/(b[2]-b[0]),(H-2*margin)/(b[3]-b[1]));
    if(!isFinite(f)||f<1e-6||f>1e6)throw new Error('Unsupported absolute factor');
    var offset=[W/(2*f)-(b[0]+b[2])/2,H/(2*f)-(b[1]+b[3])/2];
    cameraView.setFactor(f);cameraView.setOffset(new RVector(offset[0],offset[1]));
    out.camera_control={factor:f,offset:offset,high_resolution:high,margin:margin,width:W,height:H};
   }else throw new Error('Unknown camera mode');
   di.repaintViews();"""
    if old.count(before)!=1:raise ValueError('Original camera method differs')
    (a.destination/'observe_case.js').write_text(old.replace(before,after),encoding='utf-8')
    write(a.destination/'JOB-FREEZE.json',dict(files={p.relative_to(a.destination).as_posix():sha(p)for p in a.destination.rglob('*')if p.is_file()},scope='Separate exposed camera repeat, no edit/save, both old and absolute views; original cohort unchanged',preparation_sha256=sha(Path(__file__))))
if __name__=='__main__':main()
