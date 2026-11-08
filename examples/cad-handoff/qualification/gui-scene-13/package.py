"""Package exact diagnostic records; never include publisher software, fonts or settings contents."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

HERE=Path(__file__).resolve().parent
ROOT=Path('C:/Users/Steve/.cp-scratch/cad-gui-scene-13')
OLD=Path('C:/Users/Steve/.cp-scratch/cad-font-views-9/default-replay-2')
def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return (json.dumps(value,indent=2)+'\n').encode()
def main():
    files={}
    def add(name,path):
        data=path.read_bytes();assert len(data)<=4*1024*1024,name
        assert 'raw/'+name not in files;files['raw/'+name]=data
    def trace(folder,path,name):
        data=path.read_bytes();parts=[]
        for i,start in enumerate(range(0,len(data),512*1024)):
            member=f'{folder}/{name}-chunks/{i:03}.part';files['raw/'+member]=data[start:start+512*1024];parts.append(member)
        files[f'raw/{folder}/{name}-index.json']=encoded(dict(bytes=len(data),sha256=sha(data),parts=parts))
    for folder in ('ordinary','observed','observed-2','observed-3','observed-4'):
        work=ROOT/folder
        for name in ('FREEZE.json','ENVIRONMENT.json','COMPLETE.json','native-log.json','configuration-terminal.json',
                     'selected-config-initial.sha256','requests.json','desktop.sh','native_views.js','capture.py',
                     'validation-long-source.dxf','validation-long-candidate.dxf','startup.png','geometry.png','failure.json'):
            if(work/name).is_file():add(folder+'/'+name,work/name)
        for sub in ('views','receipts'):
            for p in sorted((work/sub).glob('*')):
                if p.is_file():add(folder+'/'+sub+'/'+p.name,p)
        if(work/'paint.jsonl').is_file():trace(folder,work/'paint.jsonl','paint')
    for seq in (106,107):
        add(f'reference/{seq}.png',OLD/'views-corrected'/f'{seq}.png')
        add(f'reference/{seq}.json',OLD/'receipts'/f'{seq}.json')
    add('old-config-recovery.json',ROOT/'old-config-recovery.json')
    for p in sorted((ROOT/'build').iterdir()):
        if p.is_file() and p.suffix in ('.txt','.log','.cpp','.json','.png'):
            if p.name in ('epoch.json',):continue
            add('build/'+p.name,p)
        if p.name in ('control.jsonl','control4.jsonl'):trace('build',p,p.stem)
    for folder in ('replay','replay-4'):
        for p in sorted((ROOT/folder).iterdir()):
            if p.is_file() and (p.suffix in('.png','.txt','.cpp','.log') or p.name=='groups.json'):
                add(folder+'/'+p.name,p)
            if p.name=='replay-state.jsonl':trace(folder,p,'replay-state')
    commits={'observer-3':'05ba24b','observer-4':'5642521','replay-1':'f24d3f2','replay-2':'5642521','replay-4':'1b62977'}
    for label,commit in commits.items():
        filename='paint_trace.cpp'if label.startswith('observer')else'replay.cpp'
        data=subprocess.check_output(['git','show',commit+':examples/cad-handoff/qualification/gui-scene-13/'+filename])
        files[f'raw/methods/{label}.cpp']=data
    for label,commit in [('control-1','05ba24b'),('control-4','5642521')]:
        files[f'raw/methods/{label}.cpp']=subprocess.check_output(['git','show',commit+':examples/cad-handoff/qualification/gui-scene-13/observer_control.cpp'])
    files['raw/methods/commits.json']=encoded(commits)
    sources=[]
    for name in ('RGraphicsViewImage.cpp','RGraphicsViewWorkerPainter.cpp'):
        data=(ROOT/name).read_bytes();sources.append(dict(url='https://raw.githubusercontent.com/qcad/qcad/897079c2d11aaa0869f839a6cf5df8a937dbddbe/src/gui/'+name,sha256=sha(data),bytes=len(data)))
    files['raw/SOURCES.json']=encoded(dict(public_source=sources,note='Public core source is a method lead; actual native trace/replay establishes the measured behavior. Proprietary exporter implementation is not included.'))
    archive=HERE/'evidence.tar.xz'
    with tarfile.open(archive,'w:xz',format=tarfile.USTAR_FORMAT)as packed:
        for name,data in sorted(files.items()):
            entry=tarfile.TarInfo(name);entry.size=len(data);entry.mtime=0;entry.mode=0o644;packed.addfile(entry,io.BytesIO(data))
    inventory=dict(archive=dict(path=archive.name,bytes=archive.stat().st_size,sha256=sha(archive.read_bytes())),
        raw_bytes=sum(map(len,files.values())),files={name:dict(bytes=len(data),sha256=sha(data))for name,data in sorted(files.items())},
        exclusions=['Publisher binaries and Qt/font files','Native settings contents and DBus address','Author helper binaries (hashes retained); source/build commands retained'],
        packager_sha256=sha(Path(__file__).read_bytes()))
    (HERE/'INVENTORY.json').write_bytes(encoded(inventory))
    print('Packaged',len(files),'members,',inventory['raw_bytes'],'raw bytes;',inventory['archive'])

if __name__=='__main__':main()
