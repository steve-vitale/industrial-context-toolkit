"""Serial view-only native font observations after startup/geometry have been observed."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import time
import zlib


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("requests",type=Path)
    p.add_argument("out",type=Path)
    args=p.parse_args();args.out.mkdir(exist_ok=False)
    actions=[]
    def run(*cmd):
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
        actions.append(dict(at=datetime.now(timezone.utc).isoformat(),command=list(cmd),exit=r.returncode,stdout=r.stdout,stderr=r.stderr))
        if r.returncode: raise RuntimeError("Native capture/input failed")
    try:
        for request in json.loads(args.requests.read_text(encoding="utf-8")):
            seq=request["seq"]
            temporary=Path("/work/request.next.json")
            temporary.write_text(json.dumps(request),encoding="utf-8")
            temporary.replace("/work/request.json")
            receipt=Path(f"/work/receipts/{seq}.json")
            for _ in range(160):
                if Path("/work/failure.json").exists(): raise RuntimeError("Native listener failed; retain failure.json")
                if receipt.exists():
                    try: observed=json.loads(receipt.read_text(encoding="utf-8"));break
                    except json.JSONDecodeError: pass
                time.sleep(.25)
            else: raise RuntimeError("Native camera request timed out; do not restart")
            if observed["request"]!=request: raise RuntimeError("Wrong native view receipt")
            # Padded lower-right model margin, then outside main window. Retain motion.
            run("xdotool","mousemove","1590","1220")
            time.sleep(.5)
            run("xdotool","mousemove","2380","1380")
            time.sleep(2)
            previous=None
            for frame in range(10):
                path=args.out/f"{seq}-frame-{frame}.png"
                run("scrot",str(path))
                raw,pos,data=path.read_bytes(),8,[]
                while pos<len(raw):
                    length=struct.unpack(">I",raw[pos:pos+4])[0]
                    if raw[pos+4:pos+8]==b"IDAT":data.append(raw[pos+8:pos+8+length])
                    pos+=length+12
                value=hashlib.sha256(zlib.decompress(b"".join(data))).hexdigest()
                actions.append(dict(frame=path.name,filtered_image_sha256=value))
                if value==previous:
                    (args.out/f"{seq}.png").write_bytes(raw);break
                previous=value;time.sleep(.6)
            else: raise RuntimeError("Native frame did not stabilize")
    finally:
        (args.out/"actions.json").write_text(json.dumps(actions,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
