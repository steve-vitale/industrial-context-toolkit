"""Bounded lossless native-UI evidence archives; standard library only, no CAD execution."""
import hashlib
import json
from pathlib import PurePosixPath
import tarfile

def require(test,message):
    if not test:raise ValueError(message)
def read(path):return json.loads(path.read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def equal(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))
def unpack(base,destination):
    manifest=read(base/'INVENTORY.json');archive=base/'evidence.tar.xz'
    require(manifest['archive']['path']==archive.name and archive.stat().st_size==manifest['archive']['bytes']and sha(archive)==manifest['archive']['sha256'],'Archive identity differs')
    pins=manifest['files'];require(isinstance(pins,dict)and pins,'Empty archive inventory')
    require(all(type(v['bytes'])is int and 0<=v['bytes']<=4*1024**2 for v in pins.values()),'Unbounded member declaration')
    require(type(manifest['raw_bytes'])is int and manifest['raw_bytes']==sum(v['bytes']for v in pins.values())<=256*1024**2,'Unbounded archive')
    seen=set()
    with tarfile.open(archive,'r:xz')as packed:
        for entry in packed:
            name=PurePosixPath(entry.name)
            require(entry.isfile()and not name.is_absolute()and len(name.parts)>1 and name.parts[0]=='raw'
                    and '..'not in name.parts and ':'not in entry.name and '\\'not in entry.name
                    and name.as_posix()==entry.name and entry.name not in seen and entry.name in pins,'Unsafe, duplicate or unregistered archive entry')
            pin=pins[entry.name];require(entry.size==pin['bytes'],'Archive member size differs')
            with packed.extractfile(entry)as stream:data=stream.read(entry.size+1)
            require(len(data)==entry.size and hashlib.sha256(data).hexdigest()==pin['sha256'],'Archive member differs')
            target=destination.joinpath(*name.parts);require(target.resolve().is_relative_to(destination.resolve()),'Archive target escapes destination')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);seen.add(entry.name)
    require(seen==set(pins),'Archive member omitted')
    return destination/'raw'
