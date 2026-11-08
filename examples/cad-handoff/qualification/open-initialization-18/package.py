"""Pack exact native observations and controller history, excluding private settings and binaries."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-open-initialization-18/attempt-1')
def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(v):return(json.dumps(v,indent=2)+'\n').encode('utf-8')
def main():
    native=json.loads(subprocess.check_output(['docker','inspect','ict-cad-open18-1']))[0];host=native['HostConfig']
    (ROOT/'ENVIRONMENT.json').write_bytes(encoded(dict(image=native['Image'],state=native['State'],
        user=native['Config']['User'],network=host['NetworkMode'],path=native['Path'],args=native['Args'],mounts=native['Mounts'],
        qt_hash_seed=[v for v in native['Config']['Env']if v.startswith('QT_HASH_SEED=')],
        resources={k:host[k]for k in ('NanoCpus','Memory','ShmSize','PidsLimit','CapDrop','SecurityOpt')})))
    log=subprocess.run(['docker','logs','ict-cad-open18-1'],capture_output=True)
    (ROOT/'CONTAINER-LOG.json').write_bytes(encoded(dict(exit=log.returncode,stdout=log.stdout.decode(),stderr=log.stderr.decode())))
    # The original startup controller was interrupted. Its actual actions remain in STARTUP-ACTIONS.json.
    (ROOT/'CONTROLLER-STATUS.json').write_bytes(encoded(dict(original_controller_exit=1,original_controller_interrupted=True,
        original_controller_exception_traceback=False,corrected_controller_exit=0,native_process_restarts=0)))
    files={}
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file()or '.configuration'in p.parts or '__pycache__'in p.parts or p.suffix=='.so':continue
        data=p.read_bytes()
        if len(data)>4*1024**2:raise ValueError('Evidence member exceeds receiver bound: '+str(p))
        files['raw/attempt-1/'+p.relative_to(ROOT).as_posix()]=data
    methods={p.name:sha(p.read_bytes())for p in sorted(HERE.iterdir())
             if p.suffix in ('.py','.md','.json','.js')and p.name not in ('README.md','INVENTORY.json','SUMMARY.json')}
    methods['../layout-construction-17/analyze.py']=sha((HERE.parent/'layout-construction-17/analyze.py').read_bytes())
    methods['../check_open18.py']=sha((HERE.parent/'check_open18.py').read_bytes())
    files['raw/METHODS.json']=encoded(methods)
    archive=HERE/'evidence.tar.xz'
    with tarfile.open(archive,'w:xz',format=tarfile.USTAR_FORMAT)as packed:
        for name,data in sorted(files.items()):
            entry=tarfile.TarInfo(name);entry.size=len(data);entry.mtime=0;entry.mode=0o644
            packed.addfile(entry,io.BytesIO(data))
    inventory=dict(archive=dict(path=archive.name,bytes=archive.stat().st_size,sha256=sha(archive.read_bytes())),
        raw_bytes=sum(map(len,files.values())),files={n:dict(bytes=len(d),sha256=sha(d))for n,d in sorted(files.items())},
        exclusions=['Selected settings contents; original and working hashes retained','Compiled helper and publisher binaries; source/prior compilation identity retained',
                    'Python bytecode'],packager_sha256=sha(Path(__file__).read_bytes()))
    (HERE/'INVENTORY.json').write_bytes(encoded(inventory))
    print(json.dumps(dict(members=len(files),raw_bytes=inventory['raw_bytes'],archive=inventory['archive']),indent=2))
if __name__=='__main__':main()
