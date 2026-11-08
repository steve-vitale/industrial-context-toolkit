"""Retain a terminal method2 attempt without rewriting its original inventory."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
from bridge_receive import receive

HERE = Path(__file__).resolve().parent


def package(attempt, basis, host, receipt, receipt_command, out):
    result = receive(attempt, basis, HERE / 'BRIDGE-METHODS-2.json')
    if json.loads(receipt.read_bytes()) != result: raise ValueError('Actual receiving receipt differs')
    command = json.loads(receipt_command.read_bytes())
    if command['exit'] != 0 or json.loads(command['stdout']) != result: raise ValueError('Actual receiving command differs')
    if out.exists(): raise ValueError('New packet destination required')
    files = {'attempt/' + p.relative_to(attempt).as_posix(): p.read_bytes() for p in attempt.rglob('*') if p.is_file()}
    files.update({'execution/' + p.relative_to(host).as_posix(): p.read_bytes() for p in host.rglob('*') if p.is_file()})
    files.update({'case/basis.json': basis.read_bytes(), 'receiving/result.json': receipt.read_bytes(),
                  'receiving/command.json': receipt_command.read_bytes(),
                  'methods/BRIDGE-METHODS-2.json': (HERE / 'BRIDGE-METHODS-2.json').read_bytes(),
                  'methods/package_bridge.py': Path(__file__).read_bytes()})
    out.mkdir(parents=True)
    archive = out / 'evidence.tar.xz'
    with tarfile.open(archive, 'w:xz', preset=6) as target:
        for name, data in sorted(files.items()):
            member = tarfile.TarInfo(name); member.size = len(data); member.mode = 0o644; member.mtime = 0
            target.addfile(member, io.BytesIO(data))
    sha = lambda data: hashlib.sha256(data).hexdigest()
    (out / 'INVENTORY.json').write_text(json.dumps(dict(archive_sha256=sha(archive.read_bytes()),
        files={n: dict(bytes=len(v), sha256=sha(v)) for n, v in sorted(files.items())}), indent=2) + '\n', encoding='utf-8')
    (out / 'RESULT.json').write_bytes(receipt.read_bytes())
    return dict(files=len(files), raw_bytes=sum(map(len, files.values())), archive_bytes=archive.stat().st_size, result=result)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('attempt', 'basis', 'host', 'receipt', 'receipt_command', 'out'): p.add_argument(name, type=Path)
    a = p.parse_args(); print(json.dumps(package(**vars(a)), indent=2))
