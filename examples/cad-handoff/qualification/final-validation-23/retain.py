"""Retain completed outputs without changing the frozen drawing or receiving methods."""
import hashlib
import io
import tarfile
from pathlib import Path
from campaign import read, write, sha, require
from evidence import MAX_FILES, MAX_FILE, MAX_RAW, unpack


def package(folders, out, result=None):
    require(not out.exists(), 'New retained packet required')
    saved={}
    for prefix,folder in folders:
        for path in Path(folder).rglob('*'):
            if path.is_file() and not any(p in ('.configuration','__pycache__') for p in path.relative_to(folder).parts):
                saved[prefix+'/'+path.relative_to(folder).as_posix()]=path.read_bytes()
    if result is not None:
        import json
        saved['receiving/RESULT.json']=(json.dumps(result,indent=2)+'\n').encode()
    require(0<len(saved)<=MAX_FILES and sum(map(len,saved.values()))<=MAX_RAW and max(map(len,saved.values()))<=MAX_FILE,'Packet exceeds unchanged bounds')
    out.mkdir(parents=True)
    with tarfile.open(out/'evidence.tar.xz','w:xz',preset=6) as archive:
        for name,raw in sorted(saved.items()):
            item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o644;item.mtime=0;archive.addfile(item,io.BytesIO(raw))
    write(out/'INVENTORY.json',dict(archive_sha256=sha(out/'evidence.tar.xz'),files={n:dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()) for n,raw in sorted(saved.items())}))
    if result is not None:write(out/'RESULT.json',result)
    require(unpack(out)==saved,'Retained packet round trip differs')
    return dict(inventory_sha256=sha(out/'INVENTORY.json'),archive_sha256=sha(out/'evidence.tar.xz'),files=len(saved),raw_bytes=sum(map(len,saved.values())))


def check_pin(packet, pin):
    require(sha(packet/'INVENTORY.json')==pin['inventory_sha256'] and sha(packet/'evidence.tar.xz')==pin['archive_sha256'],'External retained packet pin differs')
    return unpack(packet)
