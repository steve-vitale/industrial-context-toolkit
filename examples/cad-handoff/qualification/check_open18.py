"""Receive full-application plot initialization evidence offline, without launching CAD."""
import importlib.util
import hashlib
from pathlib import Path
from pathlib import PurePosixPath
import tarfile
import tempfile

HERE=Path(__file__).resolve().parent;BASE=HERE/'open-initialization-18'
spec=importlib.util.spec_from_file_location('cad_open18_analysis',BASE/'analyze.py')
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)
a=analysis.a

def unpack(base,destination):
    manifest=a.read(base/'INVENTORY.json');archive=base/'evidence.tar.xz'
    a.require(manifest['archive']['path']=='evidence.tar.xz'and archive.stat().st_size==manifest['archive']['bytes']
              and a.sha(archive)==manifest['archive']['sha256'],'Archive identity differs')
    a.require(manifest['raw_bytes']==sum(v['bytes']for v in manifest['files'].values())<=256*1024**2,'Unbounded archive')
    seen=set()
    with tarfile.open(archive,'r:xz')as packed:
        for entry in packed:
            name=PurePosixPath(entry.name)
            a.require(entry.isfile()and not name.is_absolute()and len(name.parts)>1 and name.parts[0]=='raw'
                      and '..'not in name.parts and ':'not in entry.name and '\\'not in entry.name
                      and name.as_posix()==entry.name and entry.name not in seen and entry.name in manifest['files'],
                      'Unsafe, duplicate or unregistered archive entry')
            pin=manifest['files'][entry.name]
            a.require(entry.size==pin['bytes']and 0<=entry.size<=4*1024**2,'Changed or unbounded archive member')
            with packed.extractfile(entry)as stream:data=stream.read(entry.size+1)
            a.require(len(data)==entry.size and hashlib.sha256(data).hexdigest()==pin['sha256'],'Archive member differs')
            target=destination.joinpath(*name.parts)
            a.require(target.resolve().is_relative_to(destination.resolve()),'Archive member escapes destination')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);seen.add(entry.name)
    a.require(seen==set(manifest['files']),'Archive member omitted')
    return destination/'raw'

def receive(root):
    for name,pin in a.read(root/'METHODS.json').items():
        target=(BASE/name).resolve()
        a.require(target.is_relative_to(HERE.resolve())and a.sha(target)==pin,'Open18 method differs: '+name)
    work=root/'attempt-1';frozen=a.read(work/'FREEZE.json');prior=a.read(HERE/'layout-construction-17/FREEZE.json')
    a.require(a.equal(frozen,a.read(BASE/'FREEZE.json')),'Published pre-execution freeze differs')
    for name in ('image','library_sha256','configuration_sha256','helper_sha256'):
        a.require(frozen[name]==prior[name],'Prior native identity differs: '+name)
    for name,pin in frozen['inputs'].items():
        if name.startswith('cases/'):a.require(pin==prior['inputs'][name],'Exposed source changed')
    for name in ('PLAN.md','prepare.py','native_open.js','run_native.py'):
        a.require(a.sha(work/name)==a.sha(BASE/name),'Published frozen code differs: '+name)
    env=a.read(work/'ENVIRONMENT.json');state=env['state']
    a.require(env['image']==frozen['image']and env['user']=='1001:1001'and env['network']=='none'and not env['qt_hash_seed'],
              'Native image/user/network differs')
    a.require(state['Status']=='exited'and not state['Running']and not state['OOMKilled']and state['ExitCode']==0,
              'Native batch not successfully terminal')
    a.require(env['path']=='dbus-run-session'and env['args']==['--','python3','/work/run_native.py'],'Different native entrypoint')
    a.require(len(env['mounts'])==1 and env['mounts'][0]['Type']=='bind'and env['mounts'][0]['Destination']=='/work',
              'Different native mount')
    a.require(env['resources']==dict(NanoCpus=2000000000,Memory=3*1024**3,ShmSize=256*1024**2,PidsLimit=256,
              CapDrop=['ALL'],SecurityOpt=['no-new-privileges']),'Different native resource constraints')
    a.require(a.read(work/'COMPILE.json')['helper_sha256']==frozen['helper_sha256'],'Prior helper compile identity differs')
    controller=a.read(work/'CONTROLLER-STATUS.json')
    a.require(controller==dict(original_controller_exit=1,original_controller_interrupted=True,original_controller_exception_traceback=False,
              corrected_controller_exit=0,native_process_restarts=0),'Controller correction history omitted')
    failure=work/'receiver-dependency-1';result=a.read(failure/'RESULT.json')
    a.require(result['exit']==1 and result['source_sha256']==a.sha(failure/'check_open18.py')
              and "No module named 'ezdxf'"in(failure/'stderr.txt').read_text(encoding='utf-8'),
              'Original standard-library receiving failure omitted')
    initial=a.read(work/'STARTUP-ACTIONS.json')
    a.require(len(initial)==4 and all(r['exit']==0 for r in initial),'Original controller actions omitted')
    for row in initial:
        a.require((work/row['screenshot']).is_file()and'"Trial":'in row['tree'],'Original startup observation omitted')
    rows=a.read(work/'CONTROL-ACTIONS.json')+a.read(work/'MDI-CLOSE-ACTIONS.json');commands=a.read(work/'native/commands.json')
    for command in commands:
        name=command['route']+'-'+command['mode']
        selected=[r for r in rows if r['process']==name]
        closes=[r for r in selected if r['action'].startswith('close-after-recorded-')]
        a.require(len(closes)==1 and all(r['exit']==0 and r['pid']==command['pid']for r in selected),'Normal UI close missing')
        for r in selected:
            a.require((work/r['screenshot']).is_file(),'Native controller screenshot omitted')
            c=r['command'];a.require(c[:3]==['docker','exec','ict-cad-open18-1'],'Different controller target')
            if r['action']=='acknowledge-visible-trial':
                a.require(c[3:6]==['xdotool','windowactivate','--sync']and c[-2:]==['key','Return'],'Different startup action')
            else:a.require(c[3:5]==['wmctrl','-ic'],'Different post-DONE close action')
        stderr=(work/('native/'+name+'.stderr')).read_text(encoding='utf-8')
        expected=("'QCoreApplication.quit' [undefined] is not a function"if command['route']=='bare'
                  else "'ws[j].getDocument()' [null] is not an object")
        a.require(expected in stderr,'Frozen cleanup error omitted')
    summary,detail=analysis.analyze(work)
    a.require(a.equal(summary,a.read(work/'analysis/summary.json'))and a.equal(detail,a.read(work/'analysis/detail.json')),
              'Retained open/init analysis differs')
    return summary

def check():
    a.require(a.sha(BASE/'package.py')==a.read(BASE/'INVENTORY.json')['packager_sha256'],'Open18 packager differs')
    with tempfile.TemporaryDirectory(prefix='ict-open18-')as temporary:
        summary=receive(unpack(BASE,Path(temporary)))
    a.require(a.equal(summary,a.read(BASE/'SUMMARY.json')),'Published open/init summary differs')
    return summary
if __name__=='__main__':
    import json
    print(json.dumps(check(),indent=2))
