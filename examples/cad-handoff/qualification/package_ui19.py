"""Retain terminal native UI cases losslessly; refuse unfinished jobs; exclude settings/binaries."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

HERE=Path(__file__).resolve().parent;BASE=HERE/'native-ui-pairs-19'
def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(v):return(json.dumps(v,indent=2)+'\n').encode('utf-8')
def collect(files,source,prefix):
    for path in sorted(source.rglob('*')):
        if not path.is_file()or any(p in path.parts for p in ('.configuration','__pycache__'))or path.suffix in ('.so','.dll','.exe'):continue
        data=path.read_bytes()
        if len(data)>4*1024**2:raise ValueError('Oversized member: '+str(path))
        files[prefix+'/'+path.relative_to(source).as_posix()]=data
def environment(root,name):
    r=subprocess.run(['docker','inspect',name],capture_output=True,text=True)
    if r.returncode:raise ValueError('Native handle missing: '+name)
    native=json.loads(r.stdout)[0];state=native['State'];host=native['HostConfig']
    if state['Status']!='exited'or state['Running']or state['OOMKilled']:raise ValueError('Native handle is not terminal: '+name)
    env=dict(container=name,image=native['Image'],state=state,user=native['Config']['User'],network=host['NetworkMode'],path=native['Path'],args=native['Args'],mounts=native['Mounts'],
             special_environment=[v for v in native['Config']['Env']if v.startswith(('QT_HASH_SEED=','LD_PRELOAD='))],resources={k:host[k]for k in ('NanoCpus','Memory','ShmSize','PidsLimit','CapDrop','SecurityOpt')})
    (root/'ENVIRONMENT.json').write_bytes(encoded(env))
    logs=subprocess.run(['docker','logs',name],capture_output=True)
    (root/'CONTAINER-LOG.json').write_bytes(encoded(dict(exit=logs.returncode,stdout=logs.stdout.decode(),stderr=logs.stderr.decode())))
    return env
def pack(files,destination,kind):
    destination.mkdir(parents=True)
    total=sum(map(len,files.values()))
    if total>256*1024**2:raise ValueError('Packet exceeds raw bound; do not truncate')
    archive=destination/'evidence.tar.xz'
    with tarfile.open(archive,'w:xz',format=tarfile.USTAR_FORMAT)as packed:
        for name,data in sorted(files.items()):
            entry=tarfile.TarInfo(name);entry.size=len(data);entry.mtime=0;entry.mode=0o644;packed.addfile(entry,io.BytesIO(data))
    inventory=dict(kind=kind,archive=dict(path=archive.name,bytes=archive.stat().st_size,sha256=sha(archive.read_bytes())),raw_bytes=total,
                   files={n:dict(bytes=len(d),sha256=sha(d))for n,d in sorted(files.items())},packager_sha256=sha(Path(__file__).read_bytes()),
                   exclusions=['Selected original/working settings contents; hashes retained','Publisher binaries and compiled libraries','Python bytecode'])
    (destination/'INVENTORY.json').write_bytes(encoded(inventory));print(destination.name,len(files),total,archive.stat().st_size,flush=True)
def case_packet(work,case,out):
    cohort=json.loads((work/'jobs-5/batch/COHORT.json').read_bytes());selected=[r for r in cohort['jobs']if r['case']==case]
    if [r['role']for r in selected]!=['baseline','edited','receiving']:raise ValueError('Changed case cohort')
    files={'raw/cohort/COHORT.json':encoded(cohort)}
    for name,pin in cohort['methods'].items():
        data=(BASE/name).read_bytes()
        if sha(data)!=pin:raise ValueError('Cohort method changed: '+name)
        files['raw/cohort/methods/'+name]=data
    for row in selected:
        job=work/'jobs-5'/row['key'];env=environment(job,row['container']);process=json.loads((job/'native/PROCESS.json').read_bytes())
        if env['state']['ExitCode']!=0 or process.get('controller_exit')!=0 or process.get('exit')!=0 or not(job/'ui/RESULT.json').exists():raise ValueError('Incomplete/failed clean case: '+row['key'])
        collect(files,job,'raw/jobs/'+row['key'])
    collect(files,work/'cases-1'/case,'raw/cases/'+case)
    pack(files,out,dict(route='clean-exposed-case',case=case))
def historical(work,out):
    files={}
    mapping={'preflight-1':'ict-cad-ui19-preflight1','jobs-1/libre-air-water-baseline':'ict-cad-ui19-air-baseline1',
             'jobs-2/libre-air-water-baseline':'ict-cad-ui19-air-baseline2','jobs-3/libre-air-water-baseline':'ict-cad-ui19-air-baseline3',
             'jobs-4/libre-air-water-baseline':'ict-cad-ui19-air-baseline4','jobs-4/libre-air-water-edited':'ict-cad-ui19-air-edited4'}
    for relative,name in mapping.items():
        root=work/relative;environment(root,name);collect(files,root,'raw/'+relative)
    for relative in ('analysis-1','infrastructure','receiver-1','receiver-2'):
        collect(files,work/relative,'raw/'+relative)
    for name in ('SELECTOR-CONTROLS.json',):files['raw/'+name]=(work/name).read_bytes()
    pack(files,out,dict(route='historical-development',clean_cohort=False))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('work',type=Path);p.add_argument('out',type=Path);p.add_argument('--case');a=p.parse_args()
    if a.case:case_packet(a.work,a.case,a.out)
    else:historical(a.work,a.out)
