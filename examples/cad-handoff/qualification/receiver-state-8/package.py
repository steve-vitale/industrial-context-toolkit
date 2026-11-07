"""Package only declared pointer experiment records, not software/settings/session addresses."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("work", type=Path)
    p.add_argument("out", type=Path)
    args = p.parse_args()
    archive = args.out / "evidence.tar.xz"
    if archive.exists() or (args.out / "INVENTORY.json").exists():
        p.error("Retain existing evidence instead of overwriting")
    names = ["00-start.png", "01-ready.png", "02-before-quit.png", "SETUP.json", "terminal.json",
             "text_in_viewports-source.dxf", "text_in_viewports-candidate.dxf", "observe_pointer.py"]
    names += [x.relative_to(args.work).as_posix() for x in sorted((args.work / "pointer-controls").iterdir())]
    pins = {}
    with tarfile.open(archive, "w:xz", preset=6) as packed:
        for name in names:
            path = args.work / name
            if not path.is_file() or path.is_symlink():
                raise ValueError("Missing/linked declared evidence: " + name)
            raw = path.read_bytes()
            member = tarfile.TarInfo("raw/" + name)
            member.size, member.mtime, member.mode = len(raw), 1794009600, 0o600
            packed.addfile(member, io.BytesIO(raw))
            pins[member.name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    inventory = dict(schema="cad-pointer-state-eight-evidence-1", files=pins,
        raw_bytes=sum(x["bytes"] for x in pins.values()),
        archive=dict(path=archive.name, bytes=archive.stat().st_size,
                     sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),
        exclusions=["CAD executables/fonts", "QCAD configuration (digest only)", "DBus session address", "infrastructure logs"])
    (args.out / "INVENTORY.json").write_text(json.dumps(inventory, indent=2)+"\n", encoding="utf-8")
    print(len(pins), "records;", inventory["archive"]["bytes"], "compressed bytes")


if __name__ == "__main__":
    main()
