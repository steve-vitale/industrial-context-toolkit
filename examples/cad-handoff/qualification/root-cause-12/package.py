"""Losslessly retain causal experiments and every failed probe; exclude settings and software binaries."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent
FOLDERS=('attempt-1','attempt-2','attempt-3','pixels-1','pixels-2','pixels-3','pixels-4','pixels-5','reference','reports','source-notices')
EXTENSIONS={'.dxf','.json','.py','.js','.png','.stdout','.stderr','.txt','.log',''}
def package(root):
    archive=HERE/'evidence.tar.xz'
    if archive.exists() or (HERE/'INVENTORY.json').exists():raise ValueError('Preserve prior archive')
    files={}
    with tarfile.open(archive,'w:xz') as packed:
        for folder in FOLDERS:
            for path in sorted((root/folder).rglob('*')):
                rel=path.relative_to(root)
                if any(p.startswith('.')or p=='__pycache__'for p in rel.parts)or not path.is_file():continue
                if path.is_symlink()or path.suffix not in EXTENSIONS:raise ValueError('Unlisted evidence kind: '+str(rel))
                data=path.read_bytes()
                if len(data)>4*1024*1024:raise ValueError('Member exceeds bounded receiver: '+str(rel))
                name='raw/'+rel.as_posix();entry=tarfile.TarInfo(name);entry.size=len(data);entry.mode=0o644
                packed.addfile(entry,io.BytesIO(data));files[name]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    result=dict(files=files,raw_bytes=sum(p['bytes']for p in files.values()),
        archive=dict(path=archive.name,bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),
        packager_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
        scope='Exposed public/adapted DXF controls, native outputs/logs, failed raster attempts, reference captures and replay. No settings, fonts or CAD binaries.')
    (HERE/'INVENTORY.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);a=ap.parse_args();r=package(a.root);print(len(r['files']),r['archive'])
