"""Package explicitly selected, already captured native font evidence; never runs CAD."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
BASE = HERE / 'font-views-9'
FOLDERS = ('default', 'default-replay-2', 'substitute')
NAMES = ('00-start.png', '01-ready.png', '02-before-quit.png', 'SETUP.json', 'terminal.json',
         'environment.json', 'HOST-NOTES.json', 'native.stdout', 'native.stderr',
         'native_views.js', 'desktop.sh', 'capture.py', 'capture-initial.py',
         'CORRECTED-METHOD.json', 'requests.json', 'requests-corrected.json', 'request.json',
         'font_manifest.py', 'font-manifest.json', 'canvas_geometry.py', 'canvas-geometry.json',
         'openbox.log', 'xvfb.log', 'vnc.log', 'websockify.log')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captured_root', type=Path)
    args = parser.parse_args()
    archive = BASE / 'evidence.tar.xz'
    if archive.exists() or (BASE / 'INVENTORY.json').exists():
        raise ValueError('Existing evidence must not be overwritten')
    files = {}
    with tarfile.open(archive, 'w:xz') as packed:
        for folder in FOLDERS:
            work = args.captured_root / folder
            paths = [work/name for name in NAMES if (work/name).is_file()]
            paths += sorted(work.glob('validation-*.dxf'))
            for sub in ('receipts', 'views', 'views-corrected'):
                directory = work/sub
                if directory.exists():
                    paths += sorted(p for p in directory.iterdir() if p.suffix in ('.png','.json'))
            for path in paths:
                name = 'raw/' + folder + '/' + path.relative_to(work).as_posix()
                data = path.read_bytes()
                assert name not in files and not path.is_symlink()
                entry = tarfile.TarInfo(name)
                entry.size, entry.mode = len(data), 0o644
                packed.addfile(entry, io.BytesIO(data))
                files[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    inventory = dict(schema='cad-font-views-nine-evidence-1', files=files,
        raw_bytes=sum(row['bytes'] for row in files.values()),
        archive=dict(path=archive.name, bytes=archive.stat().st_size,
                     sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),
        packager_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
        excluded='DBus address, CAD settings/autosaves, publisher executable and font files; font metadata retained')
    (BASE/'INVENTORY.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in inventory.items() if key!='files'}))


if __name__ == '__main__':
    main()
