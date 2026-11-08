"""Retain exact constructor evidence, excluding settings contents and publisher binaries."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = Path('C:/Users/Steve/.cp-scratch/cad-layout-construction-17')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def main():
    native = json.loads(subprocess.check_output(['docker', 'inspect', 'ict-cad-layout17-1']))[0]
    host = native['HostConfig']
    environment = dict(image=native['Image'], state=native['State'], user=native['Config']['User'], network=host['NetworkMode'],
                       path=native['Path'], args=native['Args'], mounts=native['Mounts'],
                       qt_hash_seed=[v for v in native['Config']['Env'] if v.startswith('QT_HASH_SEED=')],
                       resources={k: host[k] for k in ('NanoCpus', 'Memory', 'ShmSize', 'PidsLimit', 'CapDrop', 'SecurityOpt')})
    (ROOT / 'attempt-2/ENVIRONMENT.json').write_bytes(encoded(environment))
    log = subprocess.run(['docker', 'logs', 'ict-cad-layout17-1'], capture_output=True)
    (ROOT / 'attempt-2/CONTAINER-LOG.json').write_bytes(encoded(dict(exit=log.returncode, stdout=log.stdout.decode('utf-8'), stderr=log.stderr.decode('utf-8'))))
    files = {}
    for path in sorted(ROOT.rglob('*')):
        if path.is_file() and '.configuration' not in path.parts and '__pycache__' not in path.parts and path.suffix != '.so':
            data = path.read_bytes()
            if len(data) > 4 * 1024 * 1024:
                raise ValueError('Evidence member exceeds existing bounded receiver: ' + str(path))
            files['raw/' + path.relative_to(ROOT).as_posix()] = data
    methods = {p.name: sha(p.read_bytes()) for p in sorted(HERE.iterdir())
               if p.suffix in ('.py', '.cpp', '.md', '.json') and p.name not in ('README.md', 'INVENTORY.json', 'SUMMARY.json')}
    files['raw/METHODS.json'] = encoded(methods)
    archive = HERE / 'evidence.tar.xz'
    with tarfile.open(archive, 'w:xz', format=tarfile.USTAR_FORMAT) as packed:
        for name, data in sorted(files.items()):
            entry = tarfile.TarInfo(name)
            entry.size, entry.mtime, entry.mode = len(data), 0, 0o644
            packed.addfile(entry, io.BytesIO(data))
    inventory = dict(archive=dict(path=archive.name, bytes=archive.stat().st_size, sha256=sha(archive.read_bytes())),
                     raw_bytes=sum(map(len, files.values())), files={name: dict(bytes=len(data), sha256=sha(data)) for name, data in sorted(files.items())},
                     exclusions=['Selected settings contents (hash retained)', 'Compiled authored helper (source/compile/hash retained)',
                                 'Publisher libraries and software', 'Python bytecode'], packager_sha256=sha(Path(__file__).read_bytes()))
    (HERE / 'INVENTORY.json').write_bytes(encoded(inventory))
    print(json.dumps(dict(members=len(files), raw_bytes=inventory['raw_bytes'], archive=inventory['archive']), indent=2))


if __name__ == '__main__':
    main()
