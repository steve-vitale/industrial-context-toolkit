"""Retain public DXF test records, notices and observed failures; exclude all native settings/binaries."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent
FOLDERS=('inputs','candidates','native-1','controls-1','controls-2','controls-3','source-notices','observations')
EXTENSIONS={'.dxf','.json','.png','.py','.js','.stdout','.stderr','.log','.txt'}


def package(root):
    archive=HERE/'evidence.tar.xz'
    if archive.exists() or (HERE/'INVENTORY.json').exists():raise ValueError('Preserve prior evidence')
    files={}
    with tarfile.open(archive,'w:xz') as packed:
        for folder in FOLDERS:
            for path in sorted((root/folder).rglob('*')):
                rel=path.relative_to(root)
                if any(p.startswith('.') or p=='__pycache__' for p in rel.parts) or path.suffix not in EXTENSIONS:continue
                if not path.is_file():continue
                if path.is_symlink():raise ValueError('Linked evidence refused')
                data=path.read_bytes();name='raw/'+rel.as_posix()
                if len(data)>4*1024*1024:raise ValueError('Member exceeds existing bounded receiver')
                member=tarfile.TarInfo(name);member.mode=0o644;member.size=len(data);packed.addfile(member,io.BytesIO(data))
                files[name]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    inventory=dict(files=files,raw_bytes=sum(v['bytes'] for v in files.values()),
                   archive=dict(path=archive.name,bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),
                   packager_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
                   scope='Public source/adapted DXFs and actual native observations; retain upstream notices. No CAD executables, font binaries or native configuration contents.')
    (HERE/'INVENTORY.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8',newline='\n')
    return inventory


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);args=ap.parse_args()
    result=package(args.root);print(result['archive'],len(result['files']),'files')
