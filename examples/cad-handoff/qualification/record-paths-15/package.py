"""Retain all native attempts and exact diagnostics; no publisher software/settings."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-record-paths-15')
def sha(data):return hashlib.sha256(data).hexdigest()
def enc(v):return(json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
def main():
    files={}
    def add(name,path):
        data=path.read_bytes();assert len(data)<=4*1024*1024,name;assert 'raw/'+name not in files;files['raw/'+name]=data
    cohorts=[(f'attempt-{index}','ict-cad-record15-'+str(index))for index in range(1,5)]
    cohorts.append(('symbol-5','ict-cad-record15-symbol5'))
    for folder,name in cohorts:
        work=ROOT/folder
        raw=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
        env=dict(image=raw['Image'],state=raw['State'],user=raw['Config']['User'],network=raw['HostConfig']['NetworkMode'],
            path=raw['Path'],args=raw['Args'],mounts=raw['Mounts'],qt_hash_seed=[v for v in raw['Config']['Env']if v.startswith('QT_HASH_SEED=')])
        (work/'ENVIRONMENT.json').write_bytes(enc(env))
        log=subprocess.run(['docker','logs',name],capture_output=True)
        (work/'CONTAINER-LOG.json').write_bytes(enc(dict(exit=log.returncode,stdout=log.stdout.decode('utf-8'),stderr=log.stderr.decode('utf-8'))))
        for path in sorted(work.rglob('*')):
            if path.is_file()and'.configuration'not in path.parts and'__pycache__'not in path.parts:add(path.relative_to(ROOT).as_posix(),path)
    for path in sorted(ROOT.glob('dangling-analysis-failure.*')):add(path.name,path)
    for path in sorted((ROOT/'symbol-receiver-failure').iterdir()):add('symbol-receiver-failure/'+path.name,path)
    add('SOURCES.json',ROOT/'SOURCES.json')
    methods={p.name:sha(p.read_bytes())for p in sorted(HERE.iterdir())if p.suffix in('.py','.js','.md')and p.name!='README.md'}
    files['raw/METHODS.json']=enc(methods)
    archive=HERE/'evidence.tar.xz'
    with tarfile.open(archive,'w:xz',format=tarfile.USTAR_FORMAT)as packed:
        for name,data in sorted(files.items()):
            entry=tarfile.TarInfo(name);entry.size=len(data);entry.mtime=0;entry.mode=0o644;packed.addfile(entry,io.BytesIO(data))
    inventory=dict(archive=dict(path=archive.name,bytes=archive.stat().st_size,sha256=sha(archive.read_bytes())),
        raw_bytes=sum(map(len,files.values())),files={name:dict(bytes=len(data),sha256=sha(data))for name,data in sorted(files.items())},
        exclusions=['Native settings contents (selected hash retained)','Publisher software, fonts and libraries','Python bytecode','Public source contents (URLs/hashes retained)'],packager_sha256=sha(Path(__file__).read_bytes()))
    (HERE/'INVENTORY.json').write_bytes(enc(inventory));print('Packaged',len(files),'members,',inventory['raw_bytes'],'bytes;',inventory['archive'])
if __name__=='__main__':main()
