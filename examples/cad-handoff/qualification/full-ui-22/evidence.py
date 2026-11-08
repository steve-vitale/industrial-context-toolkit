"""Bounded lossless packaging of full native development attempts, including failed receivers."""
import argparse
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
from receive import receive, require, read, sha, digest, equal, HERE

MAX_RAW = 128*1024**2
MAX_FILE = 16*1024**2
MAX_FILES = 12000


def unpack(packet):
    index = read(packet/'INVENTORY.json'); blob = (packet/'evidence.tar.xz').read_bytes()
    require(digest(blob) == index['archive_sha256'], 'Archive bytes differ')
    require(0 < len(index['files']) <= MAX_FILES and sum(r['bytes'] for r in index['files'].values()) <= MAX_RAW, 'Unbounded full UI packet')
    files = {}; total = 0
    with tarfile.open(fileobj=io.BytesIO(blob),mode='r:xz') as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            require(member.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in member.name and '\\' not in member.name and name.as_posix() == member.name and member.name not in files and member.name in index['files'], 'Unsafe/unregistered full UI archive member')
            require(0 <= member.size <= MAX_FILE and member.size == index['files'][member.name]['bytes'], 'Archive member size differs')
            total += member.size; require(total <= MAX_RAW and len(files) < MAX_FILES, 'Archive exceeds scope')
            data = archive.extractfile(member).read(member.size+1)
            require(len(data) == member.size and digest(data) == index['files'][member.name]['sha256'], 'Archive member bytes differ')
            files[member.name] = data
    require(set(files) == set(index['files']), 'Archive member omitted')
    return files


def package(attempt, execution, failures, receipt, out):
    require(not out.exists(), 'New packet destination required')
    actual = receive(attempt,HERE/'PREPARATION-1.json',HERE/'METHODS-1.json')
    require(equal(actual,read(receipt/'RESULT.json')) and read(execution/'EXIT.json')['exit'] == 0, 'Actual receiving result/host exit differs')
    files = {}
    for prefix,folder in [('attempt',attempt),('execution',execution),('receiving',receipt),('failed-receiving',failures)]:
        for path in folder.rglob('*'):
            if path.is_file(): files[prefix+'/'+path.relative_to(folder).as_posix()] = path.read_bytes()
    for name in ('METHODS-1.json','PREPARATION-1.json','receive.py','evidence.py'):
        files['methods/'+name] = (HERE/name).read_bytes()
    require(len(files) <= MAX_FILES and sum(map(len,files.values())) <= MAX_RAW and max(map(len,files.values())) <= MAX_FILE, 'Packet exceeds frozen packaging bounds')
    out.mkdir(parents=True); archive = out/'evidence.tar.xz'
    with tarfile.open(archive,'w:xz',preset=6) as target:
        for name,data in sorted(files.items()):
            member = tarfile.TarInfo(name); member.size = len(data); member.mode = 0o644; member.mtime = 0
            target.addfile(member,io.BytesIO(data))
    (out/'INVENTORY.json').write_text(json.dumps(dict(archive_sha256=sha(archive),files={n:dict(bytes=len(v),sha256=digest(v)) for n,v in sorted(files.items())}),indent=2)+'\n',encoding='utf-8',newline='\n')
    (out/'RESULT.json').write_bytes((receipt/'RESULT.json').read_bytes())
    return dict(files=len(files),raw_bytes=sum(map(len,files.values())),archive_bytes=archive.stat().st_size,whole_cad_qualified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('attempt','execution','failures','receipt','out'): parser.add_argument(name,type=Path)
    print(json.dumps(package(**vars(parser.parse_args())),indent=2))
