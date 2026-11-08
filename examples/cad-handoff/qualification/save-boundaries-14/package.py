"""Package exact native records, including failed probes; exclude native settings/software."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-save-boundaries-14')
FOLDERS={'attempt-1':'1','payload-2':'payload2','payload-3':'payload3','seed-0-a':'seed0a','seed-0-b':'seed0b','integer-4':'integer4'}
def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(v):return(json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
def main():
    files={};chunks={}
    def add(name,data):
        if len(data)>4*1024*1024:
            parts=[]
            for i,start in enumerate(range(0,len(data),1024*1024)):
                member=f'chunks/{len(chunks):03}/{i:03}.part';files['raw/'+member]=data[start:start+1024*1024];parts.append(member)
            chunks[name]=dict(bytes=len(data),sha256=sha(data),parts=parts)
        else:files['raw/'+name]=data
    for folder,label in FOLDERS.items():
        raw=json.loads(subprocess.check_output(['docker','inspect','ict-cad-boundaries14-'+label]))[0]
        env=dict(image=raw['Image'],state=raw['State'],user=raw['Config']['User'],network=raw['HostConfig']['NetworkMode'],
            path=raw['Path'],args=raw['Args'],mounts=raw['Mounts'],qt_hash_seed=[v for v in raw['Config']['Env']if v.startswith('QT_HASH_SEED=')])
        (ROOT/folder/'ENVIRONMENT.json').write_bytes(encoded(env))
        log=subprocess.run(['docker','logs','ict-cad-boundaries14-'+label],capture_output=True)
        (ROOT/folder/'CONTAINER-LOG.json').write_bytes(encoded(dict(exit=log.returncode,stdout=log.stdout.decode('utf-8'),stderr=log.stderr.decode('utf-8'))))
        for path in sorted((ROOT/folder).rglob('*')):
            if path.is_file()and'.configuration'not in path.parts and'__pycache__'not in path.parts:
                add(path.relative_to(ROOT).as_posix(),path.read_bytes())
    for folder in('followup-analysis','integer-analysis'):
        for path in sorted((ROOT/folder).rglob('*')):
            if path.is_file():add(path.relative_to(ROOT).as_posix(),path.read_bytes())
    for name in('analyze-empty-failure.py','analyze-empty-failure.log'):
        add(name,(ROOT/name).read_bytes())
    sources=[]
    for path in sorted(ROOT.glob('*')):
        if path.name in('qhash-5.14.2.cpp','RDocument.h','RDocumentInterface.cpp','RDocumentVariables.h','RFileExporterRegistry.h','RImporter.cpp','RObject.h'):
            url='https://raw.githubusercontent.com/qt/qtbase/v5.14.2/src/corelib/tools/qhash.cpp'if path.name.startswith('qhash')else'https://raw.githubusercontent.com/qcad/qcad/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/core/'+path.name
            sources.append(dict(url=url,bytes=path.stat().st_size,sha256=sha(path.read_bytes())))
    add('SOURCES.json',encoded(sources));files['raw/CHUNKS.json']=encoded(chunks)
    methods={p.name:sha(p.read_bytes())for p in sorted(HERE.iterdir())if p.suffix in('.py','.js','.md')and p.name not in('README.md',)}
    files['raw/METHODS.json']=encoded(methods)
    archive=HERE/'evidence.tar.xz'
    with tarfile.open(archive,'w:xz',format=tarfile.USTAR_FORMAT)as packed:
        for name,data in sorted(files.items()):
            entry=tarfile.TarInfo(name);entry.size=len(data);entry.mtime=0;entry.mode=0o644;packed.addfile(entry,io.BytesIO(data))
    inventory=dict(archive=dict(path=archive.name,bytes=archive.stat().st_size,sha256=sha(archive.read_bytes())),
        raw_bytes=sum(map(len,files.values())),files={name:dict(bytes=len(data),sha256=sha(data))for name,data in sorted(files.items())},
        exclusions=['Native settings contents (selected hash retained)','Publisher software, fonts and libraries','Python bytecode'],packager_sha256=sha(Path(__file__).read_bytes()))
    (HERE/'INVENTORY.json').write_bytes(encoded(inventory));print('Packaged',len(files),'members',inventory['raw_bytes'],'raw bytes',inventory['archive'])
if __name__=='__main__':main()
