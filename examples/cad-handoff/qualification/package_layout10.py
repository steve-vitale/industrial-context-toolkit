"""Package declared local layout-development records; exclude native configuration and executables."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent
BASE=HERE/'layout-preparation-10'
FOLDERS=('development-1','development-2','development-3','controls-1','native-1','native-2')
EXTENSIONS={'.dxf','.json','.png','.py','.js','.md','.csv','.tsv','.stdout','.stderr','.log'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('captured_root',type=Path)
    root=parser.parse_args().captured_root
    archive=BASE/'evidence.tar.xz'
    if archive.exists() or (BASE/'INVENTORY.json').exists():raise ValueError('Retain existing evidence')
    files={}
    with tarfile.open(archive,'w:xz') as packed:
        for folder in FOLDERS:
            work=root/folder
            for path in sorted(work.rglob('*')):
                relative=path.relative_to(work)
                if any(part.startswith('.') or part=='qcad-config' for part in relative.parts):continue
                if not path.is_file() or path.suffix not in EXTENSIONS:continue
                if path.is_symlink():raise ValueError('Unexpected linked evidence')
                name='raw/'+folder+'/'+relative.as_posix();data=path.read_bytes()
                entry=tarfile.TarInfo(name);entry.mode=0o644;entry.size=len(data)
                packed.addfile(entry,io.BytesIO(data))
                files[name]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    inventory=dict(schema='cad-layout-preparation-ten-evidence-1',files=files,
                   raw_bytes=sum(r['bytes'] for r in files.values()),
                   archive=dict(path=archive.name,bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),
                   packager_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
                   excluded='Dot directories/local native configuration, CAD settings, font/executable binaries; digest-only setup receipt retained')
    (BASE/'INVENTORY.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in inventory.items() if k!='files'}))


if __name__=='__main__':main()
