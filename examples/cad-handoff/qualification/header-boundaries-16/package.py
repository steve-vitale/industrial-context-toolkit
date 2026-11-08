"""Package exact native header evidence with bounded, hash-bound large-file chunks."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-header-boundaries-16')
PUBLIC=Path('C:/Users/Steve/.cp-scratch/cad-header-research-16')
def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(v):return(json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
def main():
    files={};assembly={}
    def add(name,path):
        data=path.read_bytes()
        if len(data)<=2*1024*1024:
            assert 'raw/'+name not in files;files['raw/'+name]=data
        else:
            parts=[];group=len(assembly)
            for index,start in enumerate(range(0,len(data),512*1024)):
                part=f'chunks/{group:03}/{index:03}.part';files['raw/'+part]=data[start:start+512*1024];parts.append(part)
            assembly[name]=dict(bytes=len(data),sha256=sha(data),parts=parts)
    for folder,name in[('attempt-1','ict-cad-header16-1'),('dimension-2','ict-cad-header16-dimension2')]:
        work=ROOT/folder;raw=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
        host=raw['HostConfig']
        env=dict(image=raw['Image'],state=raw['State'],user=raw['Config']['User'],network=host['NetworkMode'],path=raw['Path'],args=raw['Args'],
            mounts=raw['Mounts'],qt_hash_seed=[v for v in raw['Config']['Env']if v.startswith('QT_HASH_SEED=')],
            resources={k:host[k]for k in('NanoCpus','Memory','ShmSize','PidsLimit','CapDrop','SecurityOpt')})
        (work/'ENVIRONMENT.json').write_bytes(encoded(env));log=subprocess.run(['docker','logs',name],capture_output=True)
        (work/'CONTAINER-LOG.json').write_bytes(encoded(dict(exit=log.returncode,stdout=log.stdout.decode('utf-8'),stderr=log.stderr.decode('utf-8'))))
        for path in sorted(work.rglob('*')):
            if path.is_file()and'.configuration'not in path.parts and'__pycache__'not in path.parts:add(path.relative_to(ROOT).as_posix(),path)
    for folder in('analysis-syntax-failure','analysis-fresh-failure'):
        for path in sorted((ROOT/folder).iterdir()):add(folder+'/'+path.name,path)
    add('HOST-LAUNCH-FAILURE.json',ROOT/'HOST-LAUNCH-FAILURE.json')
    add('FOLLOWUP-SOURCE.json',PUBLIC/'RLayout.source.json')
    files['raw/REASSEMBLY.json']=encoded(assembly)
    files['raw/METHODS.json']=encoded({p.name:sha(p.read_bytes())for p in sorted(HERE.iterdir())if p.suffix in('.py','.js','.md')and p.name!='README.md'})
    archive=HERE/'evidence.tar.xz'
    with tarfile.open(archive,'w:xz',format=tarfile.USTAR_FORMAT)as packed:
        for name,data in sorted(files.items()):
            entry=tarfile.TarInfo(name);entry.size=len(data);entry.mtime=0;entry.mode=0o644;packed.addfile(entry,io.BytesIO(data))
    inventory=dict(archive=dict(path=archive.name,bytes=archive.stat().st_size,sha256=sha(archive.read_bytes())),raw_bytes=sum(map(len,files.values())),
        files={name:dict(bytes=len(data),sha256=sha(data))for name,data in sorted(files.items())},
        exclusions=['Native settings contents (selected hashes retained)','Publisher software/fonts/libraries','Python bytecode','Public source contents (URLs/byte hashes retained)'],
        packager_sha256=sha(Path(__file__).read_bytes()))
    (HERE/'INVENTORY.json').write_bytes(encoded(inventory));print('Packaged',len(files),'members;',inventory['raw_bytes'],'raw bytes;',inventory['archive'])
if __name__=='__main__':main()
