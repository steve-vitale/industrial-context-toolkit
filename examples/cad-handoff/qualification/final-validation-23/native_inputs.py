"""Prepare exact final native API/render inputs and generic UI bases; no native launch."""
import argparse
import copy
import shutil
from pathlib import Path
from campaign import HERE, ROOT, read, write, sha, lf, require, binding
from prepare import frame
import cad_handoff as ch


def prepare(out,software):
    binding();require(not out.exists(),'New final native preparation required')
    out.mkdir(parents=True);api=out/'api';api.mkdir();(api/'inputs').mkdir();(api/'returned').mkdir()
    render=out/'render';render.mkdir();(render/'inputs').mkdir();ui=out/'ui';ui.mkdir()
    inputs=read(HERE/'INPUTS.json')['cases'];native=[];fresh=[];renders=[]
    config=read(HERE.parent/'full-ui-22/SECOND-REVISION-PREPARATION-1.json')['configuration_sha256']
    parent=read(HERE.parent/'full-ui-22/PREPARATION-1.json')
    prepared=dict(scope='New reserved UI bases; historical preparation metadata is parent lineage only',
        preparation=parent['preparation'],configuration_sha256=config,
        derivation=dict(producer_sha256_lf=lf(__file__),final_freeze_sha256_lf=lf(HERE/'FREEZE.json')),cases={})
    for row in inputs:
        if row['status']!='admitted':continue
        identity=row['id'];source=ROOT/row['source'];plan=ROOT/row['plan'];candidate=software/identity/'candidate/candidate.dxf'
        result=read(software/identity/'EVALUATION.json')
        if result['routes']['value-spans'].get('strict_status')!='pass':continue
        require(sha(source)==row['source_sha256'] and sha(plan)==row['plan_sha256'],'Native final source differs')
        require(not ch.compare(ch.snapshot(source),ch.snapshot(candidate),read(plan))['unexpected'],'Native final candidate strict gate failed')
        for folder in (api,render):
            for label,path in [('source',source),('candidate',candidate),('plan',plan)]:shutil.copyfile(path,folder/'inputs'/(identity+'-'+label+path.suffix))
        empty=copy.deepcopy(read(plan));empty['changes']=[];write(api/'inputs'/(identity+'-noedit.json'),empty)
        for role,planname,cand in [('baseline','noedit','source'),('edited','plan','candidate')]:
            native.append(dict(id=identity+'-'+role,source='/work/inputs/'+identity+'-source.dxf',candidate='/work/inputs/'+identity+'-'+cand+'.dxf',
                plan='/work/inputs/'+identity+'-'+planname+'.json',native_default='/work/returned/'+identity+'-'+role+'-default.dxf',
                native_r15='/work/returned/'+identity+'-'+role+'-r15.dxf'))
        fresh.append(dict(id=identity+'-source-candidate',source='/work/inputs/'+identity+'-source.dxf',candidate='/work/inputs/'+identity+'-candidate.dxf',plan='/work/inputs/'+identity+'-plan.json'))
        for version in ('default','r15'):
            fresh.append(dict(id=identity+'-'+version,source='/work/returned/'+identity+'-baseline-'+version+'.dxf',candidate='/work/returned/'+identity+'-edited-'+version+'.dxf',plan='/work/inputs/'+identity+'-plan.json'))
        docs=[ch.load(source),ch.load(candidate)];snapshot=ch.snapshot(source)
        frames=dict(overview=frame([e for d in docs for e in d.modelspace()]))
        for n,asset in enumerate(snapshot['assets'],1):
            inserts=[d.entitydb[asset['handle']] for d in docs];attrs=[a for insert in inserts for a in insert.attribs]
            frames['asset-'+str(n)]=frame(inserts+attrs);frames['labels-'+str(n)]=frame(attrs)
        for label in ('source','candidate'):
            path=render/'inputs'/(identity+'-'+label+'.dxf')
            renders.append(dict(id=identity+'-model-'+label,path=path.relative_to(render).as_posix(),sha256=sha(path),window=frames['overview'],layout='Model'))
        for layout in docs[0].layouts:
            views=[v for v in layout.query('VIEWPORT') if v.dxf.id>1]
            if layout.name=='Model' or not views:continue
            boxes=[(v.dxf.center.x-v.dxf.width/2,v.dxf.center.y-v.dxf.height/2,v.dxf.center.x+v.dxf.width/2,v.dxf.center.y+v.dxf.height/2) for v in views]
            x,y=min(b[0] for b in boxes),min(b[1] for b in boxes);right,top=max(b[2] for b in boxes),max(b[3] for b in boxes)
            pad=max(2,.2*max(right-x,top-y));window=[x-pad,y-pad,right+pad,top+pad]
            for label in ('source','candidate'):
                path=render/'inputs'/(identity+'-'+label+'.dxf')
                renders.append(dict(id=identity+'-paper-'+str(len(renders))+'-'+label,path=path.relative_to(render).as_posix(),sha256=sha(path),window=window,layout=layout.name))
        if identity in ('public-air-water','final-foreign'):
            folder=ui/identity;folder.mkdir();shutil.copyfile(source,folder/'source.dxf');shutil.copyfile(plan,folder/'plan.json')
            (folder/'software/candidate').mkdir(parents=True);shutil.copyfile(candidate,folder/'software/candidate/candidate.dxf')
            basis=dict(case=identity,source_sha256=sha(source),plan_sha256=sha(plan),assets=snapshot['assets'],changes=read(plan)['changes'],frames=frames,
                       scope='Predetermined reserved public-adapted/procedural UI transfer; not plant or engineering acceptance')
            write(folder/'basis.json',basis)
            prepared['cases'][identity]=dict(basis=basis,files={p.relative_to(folder).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()})
    for target,path in [('native-batch.js',HERE.parent/'native-batch.js'),('native-view-bounds.js',HERE.parent/'native-view-bounds.js'),
                        ('native_profile.js',HERE.parent/'public-validation-11/native_profile.js'),('run_native.py',HERE.parent/'public-validation-11/run_native.py')]:
        (api/target).write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
    write(api/'BATCH.json',dict(cases=native,read_only=False));write(api/'FRESH.json',dict(cases=fresh,read_only=True))
    write(api/'NATIVE.json',dict(configuration_sha256=config,inputs={p.relative_to(api).as_posix():sha(p) for p in api.rglob('*') if p.is_file()}))
    for name,path in [('render.py',HERE/'render.py'),('window.py',HERE.parent/'public-validation-11/window.py')]:
        (render/name).write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
    write(render/'MANIFEST.json',dict(configuration_sha256=config,jobs=renders))
    write(out/'UI-PREPARATION.json',prepared)
    write(out/'PREPARATION.json',dict(scope='Prepared after frozen software results, before any native calls; all original failures remain',
        final_freeze_sha256_lf=lf(HERE/'FREEZE.json'),api_cases=len(native),fresh_cases=len(fresh),renders=len(renders),ui_cases=list(prepared['cases']),
        files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}))
    return prepared


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('software',type=Path);a=p.parse_args()
    result=prepare(a.out,a.software);print('Prepared native API/renders and',len(result['cases']),'predetermined UI cases')
